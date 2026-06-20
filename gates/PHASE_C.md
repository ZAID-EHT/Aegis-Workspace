# Gate report — Phase C · Monitor (+ pipeline)

**Status:** ✅ complete · audit hook green · reviewers run, both BLOCKING fixed, none open
**Date:** 2026-06-21

## What was built
- **`engine/phase_c_health.py`** — all off the seeded `activity_log` (+ per-team `monitoring`):
  - **4-component health score** (task_completion 0.30, workload_balance 0.25, engagement 0.30,
    milestone 0.15) → bands Healthy ≥75 / At-Risk 50–74 / Critical <50.
  - **3-tier ghosting** (Tier 3 ≥10 zero days, Tier 2 ≥6, Tier 1 ≥40% drop with an
    established-footprint gate); window anchored to a config sprint length.
  - **Sympathy-carry** (`carry_ratio` ≥ 0.95 → carrier identified) and **burnout**
    (footprint ≥ 2× team average).
  - `alerts()` → triaged `Alert` list (severity by trigger).
- **`engine/pipeline.py`** — orchestrates A→B→C into one `AllocationResult` (the Phase D API
  will just wrap this). Stamps each `Team.health_score`.
- **domain** — `TeamMonitoring`; `TaskAllocation` moved into domain (so `AllocationResult` can
  hold it without breaking the engine→domain layering); `AllocationResult.task_allocations`.
- **seed** — per-team `monitoring` block + finalized `activity_log` engineered for a 3-band spread.

## Demonstrated on the seed (one `run()`)
- **Health bands:** P_04 **Healthy 83.9** · P_01 **At-Risk 69.0** (carry imbalance + burnout) ·
  P_05 **Critical 41.2** (ghost + overload + low completion).
- **Ghosting Tier 3:** STU_07 (zero footprint, 14 days) — the only ghost.
- **Sympathy-carry:** STU_05 carried 100% by teammate STU_01 (≥0.95).
- **Burnout:** STU_01 (footprint ≥ 2× P_01 average).
- Exactly **5 alerts** — the engineered cases, no false-positive noise.

## Test results
```
ruff check aegis → All checks passed!
mypy aegis       → Success: no issues found in 26 source files
pytest -q        → 63 passed
```
New tests: band spread + ranges; component renormalisation on missing monitoring; empty-team →
0/critical; ghosting Tier-3 on seed + **boundary tests (exactly 6 / 9 / 10)** + window-anchor
test + steady-light-not-ghosted; sympathy ratio + carrier + only-STU_05; burnout flags carrier;
alerts cover all engineered cases; **full A→B→C pipeline** end-to-end + all-conflict-types +
determinism; seed activity-tagging coherence.

## Reviewers (read-only, parallel)
Two **BLOCKING** silent-failure traps found and fixed:
- **Missing-monitoring asymmetry** — a team with no monitoring entry silently capped at 70
  (task_completion→0 but milestone→1.0). Now the absent components are dropped and the surviving
  weights renormalised; "no data" never reads as failure or success.
- **Ghost window rode the global max sim_day** — trimming unrelated late events would shrink the
  window and silently downgrade a Tier-3 ghost. Window now anchored to `MONITORING_WINDOW_DAYS`.

Also fixed: `Team.health_score` was never set (now stamped in the pipeline); burnout alert text
hardcoded "2x" (now `config.BURNOUT_MULT`); empty-team short-circuit; ghosting boundary + window
coverage; seed activity-tagging coherence test.

Documented (not changed): workload_balance measures activity-footprint variance, not
task-allocation utilisation (which is uniform by construction) — deviation noted in config.
Burnout uses the README's include-self team average (matches the spec's worked example).

## Status vs build plan
Phases 0, A, B, C complete — **the engine spine runs end-to-end on seed** (`pipeline.run`). The
55 algorithm marks are now covered and golden-tested.

## Next — Phase D (API & dashboard) ← the website
FastAPI (`POST /run`, `GET /teams`, `GET /alerts`, `GET /students/{id}`) over `pipeline.run`,
then the Next.js dashboard using `design-system/` (AppShell + PipelineStepper wired to `/run`,
HealthRing, EvidenceBar, alert inbox). Make the C=0.5 correction and conflict panel visible.
