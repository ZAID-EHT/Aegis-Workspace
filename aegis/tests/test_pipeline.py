"""End-to-end golden test: the full A->B->C pipeline on the seed."""

from __future__ import annotations

from aegis.domain.models import Cohort
from aegis.engine.pipeline import run


def test_pipeline_runs_end_to_end(cohort: Cohort) -> None:
    result = run(cohort)
    # Phase B: 3 full teams, everyone placed, nobody stranded.
    assert {t.project_id for t in result.teams} == {"P_01", "P_04", "P_05"}
    assert result.exception_pool == []
    placed = [sid for t in result.teams for sid in t.member_ids]
    assert sorted(placed) == sorted(s.student_id for s in cohort.students)
    # Phase A artefacts present.
    assert len(result.skill_matrices) == len(cohort.students)
    assert any({f.project_a, f.project_b} == {"P_02", "P_03"} for f in result.duplicate_flags)
    # one allocation + one health report per team.
    assert len(result.task_allocations) == 3
    assert len(result.health) == 3


def test_pipeline_surfaces_all_conflict_types(cohort: Cohort) -> None:
    """The four headline cases are all visible in one run."""
    result = run(cohort)
    triggers = {a.trigger_type for a in result.alerts}
    assert "ghosting_tier3" in triggers
    assert "sympathy_carry" in triggers
    assert "burnout" in triggers
    assert {"health_critical", "health_at_risk"} <= triggers
    # overload guard surfaced in task allocations (P_05 over-committed).
    assert any(a.overloaded for a in result.task_allocations)


def test_pipeline_deterministic(cohort: Cohort) -> None:
    a = run(cohort)
    b = run(cohort)
    assert [t.member_ids for t in a.teams] == [t.member_ids for t in b.teams]
    assert {al.trigger_type for al in a.alerts} == {al.trigger_type for al in b.alerts}
