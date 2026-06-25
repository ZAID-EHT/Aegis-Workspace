# AEGIS

AEGIS is a capstone team platform built for the CIPHER 2.0 challenge at the Informatics Institute of Technology. It helps faculty form balanced project teams from real evidence, then monitors team health so risk is visible before a project derails.

The repository holds a working full-stack system: an evidence-weighted allocation engine (Python/FastAPI) and a role-based dashboard (Next.js) backed by Supabase. The engine has been run end-to-end on a live 70-71 student cohort, producing 15 teams plus an exception pool, and the dashboard renders that result live.

## What it does

Group projects fail in predictable ways: one person does everything, someone quietly disappears, two teams pick the same idea, or a student gets placed somewhere that does not match their skills. AEGIS handles those problems with an explainable allocation and monitoring pipeline rather than manual guesswork.

There are three product views:

- Students see their own workspace: their team, their team's health, their teammates, and the reasoning behind their placement.
- Lecturers see every team they supervise, an alert inbox for problems that need attention, and a one-click allocation run. Flags are review prompts, not automatic decisions.
- Admins see governance controls: pending approvals, recommendation overrides, the activity log, and the audit-chain integrity check.

## Key features

- Role-based experience for students, lecturers, and admins, backed by Supabase Auth and row-level security
- Evidence-weighted skill scoring, where a declared skill level is adjusted by confidence (`A = L x C`)
- Confidence tiers: `verified=1.0`, `portfolio=0.8`, `self_report=0.6`, `contradicted=0.5`
- Team formation using Abraham-Manlove SPA, then a maximin objective to lift the weakest valid team
- Duplicate-idea gate using TF-IDF cosine similarity, with proposals flagged for review at `>= 0.75`
- Health monitoring from four signals: engagement, workload balance, task completion, and milestone progress
- Hash-chained governance audit log with an integrity check over privileged actions
- Consent and data-governance model written around Sri Lanka's PDPA No. 9 of 2022
- Planned roadmap: in-workspace team messaging scoped to team members only; each team sees only its own messages, consistent with the existing object-scoped RLS model

## Current results

**LIVE run (Supabase-backed, June 25, 2026):**

- 71 student profiles returned by `/run`; the live cohort fluctuates around 70-71 students
- 15 teams formed, with 2 students in the faculty exception pool
- Duplicate proposal flag: `0.9111` cosine similarity
- Health bands: 11 healthy / 4 at risk / 0 critical
- Alerts returned: 6

**DEMONSTRATION SCENARIO (bundled seed cohort, no Supabase env):**

- 12 students, 8 projects, 3 teams, 0 exception-pool students
- Duplicate proposal flag: `0.9604` cosine similarity
- Health bands: 1 healthy / 1 at risk / 1 critical, with representative scores around 84 / 69 / 41
- Alerts returned: 5

Live figures and seed figures are intentionally separate. Do not use the live 15-team/0.911 result as a claim about the committed seed cohort, and do not use the 12-student seed result as a claim about the live Supabase cohort.

## Architecture

The system is two pieces that talk over HTTP.

**Engine (`aegis/`, Python 3.13 / FastAPI).** A pure allocation pipeline with no framework or database dependencies in its core, run through phases:

- **Phase A - scoring** (`engine/phase_a_scoring.py`): adjusts each declared skill by a confidence factor (`A = L x C`).
- **Phase B - formation** (`engine/phase_b_*.py`): duplicate-idea dedupe (`cosine >= 0.75`), Abraham-Manlove SPA, maximin team formation, and capacity-proportional task allocation.
- **Phase C - health** (`engine/phase_c_health.py`): four health signals plus ghosting, burnout, and sympathy-carry alerts over a sprint window.
- **Phase D - API** (`api/main.py`): a thin FastAPI surface that loads a cohort, runs the pipeline, and serializes the result.

A hard architectural invariant keeps the core clean and is enforced by `aegis/tests/test_architecture.py`: `aegis/engine/` imports nothing from adapters or API. All weights and thresholds live in `aegis/engine/config.py`.

The engine reads its cohort through an adapter (`aegis/adapters/`). The data source is chosen at runtime by an environment switch: if `SUPABASE_URL` is set it loads the live Supabase cohort; if unset it loads the bundled seed cohort, so offline development and tests run with zero setup. Results are cached, so restart the API to switch sources.

**Dashboard (`app/`, Next.js 15 / React 19 / Tailwind v4 / shadcn).** Role-based screens for students, lecturers, and admins. Authentication and Supabase reads go through `@supabase/ssr`, with route gating in `middleware.ts` and authorization enforced in the database via row-level security. The dashboard calls the engine API for allocation results.

**Drive/workspace integration.** Provisioning is built and proven; it creates Drive workspaces and persists the folder id. Live activity ingestion requires Google Workspace for actor attribution and is the documented production deployment path.

**Data (`supabase/`).** Postgres schema, RLS policies, and the governance/audit model are defined as ordered SQL migrations (`migrations/0001` through `0006`). `0006_staff_directory.sql` is drafted and reviewed, but applying it is a live change-management task.

## Tech stack

**Engine**

- Python 3.13, FastAPI + Uvicorn
- scikit-learn for TF-IDF cosine duplicate detection
- `matching` for Abraham-Manlove SPA
- `supabase` for the live data adapter

**Dashboard**

- Next.js 15, React 19, TypeScript
- Tailwind CSS v4, shadcn/ui-style components, lucide-react, framer-motion
- `@supabase/ssr` and `@supabase/supabase-js` for auth and data
- `googleapis` for Drive workspace/activity integration
- pnpm for package management

**Backend services**

- Supabase (Postgres, Auth, row-level security) for data and sign-in
- Google Drive API for workspace provisioning and the production activity path
- Resend for transactional email such as faculty check-ins

## Folder structure

```text
.
|-- aegis/                     Python allocation engine + API
|   |-- engine/                Pure pipeline: phases A-C + config
|   |-- api/                   FastAPI surface
|   |-- adapters/              Cohort loaders: seed, live Supabase, mock
|   |-- domain/                Core data models
|   |-- governance/            Hash-chained audit log + integrity check
|   |-- seed/                  Bundled demonstration cohort
|   `-- tests/                 pytest suite
|-- app/                       Next.js dashboard routes
|-- components/                React UI components
|-- lib/                       Frontend helpers: api client, supabase, google, nav
|-- middleware.ts              Route-gating + session refresh
|-- supabase/migrations/       Ordered SQL migrations
|-- scripts/                   Data loaders + Drive/OAuth utilities
|-- pyproject.toml             Python project + tooling
|-- package.json               Dashboard dependencies + scripts
`-- aegis-platform-v2.html     Earlier single-file UI concept
```

## Setup

You need two processes: the engine API and the dashboard.

### Requirements

- Python 3.13+ and `uv`
- Node.js 20+ and pnpm
- Optional for live data: a Supabase project, a Google Cloud project with the Drive API, and a Resend account

### 1. Run the engine API

```bash
uv venv
uv pip install -e .
uv run uvicorn aegis.api.main:app --reload
```

With no environment configured, the API serves the bundled seed cohort. To run against live Supabase data, set `SUPABASE_URL` and the service role key before starting Uvicorn; restart to switch sources.

`POST /run` executes the full A-B-C pipeline. Other endpoints: `GET /teams`, `GET /alerts`, `GET /students/{id}`, `GET /health`, and the admin/governance set (`/admin/audit`, `/admin/approvals`, `/admin/overrides`, `/admin/integrity`).

### 2. Run the dashboard

```bash
pnpm install
pnpm dev
```

In this repository path, use `pnpm dev` for verification. The project folder contains `!`, which can break a Next production build through the Webpack loader separator path issue.

## Environment variables

Copy the example file and fill it in:

```bash
cp .env.example .env.local
```

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Public Supabase key for the browser client |
| `NEXT_PUBLIC_API_URL` | URL of the engine API the dashboard calls |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-side key, never exposed to the browser |
| `SUPABASE_URL` | Set for the engine to read the live cohort; unset uses the bundled seed |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth client id |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth secret, server only |
| `GOOGLE_DRIVE_SERVICE_ACCOUNT` | Service account JSON for Drive activity polling |
| `RESEND_API_KEY` | Email delivery for faculty check-ins |
| `APP_BASE_URL` | Public URL of the deployed app |

`service_role` bypasses RLS. Keep it backend-only, never with a `NEXT_PUBLIC_` prefix. `.env*`, `secrets/`, `backups/`, and `*_seed.local.sql` are gitignored.

## Development commands

**Engine**

```bash
uv run pytest
uv run ruff check .
uv run mypy aegis
```

**Dashboard**

```bash
pnpm dev
pnpm typecheck
pnpm lint
```

Avoid relying on `pnpm build` while the project directory contains `!`; use `pnpm dev` plus `pnpm typecheck` for local verification in this checkout.

## Security and governance

- API5 remediation is applied: `/admin/*` FastAPI routes are protected by a shared `require_admin` dependency, with token-verified admin role checks on the live path.
- API1/open-redirect remediation is applied in the frontend navigation path.
- Row-level security is the load-bearing control for Supabase data. Migrations define object-scoped policies for students, lecturers, and admins.
- Role-of-record is `profiles.role`; it is not self-assignable. The database role is authoritative even if a cosmetic client metadata label differs.
- Secrets handling follows CIS Control 3 intent: service-role keys and Drive credentials are backend-only and gitignored.
- `0006_staff_directory.sql` is reviewed and hardened, but not automatically applied by this repo. Apply it only as a deliberate live migration.

See `SECURITY_REVIEW.md`, `AUTH_AUDIT.md`, `RLS_VERIFICATION.md`, `APPLY_0006_REVIEW.md`, and `BACKEND_BACKLOG.md` for evidence, live runbooks, and deferred findings.

## Deferred backlog

The following are post-submission items, not demo blockers at the current cohort scale:

- `S2`: Governance fallback should fail closed instead of masking a live audit failure with seed governance data.
- `C2`: Large Supabase/PostgREST reads need pagination so institutional-scale tables cannot silently truncate.
- `D1`: Drive provisioning should be idempotent and return an existing workspace when one already exists.
- `H1`: Migrations should be atomic and managed by a reproducible migration runner.
- `H3`: Migrations should become the single source of truth for live schema, with drift and down-migrations resolved.

## Team

AEGIS was built by Team Amateurs for CIPHER 2.0 at the Informatics Institute of Technology.

## License

Released under the MIT License. See `LICENSE`.
