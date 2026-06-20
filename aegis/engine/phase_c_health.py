"""Phase C — engagement monitoring: health score, ghosting, sympathy, burnout.

Everything here reads the seeded ``activity_log`` (and per-team ``monitoring``) —
no live Drive. It turns raw behaviour into a 0–100 team health score, a 3-tier
ghosting classification, and sympathy-carry / burnout flags, all emitted as
``Alert`` objects for the faculty inbox.

Pure: depends on domain + config only.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from aegis.domain.models import ActivityEvent, Alert, Cohort, HealthReport, Student, Team
from aegis.engine import config

# Severity strings (README "Alert Severity Reference").
INFO = "INFO"
WARNING = "WARNING"
CRITICAL = "CRITICAL"


# ── activity helpers ────────────────────────────────────────────────────────
def _window_end(cohort: Cohort) -> int:
    # Anchor to the configured sprint length so a ghost's trailing silence is counted
    # regardless of when other students last acted; extend if data runs longer.
    observed = max((e.sim_day for e in cohort.activity_log), default=0)
    return max(config.MONITORING_WINDOW_DAYS, observed)


def _authored(cohort: Cohort, student_id: str) -> list[ActivityEvent]:
    return [e for e in cohort.activity_log if e.author_id == student_id]


def contribution(cohort: Cohort, student_id: str) -> int:
    """How many events a student actually authored (their real footprint)."""
    return len(_authored(cohort, student_id))


# ── health score (4 components) ─────────────────────────────────────────────
def _engagement(members: Sequence[Student], cohort: Cohort) -> float:
    if not members:
        return 0.0
    actual = sum(contribution(cohort, m.student_id) for m in members)
    expected = config.EXPECTED_EVENTS_PER_STUDENT * len(members)
    return min(actual / expected, 1.0) if expected else 0.0


def _workload_balance(members: Sequence[Student], cohort: Cohort) -> float:
    counts = [contribution(cohort, m.student_id) for m in members]
    mean = statistics.fmean(counts) if counts else 0.0
    if len(counts) <= 1 or mean <= 0:
        return 1.0
    return max(0.0, 1.0 - statistics.pstdev(counts) / mean)


def _band(score: float) -> str:
    if score >= config.HEALTH_BANDS["healthy"]:
        return "healthy"
    if score >= config.HEALTH_BANDS["at_risk"]:
        return "at_risk"
    return "critical"


def health_report(team: Team, cohort: Cohort) -> HealthReport:
    """4-component health: task_completion + workload_balance + engagement + milestone.

    Components without data (a team with no monitoring entry, or zero tasks/milestones)
    are dropped and the surviving weights renormalised — so "no data" never silently
    reads as either failure (0) or success (1). An empty team scores 0/critical.
    """
    students = {s.student_id: s for s in cohort.students}
    members = [students[mid] for mid in team.member_ids]
    if not members:
        return HealthReport(team_id=team.team_id, score=0.0, band="critical", components={})

    mon = cohort.monitoring.get(team.project_id)
    weights = config.HEALTH_WEIGHTS

    # engagement and workload are always derivable from the activity log.
    components: dict[str, float] = {
        "engagement": _engagement(members, cohort),
        "workload_balance": _workload_balance(members, cohort),
    }
    if mon and mon.tasks_assigned:
        components["task_completion"] = mon.tasks_done / mon.tasks_assigned
    if mon and mon.milestones_due:
        components["milestone"] = mon.milestones_done / mon.milestones_due

    total_weight = sum(weights[name] for name in components)
    score = 100.0 * sum(weights[name] * value for name, value in components.items()) / total_weight
    return HealthReport(team_id=team.team_id, score=score, band=_band(score), components=components)


# ── ghosting (3-tier) ───────────────────────────────────────────────────────
def _longest_zero_run(active_days: set[int], window_end: int) -> int:
    longest = run = 0
    for day in range(1, window_end + 1):
        run = 0 if day in active_days else run + 1
        longest = max(longest, run)
    return longest


def ghosting_tier(cohort: Cohort, student_id: str) -> int:
    """0 = fine; 1 = footprint dropped >=40%; 2 = >=6 zero days; 3 = >=10 zero days."""
    window_end = _window_end(cohort)
    if window_end == 0:
        return 0
    active_days = {e.sim_day for e in _authored(cohort, student_id)}
    zero_run = _longest_zero_run(active_days, window_end)
    if zero_run >= config.GHOST_TIER["tier3_days"]:
        return 3
    if zero_run >= config.GHOST_TIER["tier2_days"]:
        return 2
    # Tier 1: a >=40% drop in footprint from the first half of the window to the
    # second — but only once an established footprint existed (else a steady-but-light
    # contributor is wrongly flagged).
    mid = window_end // 2
    first = sum(1 for d in active_days if d <= mid)
    second = sum(1 for d in active_days if d > mid)
    if first >= config.GHOST_TIER1_MIN_BASELINE and second <= (
        1.0 - config.GHOST_TIER["tier1_drop"]
    ) * first:
        return 1
    return 0


# ── sympathy-carry ──────────────────────────────────────────────────────────
def carry_ratio(cohort: Cohort, student_id: str) -> float:
    """Of all work on a student's tasks, the fraction authored by someone else."""
    on_tasks = [e for e in cohort.activity_log if e.assigned_to == student_id]
    if not on_tasks:
        return 0.0
    by_others = sum(1 for e in on_tasks if e.author_id != student_id)
    return by_others / len(on_tasks)


def primary_carrier(cohort: Cohort, student_id: str) -> str | None:
    """Who does the most work on this student's tasks (the carrier), if anyone."""
    others: dict[str, int] = {}
    for e in cohort.activity_log:
        if e.assigned_to == student_id and e.author_id != student_id:
            others[e.author_id] = others.get(e.author_id, 0) + 1
    if not others:
        return None
    return max(others, key=lambda a: (others[a], a))


# ── burnout ─────────────────────────────────────────────────────────────────
def burnout_members(team: Team, cohort: Cohort) -> list[str]:
    """Members whose footprint is >= BURNOUT_MULT × the team's average."""
    counts = {mid: contribution(cohort, mid) for mid in team.member_ids}
    mean = statistics.fmean(counts.values()) if counts else 0.0
    if mean <= 0:
        return []
    return [mid for mid, c in counts.items() if c >= config.BURNOUT_MULT * mean]


# ── alerts ──────────────────────────────────────────────────────────────────
_GHOST_SEVERITY = {1: INFO, 2: WARNING, 3: CRITICAL}


def alerts(teams: Sequence[Team], cohort: Cohort) -> list[Alert]:
    """Distil all Phase C signals into a triaged alert list."""
    out: list[Alert] = []
    for team in teams:
        report = health_report(team, cohort)
        detail = f"{team.team_id} health {report.score:.0f}"
        if report.band == "critical":
            out.append(Alert(CRITICAL, "health_critical", detail, team.team_id))
        elif report.band == "at_risk":
            out.append(Alert(WARNING, "health_at_risk", detail, team.team_id))

        for mid in team.member_ids:
            tier = ghosting_tier(cohort, mid)
            if tier:
                out.append(
                    Alert(
                        _GHOST_SEVERITY[tier],
                        f"ghosting_tier{tier}",
                        f"{mid}: ghosting tier {tier}",
                        team.team_id,
                        mid,
                    )
                )
            if carry_ratio(cohort, mid) >= config.SYMPATHY_RATIO:
                carrier = primary_carrier(cohort, mid)
                out.append(
                    Alert(
                        WARNING,
                        "sympathy_carry",
                        f"{mid}'s tasks carried by {carrier}",
                        team.team_id,
                        mid,
                    )
                )
        for mid in burnout_members(team, cohort):
            detail = f"{mid}: footprint >= {config.BURNOUT_MULT:g}x team average"
            out.append(Alert(WARNING, "burnout", detail, team.team_id, mid))
    return out
