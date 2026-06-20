"""Phase B (3/3) — capacity-based task allocation with an overload guard.

Each member gets a share of the sprint's estimated hours proportional to their
capacity (``Task_Share(i) = cap(i) / Σ cap``), which equalises utilisation by
construction. If the sprint is over-committed for the team — utilisation would
exceed ``OVERLOAD`` (1.2) — the guard caps each member at the overload ceiling
and reports the hours that could not be placed, so faculty can cut scope or add
capacity rather than silently overloading the team.

Pure: depends on domain + config only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from aegis.domain.models import Cohort, Project, Student, Team
from aegis.engine import config


@dataclass(frozen=True)
class TaskAllocation:
    team_id: str
    project_id: str
    hours: dict[str, float]  # student_id -> assigned hours (after the guard)
    utilisation: dict[str, float]  # student_id -> U(i) = assigned / capacity
    overloaded: list[str] = field(default_factory=list)
    unallocated_hours: float = 0.0  # hours shed by the overload guard
    zero_capacity: list[str] = field(default_factory=list)  # members with no capacity (data error)


def allocate_tasks(team: Team, cohort: Cohort) -> TaskAllocation:
    students: dict[str, Student] = {s.student_id: s for s in cohort.students}
    projects: dict[str, Project] = {p.project_id: p for p in cohort.projects}
    project = projects[team.project_id]
    members = [students[mid] for mid in team.member_ids]

    total_capacity = sum(m.capacity_hours for m in members)
    hours: dict[str, float] = {}
    utilisation: dict[str, float] = {}
    overloaded: list[str] = []
    zero_capacity = [m.student_id for m in members if m.capacity_hours <= 0]
    unallocated = 0.0

    if total_capacity <= 0:
        # No capacity anywhere: surface every member at U=0 (and the whole sprint
        # as unallocated) rather than silently returning an empty allocation.
        for member in members:
            hours[member.student_id] = 0.0
            utilisation[member.student_id] = 0.0
        return TaskAllocation(
            team_id=team.team_id,
            project_id=team.project_id,
            hours=hours,
            utilisation=utilisation,
            unallocated_hours=project.total_hours,
            zero_capacity=zero_capacity,
        )

    for member in members:
        share = member.capacity_hours / total_capacity
        assigned = share * project.total_hours
        util = assigned / member.capacity_hours if member.capacity_hours > 0 else 0.0
        if util > config.OVERLOAD:
            ceiling = config.OVERLOAD * member.capacity_hours
            unallocated += assigned - ceiling
            assigned = ceiling
            util = config.OVERLOAD
            overloaded.append(member.student_id)
        hours[member.student_id] = assigned
        utilisation[member.student_id] = util

    return TaskAllocation(
        team_id=team.team_id,
        project_id=team.project_id,
        hours=hours,
        utilisation=utilisation,
        overloaded=overloaded,
        unallocated_hours=unallocated,
        zero_capacity=zero_capacity,
    )
