# Gate report — Phase A · Verify

**Status:** ✅ complete · audit hook green · reviewers run, no blocking findings open
**Date:** 2026-06-20

## What was built
- **`engine/phase_a_scoring.py`** — pure scoring:
  - `adjusted(decl)` = **Â = L × C** (verified 1.0 / portfolio 0.8 / self_report 0.6 / contradicted 0.5).
  - `skill_matrix(student)` — adjusted score per discipline (strongest wins on duplicates).
  - `fit(student, project)` = **100·[0.50·SkillMatch + 0.30·AvailMatch + 0.20·RoleMatch]**.
    SkillMatch caps each skill at "requirement met" (`SKILL_TARGET`), critical skills ×2;
    AvailMatch = slot overlap ÷ required (capped 1, vacuous→1); RoleMatch 1.0/0.6/0.3.
- **`engine/phase_b_dedupe.py`** — `duplicate_flags(projects)`: TF-IDF (sklearn, english stop
  words) + cosine; pairs **≥ 0.75 flagged** (not blocked); deterministic order; empty-corpus safe.
- **`engine/config.py`** — added Phase A tunables: `SKILL_TARGET`, `CRITICAL_SKILL_MULT`,
  `ROLE_MATCH`, `ROLE_DISCIPLINE`, `SIMILARITY_PRECISION`. Still the only home for constants.
- **`adapters/repo_seed.py`** — loud vocab validation: a typo'd discipline/confidence_basis
  now raises `ValueError` with student/project context instead of silently scoring 0.
- **`seed/seed.json`** — P_03 rewritten as a true near-duplicate of P_02 (cosine 0.96; the
  original 0.58 sat below the gate and never fired).

## Test results
```
ruff check aegis → All checks passed!
mypy aegis       → Success: no issues found in 16 source files
pytest -q        → 28 passed
```
Golden coverage: Dunning-Kruger 5/5-no-evidence → 2.5; verified 5 → 5.0; portfolio/self-report
tiers; **exact pinned Fit values** (87.5 / 90.83 — catch weight-swaps & scaling bugs);
inflated-claim loses when the discounted skill is what the project needs; P_02/P_03 flagged;
**gate calibration** (engineered pair > 0.90, all others < 0.60, threshold sits in the gap);
loader rejects unknown vocab.

## Reviewers (read-only, parallel — via general-purpose; named subagents not registered here)
Resolved:
- **BLOCKING-grade** dedupe tests couldn't catch threshold de-calibration → added `test_gate_calibration` pinning the band.
- **SHOULD-FIX** every Fit assertion was an inequality (a swapped skill/avail weight stayed green) + a tautological `fit==fit` test → replaced with exact pinned Fit values.
- **SHOULD-FIX** typo'd discipline/basis silently became 0-coverage → loader now validates against `DISCIPLINES`/`CONFIDENCE_BASES`.
- empty `required_skills` returned 0.0 (penalised) → now 1.0 (vacuously satisfied), consistent with AvailMatch.
- non-deterministic dedupe tie order → secondary sort key `(-sim, a, b)`.
- stray `round(…,4)` literal → `config.SIMILARITY_PRECISION` (no-magic-numbers rule).
- empty/stopword-only abstracts could crash with "empty vocabulary" → guarded, returns [].
- float `== ` consistency → `pytest.approx` throughout.

## Note for viva (doc inconsistency, not a code bug)
`docs/AEGIS_README_v3.md` says the cosine gate "locks the portal and forces a change" (hard-block)
in one place and "flagged for faculty review rather than hard-blocked" in another. The build plan
mandates **flag-for-review with an override path**, which is what the code implements. Reconcile
the README line before submission.

## Next — Phase B (Match & form)
Abraham–Manlove SPA (students→projects) + oversubscription cascade (Priority = Fit +
RareSkillBonus); maximin team formation (seed → greedy → swap → exception pool); capacity-based
task allocation with U ≤ 1.2 guard. New dep: `matching`. `database-reviewer` not needed (no SQL).
