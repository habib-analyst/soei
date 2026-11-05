"""Headline/pilot runner: builds ledgers, runs both arms, attacks, bootstraps.

Arms:
- baseline (no-ledger naive recorder): marks every to-do claim complete and
  performs no verification, so it flags 0 unverified episodes by construction.
  Disease rates D1/D2 are measured against generator ground truth.
- ledger arm: every event appended to a hash-chained ledger; verdicts come
  from the verification layer reading the ledger only.

Attack tests (one tamper, one replay, one truncation per main-cohort session):
- tamper: one stored payload mutated without rehashing.
- replay: one existing entry appended a second time.
- truncation: tail entries dropped, verified against the head recorded at
  session close; plus a middle-drop verified without an expected head.

Output JSON is fully deterministic: no timestamps, sorted keys, fixed seeds.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys

from .harness import generate_cohort
from .ledger import Ledger, verify
from .verify import episode_verdicts, todo_verdicts


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _bootstrap_ci(rng: random.Random, values: list[float], n_resamples: int,
                  ) -> tuple[float, float]:
    """Percentile 95% CI of the mean under resampling of the given units."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    means = []
    for _ in range(n_resamples):
        means.append(_mean([values[rng.randrange(n)] for _ in range(n)]))
    means.sort()
    lo = means[int(0.025 * n_resamples)]
    hi = means[min(n_resamples - 1, int(0.975 * n_resamples))]
    return (lo, hi)


def analyse_session(events: list[dict]) -> dict:
    """Run one session through the ledger arm; return verdicts + ledger."""
    ledger = Ledger()
    for ev in events:
        ledger.append(ev)
    clean = verify(ledger)
    payloads = [e.payload for e in ledger.entries]
    return {
        "ledger": ledger,
        "clean_ok": clean["ok"],
        "clean_problems": clean["problems"],
        "episode_verdicts": episode_verdicts(payloads),
        "todo_verdicts": todo_verdicts(payloads),
    }


def attack_ledger(ledger: Ledger) -> dict:
    """Tamper / replay / truncation attacks on copies of one ledger."""
    out: dict = {}
    # Tamper: mutate a middle payload without rehashing.
    tampered = Ledger(entries=copy.deepcopy(ledger.entries))
    if tampered.entries:
        mid = tampered.entries[len(tampered.entries) // 2]
        mid.payload["artifact"] = "src/tampered.py"
    out["tamper_detected"] = not verify(tampered)["ok"]
    # Replay: append an existing entry a second time.
    replayed = Ledger(entries=copy.deepcopy(ledger.entries))
    if replayed.entries:
        replayed.entries.append(copy.deepcopy(ledger.entries[1]))
    out["replay_detected"] = not verify(replayed)["ok"]
    # Truncation (tail): drop tail entries, check against recorded head.
    truncated = Ledger(entries=copy.deepcopy(ledger.entries[:-2]))
    out["truncation_detected"] = not verify(
        truncated, expected_head=ledger.head_hash)["ok"]
    # Truncation (middle drop): remove a middle entry, no expected head.
    dropped = Ledger(entries=copy.deepcopy(ledger.entries))
    if len(dropped.entries) > 3:
        del dropped.entries[len(dropped.entries) // 2]
    out["middle_drop_detected"] = not verify(dropped)["ok"]
    return out


def run(seed: int, n_main: int, n_benign: int, n_resamples: int) -> dict:
    main = generate_cohort(seed, n_main)
    benign = generate_cohort(seed + 1, n_benign, profile="benign")

    # Per-session unit values for session-level bootstrap.
    d1_units, d2_units, m4_units = [], [], []
    m3_units: list[float] = []  # 1.0 if a proof-less claim was marked Verified
    tamper_units, replay_units, trunc_units = [], [], []
    b1_ep_units, b1_todo_units = [], []
    n_episodes = n_todos = 0
    n_unverified_episodes = n_proofless_todos = 0
    n_clean_chains = 0

    for sess in main:
        res = analyse_session(sess["events"])
        assert res["clean_ok"], f"clean ledger failed: {res['clean_problems']}"
        n_clean_chains += 1
        ep_v = {v["episode"]: v["verified"] for v in res["episode_verdicts"]}
        td_v = {v["todo"]: v["verified"] for v in res["todo_verdicts"]}
        # D1: episode unverified share (verifier verdict == ground truth).
        ep_truth = sess["truth"]["episodes"]
        for ep, t in ep_truth.items():
            assert ep_v[ep] == t["verified"], f"episode verdict mismatch {ep}"
        n_episodes += len(ep_truth)
        unverified = [ep for ep, t in ep_truth.items() if not t["verified"]]
        n_unverified_episodes += len(unverified)
        d1_units.append(len(unverified) / len(ep_truth))
        flagged = [ep for ep in unverified if not ep_v[ep]]
        m4_units.append(len(flagged) / len(unverified) if unverified else 1.0)
        # D2 + M3: to-do claims.
        td_truth = sess["truth"]["todos"]
        proofless = [td for td, t in td_truth.items() if not t["proof"]]
        n_todos += len(td_truth)
        n_proofless_todos += len(proofless)
        d2_units.append(len(proofless) / len(td_truth))
        for td in proofless:
            assert td in td_v, f"missing to-do verdict {td}"
            m3_units.append(1.0 if td_v[td] else 0.0)
        # Attacks.
        atk = attack_ledger(res["ledger"])
        tamper_units.append(1.0 if atk["tamper_detected"] else 0.0)
        replay_units.append(1.0 if atk["replay_detected"] else 0.0)
        trunc_units.append(1.0 if atk["truncation_detected"]
                           and atk["middle_drop_detected"] else 0.0)

    for sess in benign:
        res = analyse_session(sess["events"])
        ep_v = {v["episode"]: v["verified"] for v in res["episode_verdicts"]}
        td_v = {v["todo"]: v["verified"] for v in res["todo_verdicts"]}
        b1_ep_units.append(_mean([1.0 if v else 0.0 for v in ep_v.values()]))
        b1_todo_units.append(_mean([1.0 if v else 0.0 for v in td_v.values()]))

    rng = random.Random(seed + 999)
    results = {
        "seed": seed,
        "n_main_sessions": n_main,
        "n_benign_sessions": n_benign,
        "n_episodes": n_episodes,
        "n_todos": n_todos,
        "n_unverified_episodes": n_unverified_episodes,
        "n_proofless_todos": n_proofless_todos,
        "n_clean_chains_verified": n_clean_chains,
        "d1_unverified_episode_share": _mean(d1_units),
        "d1_ci95": _bootstrap_ci(rng, d1_units, n_resamples),
        "d2_proofless_todo_share": _mean(d2_units),
        "d2_ci95": _bootstrap_ci(rng, d2_units, n_resamples),
        "m1_tamper_detection_rate": _mean(tamper_units),
        "m1_ci95": _bootstrap_ci(rng, tamper_units, n_resamples),
        "m2_replay_detection_rate": _mean(replay_units),
        "m2_ci95": _bootstrap_ci(rng, replay_units, n_resamples),
        "m_truncation_detection_rate": _mean(trunc_units),
        "m_truncation_ci95": _bootstrap_ci(rng, trunc_units, n_resamples),
        "m3_proofless_marked_verified_share": _mean(m3_units),
        "m3_ci95": _bootstrap_ci(rng, m3_units, n_resamples),
        "m4_unverified_episode_flag_rate": _mean(m4_units),
        "m4_ci95": _bootstrap_ci(rng, m4_units, n_resamples),
        "b1_benign_episode_verified_share": _mean(b1_ep_units),
        "b1_episode_ci95": _bootstrap_ci(rng, b1_ep_units, n_resamples),
        "b1_benign_todo_verified_share": _mean(b1_todo_units),
        "b1_todo_ci95": _bootstrap_ci(rng, b1_todo_units, n_resamples),
        "baseline_flagged_unverified_episodes": 0,
        "bootstrap_resamples": n_resamples,
    }
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n-main", type=int, default=300)
    ap.add_argument("--n-benign", type=int, default=100)
    ap.add_argument("--n-resamples", type=int, default=2000)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    results = run(args.seed, args.n_main, args.n_benign, args.n_resamples)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, sort_keys=True, indent=2)
        fh.write("\n")
    print(json.dumps(results, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
