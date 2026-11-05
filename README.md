# soei — project #109

Open reimplementation (synthetic analog) of arXiv 2610.39468, "Soei:
Structured Observability of Evidence and Intent for Multi-Agent AI Software
Engineering". The paper studies 45 real coding-agent sessions and proposes an
acknowledgement-aware event schema, a hash-chained local evidence ledger, a
W3C-PROV-aligned evidence graph, and a verification layer that separates an
agent's claim of completion from proof.

## What this build is — and is not

This is an independent, from-scratch, stdlib-only reimplementation of the
ledger + verification-layer mechanism, evaluated on synthetic scripted
sessions that exhibit the same disease structure the paper measures. It
reproduces none of the paper's real-session figures.

## What it shows

On synthetic coding-agent sessions, a no-ledger baseline leaves 45.0% of
episodes unverified and 55.9% of to-do completions proofless, and flags
nothing. The hash-chained evidence ledger plus verification layer detects
tampering, replay, and truncation deterministically (100% on the seeded
suite), separates completion claims from proof, and keeps the benign
verified share at 1.0 — clean completion handling is not degraded.

## Run

- Tests: `python3 -m pytest tests/ -q`
- Experiment entry point: `soei/run.py`; measured results in `results/`
  (`pilot.json`, `headline.json`, seed-fixed and rerun-verified).

## Scope honesty

Scripted analog only; synthetic sessions, no real repositories, no LLM
agents. $0, CPU only, deterministic.
