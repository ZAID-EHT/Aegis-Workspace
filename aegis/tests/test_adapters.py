"""Tests for the data adapters: mock-cohort generator + Supabase row mapping."""

from __future__ import annotations

from pathlib import Path

from aegis.adapters.repo_db import rows_to_cohort
from aegis.adapters.repo_mock import DEFAULT_MOCK, load_mock_cohort
from aegis.domain.models import CONFIDENCE_BASES, DISCIPLINES
from aegis.engine.pipeline import run

MOCK_PRESENT = Path(DEFAULT_MOCK).exists()


def test_mock_cohort_maps_into_engine_vocab() -> None:
    if not MOCK_PRESENT:
        return  # uploaded mock file is untracked; skip when absent
    cohort = load_mock_cohort()
    assert len(cohort.students) == 70
    assert len(cohort.projects) == 15
    assert len(cohort.monitoring) == 15
    for s in cohort.students:
        for sk in s.skills:
            assert sk.discipline in DISCIPLINES  # pillar -> discipline mapping
            assert sk.confidence_basis in CONFIDENCE_BASES  # verified_lms -> verified
            assert 0.0 <= sk.declared_level <= 5.0  # rescaled from the 1-10 mock scale


def test_mock_cohort_runs_through_pipeline() -> None:
    if not MOCK_PRESENT:
        return
    result = run(load_mock_cohort())
    assert len(result.teams) > 0
    assert len(result.health) == len(result.teams)
    # the engineered duplicate pair should still flag
    assert any({d.project_a, d.project_b} == {"P_02", "P_03"} for d in result.duplicate_flags)


def test_rows_to_cohort_pure_mapping() -> None:
    """Supabase row shape -> Cohort, with no database involved."""
    students = [
        {
            "id": "u1",
            "name": "Asha",
            "email": "a@x.test",
            "capacity_hours": 8,
            "preferred_projects": ["P_01"],
            "availability": ["mon_am"],
            "preferred_role": "tech_lead",
            "preferred_teammate_id": None,
        }
    ]
    skills = [
        {
            "student_id": "u1",
            "discipline": "technical",
            "declared_level": 4,
            "confidence_basis": "verified",
        }
    ]
    projects = [
        {
            "id": "P_01",
            "title": "Demo",
            "abstract": "abstract",
            "capacity": 4,
            "required_skills": ["technical"],
            "critical_skills": ["technical"],
            "meeting_slots": ["mon_am"],
            "total_hours": 28,
            "supervisor_id": None,
        }
    ]
    activity = [
        {
            "student_id": "u1",
            "sim_day": 2,
            "event_type": "commit",
            "assigned_to": "u1",
            "task_id": "T1",
        }
    ]
    monitoring = [
        {
            "project_id": "P_01",
            "tasks_assigned": 12,
            "tasks_done": 9,
            "milestones_due": 4,
            "milestones_done": 3,
        }
    ]
    cohort = rows_to_cohort(students, skills, projects, activity, monitoring)
    assert cohort.students[0].name == "Asha"
    assert cohort.students[0].skills[0].discipline == "technical"
    assert cohort.projects[0].required_skills == ("technical",)
    assert cohort.activity_log[0].author_id == "u1"
    assert cohort.monitoring["P_01"].tasks_done == 9
