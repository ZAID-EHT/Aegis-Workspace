#!/usr/bin/env python
"""Load the mock cohort into Supabase (one-off).

Reads .env for SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY, builds the Cohort from the
uploaded mock students (+ generated projects/activity/monitoring), and writes it to
the tables created by migrations 0001 + 0003. Student ids are mapped to stable UUIDs
(students.id is uuid). Run once after applying the migrations:

    python scripts/load_supabase.py

To reload, first clear the tables (Supabase SQL editor):
    truncate team_monitoring, activity_log, skills_declared,
             team_members, tasks, alerts, teams, students, projects cascade;
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path

from aegis.adapters.repo_mock import load_mock_cohort
from aegis.engine import config

NAMESPACE = uuid.UUID("a3e9c0de-0000-4000-8000-000000000a15")  # stable namespace for AEGIS ids


def _sid(student_id: str) -> str:
    """Deterministic UUID for a mock student id (students.id is uuid)."""
    return str(uuid.uuid5(NAMESPACE, student_id))


def _load_env() -> None:
    env = Path(".env")
    if not env.exists():
        return
    for raw in env.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split("  #")[0].strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def main() -> None:
    _load_env()
    from supabase import create_client

    sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    cohort = load_mock_cohort()

    sb.table("projects").insert(
        [
            {
                "id": p.project_id,
                "title": p.title,
                "abstract": p.abstract,
                "capacity": p.capacity,
                "required_skills": list(p.required_skills),
                "critical_skills": list(p.critical_skills),
                "meeting_slots": list(p.meeting_slots),
                "total_hours": p.total_hours,
            }
            for p in cohort.projects
        ]
    ).execute()

    # preferred_teammate_id is left null on load to avoid self-FK ordering; it is a
    # soft signal (null for most students anyway).
    sb.table("students").insert(
        [
            {
                "id": _sid(s.student_id),
                "cohort_id": "CS-2026",
                "name": s.name,
                "email": s.email,
                "capacity_hours": s.capacity_hours,
                "availability": list(s.availability),
                "preferred_projects": list(s.preferred_projects),
                "preferred_role": s.preferred_role,
            }
            for s in cohort.students
        ]
    ).execute()

    skills = [
        {
            "student_id": _sid(s.student_id),
            "discipline": sk.discipline,
            "declared_level": sk.declared_level,
            "confidence_basis": sk.confidence_basis,
            "adjusted_score": round(sk.declared_level * config.CONFIDENCE[sk.confidence_basis], 2),
        }
        for s in cohort.students
        for sk in s.skills
    ]
    sb.table("skills_declared").insert(skills).execute()

    activity = [
        {
            "student_id": _sid(e.author_id),
            "action": e.event_type,
            "sim_day": e.sim_day,
            "event_type": e.event_type,
            "assigned_to": None if e.assigned_to is None else _sid(e.assigned_to),
            "task_id": e.task_id,
        }
        for e in cohort.activity_log
    ]
    for i in range(0, len(activity), 500):
        sb.table("activity_log").insert(activity[i : i + 500]).execute()

    sb.table("team_monitoring").insert(
        [
            {
                "project_id": pid,
                "tasks_assigned": m.tasks_assigned,
                "tasks_done": m.tasks_done,
                "milestones_due": m.milestones_due,
                "milestones_done": m.milestones_done,
            }
            for pid, m in cohort.monitoring.items()
        ]
    ).execute()

    print(
        f"loaded: {len(cohort.students)} students, {len(cohort.projects)} projects, "
        f"{len(skills)} skills, {len(activity)} activity events, "
        f"{len(cohort.monitoring)} monitoring rows"
    )


if __name__ == "__main__":
    main()
