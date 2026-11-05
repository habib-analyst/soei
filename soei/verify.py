"""Verification layer: keeps a claim of completion apart from proof.

Event types (all recorded in the ledger):
- edit: an agent edit to an artifact (payload: session, episode, artifact, digest)
- check: an independent check after an edit (payload: session, episode,
  artifact, digest, kind in {test, build, exec, smoke})
- todo_claim: the agent marks a to-do complete (payload: session, todo,
  artifacts edited under it)

Verdicts:
- An episode is VERIFIED iff at least one check event references the artifact
  digest produced by the LAST edit of the episode, ordered after that edit.
- A to-do is VERIFIED iff at least one check event falls between the to-do's
  last edit and its claim, referencing one of the to-do's artifacts.
- Otherwise the to-do is CLAIMED_UNVERIFIED: the claim is recorded, but it is
  never reported as verified. A claim without proof can never become Verified
  by re-assertion: only a later proof event (a check) followed by a fresh
  claim changes the verdict, and the ledger records both.
"""
from __future__ import annotations

EPISODE_CHECK_KINDS = {"test", "build", "exec", "smoke"}


def _payload(ev: dict) -> dict:
    # Accept either a ledger entry dict ({"payload": {...}}) or a bare
    # payload dict, so the layer works on ledger contents and on raw events.
    return ev["payload"] if "payload" in ev else ev


def episode_verdicts(events: list[dict]) -> list[dict]:
    """One verdict per code-editing episode, from ledger events only."""
    episodes: dict[str, dict] = {}
    order: list[str] = []
    for pos, ev in enumerate(events):
        ev = _payload(ev)
        ep = ev.get("episode")
        if ep is None:
            continue
        if ep not in episodes:
            episodes[ep] = {"episode": ep, "last_edit_pos": -1, "last_digest": None,
                            "check_after_last_edit": False}
            order.append(ep)
        rec = episodes[ep]
        kind = ev.get("type")
        if kind == "edit":
            rec["last_edit_pos"] = pos
            rec["last_digest"] = ev.get("digest")
            rec["check_after_last_edit"] = False
        elif kind == "check" and rec["last_edit_pos"] >= 0:
            if (ev.get("kind") in EPISODE_CHECK_KINDS
                    and ev.get("digest") == rec["last_digest"]):
                rec["check_after_last_edit"] = True
    out = []
    for ep in order:
        rec = episodes[ep]
        out.append({
            "episode": ep,
            "has_edit": rec["last_edit_pos"] >= 0,
            "verified": bool(rec["check_after_last_edit"]),
        })
    return out


def todo_verdicts(events: list[dict]) -> list[dict]:
    """One verdict per to-do completion claim, from ledger events only."""
    # Track per-todo: last edit position and the set of artifact digests edited.
    state: dict[str, dict] = {}
    claims: list[dict] = []
    for pos, ev in enumerate(events):
        p = _payload(ev)
        todo = p.get("todo")
        if todo is None:
            continue
        st = state.setdefault(todo, {"last_edit_pos": -1, "digests": set(),
                                     "proof": False})
        kind = p.get("type")
        if kind == "edit":
            st["last_edit_pos"] = pos
            st["digests"].add(p.get("digest"))
            st["proof"] = False
        elif kind == "check" and st["last_edit_pos"] >= 0:
            if (p.get("kind") in EPISODE_CHECK_KINDS
                    and p.get("digest") in st["digests"]):
                st["proof"] = True
        elif kind == "todo_claim":
            claims.append({
                "todo": todo,
                "has_edit": st["last_edit_pos"] >= 0,
                "verified": bool(st["proof"]),
            })
    return claims
