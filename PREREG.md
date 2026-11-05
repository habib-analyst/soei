# Project #109 `soei` — HEADLINE PREREGISTRATION (LOCKED before the headline run)

**Locked:** 2026-11-01 ~22:35 PKT, AFTER the pilot (seed 109001, n=60+20) and
BEFORE any headline number. Headline seed 109002 (fresh), n_main = 300
sessions, n_benign = 100 sessions, paired session-level bootstrap with 2000
resamples, 95% percentile CIs on every bar.
**Lock order (by mtime):** PILOT_PREREG.md < pilot run < PREREG.md (this file)
< headline run. No amendments after locking; no re-seed, re-tune, re-split,
or bar-weakening after a failure.

## Design (synthetic analog of arXiv 2610.39468's measurement)

Scripted coding-agent sessions (deterministic, zero LLM calls): each session is
a flat event stream of edits, independent checks (test/build/exec/smoke), and
to-do completion claims, generated under a diligent/typical/sloppy profile
mixture. Two arms run on the SAME sessions (paired):
- Baseline (no-ledger naive recorder): marks every claim complete, performs no
  verification, flags 0 unverified episodes by construction.
- Ledger arm: every event appended to a SHA-256 hash-chained ledger; a
  verification layer reads the ledger only and returns per-episode and
  per-to-do verdicts (Verified vs ClaimedUnverified).
A separate benign cohort (all-diligent profile, p_check=1.00,
p_premature=0.00) measures clean-completion handling.

## Locked bars — ANY failure KILLS the project

Disease bars (reproduce the paper's disease structure synthetically):
- D1: share of code-editing episodes ending with no independent check after
  the last edit. BAR: lower 95% CI bound > 0.20.
- D2: share of to-dos marked complete with no proof between last edit and
  claim. BAR: lower 95% CI bound > 0.30.

Mechanism bars (hash-chained ledger + verification layer vs no-ledger baseline):
- M1 (tamper): tamper-detection rate over attacked ledgers. BAR: exactly 1.00
  with lower 95% CI bound = 1.00.
- M2 (replay): replay-detection rate over attacked ledgers. BAR: exactly 1.00
  with lower 95% CI bound = 1.00.
- M-trunc (truncation): detection rate over tail-truncation (against the head
  recorded at session close) AND middle-drop attacks. BAR: exactly 1.00 with
  lower 95% CI bound = 1.00.
- M3 (claim/proof separation): share of proof-less completion claims the
  ledger arm marks Verified. BAR: exactly 0.00 with upper 95% CI bound = 0.00.
- M4 (detection coverage): share of truly-unverified episodes the ledger arm
  flags (baseline flags 0 by construction). BAR: lower 95% CI bound >= 0.95.

Benign bound (ledger must not degrade clean completion handling):
- B1: on the benign cohort, episode Verified share AND to-do Verified share.
  BAR: both lower 95% CI bounds >= 0.98.

## Decision rule

PASS iff D1, D2, M1, M2, M-trunc, M3, M4, and B1 (both parts) ALL meet their
bars. ANY locked bar fails -> KILL: write KILLED.md + negative PAPER.md, NO
LinkedIn draft, NO repo request. Determinism requirement (not a bar, but a
validity condition): the headline run repeated byte-identically
(headline_rerun.json identical bytes to headline.json) and the SHA-256 digest
of results/headline.json is reported; a determinism failure invalidates the
run and it must be re-run before any PASS claim.

## Scope honesty (carried into PAPER.md)

Scripted analog only. The paper's figures (23.4% / 57.8% on 45 real sessions)
are context only, never claimed as reproduced. What is claimed on PASS: on
synthetic sessions exhibiting the same disease structure, the ledger +
verification layer deterministically detects tampering/replay/truncation,
separates claim from proof, and does not degrade clean completion handling.
