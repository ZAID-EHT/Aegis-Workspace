# MORNING_RUNLIST.md — your ordered hands-on steps (demo day)

Everything below needs **you, at the running system** — that's why the overnight pass stopped here.
Risky steps are flagged **⚠️ LIVE**. Nothing overnight touched the live DB, live auth, or applied
`0006`; all of it is committed and reversible. Work top to bottom.

> Produced for you overnight (read these first): `APPLY_0006_REVIEW.md` (0006 pre-apply pack),
> `ENGINE_AUDIT.md` (correctness audit — all **post-submission**, none demo-blocking),
> re-rendered `CIPHER2_theametuers_Documentation.pdf`.

---

## 1 · Review the 0006 apply pack — eyeball the two invariants  *(read-only, ~5 min)*
Open `APPLY_0006_REVIEW.md` and confirm, against the verbatim excerpts:
- **(a)** `handle_new_user` sets `role` from **only** the `staff_directory` lookup or the hard-coded
  `'student'` — `raw_user_meta_data` is never read.
- **(b)** `staff_directory` is **admin/service_role write-only** (RLS on, single `is_admin()` policy,
  default-deny for everyone else).
- The hardening table (SECURITY DEFINER, `set search_path`, `begin/commit`, if-exists guards,
  dependency guard, role CHECK) is all ✔.
- **Gate:** confirm live `profiles` columns are `(id, email, role, cohort_id, status)`. If they
  differ (H3 drift), **reconcile the INSERT list before applying** — do not apply against a mismatch.

## 2 · Apply 0006 to live  ⚠️ LIVE — WATCH IT  *(this is the risky one)*
> This modifies live auth (ISO 27001 A.12.1.2 change management). Snapshot/backup first if you can.
1. Apply to a **NON-PROD** Supabase project first → expect "Success" → sanity-check `staff_directory`
   exists, RLS on, trigger `on_auth_user_created` present.
2. Decide on **section 4** (the `auth.users` trigger re-assertion) — keep it (recommended) or comment
   it out. See the pack.
3. Apply to **LIVE** (next migration after `0005`).
4. Seed staff from a **gitignored** source: copy `supabase/staff_directory_seed.example.sql` →
   `staff_directory_seed.local.sql`, real lecturer/admin emails in, run it. **Never commit real emails.**
5. **Set your own demo admin so you don't lock out of Governance** (Supabase SQL editor — `auth.uid()`
   is NULL there, so the `enforce_role_immutable` trigger allows it):
   ```sql
   update public.profiles set role='admin', status='approved'
   where email='<your-demo-google-account>' returning id, email, role, status;
   ```
   Zero rows back → log in once via Google first (creates the profile), then re-run.

## 3 · Incognito login tests  ⚠️ LIVE  *(immediately after 0006)*
In fresh incognito windows, confirm the directory-sourced role assignment:
- **Staff email** (in `staff_directory`) → lands `role=lecturer`/`admin`, `status=approved`, sees
  cohort views (not "pending").
- **Normal email** (not in directory) → lands `role=student`, `status=pending`.
- **Signup still works** end-to-end (no error on the callback; profile row created).
- *(optional escalation spot-check)* a student JWT cannot `POST` to `staff_directory` (expect RLS
  denial) — curl in `APPLY_0006_REVIEW.md` step 9.

## 4 · Capture session — fill live numbers + figures  *(eyes on the dashboard)*
Drive with `CAPTURE_SESSION.md`. Backend **with `SUPABASE_URL` set** (live) + `pnpm dev`.
- Confirm **live cohort = 70 students**, `/run` → duplicate cosine **0.911**, **15 teams + 1
  exception pool**. If cosine ≠ 0.911, update §2.2/§5.2 + the framing table to the real number.
- Record the **health-band distribution** and drop it into HTML **§5.2** + the `BUILD_NOTES_PDF.md`
  framing table's **"not separately reported"** cell (overnight left this cell as-is for you).
- Capture **FIG 1 from the LIVE run** (pipeline stepper), then restart uvicorn **without**
  `SUPABASE_URL` (seed) and capture **FIG 2 + FIG 3 from the SEED run**. (Labels already in the HTML:
  FIG1→live §5.2, FIG2/3→seed §5.1.)
- Re-render the PDF (headless-Chrome command at the top of `BUILD_NOTES_PDF.md`).
  *Already verified clean overnight: 4 pages, glyphs `Â/×/≥/→` render, all three `[FIG]` boxes intact.*

## 5 · Final commit + push
- Stage the filled docs, the re-rendered PDF, and the 3 figures. Confirm nothing sensitive is staged
  (`.env*`, `secrets/`, `*_seed.local.sql` are all gitignored — re-verified clean overnight).
- `git push`.

## 6 · T-minus-30 demo checklist  *(run 30 min before the panel)*
- [ ] **Every judge email in BOTH places:** Google consent **Test users** *and* `staff_directory`
      with the right role. (Missing from Test users = "access blocked", the #1 killer.)
- [ ] **Redirect URIs match the demo origin** (Google client → Supabase callback; Supabase Redirect
      URLs include the exact `/auth/callback` you present from — `localhost` ≠ `127.0.0.1`).
- [ ] **Two fallback accounts you control** (one lecturer, one admin) via
      `scripts/seed_demo_users.py` — password login, skips Google entirely. Confirm both log in now.
- [ ] **Governance panel loads as admin:** sign in as your `role='admin'` account → `/admin` renders
      (the API now enforces the gate — a non-admin/no token gets 403/401 **by design**, not a bug).
- [ ] **Brief judges** on the "Google hasn't verified this app → Advanced → Continue" click, or lead
      with the password fallback accounts.

---

### Notes from the overnight pass (FYI — no action required tonight)
- **`ENGINE_AUDIT.md` flagged one thing worth knowing for the viva:** `scripts/load_supabase.py` has
  a NameError (`_sid` undefined) and **cannot run as written** — it does **not** affect the demo (the
  live cohort is already loaded; the dashboard reads it fine), but don't try to re-run that loader
  live. Everything else in the audit is post-submission hardening.
- **Docs reconciled to reality:** §4 states the `/admin/*` gate is remediated with **401/403/200
  test evidence**. I did **not** claim "live browser-verified" — that's step 6 above, your call to
  confirm in the browser. Once you've seen the panel load as admin, you can add that claim honestly.
