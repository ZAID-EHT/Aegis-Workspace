"""FastAPI surface over the engine pipeline.

Thin HTTP layer: it loads the seed cohort (an adapter concern), runs the pure
``engine.pipeline``, and serialises the result. No engine logic lives here —
the API may import engine + adapters; the engine never imports the API.

Endpoints:
  POST /run             -> run the full A->B->C pipeline, return everything
  GET  /teams           -> teams + health
  GET  /alerts          -> triaged alert inbox
  GET  /students/{id}   -> adjusted skill profile (Â = L x C) + placement rationale
"""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aegis.adapters.repo_governance import load_governance
from aegis.adapters.repo_seed import load_cohort
from aegis.domain.models import AllocationResult, Cohort
from aegis.engine import config
from aegis.engine.phase_a_scoring import fit
from aegis.engine.pipeline import run
from aegis.governance.audit import verify
from aegis.governance.models import GovernanceData

app = FastAPI(title="AEGIS", version="1.0.0", description="Capstone allocation engine API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── cached engine run (seed is static; one run serves every endpoint) ────────
@lru_cache(maxsize=1)
def _cohort() -> Cohort:
    # Live Supabase when configured (SUPABASE_URL set); otherwise the bundled seed,
    # so offline dev and tests keep working with zero setup.
    if os.environ.get("SUPABASE_URL"):
        from aegis.adapters.repo_db import load_db_cohort

        return load_db_cohort()
    return load_cohort()


@lru_cache(maxsize=1)
def _result() -> AllocationResult:
    # Seed is static, so one run serves every request. INVARIANT: callers must treat
    # the returned object as read-only — all serialisers below only read it.
    return run(_cohort())


@lru_cache(maxsize=1)
def _governance() -> GovernanceData:
    # Static seed; one load serves every request. Read-only invariant as in _result().
    return load_governance()


# ── response models ──────────────────────────────────────────────────────────
class SkillView(BaseModel):
    discipline: str
    declared: float
    confidence: float
    adjusted: float
    basis: str
    corrected: bool  # True when the C=0.5 Dunning-Kruger correction fired


class StudentProfile(BaseModel):
    student_id: str
    name: str
    skills: list[SkillView]
    team_id: str | None
    project_id: str | None
    fit: float | None
    rationale: str


class MemberView(BaseModel):
    student_id: str
    name: str
    utilisation: float | None
    overloaded: bool


class TeamView(BaseModel):
    team_id: str
    project_id: str
    project_title: str
    members: list[MemberView]
    health_score: float
    band: str
    components: dict[str, float]
    unallocated_hours: float


class AlertView(BaseModel):
    severity: str
    trigger_type: str
    detail: str
    team_id: str | None
    student_id: str | None


class DuplicateView(BaseModel):
    project_a: str
    project_b: str
    similarity: float


class PipelineStage(BaseModel):
    key: str
    label: str
    hint: str


class RunResponse(BaseModel):
    stages: list[PipelineStage]
    teams: list[TeamView]
    alerts: list[AlertView]
    duplicate_flags: list[DuplicateView]
    exception_pool: list[str]
    student_profiles: list[StudentProfile]


_STAGES = [
    PipelineStage(key="verify", label="Verify", hint="Â = L × C"),
    PipelineStage(key="dedupe", label="Dedupe", hint="cosine ≥ 0.75"),
    PipelineStage(key="match", label="Match", hint="SPA"),
    PipelineStage(key="form", label="Form", hint="maximin"),
    PipelineStage(key="monitor", label="Monitor", hint="health + alerts"),
]


# ── serialisation helpers ────────────────────────────────────────────────────
def _skill_views(cohort: Cohort, student_id: str) -> list[SkillView]:
    student = next(s for s in cohort.students if s.student_id == student_id)
    views: list[SkillView] = []
    for decl in student.skills:
        factor = config.CONFIDENCE[decl.confidence_basis]
        views.append(
            SkillView(
                discipline=decl.discipline,
                declared=decl.declared_level,
                confidence=factor,
                adjusted=decl.declared_level * factor,
                basis=decl.confidence_basis,
                corrected=decl.confidence_basis == "contradicted",
            )
        )
    return views


def _profile(cohort: Cohort, result: AllocationResult, student_id: str) -> StudentProfile:
    student = next(s for s in cohort.students if s.student_id == student_id)
    projects = {p.project_id: p for p in cohort.projects}
    bands = {r.team_id: r.band for r in result.health}
    team = next((t for t in result.teams if student_id in t.member_ids), None)
    views = _skill_views(cohort, student_id)

    fit_score: float | None = None
    if team is not None:
        fit_score = round(fit(student, projects[team.project_id]), 2)
        prefs = student.preferred_projects
        rank = prefs.index(team.project_id) + 1 if team.project_id in prefs else None
        pref_txt = f"preference #{rank}" if rank else "via maximin rebalance"
        health = team.health_score if team.health_score is not None else 0.0
        rationale = (
            f"Placed in {team.project_id} ({pref_txt}); Fit {fit_score}. "
            f"Team health {health:.0f} ({bands.get(team.team_id, 'n/a')})."
        )
    else:
        rationale = "Unplaced — held in the faculty exception pool for review."

    corrected = [v for v in views if v.corrected]
    if corrected:
        c = corrected[0]
        rationale += (
            f" Evidence correction: {c.discipline} claim {c.declared:.1f} discounted to "
            f"{c.adjusted:.1f} (contradicted by throughput)."
        )
    return StudentProfile(
        student_id=student.student_id,
        name=student.name,
        skills=views,
        team_id=team.team_id if team else None,
        project_id=team.project_id if team else None,
        fit=fit_score,
        rationale=rationale,
    )


def _team_views(cohort: Cohort, result: AllocationResult) -> list[TeamView]:
    students = {s.student_id: s for s in cohort.students}
    projects = {p.project_id: p for p in cohort.projects}
    allocs = {a.team_id: a for a in result.task_allocations}
    reports = {r.team_id: r for r in result.health}
    views: list[TeamView] = []
    for team in result.teams:
        alloc = allocs.get(team.team_id)
        report = reports[team.team_id]
        members = [
            MemberView(
                student_id=mid,
                name=students[mid].name,
                utilisation=round(alloc.utilisation[mid], 2) if alloc else None,
                overloaded=bool(alloc and mid in alloc.overloaded),
            )
            for mid in team.member_ids
        ]
        views.append(
            TeamView(
                team_id=team.team_id,
                project_id=team.project_id,
                project_title=projects[team.project_id].title,
                members=members,
                health_score=round(report.score, 1),
                band=report.band,
                components={k: round(v, 3) for k, v in report.components.items()},
                unallocated_hours=round(alloc.unallocated_hours, 1) if alloc else 0.0,
            )
        )
    return views


def _alert_views(result: AllocationResult) -> list[AlertView]:
    order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
    alerts = sorted(result.alerts, key=lambda a: order.get(a.severity, 9))
    return [
        AlertView(
            severity=a.severity,
            trigger_type=a.trigger_type,
            detail=a.detail,
            team_id=a.team_id,
            student_id=a.student_id,
        )
        for a in alerts
    ]


def _run_response() -> RunResponse:
    cohort, result = _cohort(), _result()
    return RunResponse(
        stages=_STAGES,
        teams=_team_views(cohort, result),
        alerts=_alert_views(result),
        duplicate_flags=[
            DuplicateView(project_a=d.project_a, project_b=d.project_b, similarity=d.similarity)
            for d in result.duplicate_flags
        ],
        exception_pool=result.exception_pool,
        student_profiles=[_profile(cohort, result, s.student_id) for s in cohort.students],
    )


# ── endpoints ────────────────────────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def post_run() -> RunResponse:
    return _run_response()


@app.get("/teams", response_model=list[TeamView])
def get_teams() -> list[TeamView]:
    return _team_views(_cohort(), _result())


@app.get("/alerts", response_model=list[AlertView])
def get_alerts() -> list[AlertView]:
    return _alert_views(_result())


@app.get("/students/{student_id}", response_model=StudentProfile)
def get_student(student_id: str) -> StudentProfile:
    cohort = _cohort()
    if not any(s.student_id == student_id for s in cohort.students):
        raise HTTPException(status_code=404, detail=f"unknown student {student_id}")
    return _profile(cohort, _result(), student_id)


# ── admin console (governance) ───────────────────────────────────────────────
class AuditView(BaseModel):
    id: int
    actor_id: str
    actor_role: str
    action: str
    target_id: str | None
    reason: str | None
    created_at: str
    row_hash: str | None


class ApprovalView(BaseModel):
    request_id: str
    full_name: str
    email: str
    role_requested: str
    requested_at: str


class OverrideView(BaseModel):
    team_id: str
    lecturer: str
    from_status: str
    to_status: str
    reason: str
    at: str


class IntegrityView(BaseModel):
    verified: bool
    broken_at: int | None  # id of the first tampered audit row, or null if intact
    entries: int


@app.get("/admin/audit", response_model=list[AuditView])
def get_audit() -> list[AuditView]:
    return [
        AuditView(
            id=e.id,
            actor_id=e.actor_id,
            actor_role=e.actor_role,
            action=e.action,
            target_id=e.target_id,
            reason=e.reason,
            created_at=e.created_at,
            row_hash=e.row_hash,
        )
        for e in _governance().audit
    ]


@app.get("/admin/approvals", response_model=list[ApprovalView])
def get_approvals() -> list[ApprovalView]:
    return [
        ApprovalView(
            request_id=a.request_id,
            full_name=a.full_name,
            email=a.email,
            role_requested=a.role_requested,
            requested_at=a.requested_at,
        )
        for a in _governance().approvals
    ]


@app.get("/admin/overrides", response_model=list[OverrideView])
def get_overrides() -> list[OverrideView]:
    return [
        OverrideView(
            team_id=o.team_id,
            lecturer=o.lecturer,
            from_status=o.from_status,
            to_status=o.to_status,
            reason=o.reason,
            at=o.at,
        )
        for o in _governance().overrides
    ]


@app.get("/admin/integrity", response_model=IntegrityView)
def get_integrity() -> IntegrityView:
    """Mirror of SQL audit_verify(): recompute the hash chain, report any break.

    An empty log is NOT "verified" — a truncated/zeroed audit trail must never show
    a green badge over nothing.
    """
    audit = _governance().audit
    broken = verify(audit)
    verified = broken is None and len(audit) > 0
    return IntegrityView(verified=verified, broken_at=broken, entries=len(audit))
