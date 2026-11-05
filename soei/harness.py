"""Synthetic scripted-agent session generator (deterministic, no LLM calls).

A session is a flat, ordered event stream. Event payloads carry a "type" and
the fields the verification layer needs. Content is simulated: an artifact's
digest is SHA-256 of "path:version", so digests behave like real content
hashes (a new edit = a new digest) without any real files.

Profiles (scripted behaviours, drawn per session):
- diligent: checks after edits with p=0.90, premature claims with p=0.05
- typical:  p=0.55 / p=0.25
- sloppy:   p=0.20 / p=0.55
- benign (clean cohort only): p=1.00 / p=0.00

Disease structure (mirrors the paper's measurement, synthetically):
- D1: a code-editing episode ends with no independent check after its last edit.
- D2: a to-do is marked complete with no proof (check on its artifacts)
  between its last edit and its claim. A "premature" claim is emitted before
  the check that follows the last edit, so the check lands AFTER completion
  and does not count as proof -- the claim/proof separation the paper diagnoses.
  Note the asymmetry this creates: a premature to-do's episode can still be
  VERIFIED (its check exists, after the last edit) while the to-do claim
  itself is UNVERIFIED (no proof before the claim). That asymmetry is the
  point: claim and proof are different objects.

generate_session returns (events, truth) where truth is generator-side ground
truth kept OUT of the ledger payloads: per episode, whether a check follows
its last edit; per to-do, whether proof precedes its claim. The verifier never
sees truth; the run compares verifier verdicts against it.
"""
from __future__ import annotations

import hashlib
import random

CHECK_KINDS = ("test", "build", "exec", "smoke")

PROFILES = {
    "diligent": {"p_check": 0.90, "p_premature": 0.05},
    "typical": {"p_check": 0.55, "p_premature": 0.25},
    "sloppy": {"p_check": 0.20, "p_premature": 0.55},
    "benign": {"p_check": 1.00, "p_premature": 0.00},
}

MIXTURE = (("diligent", 0.25), ("typical", 0.50), ("sloppy", 0.25))


def _digest(artifact: str, version: int) -> str:
    return hashlib.sha256(f"{artifact}:v{version}".encode("utf-8")).hexdigest()[:16]


def _pick_profile(rng: random.Random) -> str:
    u = rng.random()
    acc = 0.0
    for name, w in MIXTURE:
        acc += w
        if u < acc:
            return name
    return MIXTURE[-1][0]


def generate_session(rng: random.Random, session_id: str,
                     profile: str | None = None) -> tuple[list[dict], dict]:
    """Return (event payloads in order, ground truth)."""
    if profile is None:
        profile = _pick_profile(rng)
    params = PROFILES[profile]
    events: list[dict] = []
    truth: dict = {"episodes": {}, "todos": {}}
    n_episodes = rng.randint(3, 7)
    versions: dict[str, int] = {}

    def edit(artifact: str, episode: str, todo: str) -> str:
        versions[artifact] = versions.get(artifact, 0) + 1
        digest = _digest(artifact, versions[artifact])
        events.append({"type": "edit", "session": session_id, "episode": episode,
                       "todo": todo, "artifact": artifact, "digest": digest})
        return digest

    def check(episode: str, todo: str, digest: str) -> None:
        events.append({"type": "check", "session": session_id, "episode": episode,
                       "todo": todo, "artifact": None,
                       "digest": digest, "kind": rng.choice(CHECK_KINDS)})

    # Partition episodes into to-dos of 1-2 episodes each.
    todo_groups: list[list[str]] = []
    ep = 0
    while ep < n_episodes:
        size = rng.randint(1, 2) if ep + 1 < n_episodes else 1
        todo_groups.append([f"{session_id}/ep{k}" for k in range(ep, ep + size)])
        ep += size

    for gi, group in enumerate(todo_groups):
        todo = f"{session_id}/todo{gi}"
        premature = rng.random() < params["p_premature"]
        last_digest: str | None = None
        last_episode: str | None = None
        last_has_check = False
        for j, episode in enumerate(group):
            artifact = f"src/module{rng.randint(0, 4)}.py"
            for _ in range(rng.randint(1, 3)):
                last_digest = edit(artifact, episode, todo)
            has_check = rng.random() < params["p_check"]
            truth["episodes"][episode] = {"verified": has_check}
            is_last = j == len(group) - 1
            if is_last:
                last_episode = episode
                last_has_check = has_check
                # Premature: the claim goes out BEFORE the check that follows
                # the last edit, so the check is not proof for this claim.
                if premature:
                    events.append({"type": "todo_claim", "session": session_id,
                                   "episode": episode, "todo": todo,
                                   "artifact": None, "digest": last_digest})
                    if has_check:
                        check(episode, todo, last_digest)
                else:
                    if has_check:
                        check(episode, todo, last_digest)
                    events.append({"type": "todo_claim", "session": session_id,
                                   "episode": episode, "todo": todo,
                                   "artifact": None, "digest": last_digest})
            else:
                if has_check:
                    check(episode, todo, last_digest)
        truth["todos"][todo] = {"proof": (last_has_check and not premature)}
    return events, truth


def generate_cohort(seed: int, n_sessions: int,
                    profile: str | None = None) -> list[dict]:
    """Return [{"session", "profile", "events", "truth"}, ...]."""
    rng = random.Random(seed)
    cohort = []
    for i in range(n_sessions):
        sid = f"s{i:04d}"
        prof = profile if profile is not None else _pick_profile(rng)
        events, truth = generate_session(rng, sid, profile=prof)
        cohort.append({"session": sid, "profile": prof, "events": events,
                       "truth": truth})
    return cohort
