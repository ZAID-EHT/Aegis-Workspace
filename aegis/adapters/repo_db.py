"""Supabase read adapter: live tables -> domain Cohort.

Reads the engine-shaped rows (after 0001+0002+0003 and a data load) via supabase-py
with the service_role key, and maps them into the same immutable Cohort that
``repo_seed`` / ``repo_mock`` produce — so the engine and API are unchanged.

Impure edge: depends on domain + supabase-py. Never imported by ``engine/``. The
pure ``rows_to_cohort`` mapping is unit-testable without a live database; only
``load_db_cohort`` touches the network.
"""

from __future__ import annotations

import os
from typing import Any

from aegis.domain.models import (
    ActivityEvent,
    Cohort,
    Project,
    SkillDeclaration,
    Student,
    TeamMonitoring,
)

Row = dict[str, Any]


def _str_list(v: Any) -> tuple[str, ...]:
    return tuple(str(x) for x in (v or []))


def rows_to_cohort(
    students: list[Row],
    skills: list[Row],
    projects: list[Row],
    activity: list[Row],
    monitoring: list[Row],
) -> Cohort:
    """Pure mapping from Supabase rows to a Cohort. No I/O — safe to unit-test."""
    skills_by_student: dict[str, list[SkillDeclaration]] = {}
    for r in skills:
        skills_by_student.setdefault(str(r["student_id"]), []).append(
            SkillDeclaration(
                discipline=str(r["discipline"]),
                declared_level=float(r["declared_level"]),
                confidence_basis=str(r["confidence_basis"]),
            )
        )

    student_objs = tuple(
        Student(
            student_id=str(r["id"]),
            name=str(r["name"]),
            email=str(r["email"]),
            capacity_hours=float(r["capacity_hours"]),
            skills=tuple(skills_by_student.get(str(r["id"]), [])),
            preferred_projects=_str_list(r.get("preferred_projects")),
            preferred_teammate_id=(
                None if r.get("preferred_teammate_id") is None else str(r["preferred_teammate_id"])
            ),
            availability=_str_list(r.get("availability")),
            preferred_role=(None if r.get("preferred_role") is None else str(r["preferred_role"])),
        )
        for r in students
    )

    project_objs = tuple(
        Project(
            project_id=str(r["id"]),
            title=str(r["title"]),
            abstract=str(r["abstract"]),
            capacity=int(r["capacity"]),
            required_skills=_str_list(r.get("required_skills")),
            critical_skills=_str_list(r.get("critical_skills")),
            meeting_slots=_str_list(r.get("meeting_slots")),
            supervisor_id=(None if r.get("supervisor_id") is None else str(r["supervisor_id"])),
            total_hours=float(r.get("total_hours") or 0.0),
        )
        for r in projects
    )

    activity_objs = tuple(
        ActivityEvent(
            author_id=str(r["student_id"]),
            sim_day=int(r["sim_day"]),
            event_type=str(r["event_type"]),
            assigned_to=(None if r.get("assigned_to") is None else str(r["assigned_to"])),
            task_id=(None if r.get("task_id") is None else str(r["task_id"])),
        )
        for r in activity
        if r.get("sim_day") is not None and r.get("event_type") is not None
    )

    monitoring_map = {
        str(r["project_id"]): TeamMonitoring(
            tasks_assigned=int(r["tasks_assigned"]),
            tasks_done=int(r["tasks_done"]),
            milestones_due=int(r["milestones_due"]),
            milestones_done=int(r["milestones_done"]),
        )
        for r in monitoring
    }

    return Cohort(
        students=student_objs,
        projects=project_objs,
        activity_log=activity_objs,
        monitoring=monitoring_map,
    )


def load_db_cohort() -> Cohort:
    """Fetch the cohort from Supabase. Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY."""
    from supabase import create_client  # imported lazily so seed-only runs need no client

    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)

    def fetch(table: str) -> list[Row]:
        data: Any = client.table(table).select("*").execute().data
        return list(data)

    return rows_to_cohort(
        students=fetch("students"),
        skills=fetch("skills_declared"),
        projects=fetch("projects"),
        activity=fetch("activity_log"),
        monitoring=fetch("team_monitoring"),
    )
