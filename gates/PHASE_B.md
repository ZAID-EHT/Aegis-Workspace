# Gate report — Phase B · Match & form (the hero feature)

**Status:** ✅ complete · audit hook green · reviewers run, BLOCKING fixed, no findings open
**Date:** 2026-06-20

## What was built
- **`engine/phase_b_match.py`** — Abraham–Manlove **SPA** via the `matching` library.
  One supervisor per project; each project ranks its applicants by
  **Priority = Fit + RareSkillBonus** (+15 for a scarce critical skill). Student-optimal
  solve gives a stable assignment; oversubscription cascade is intrinsic. Returns
  `Assignment(by_project, unmatched)`; `unmatched` derived from the full roster (no lost students).
- **`engine/phase_b_teams.py`** — maximin formation. `team_score` (6 README components,
  config-weighted, 0..100); `maximin_swap` local search that accepts a 1-for-1 swap **only if
  it raises the minimum team score** and breaks no hard constraint (size, critical coverage,
  **and SPA acceptability — members stay on a ranked project**); `form_teams` routes
  under/over-sized + unmatched to the exception pool.
- **`engine/phase_b_tasks.py`** — capacity-share allocation (`Task_Share = cap/Σcap`) with the
  **U ≤ 1.2 overload guard** (caps utilisation, reports shed `unallocated_hours`); surfaces
  `zero_capacity` members instead of dropping them.
- **`config.py`** — `TEAM_SCORE_WEIGHTS`, `PREF_SAT`(+default), `MAX_SWAP_ITERATIONS`,
  `RARE_SKILL_SCARCITY`. Still the single home for constants.
- **`seed.json`** — preferences re-engineered to funnel into **3 full teams**; per-sprint
  `total_hours`; `activity_log` rebuilt so carrier(STU_01)+carried(STU_05) share team P_01.

## Demonstrated on the seed (the on-camera moments)
- **Oversubscription cascade:** 5 students rank P_01 (cap 4); STU_07 cascades to P_05.
- **Rare-skill seeding:** UX is the only scarce critical skill → STU_03 & STU_12 seed into P_04.
- **Maximin lifts the weakest team:** min team score **85.75 → 95.29** (swaps STU_11↔STU_08).
- **Overload guard:** P_05 (cap 26, 36 sprint h) → U capped at 1.2, 4.8 h flagged unallocated;
  P_01/P_04 healthy (U ≤ 1.0).
- **Exception pool:** empty on the full seed (all 12 placed); populated via the rigged unit test.

## Test results
```
ruff check aegis → All checks passed!
mypy aegis       → Success: no issues found in 22 source files
pytest -q        → 44 passed
```
New golden tests: SPA places all into 3 full teams; cascade; rare-skill bonus value; maximin
raises the minimum (+ golden post-swap memberships, so a balanced-SPA regression fails loudly);
**maximin keeps every member on a ranked project**; exception pool populates; overload guard
trips on P_05; proportional split sums to sprint hours; utilisation uniform when not overloaded.

## Reviewers (read-only, parallel — via general-purpose)
- **BLOCKING (fixed):** `maximin_swap` enforced size + critical coverage but not SPA
  acceptability — a swap could strand a student on a project they never ranked, violating the
  locked "maximin must not break SPA hard constraints" decision (passed before only by seed
  luck). `_hard_ok` now rejects any member on an unranked project; new invariant test added.
- **Fixed:** zero-total-capacity team dropped members silently → now reports them at U=0 with the
  sprint as unallocated; added `zero_capacity` field for visibility.
- **Fixed:** seed-fragile maximin test → pinned golden memberships.
- **Fixed:** stale `_meta`/docstring (P_05 cap 27/U1.33 → 26/U≈1.385 post-swap).
- Verified clean by the hunter: warning suppression can't hide a dropped student (real
  inconsistencies raise loudly); `unmatched` complete; cascade correct; swaps never accept a
  hard-constraint break; overload-guard test fails if the guard is removed.

## Deferred (non-blocking, documented)
- `maximin_swap` returns no convergence signal if it ever hit `MAX_SWAP_ITERATIONS` (converges
  in ≤2 iters at prototype scale; revisit if cohorts grow).
- Warning filter matches on message text — pinned to `matching` 1.4.x in pyproject.

## Next — Phase C (Monitor)
4-component health score → Healthy/At-Risk/Critical; 3-tier ghosting (STU_07→Tier 3);
sympathy-carry (STU_05, ≥0.95) + burnout (STU_01, ≥2× avg) → Alert objects. All off the seeded
`activity_log`, no live Drive.
