# CAPTURE_SESSION.md — live capture + verification runbook

Run this **once, in order, at the live dashboard**. It covers everything that needs the running
system: start services, verify the live numbers against the PDF, grab the health-band distribution,
and capture the three figures from the correct cohort. PowerShell one-liners are copy-paste ready.

> Reality check baked in (verified against `aegis/api/main.py`):
> - There is **no "Supabase adapter active" log line** in the backend. The adapter is chosen
>   *silently* on `SUPABASE_URL` (`main.py:46`). **Confirm the live cohort by the student count
>   (70 live vs 12 seed), not by a log message.**
> - `_cohort()`/`_result()` are `@lru_cache`d and the env is read on the **first** `/run`. The repo
>   does **not** auto-load `.env` for the API. So switching seed↔live = **restart uvicorn** with or
>   without `$env:SUPABASE_URL` set — you cannot flip cohorts inside a running process.

---

## 0 · One-time setup (before the session)
- Backend deps: `pip install -e .` (or `pip install supabase fastapi uvicorn scikit-learn matching`).
- Frontend deps: `pnpm install`.
- Frontend env (`.env.local`): `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  (for login), and optionally `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000`).
- Have a login ready: a seeded judge/admin account (`scripts/seed_demo_users.py`) or your own —
  `/dashboard` is gated by `middleware.ts`, so you must be signed in to screenshot it.
- Live data already loaded into Supabase (`scripts/load_supabase.py` → 70 students / 15 projects).

---

## 1 · Start the LIVE backend (70-student cohort)

Open **Terminal A** (backend). Set the live env in THIS shell, then start uvicorn:
```powershell
$env:SUPABASE_URL = "https://<your-ref>.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "<service_role key>"   # backend only — bypasses RLS
python -m uvicorn aegis.api.main:app --port 8000
```
Leave it running. (Do **not** set `AEGIS_PERSIST=1` — that opt-in write-back replaces the live
allocation. Capture is read-only.)

Open **Terminal B** (frontend):
```powershell
pnpm dev    # Next.js on http://localhost:3000
```

### Confirm the LIVE adapter is active (the real check — no log string exists)
In **Terminal C** (verification):
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://localhost:8000/run
"students=$($r.student_profiles.Count)  teams=$($r.teams.Count)  exception_pool=$($r.exception_pool.Count)"
```
- **Expect `students=70`** → live adapter is active. If it says `students=12`, you are on the **seed**
  cohort: `SUPABASE_URL` wasn't set in Terminal A — stop uvicorn, set it, restart, re-run.

---

## 2 · Verify the live numbers against the PDF, and record the health bands

Still in **Terminal C**, against the same `$r` (it's one cached run, so all reads agree):

**(a) Live duplicate cosine — must match the PDF's 0.911; FLAG if it shifted**
```powershell
$r.duplicate_flags | ForEach-Object { "{0}/{1} = {2:N3}" -f $_.project_a, $_.project_b, $_.similarity }
```
- Expect a pair at **≈ 0.911** (compare to 3 dp). **If it is not 0.911**, the live data changed —
  do **not** silently edit: note the new value and update §2.2/§5.2 + `BUILD_NOTES_PDF.md` to match,
  then re-render. (Invent nothing; the PDF must equal what `/run` actually returns.)

**(b) Team count — must be 15 teams + a non-empty exception pool**
```powershell
"teams=$($r.teams.Count)  exception_pool_members=$($r.exception_pool.Count)"
```
- Expect **`teams=15`** and **`exception_pool_members ≥ 1`** (that's the "+ 1 exception pool"). Flag
  any deviation.

**(c) Health-band distribution — fills the "not separately reported" cell**
```powershell
$r.teams | Group-Object band | ForEach-Object { "{0}: {1}" -f $_.Name, $_.Count }
```
- This prints e.g. `healthy: 9 / at_risk: 4 / critical: 2` (the band keys are `healthy`,
  `at_risk`, `critical` — from `aegis/api/main.py` / dashboard). **Copy this exact distribution** —
  it is the live health-band figure to drop into:
  - HTML **§5.2** (replace nothing in §5.1's 84/69/41 — those stay seed), and
  - `BUILD_NOTES_PDF.md` Two-run framing table, the **"not separately reported"** cell.

**(d) One-shot record block (paste the whole thing — produces a copy-ready summary)**
```powershell
$r = Invoke-RestMethod -Method Post -Uri http://localhost:8000/run
"=== LIVE /run $(Get-Date -Format s) ==="
"students        : $($r.student_profiles.Count)   (expect 70)"
"teams           : $($r.teams.Count)   (expect 15)"
"exception_pool  : $($r.exception_pool.Count)   (expect >= 1)"
"duplicates      :"; $r.duplicate_flags | ForEach-Object { "  {0}/{1} = {2:N3}  (expect ~0.911)" -f $_.project_a,$_.project_b,$_.similarity }
"health bands    :"; $r.teams | Group-Object band | ForEach-Object { "  {0}: {1}" -f $_.Name,$_.Count }
```

---

## 3 · Capture the three figures — each from the CORRECT cohort

| Figure | Content | Cohort to run from | Why |
|---|---|---|---|
| **FIG 1** Pipeline stepper | intake → de-dup → match → form → monitor | **LIVE (70-student)** | shows production scale; de-dup step should read **0.911** |
| **FIG 2** Team health bands | P_04 84 / P_01 69 / P_05 41 | **SEED (12-student)** | those exact scores are engineered seed values |
| **FIG 3** Alert inbox | STU_07 ghost + STU_01/STU_05 carry & burnout | **SEED (12-student)** | STU_ IDs exist only in the seed cohort |

### 3a · FIG 1 — capture now, while LIVE is running
- In the browser (`http://localhost:3000`), sign in, open **/dashboard**, click **Run allocation**,
  and screenshot the **pipeline stepper** strip. The de-dup stage reflects the 0.911 pair.

### 3b · Switch to the SEED cohort for FIG 2 + FIG 3 (the env-switch)
The cohort is fixed at the first `/run` and cached, and there's no dotenv — so **restart the backend
without `SUPABASE_URL`**:
1. In **Terminal A**: `Ctrl+C` to stop uvicorn.
2. Clear the live env in that shell (or just open a fresh terminal that never set it):
   ```powershell
   Remove-Item Env:SUPABASE_URL -ErrorAction SilentlyContinue
   Remove-Item Env:SUPABASE_SERVICE_ROLE_KEY -ErrorAction SilentlyContinue
   python -m uvicorn aegis.api.main:app --port 8000
   ```
3. Confirm you're on seed:
   ```powershell
   (Invoke-RestMethod -Method Post -Uri http://localhost:8000/run).student_profiles.Count   # expect 12
   ```
4. Back in the browser, **/dashboard → Run allocation** (frontend unchanged — it just calls the API).
   - **FIG 2:** screenshot the **team health bands** (84 / 69 / 41).
   - **FIG 3:** open **/alerts** and screenshot the **alert inbox** (STU_07 ghost; STU_01/STU_05
     carry + burnout).

> Switch back to live afterward only if you need to: stop uvicorn, re-set `$env:SUPABASE_URL`
> (+ service role), restart.

---

## 4 · Resolution / crop guidance (so the 3 figures look consistent in the PDF)

The figure boxes sit at ~**170 mm** content width on A4. Match all three so they don't look mismatched:
- **Browser width:** set the window to a fixed **1440 px** for all three captures (don't resize between).
- **Zoom:** browser at **100%**; OS display scaling consistent. Use a **2× DPI / "Retina"** capture
  (DevTools device toolbar at DPR 2, or a HiDPI screen) so text stays crisp when scaled into print.
- **Theme:** **light mode** (toggle in the app) — the PDF is light; dark cards print muddy.
- **Format:** **PNG** (lossless; sharp text/edges). Avoid JPEG for UI.
- **Crop:** tight to the card/panel bounds with an **even ~12 px margin** on all sides; same margin
  for all three. Don't include browser chrome, the sidebar, or the right rail unless it's the subject.
- **Aspect:** keep the three within a similar landscape ratio (roughly **16:7 to 16:9**). The boxes
  are ≥150 px tall in the layout, so a wide-but-short crop drops in cleanly.
- **Target pixels:** aim for **≥ 1600 px wide** source so the image isn't upscaled at print size.
- Save as `fig1_pipeline_live.png`, `fig2_bands_seed.png`, `fig3_alerts_seed.png` for an obvious
  drop-in order.

To place them: edit the matching `.figbox` block in `CIPHER2_theametuers_Documentation.html`
(insert an `<img src="..." style="width:100%">`), then re-render with the headless-Chrome command
in `BUILD_NOTES_PDF.md`.

---

## 5 · Session output (hand this to the doc edit in NEXT_STEPS step 2)
By the end you should have written down:
- [ ] Live duplicate cosine (= 0.911, or the flagged new value).
- [ ] `teams=15`, `exception_pool` count.
- [ ] Live health-band distribution (`healthy:N / at_risk:N / critical:N`).
- [ ] Three PNGs captured from the cohorts in the §3 table.
