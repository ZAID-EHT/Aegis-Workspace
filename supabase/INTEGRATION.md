# Connecting the backend to Supabase

The dashboard never talks to Supabase directly. The flow is:

```
Supabase tables ──(repo_db, service_role)──► engine.pipeline ──► /run ──► dashboard
```

So "integrating Supabase" = the FastAPI backend reads the cohort from Supabase instead of
`seed.json`. The frontend is unchanged. The engine stays pure (the DB lives in an adapter).

> ⚠️ I could not run any of this here (your project, your keys). Everything below is built and
> the engine is proven to run on your 70 mock students locally — but **you** run the load + serve
> steps against your Supabase. If anything errors, paste the message and I'll patch it.

## Prerequisites
- Migrations applied **in order**: `0001_base_schema.sql`, `0002_governance.sql`,
  **`0003_engine_fields.sql`** (new — adds the engine fields: project skills/slots/hours,
  student availability/preferences, the sim-day activity columns, and `team_monitoring`).
- Python deps: `pip install -e .` (or `pip install supabase fastapi uvicorn scikit-learn matching`).

## Step 1 — credentials (`.env`, never committed)
```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service_role key>   # backend only — bypasses RLS
```
The service_role key stays server-side; it never gets a `NEXT_PUBLIC_` prefix.

## Step 2 — load data into the tables
Your mock set is students only, so the loader also generates matching projects, activity, and
monitoring (the same data the engine was verified on):
```
python scripts/load_supabase.py
# -> loaded: 70 students, 15 projects, 280 skills, 346 activity events, 15 monitoring rows
```
Student ids map to stable UUIDs (`students.id` is `uuid`). To reload, clear first in the SQL editor:
```sql
truncate team_monitoring, activity_log, skills_declared,
         team_members, tasks, alerts, teams, students, projects cascade;
```

## Step 3 — run the API against Supabase
The API auto-detects the source: **Supabase when `SUPABASE_URL` is set, else the bundled seed.**
```
python -m uvicorn aegis.api.main:app --port 8000
```
`POST /run` now reflects the live Supabase cohort. The dashboard (`pnpm dev`) shows it with **zero
frontend changes**.

## Verify
```
curl -s -X POST http://localhost:8000/run | python -c "import sys,json;d=json.load(sys.stdin);print(len(d['teams']),'teams,',len(d['student_profiles']),'students')"
# expect ~15 teams, 70 students
```

## What's proven vs. what you run
- ✅ Proven locally: the engine runs end-to-end on the 70 mock students (15 teams, sensible
  health bands + alerts, the P_02/P_03 duplicate flags), and the row→Cohort mapping (unit-tested).
- ▶️ You run (needs your keys): applying `0003`, `scripts/load_supabase.py`, and the live `/run`.

## Next (separate step, optional)
Write-back: persist computed teams/alerts to Supabase so the governance triggers (audit log) fire.
Say the word and I'll add a `repo_db.save_result()` + an opt-in write at the end of `/run`.
