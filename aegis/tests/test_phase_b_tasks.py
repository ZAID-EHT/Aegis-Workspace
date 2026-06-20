"""Golden tests for Phase B capacity-based task allocation + overload guard."""

from __future__ import annotations

import pytest

from aegis.domain.models import Cohort, Team
from aegis.engine import config
from aegis.engine.phase_b_match import assign_projects
from aegis.engine.phase_b_tasks import allocate_tasks
from aegis.engine.phase_b_teams import form_teams


def _teams(cohort: Cohort) -> dict[str, Team]:
    teams, _ = form_teams(cohort, assign_projects(cohort))
    return {t.project_id: t for t in teams}


def test_healthy_team_under_capacity(cohort: Cohort) -> None:
    """P_01: 28 sprint hours over 32 capacity -> uniform U≈0.875, no overload."""
    alloc = allocate_tasks(_teams(cohort)["P_01"], cohort)
    assert alloc.overloaded == []
    assert alloc.unallocated_hours == pytest.approx(0.0)
    assert all(u <= 1.0 for u in alloc.utilisation.values())


def test_proportional_split_sums_to_sprint_hours(cohort: Cohort) -> None:
    alloc = allocate_tasks(_teams(cohort)["P_01"], cohort)
    assert sum(alloc.hours.values()) == pytest.approx(28.0)  # P_01 total_hours


def test_utilisation_uniform_when_not_overloaded(cohort: Cohort) -> None:
    """Capacity-proportional allocation equalises utilisation by construction."""
    utils = list(allocate_tasks(_teams(cohort)["P_04"], cohort).utilisation.values())
    assert max(utils) - min(utils) < 1e-9


def test_overload_guard_trips_on_p05(cohort: Cohort) -> None:
    """P_05 final team (cap 26): 36 sprint hours -> raw U~1.385 > 1.2 guard fires."""
    alloc = allocate_tasks(_teams(cohort)["P_05"], cohort)
    assert set(alloc.overloaded) == set(_teams(cohort)["P_05"].member_ids)
    assert all(u == pytest.approx(config.OVERLOAD) for u in alloc.utilisation.values())
    assert alloc.unallocated_hours > 0.0
