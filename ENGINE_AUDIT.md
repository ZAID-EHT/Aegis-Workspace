# ENGINE_AUDIT.md — independent correctness audit (read-only)

**Scope:** `aegis/engine/` (all phases), `aegis/adapters/repo_db.py`, `aegis/adapters/repo_mock.py`,
`scripts/load_supabase.py`. Reviewed against **ASVS V5 (validation)** and **CWE**. **No fixes
applied — report only.** Each finding is marked **KNOWN** (already in `BACKEND_BACKLOG.md`) or
**NEW**. Severity: 🔴 high · 🟠 medium · 🟡 low.

**Headline:** the **engine core is clean** — div-by-zero, empty-data, and "no-data" paths are
consistently guarded (details in §C). The real findings concentrate in the **adapter/script edge**,
where the live path (`repo_db`) and the loader (`load_supabase`) lack validation the mock path has.
The single most important item: **`scripts/load_supabase.py` cannot run — it calls an undefined
`_sid()` (NameError on first use).**

---

## A · NEW findings

### 🔴 N1 — `load_supabase.py` references an undefined `_sid()` → script crashes (CWE-457/758)
`scripts/load_supabase.py:78,112,129,145,149` call `_sid(...)`, but **no `_sid` is defined or
imported anywhere in the repo** (only `_pid` is defined, at `:29`, and it is **never used**).
Running the documented command `python -m scripts.load_supabase` raises
`NameError: name '_sid' is not defined` at **line 78**, before any write. The loader is currently
non-functional as written.
- **Impact:** the repo's documented "load the cohort into Supabase" path does not execute. (The live
  70-student cohort must have been loaded by some other means; this script can't reproduce it.)
- **Likely cause:** an incomplete rename — `_pid(project_id)` was probably meant to be the
  student-id mapper `_sid(student_id)` (or a sibling `_sid` was dropped). Note `_pid` builds a
  `uuid5`, matching what the student rows need.
- **Fix (do not apply):** define `_sid(student_id) -> str` (e.g. `str(uuid.uuid5(NAMESPACE, student_id))`)
  and either use `_pid` for project ids or delete it. Add a `python -m scripts.load_supabase`
  smoke step to CI so a broken loader fails loudly.

### 🟠 N2 — `rows_to_cohort` accepts engine inputs with no validation (ASVS V5.1, CWE-20)
`aegis/adapters/repo_db.py:46–53,55–70` map live rows straight into domain objects with bare casts
and **no range/vocabulary checks** — unlike the mock loader, which clamps. Three concrete gaps:
- **`declared_level` not clamped to 1–5** (`repo_db.py:50` `float(r["declared_level"])`). `repo_mock`
  clamps (`repo_mock.py:81` `min(5, max(1, …))`); `repo_db` does not. A DB value of `9` or `-2`
  flows unclamped into `Â = L × C` (`phase_a_scoring.py:17`) and **silently skews** every downstream
  score, fit, and team formation. **Divergent validation between the two load paths** is itself a
  correctness risk.
- **`confidence_basis` not validated** (`repo_db.py:51`). An unknown/typo'd basis (e.g.
  `"self-report"` vs `"self_report"`) is not caught at load; it later **KeyErrors** at
  `config.CONFIDENCE[decl.confidence_basis]` (`phase_a_scoring.py:17`), crashing the **entire run**
  on one bad row. Loud, but it takes the whole `/run` down rather than isolating the row.
- **`preferred_role` not validated** (`repo_db.py:67`). `models.py:29` comments "validated at load",
  but `repo_db` does not — an unknown role **silently** scores `RoleMatch = 0.3`
  (`phase_a_scoring.py:64–71`) instead of being rejected.
- **Fix (do not apply):** validate at the adapter boundary — clamp `declared_level`, assert
  `confidence_basis ∈ CONFIDENCE_BASES` and `preferred_role ∈ ROLES ∪ {None}`, and either skip+log
  or fail-fast with the offending id. Share one validator across `repo_db`/`repo_mock`/`repo_seed`.

### 🟠 N3 — `save_result` write-back is non-atomic → a mid-write failure wipes the live allocation (CWE-662)
`aegis/adapters/repo_db.py:154–186`: the opt-in persistence (`AEGIS_PERSIST=1`) does
`delete alerts → delete teams → insert teams → insert members → insert alerts` as **separate,
un-transactioned PostgREST calls**. If any insert fails after the deletes (network blip, constraint,
the 500-row batch loop at `:173`), the prior allocation is **already deleted** and the new one is
**partial** — the live DB is left in a torn state with no rollback.
- Distinct from backlog **H1** (which is about *migration* atomicity); this is the *write-back* path.
- **Fix (do not apply):** wrap the reset+write in a single transaction (an RPC/`pg` function, or
  Supabase transaction), or write to a staging set and swap. At minimum surface the failure
  (relates to **H2**, below).

### 🟡 N4 — `load_supabase.py` `_pid` defined-but-unused + projects loaded with raw string ids (CWE-561, id-mapping drift)
`scripts/load_supabase.py:29` defines `_pid` (a `uuid5` mapper) whose docstring says
*"projects.id is uuid"*, but it is **never called**: projects are upserted with the **raw** id
(`:84` `"id": p.project_id` → `"P_01"`), and `team_monitoring`/`preferred_projects` also carry raw
`P_*` strings. Students, by contrast, are intended to map to UUIDs (via the missing `_sid`). The
result is an **abandoned/half-applied UUID scheme**: an unused uuid mapper for projects, raw strings
actually written, and a divergent (broken) uuid path for students — exactly the "forward/inverse
mapping diverging" risk. If `projects.id` is a `uuid` column, the raw-string upsert at `:84` also
fails type-wise.
- **Fix (do not apply):** pick one scheme. Either keep `P_*` text ids everywhere (delete `_pid`), or
  map both students and projects through uuid5 (use `_pid`, define `_sid`) — consistently across the
  upsert, the FK columns, and `preferred_projects`.

### 🟡 N5 — `repo_mock._activity` indexes `students[0..2]` without a length guard (CWE-129)
`aegis/adapters/repo_mock.py:134–136` reads `students[0]`, `students[1]`, `students[2]` to script the
ghost/carried/carrier demo. A mock file with **< 3 students** raises `IndexError`. Harmless at the
fixed 12-student mock, but brittle if the mock JSON is trimmed.
- **Fix (do not apply):** guard `if len(students) < 3: return []` (or scale the scripted cases).

---

## B · KNOWN findings confirmed still present (in `BACKEND_BACKLOG.md`)

| ID | Finding | Location (confirmed) | Backlog row |
|---|---|---|---|
| **C2** | 1000-row PostgREST cap; reads fetch all with no paging → silent tail-drop past ~1000 rows | `repo_db.py:129` (`fetch` `select("*")`), `:210–217` (`load_db_audit`), `:233–240` (`load_pending_profiles` — same pattern, worth adding to the row) | C2 |
| **S1** | `set_profile_status` returns success even on **zero rows matched** (bad id) | `repo_db.py:243–247` (no `returning`/affected-count check) | S1 |
| **S2** | Governance endpoints fall back to **seed** on any live error → integrity badge fail-open | `api/main.py` (admin handlers) — *out of this audit's file set but the `except` paths it depends on originate here* | S2 |
| **H2** | Write-back swallows errors (`try/except` just prints `[write-back] skipped`) → failed persist invisible | `api/main.py:62–69` (calls `repo_db.save_result`) | H2 |

> N2/N3/N5 are **NEW** (not in the backlog). C2 note: `load_pending_profiles` (`repo_db.py:230`) has
> the same unpaginated `select` as the two sites the backlog already lists — fold it into C2.

---

## C · Engine edge-cases reviewed — guarded (no action)

The engine handles the edge cases Task 3 asked about **defensively**; recording the evidence so the
viva can claim it:
- **Empty cohort / no teams:** `min_team_score(..., default=0.0)` (`phase_b_teams.py:113`); an empty
  team scores `0.0/critical` (`phase_b_teams.py:55–56`, `phase_c_health.py:77`). `team_score`'s
  cohort-mean is only reached when teams exist (teams require members), so the `fmean` over
  `cohort.students` (`phase_b_teams.py:97`) is non-empty when called.
- **< 2 projects / single project:** dedupe returns `[]` (`phase_b_dedupe.py:27`); empty-vocabulary
  corpus is caught (`:32–34`).
- **Division-by-zero:** guarded everywhere checked — engagement `if expected else 0`
  (`phase_c_health.py:48`), workload `mean<=0` (`:54`), burnout `mean<=0` (`phase_c_health.py:156`),
  carry `if not on_tasks` (`:134`), task share `total_capacity<=0` (`phase_b_tasks.py:32`) and
  per-member `capacity_hours>0` (`:50`), team workload `mean_cap>0` (`phase_b_teams.py:91`),
  experience `if cohort_mean else 1.0` (`:99`).
- **Preferences → nonexistent project:** filtered before SPA (`phase_b_match.py:66–70`); the maximin
  swap refuses to strand a student on an unranked project (`phase_b_teams.py:128`).
- **Unknown `preferred_role` inside the engine:** degrades to `RoleMatch 0.3` rather than crashing
  (`phase_a_scoring.py:62–71`) — safe *in the engine*; the gap is that the **adapter** doesn't reject
  it (see N2).
- **Determinism:** dedupe and SPA ranking sort with explicit tie-breaks
  (`phase_b_dedupe.py:49`, `phase_b_match.py:82`) — reproducible runs.

The engine's weakness is therefore **not** its arithmetic; it is that **`repo_db` trusts the database**
to have already enforced the domain invariants the mock loader enforces in code (N2).

---

## D · Severity-ranked action order (post-submission)
1. **N1** 🔴 — fix the `_sid` NameError so the loader runs at all (and add a smoke test).
2. **S2** 🟠 (KNOWN) — integrity fail-open is the only finding that *misreports a governance control*.
3. **N2** 🟠 — validate adapter inputs; close the mock-vs-live validation gap.
4. **N3** 🟠 — make `save_result` atomic (or stage-and-swap).
5. **C2 / S1 / H2** 🟠 (KNOWN) — paging, zero-row update check, observable write-back.
6. **N4 / N5** 🟡 — settle the id scheme; guard the mock activity indexing.

*Read-only audit. No engine, adapter, or script code was modified.*
