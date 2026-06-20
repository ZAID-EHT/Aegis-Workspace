"""Golden tests for Phase C — health score, ghosting, sympathy, burnout."""

from __future__ import annotations

import pytest

from aegis.domain.models import ActivityEvent, Cohort, Team
from aegis.engine.phase_b_match import assign_projects
from aegis.engine.phase_b_teams import form_teams
from aegis.engine.phase_c_health import (
    alerts,
    burnout_members,
    carry_ratio,
    ghosting_tier,
    health_report,
    primary_carrier,
)


def _teams(cohort: Cohort) -> dict[str, Team]:
    teams, _ = form_teams(cohort, assign_projects(cohort))
    return {t.project_id: t for t in teams}


def _ghost_cohort(events: list[tuple[str, int]]) -> Cohort:
    """Minimal cohort carrying only an activity log (for ghosting unit tests)."""
    log = tuple(ActivityEvent(author_id=a, sim_day=d, event_type="commit") for a, d in events)
    return Cohort(students=(), projects=(), activity_log=log)


# ── health score / bands ─────────────────────────────────────────────────────
def test_health_band_spread(cohort: Cohort) -> None:
    teams = _teams(cohort)
    assert health_report(teams["P_04"], cohort).band == "healthy"
    assert health_report(teams["P_01"], cohort).band == "at_risk"
    assert health_report(teams["P_05"], cohort).band == "critical"


def test_health_scores_in_band_ranges(cohort: Cohort) -> None:
    teams = _teams(cohort)
    assert health_report(teams["P_04"], cohort).score >= 75
    assert 50 <= health_report(teams["P_01"], cohort).score < 75
    assert health_report(teams["P_05"], cohort).score < 50


def test_health_bounded_and_components(cohort: Cohort) -> None:
    report = health_report(_teams(cohort)["P_05"], cohort)
    assert 0.0 <= report.score <= 100.0
    assert report.components["task_completion"] == pytest.approx(0.5)  # 6/12 from monitoring
    assert set(report.components) == {
        "task_completion",
        "workload_balance",
        "engagement",
        "milestone",
    }


def test_missing_monitoring_renormalises(cohort: Cohort) -> None:
    """A team whose project has no monitoring entry must not be silently capped at 70:
    the absent task_completion/milestone components are dropped and weights renormalised."""
    # P_02 has no monitoring entry in the seed.
    active = Team("T::P_02", "P_02", ["STU_01", "STU_02", "STU_11", "STU_12"])
    report = health_report(active, cohort)
    assert set(report.components) == {"engagement", "workload_balance"}  # only derivable ones
    assert "task_completion" not in report.components  # not silently scored 0.0
    assert report.score <= 100.0


def test_empty_team_scores_zero(cohort: Cohort) -> None:
    report = health_report(Team("T::empty", "P_01", []), cohort)
    assert report.score == 0.0
    assert report.band == "critical"


# ── ghosting (3-tier) ────────────────────────────────────────────────────────
def test_ghosting_tier3_on_seed(cohort: Cohort) -> None:
    assert ghosting_tier(cohort, "STU_07") == 3
    others = {s.student_id: ghosting_tier(cohort, s.student_id) for s in cohort.students}
    assert {sid: t for sid, t in others.items() if t} == {"STU_07": 3}  # only the ghost


def test_ghosting_window_anchored_not_data_dependent() -> None:
    """A pure ghost must read Tier 3 even when no other student acts late — the window
    is anchored to the sprint length, not the cohort's last observed event."""
    c = _ghost_cohort([("OTHER", 3)])  # only one early event anywhere
    assert ghosting_tier(c, "GHOST") == 3  # 14-day window -> 14 zero days


def test_ghosting_tier_boundaries() -> None:
    # exactly 10 zero days (days 2..11) -> Tier 3
    assert ghosting_tier(_ghost_cohort([("T", 1), ("T", 12)]), "T") == 3
    # exactly 9 zero days (days 2..10) -> Tier 2, not yet Tier 3
    assert ghosting_tier(_ghost_cohort([("T", 1), ("T", 11)]), "T") == 2
    # exactly 6 zero days (days 2..7) -> Tier 2
    assert ghosting_tier(_ghost_cohort([("T", 1), ("T", 8)]), "T") == 2
    # max 5 zero days, light-but-steady -> no tier
    assert ghosting_tier(_ghost_cohort([("T", 1), ("T", 7), ("T", 13)]), "T") == 0


def test_ghosting_tier1_established_then_drops() -> None:
    c = _ghost_cohort([("T", 1), ("T", 2), ("T", 3), ("T", 4), ("T", 8), ("T", 11)])
    assert ghosting_tier(c, "T") == 1  # first-half 4 (>=baseline), second-half 2 -> >=40% drop


def test_steady_light_contributor_not_ghosted() -> None:
    c = _ghost_cohort([("T", 1), ("T", 5), ("T", 10)])
    assert ghosting_tier(c, "T") == 0  # no established footprint -> not a false ghost


# ── sympathy-carry ───────────────────────────────────────────────────────────
def test_sympathy_carry_detected(cohort: Cohort) -> None:
    assert carry_ratio(cohort, "STU_05") == pytest.approx(1.0)
    assert primary_carrier(cohort, "STU_05") == "STU_01"


def test_only_carried_student_flagged(cohort: Cohort) -> None:
    from aegis.engine import config

    carried = [
        s.student_id
        for s in cohort.students
        if carry_ratio(cohort, s.student_id) >= config.SYMPATHY_RATIO
    ]
    assert carried == ["STU_05"]


# ── burnout ──────────────────────────────────────────────────────────────────
def test_burnout_flags_carrier(cohort: Cohort) -> None:
    teams = _teams(cohort)
    assert burnout_members(teams["P_01"], cohort) == ["STU_01"]
    assert burnout_members(teams["P_04"], cohort) == []
    assert burnout_members(teams["P_05"], cohort) == []


# ── alerts ───────────────────────────────────────────────────────────────────
def test_alerts_cover_engineered_cases(cohort: Cohort) -> None:
    teams = list(_teams(cohort).values())
    found = {(a.severity, a.trigger_type) for a in alerts(teams, cohort)}
    assert ("CRITICAL", "ghosting_tier3") in found
    assert ("WARNING", "sympathy_carry") in found
    assert ("WARNING", "burnout") in found
    assert ("CRITICAL", "health_critical") in found
    assert ("WARNING", "health_at_risk") in found


def test_ghost_alert_targets_stu07(cohort: Cohort) -> None:
    teams = list(_teams(cohort).values())
    ghost = [a for a in alerts(teams, cohort) if a.trigger_type == "ghosting_tier3"]
    assert len(ghost) == 1
    assert ghost[0].student_id == "STU_07"
    assert ghost[0].severity == "CRITICAL"
