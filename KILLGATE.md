# Project #109 `soei` — KILLGATE (gate verdicts)

**Verdict: PASS — all locked bars met. No kill triggered.**

## Gate order (verified by filesystem mtime, UTC)

1. G1 author-code recheck — PASSED 2026-11-01 ~22:20 PKT (see G1_STATUS.md for
   the full machine-readable sweep; first full-text sweep for #109).
2. PILOT_PREREG.md — written BEFORE any pilot number.
3. Pilot (seed 109001, n=60 main + 20 benign) — PASSED all pilot gates P1–P7.
4. PREREG.md — locked AFTER the pilot, BEFORE the headline run.
5. Headline (seed 109002, n=300 main + 100 benign, 2000 bootstrap resamples)
   — ALL locked bars PASS (see below).
6. Tests: 14/14 pytest pass. Determinism: headline.json and
   headline_rerun.json byte-identical, SHA-256
   b711533e9e8fb3a26d4927fa527a1fa9db94eb970b30ea7622efad787c5c6773.

## Headline bars (PREREG.md decision rule: ANY failure KILLS)

| Bar | Result (95% CI) | Verdict |
|-----|-----------------|---------|
| D1 unverified-episode share, lower CI > 0.20 | 0.4497 [0.4138, 0.4838] | PASS |
| D2 proofless-to-do share, lower CI > 0.30 | 0.5593 [0.5186, 0.5987] | PASS |
| M1 tamper detection = 1.00 | 1.00 [1.00, 1.00], n=300 attacked ledgers | PASS |
| M2 replay detection = 1.00 | 1.00 [1.00, 1.00], n=300 attacked ledgers | PASS |
| M-trunc truncation detection = 1.00 | 1.00 [1.00, 1.00], n=300 attacked ledgers | PASS |
| M3 proofless claims marked Verified = 0.00 | 0.00 [0.00, 0.00], n=592 proofless claims | PASS |
| M4 unverified-episode flag rate, lower CI >= 0.95 | 1.00 [1.00, 1.00] (baseline: 0 by construction) | PASS |
| B1 benign episode Verified, lower CI >= 0.98 | 1.00 [1.00, 1.00], n=100 sessions | PASS |
| B1 benign to-do Verified, lower CI >= 0.98 | 1.00 [1.00, 1.00], n=100 sessions | PASS |

Counts: 1,490 episodes (665 unverified), 1,053 to-do claims (592 proofless),
300/300 clean ledgers verified.

## Timestamp correction (honesty note)

PREREG.md's header text says "Locked: 2026-11-01 ~22:35 PKT" — that was a
wall-clock estimate error by the builder. The filesystem mtime of PREREG.md is
22:24 PKT, BEFORE results/headline.json (22:24 PKT, seconds later) and AFTER
results/pilot.json. The lock ORDER (pilot prereg < pilot < prereg < headline)
is verified by mtime; PREREG.md was NOT edited after the headline run (doing
so would have destroyed its evidentiary value), so the ~22:35 text stands
uncorrected in that file and is corrected here instead.

## #100 re-examination trigger (standing)

If a download location, repo URL, DOI, or Zenodo record for the authors'
research/soei/prototype/ package (or any author Soei package) is located
later, the G1 PASS must be re-examined and this build re-gated before any repo
request. No repo was created, no push was made, no repo request is made by
this builder — repo creation is the orchestrator's call after verification.

## Scope honesty

Synthetic analog only: deterministic scripted agents, zero LLM calls, no real
coding-agent transcripts. The paper's figures (23.4% unverified episodes,
57.8% proofless to-dos, on 45 real sessions) are context only, never claimed
as reproduced. Truncation detection for tail removal requires the auditor to
hold the head hash recorded at session close (standard hash-chain property,
stated in the code docs); middle-drop truncation is detected without it.
