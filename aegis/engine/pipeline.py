"""The engine pipeline — orchestrates Phase A -> B -> C into one result.

Pure and deterministic: a :class:`Cohort` in, one :class:`AllocationResult` out.
This is the single entry point the API (Phase D) wraps; it imports only domain,
config, and the phase modules — nothing from adapters/api.
"""

from __future__ import annotations

from aegis.domain.models import AllocationResult, Cohort
from aegis.engine.phase_a_scoring import skill_matrix
from aegis.engine.phase_b_dedupe import duplicate_flags
from aegis.engine.phase_b_match import assign_projects
from aegis.engine.phase_b_tasks import allocate_tasks
from aegis.engine.phase_b_teams import form_teams
from aegis.engine.phase_c_health import alerts, health_report


def run(cohort: Cohort) -> AllocationResult:
    # Phase A — verify: adjusted skill matrices + duplicate-project gate.
    matrices = [skill_matrix(s) for s in cohort.students]
    dupes = duplicate_flags(cohort.projects)

    # Phase B — match, form, allocate.
    assignment = assign_projects(cohort)
    teams, exception_pool = form_teams(cohort, assignment)
    allocations = [allocate_tasks(team, cohort) for team in teams]

    # Phase C — monitor.
    health = [health_report(team, cohort) for team in teams]
    for team, report in zip(teams, health, strict=True):
        team.health_score = report.score  # stamp the score onto the team for consumers
    alert_list = alerts(teams, cohort)

    return AllocationResult(
        teams=teams,
        task_allocations=allocations,
        alerts=alert_list,
        health=health,
        skill_matrices=matrices,
        duplicate_flags=dupes,
        exception_pool=exception_pool,
    )
