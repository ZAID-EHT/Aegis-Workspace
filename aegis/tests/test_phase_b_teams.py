"""Golden tests for Phase B maximin team formation."""

from __future__ import annotations

from aegis.domain.models import Cohort, Team
from aegis.engine.phase_b_match import Assignment, assign_projects
from aegis.engine.phase_b_teams import (
    form_teams,
    maximin_swap,
    min_team_score,
    team_score,
)


def _spa_teams(cohort: Cohort) -> list[Team]:
    a = assign_projects(cohort)
    return [Team(f"T::{p}", p, list(m)) for p, m in a.by_project.items() if m]


def test_maximin_raises_minimum(cohort: Cohort) -> None:
    """The swap pass must strictly raise the weakest team's score on this seed."""
    initial = _spa_teams(cohort)
    before = min_team_score(initial, cohort)
    after_teams = maximin_swap(initial, cohort)
    after = min_team_score(after_teams, cohort)
    assert after > before


def test_maximin_never_lowers_minimum(cohort: Cohort) -> None:
    initial = _spa_teams(cohort)
    before = min_team_score(initial, cohort)
    after = min_team_score(maximin_swap(initial, cohort), cohort)
    assert after >= before


def test_form_teams_on_seed(cohort: Cohort) -> None:
    teams, exception = form_teams(cohort, assign_projects(cohort))
    assert {t.project_id for t in teams} == {"P_01", "P_04", "P_05"}
    assert all(len(t.member_ids) == 4 for t in teams)
    assert exception == []
    # every student placed exactly once
    placed = [sid for t in teams for sid in t.member_ids]
    assert sorted(placed) == sorted(s.student_id for s in cohort.students)


def test_exception_pool_populates(cohort: Cohort) -> None:
    """Under-sized groups and unmatched students fall to the exception pool."""
    rigged = Assignment(by_project={"P_01": ["STU_01", "STU_02"]}, unmatched=["STU_07"])
    teams, exception = form_teams(cohort, rigged)
    assert teams == []  # the only group (size 2) is below the minimum
    assert set(exception) == {"STU_01", "STU_02", "STU_07"}


def test_team_score_bounded(cohort: Cohort) -> None:
    for team in _spa_teams(cohort):
        assert 0.0 <= team_score(team, cohort) <= 100.0


def test_maximin_golden_memberships(cohort: Cohort) -> None:
    """Pin the exact post-swap teams so a balanced-SPA regression fails loudly here
    (telling 'the assignment changed' apart from 'maximin is broken')."""
    teams, _ = form_teams(cohort, assign_projects(cohort))
    members = {t.project_id: set(t.member_ids) for t in teams}
    assert members == {
        "P_01": {"STU_11", "STU_01", "STU_05", "STU_02"},
        "P_04": {"STU_12", "STU_03", "STU_06", "STU_10"},
        "P_05": {"STU_04", "STU_08", "STU_07", "STU_09"},
    }


def test_maximin_keeps_students_on_ranked_projects(cohort: Cohort) -> None:
    """SPA hard constraint: after the swap pass, every member still sits on a
    project they ranked (maximin must not strand anyone on an unranked project)."""
    students = {s.student_id: s for s in cohort.students}
    teams = maximin_swap(_spa_teams(cohort), cohort)
    for team in teams:
        for mid in team.member_ids:
            assert team.project_id in students[mid].preferred_projects
