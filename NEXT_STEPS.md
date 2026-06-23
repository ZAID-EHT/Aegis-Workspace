# NEXT_STEPS.md — your ordered run-list (live-capture prep)

C1 is done. This pass added the **live-capture runbook** and re-verified the auth audit + draft
migration. Nothing here touched the live DB or live auth; everything below is yours to execute.
A checkpoint commit precedes this work, so it's all reversible.

**Prepared for you (safe, committed):**
- `CAPTURE_SESSION.md` — the at-the-dashboard runbook (start services, verify 0.911/15-teams, grab
  health bands, capture the 3 figures from the right cohort, crop guidance).
- `AUTH_AUDIT.md` — read-only login→callback→session→role→redirect trace + demo-day failure modes
  (verified to cover: consent Testing mode, unverified-app interstitial, redirect/origin mismatch,
  first-login race, session persistence). **No code changed.**
- `supabase/migrations/0006_staff_directory.sql` — **DRAFT, not applied.** admin/service_role-write-only
  `staff_directory` + RLS; `handle_new_user` sources role ONLY from the directory lookup or the
  hard-coded `'student'` default (never `raw_user_meta_data`); `SET search_path` pinned; begin/commit;
  before-you-apply header.
- `supabase/staff_directory_seed.example.sql` (template) + `.gitignore` rule so the real-email
  `*.local.sql` seed never commits.

---

## The four steps, in order

### 1 · Live capture session  →  follow `CAPTURE_SESSION.md`
- Start backend (`uvicorn`, with `$env:SUPABASE_URL` set) + frontend (`pnpm dev`).
- Confirm the **live** cohort by **student count = 70** (there is no "adapter active" log line — the
  runbook explains why and gives the real check).
- Run `/run` and **verify**: duplicate cosine **= 0.911** (flag if shifted), **15 teams + 1 exception
  pool**, and record the **health-band distribution** (`$r.teams | Group-Object band`).
- Capture **FIG 1 (pipeline stepper) from the LIVE run**; restart uvicorn **without** `SUPABASE_URL`
  to drop to the **seed** cohort, then capture **FIG 2 (bands 84/69/41)** and **FIG 3 (alerts STU_07 +
  STU_01/STU_05)** from the **SEED run**.

### 2 · Fill live health bands + re-render
- Put the recorded live distribution into:
  - HTML **§5.2** (leave §5.1's 84/69/41 as the seed values), and
  - `BUILD_NOTES_PDF.md` Two-run framing table — replace the **"not separately reported"** cell.
- Drop the 3 PNGs into the matching `.figbox` blocks in the HTML.
- Re-render the PDF with the headless-Chrome command at the top of `BUILD_NOTES_PDF.md`.
- If the live cosine came back **≠ 0.911**, update §2.2/§5.2 + the framing table to the real value —
  do not leave 0.911 if the run disagrees. (Invent nothing.)

### 3 · Apply auth changes (the gate — review first)
- Read the **header checklist** in `0006_staff_directory.sql`; confirm your live `profiles` columns
  match the INSERT list. Apply `0006` to a **non-prod** project first, then live.
- Add judge emails in **two** places (see `AUTH_AUDIT.md` §1, §6):
  - **Google consent screen → Test users** (the #1 demo killer if missing), and
  - **`staff_directory`** — copy `staff_directory_seed.example.sql` → `staff_directory_seed.local.sql`
    (gitignored), put real lecturer/admin emails in, run it.
- **Test login in incognito** as both: a **supervisor/lecturer** email (in the directory → expect
  `lecturer` + `approved`) and a **student** email (not in directory → expect `student` + `pending`).
- Note the `AUTH_AUDIT.md` §6 **[BLOCKER]**: the FastAPI `/admin/*` endpoints are unauthenticated —
  keep that API private during the demo, or gate it before showing Governance.

### 4 · Final commit + push
- Commit the filled-in docs, re-rendered PDF, and the 3 figures.
- `git push` to the public repo (confirm no secrets / no real emails staged — the gitignore rules
  cover `.env*` and `*_seed.local.sql`).

---

## Rollback
Everything from this run is in git behind the checkpoint commit. `0006` was **never applied**, so
there is nothing to undo in the database — `git revert` the work commit to drop the file changes.

## Hard rules honoured this pass
No live-DB writes, no migration applied, engine (`aegis/`) untouched, `.env`/`.env.local` not read,
all artifacts reversible and committed.
