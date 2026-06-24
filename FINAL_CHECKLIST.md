# FINAL_CHECKLIST.md — your remaining hands-on steps (in order)

Everything below needs **you at the running system / browser**. Live-DB steps are flagged
**[LIVE-TOUCH]** — apply those watching; everything is reversible. Engine logic, live auth, and
the DB were not changed by the assistant; **0006 stays unapplied**.

**State going in:** code + docs pushed to `origin/master` (M1 role-of-record, N1 open-redirect
guard, sample-data banner, §4/§6 security docs, re-rendered 5-page PDF). Servers expected up:
frontend `http://localhost:3000`, backend `:8000` in live mode (`/run` → 70 students / 15 teams).
Demo accounts (password): `judge.student` / `judge.lecturer` / `judge.admin` @aegis.test.

---

## a. Browser-verify M1 (the role-of-record proof)
1. **Student:** sign in as `judge.student@aegis.test` → lands on **My workspace** showing only their
   own team + team health + their details. No Teams/Alerts/Governance nav. (Hard-refresh
   Ctrl+Shift+R if a stale tab is open.)
2. **Admin:** sign in as `judge.admin@aegis.test` → full monitoring (Overview/Teams/Alerts/Pipeline)
   **and** Governance loads.
3. **M1 proof — the key test:** an account whose role is set **only** in `profiles.role='admin'`
   (no `user_metadata.role`) must now land on the **admin** view (pre-M1 it wrongly showed the
   student view). Use your Google demo admin, or temporarily clear an account's metadata role.
4. **Banner check:** stop the backend (Ctrl+C in the uvicorn window) and reload a dashboard page →
   the amber **"Showing sample data — live API unavailable"** banner must appear (never silently
   shows seed as a live run). Restart the backend afterward.

## b. Two-device two-role simultaneous test (dress rehearsal)
- Device/browser 1: `judge.student` → workspace. Device/browser 2: `judge.admin` → monitoring +
  governance. Confirm both work **at the same time** with no errors. This is the demo flow.

## c. Glance at /admin governance — note live vs seed (for the viva)
- As admin, open **Governance**. Note whether audit/approvals/integrity show **live** data or the
  **seed** fallback (S2 fail-open: on a live read error it silently serves seed; an empty live
  `audit_log` shows integrity `verified=false`). Know which you're presenting; it won't error.

## d. Capture / verify figures
- Confirm against the live run: duplicate **0.911**, **15 teams + 1 exception pool**, and the
  health-band split (e.g. healthy/at-risk/critical).
- Figures: **FIG 1** from the live 70-student run (§5.2, de-dup reads 0.911); **FIG 2 & FIG 3**
  from the 12-student seed run (§5.1). Drop PNGs into the `.figbox` blocks in
  `CIPHER2_theametuers_Documentation.html`.
- **Live health-band cell** in §5.2 / the `BUILD_NOTES_PDF.md` framing table is still
  **"not separately reported"** — fill it only if you decide to publish the live bands.
- **Re-render the PDF if anything changed:**
  ```powershell
  & "C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --disable-gpu `
    --no-pdf-header-footer "--user-data-dir=$env:TEMP\aegis-chrome-pdf" --virtual-time-budget=8000 `
    "--print-to-pdf=C:\Aasims Stuff\AEGIS engine\AEGIS.!\CIPHER2_theametuers_Documentation.pdf" `
    "C:\Aasims Stuff\AEGIS engine\AEGIS.!\CIPHER2_theametuers_Documentation.html"
  ```
  (Chrome prints an "exit 13 / Multiple targets" warning *after* writing — benign; verify the PDF
  timestamp/size updated.)

## e. [LIVE-TOUCH] demo-admin role-set — ONLY if demoing via Google login
If the admin you present with is a Google account (not the `judge.admin` password account), set its
authoritative role on the live DB (Supabase SQL editor — `auth.uid()` is null there, so the
role-immutable trigger allows it):
```sql
update public.profiles set role='admin', status='approved'
where email='<your-demo-google-admin>' returning id, email, role, status;
```
Zero rows back → log in once via Google first (creates the profile), then re-run. With M1 in place
this alone is enough for that account to land on the admin view.

## f. [OPTIONAL — skip for the demo] Apply 0006 (directory auto-roling)
Manual roles already work, so **0006 is not needed for the demo**. Apply it only if you want
signup-time role assignment from `staff_directory` — and then **[LIVE-TOUCH]**, watching, with a DB
backup in place first (`python scripts/backup_db.py`), non-prod before live. See
`APPLY_0006_REVIEW.md`.

## g. Final commit + push
- If you changed figures/§5.2/PDF: stage them, confirm nothing sensitive is staged
  (`.env*`, `secrets/`, `backups/`, `*_seed.local.sql`, demo scripts are gitignored), commit, and
  `git pull --rebase origin master` then `git push origin master`.

---
**T-minus checks:** judge emails in Google consent **Test users** *and* (if using directory roling)
`staff_directory`; redirect URIs match the demo origin (`localhost` ≠ `127.0.0.1`); both fallback
password accounts log in; Governance loads as admin.
