# Project #109 `soei` — PILOT PREREGISTRATION (written BEFORE any pilot number)

**Date:** 2026-11-01 ~22:25 PKT. G1 PASSED 2026-11-01 ~22:20 PKT (see G1_STATUS.md).
**Purpose:** verify the build is not vacuous before locking headline bars. Pilot seed
109001, pilot n = 60 scripted sessions. Headline uses a FRESH seed (109002) and
bars locked in PREREG.md AFTER the pilot, BEFORE the headline run.

## What the pilot tests (no headline bars are set here)

- P1 — Generation volume: the harness produces >= 100 code-editing episodes and
  >= 100 to-do completion claims across the 60 pilot sessions.
- P2 — Non-vacuous disease: baseline (ground-truth audit of the generated event
  log) unverified-episode share in (0.05, 0.95) AND to-do-no-proof share in
  (0.05, 0.95). A share of 0 or 1 means the generator is degenerate, not that
  the disease is reproduced.
- P3 — Ledger integrity: a clean ledger verifies; a tampered ledger (one payload
  byte changed), a replayed ledger (one entry duplicated), and a truncated
  ledger (tail entries removed) are ALL detected by verify().
- P4 — Claim/proof separation: the verification layer marks ZERO proof-less
  completion claims as Verified in the pilot.
- P5 — Benign sanity: on the pilot's clean slice (sessions where every episode
  has an independent check and every to-do has proof), the ledger arm marks
  >= 0.95 of to-dos Verified (pilot-level sanity only; the headline B1 bound is
  locked separately in PREREG.md).
- P6 — Determinism: running the pilot generator twice with seed 109001 yields
  byte-identical event logs.
- P7 — Tests: the pytest suite passes in full.

## Pilot PASS rule

Pilot PASSES iff P1–P7 all hold. On pilot FAIL: stop, diagnose, fix the
generator/mechanism (not the bars — no headline bars exist yet), and re-run the
pilot. Pilot numbers NEVER feed the headline result; the headline is a fresh
seed and its bars are locked in PREREG.md before it runs.

## Scope honesty (carried into PREREG.md and PAPER.md)

This is a synthetic, scripted analog only: deterministic scripted agents, no LLM
calls, no real coding-agent transcripts. The paper's figures (23.4% unverified
episodes, 57.8% to-dos without proof, on 45 real sessions) are CONTEXT ONLY and
are never claimed as reproduced. What is claimed: that a hash-chained evidence
ledger + verification layer, run on synthetic sessions exhibiting the same
disease structure, deterministically detects tampering/replay and separates
claim from proof without degrading clean completion handling.
