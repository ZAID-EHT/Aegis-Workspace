"""Golden tests for Phase B SPA assignment + oversubscription cascade."""

from __future__ import annotations

from aegis.domain.models import Cohort, Project, Student
from aegis.engine.phase_b_match import (
    assign_projects,
    rare_skill_bonus,
    scarce_critical_skills,
)


def _project(cohort: Cohort, pid: str) -> Project:
    return next(p for p in cohort.projects if p.project_id == pid)


def _student(cohort: Cohort, sid: str) -> Student:
    return next(s for s in cohort.students if s.student_id == sid)


def test_everyone_placed_in_three_full_teams(cohort: Cohort) -> None:
    a = assign_projects(cohort)
    sized = {pid: members for pid, members in a.by_project.items() if members}
    assert set(sized) == {"P_01", "P_04", "P_05"}
    assert all(len(m) == 4 for m in sized.values())
    assert a.unmatched == []


def test_oversubscription_cascade(cohort: Cohort) -> None:
    """5 students rank P_01 first (cap 4); the lowest-priority one cascades to P_05."""
    a = assign_projects(cohort)
    assert len(a.by_project["P_01"]) == 4  # capped at capacity
    first_choice_p01 = {
        s.student_id
        for s in cohort.students
        if s.preferred_projects and s.preferred_projects[0] == "P_01"
    }
    assert len(first_choice_p01) == 5  # demand exceeds capacity
    cascaded = first_choice_p01 - set(a.by_project["P_01"])
    assert len(cascaded) == 1
    # the cascaded student landed in a later preference, not the exception pool
    placed = {sid for members in a.by_project.values() for sid in members}
    assert cascaded <= placed


def test_rare_skill_seeded(cohort: Cohort) -> None:
    """UX is the only scarce critical skill; both UX holders seed into P_04."""
    assert scarce_critical_skills(cohort) == {"ux"}
    a = assign_projects(cohort)
    assert {"STU_03", "STU_12"} <= set(a.by_project["P_04"])


def test_rare_skill_bonus_value(cohort: Cohort) -> None:
    scarce = scarce_critical_skills(cohort)
    p04 = _project(cohort, "P_04")  # critical ux (scarce)
    p01 = _project(cohort, "P_01")  # critical technical (not scarce)
    assert rare_skill_bonus(_student(cohort, "STU_03"), p04, scarce) == 15.0
    assert rare_skill_bonus(_student(cohort, "STU_01"), p04, scarce) == 0.0  # no UX coverage
    assert rare_skill_bonus(_student(cohort, "STU_01"), p01, scarce) == 0.0  # tech not scarce


def test_assignment_is_deterministic(cohort: Cohort) -> None:
    assert assign_projects(cohort).by_project == assign_projects(cohort).by_project
