"""Build a Cohort from the uploaded mock student set.

The mock files (``student_profiles.json``) carry *students only* — and on a 1–10
declared scale with pillar names + an LMS-flavoured ``basis`` vocabulary. This
adapter maps them into the engine's domain (1–5 scale, four disciplines, engine
``confidence_basis`` vocab) and deterministically generates the pieces the engine
needs but the mock lacks: projects, availability, roles, an activity log, and
per-team monitoring. Deterministic (index-based, no RNG) so every load is identical.

This is an impure edge: it depends on ``domain`` only and is never imported by
``engine/``. The same Cohort it returns is what ``scripts/load_supabase.py`` writes
to Supabase and what ``repo_db`` later reads back.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aegis.domain.models import (
    DISCIPLINES,
    ROLES,
    ActivityEvent,
    Cohort,
    Project,
    SkillDeclaration,
    Student,
    TeamMonitoring,
)

DEFAULT_MOCK: Path = Path(__file__).resolve().parents[2] / "student_profiles.json"

PILLAR_TO_DISCIPLINE: dict[str, str] = {
    "technical_architecture": "technical",
    "user_experience_design": "ux",
    "project_management_ops": "management",
    "communication_presentation": "communication",
}
BASIS_MAP: dict[str, str] = {
    "verified_lms": "verified",
    "portfolio": "portfolio",
    "self_report": "self_report",
    "contradicted": "contradicted",
}

SLOTS: tuple[str, ...] = (
    "mon_am", "mon_pm", "tue_am", "tue_pm", "wed_am",
    "wed_pm", "thu_am", "thu_pm", "fri_am", "fri_pm",
)

PROJECT_IDS: tuple[str, ...] = tuple(f"P_{i:02d}" for i in range(1, 16))  # P_01..P_15

# 15 abstracts. P_02 and P_03 are a deliberate near-duplicate pair (dedupe demo).
_ABSTRACTS: dict[str, tuple[str, str]] = {
    "P_01": ("Campus Wellbeing App", "A mobile companion that helps students track mood, book counsellor time, and find quiet peer support during heavy assessment periods."),
    "P_02": ("Smart Canteen Food-Waste Platform", "Uses computer vision at the tray return to measure plate waste and machine learning to forecast demand so kitchens cook closer to what is eaten, with surplus offered to a student marketplace."),
    "P_03": ("Canteen Surplus and Plate-Waste Analytics", "Uses computer vision at the tray return to measure plate waste and machine learning to forecast demand so kitchens cook closer to what is eaten, with leftover surplus offered to a student marketplace before service ends."),
    "P_04": ("Accessible Museum AR Tour", "An augmented-reality authoring tool that lets curators build self-guided tours adapting to each visitor's accessibility needs across audio, sign language, and simplified tracks."),
    "P_05": ("Peer Skill Exchange Network", "A marketplace where students trade skills rather than money, with scheduling, reputation, and a fair-exchange ledger that keeps trades balanced over time."),
    "P_06": ("Community Disaster-Response Hub", "Coordinates neighbourhood volunteers, supplies, and shelter capacity during floods, working offline-first and falling back to SMS when networks fail."),
    "P_07": ("Research Reproducibility Tracker", "Captures the exact code, data snapshot, and environment behind every published figure and re-runs the pipeline on demand to catch silent reproducibility rot."),
    "P_08": ("Urban Cycling Safety Map", "Fuses crowdsourced near-miss reports, accident records, and road-gradient data to highlight dangerous junctions and suggest safer commuter routes."),
    "P_09": ("Volunteer Matching Portal", "Connects students with local non-profits by matching skills and availability to short, well-scoped volunteering tasks."),
    "P_10": ("Sustainable Campus Dashboard", "Visualises building-level energy and water use and nudges departments toward measurable reduction targets each term."),
    "P_11": ("Inclusive Hiring Assistant", "Helps small employers write fairer job posts and screen applications with bias checks and structured, evidence-based scoring."),
    "P_12": ("Local Food Co-op Logistics", "Plans pickups, shares, and routes for a neighbourhood food co-operative, balancing member demand against supplier capacity."),
    "P_13": ("Mental-Health Peer Chat", "A moderated, anonymous peer-support chat with gentle triage that escalates higher-risk conversations to trained staff."),
    "P_14": ("Open Lecture Notes Platform", "A collaborative space for students to co-author, review, and version lecture notes with clear attribution and quality signals."),
    "P_15": ("Smart Timetable Optimiser", "Builds conflict-free study and group-meeting schedules from everyone's availability, room capacity, and travel time."),
}


def _student(raw: dict[str, Any], idx: int) -> Student:
    sid = str(raw["student_id"])
    skills: list[SkillDeclaration] = []
    for pillar, entry in raw["skill_matrix_adjusted"].items():
        discipline = PILLAR_TO_DISCIPLINE[pillar]
        # mock declared is on a 1–10 scale; the engine works on 1–5.
        declared = round(float(entry["declared"]) / 2.0, 2)
        skills.append(
            SkillDeclaration(
                discipline=discipline,
                declared_level=declared,
                confidence_basis=BASIS_MAP[str(entry["basis"])],
            )
        )
    # deterministic availability (3 slots) and a preferred role, derived from index.
    avail = tuple(SLOTS[(idx + k) % len(SLOTS)] for k in range(3))
    teammate = raw.get("preferred_teammate")
    return Student(
        student_id=sid,
        name=str(raw["name"]),
        email=f"{sid.lower()}@aegis.test",
        capacity_hours=round(float(raw["capacity_allowance_hours"]), 1),
        skills=tuple(skills),
        preferred_projects=tuple(str(p) for p in raw.get("preferred_projects", [])),
        preferred_teammate_id=None if teammate is None else str(teammate),
        availability=avail,
        preferred_role=ROLES[idx % len(ROLES)],
    )


def _projects() -> list[Project]:
    projects: list[Project] = []
    for i, pid in enumerate(PROJECT_IDS):
        title, abstract = _ABSTRACTS[pid]
        critical = DISCIPLINES[i % len(DISCIPLINES)]
        secondary = DISCIPLINES[(i + 1) % len(DISCIPLINES)]
        slots = (SLOTS[(i * 2) % len(SLOTS)], SLOTS[(i * 2 + 1) % len(SLOTS)])
        # most sprints ~U 0.8; a few heavier to exercise the overload guard.
        total_hours = 34.0 if i % 5 == 0 else 28.0
        projects.append(
            Project(
                project_id=pid,
                title=title,
                abstract=abstract,
                capacity=5,
                required_skills=(critical, secondary),
                critical_skills=(critical,),
                meeting_slots=slots,
                supervisor_id=f"SUP_{i + 1:02d}",
                total_hours=total_hours,
            )
        )
    return projects


def _activity(students: list[Student]) -> list[ActivityEvent]:
    """Light, deterministic activity. The first student ghosts (no events); the
    second is carried by the third (sympathy + burnout) so Phase C has live cases."""
    log: list[ActivityEvent] = []
    ghost = students[0].student_id
    carried = students[1].student_id
    carrier = students[2].student_id
    for s in students:
        if s.student_id == ghost:
            continue  # pure ghost: zero authored events
        if s.student_id == carried:
            # present via general pings (so not a ghost) but does none of their own tasks
            for day in (1, 6, 10):
                log.append(ActivityEvent(carried, day, "ping"))
            continue
        n = s.student_id[-2:]
        days = [2, 5, 8, 11, 14]
        for k, day in enumerate(days):
            log.append(
                ActivityEvent(
                    author_id=s.student_id,
                    sim_day=day,
                    event_type="commit" if k % 2 == 0 else "edit",
                    assigned_to=s.student_id,
                    task_id=f"T_{n}{chr(97 + k // 2)}",
                )
            )
    # carrier covers the carried student's tasks (sympathy >= 0.95; extra load = burnout)
    for day in (3, 5, 7, 9, 11):
        log.append(ActivityEvent(carrier, day, "commit", assigned_to=carried, task_id="T_carry"))
    return log


def _monitoring() -> dict[str, TeamMonitoring]:
    mon: dict[str, TeamMonitoring] = {}
    for i, pid in enumerate(PROJECT_IDS):
        done = (12, 6, 9, 11, 8)[i % 5]  # spread completion for a health-band mix
        m_done = (4, 1, 3, 4, 2)[i % 5]
        mon[pid] = TeamMonitoring(
            tasks_assigned=12, tasks_done=done, milestones_due=4, milestones_done=m_done
        )
    return mon


def load_mock_cohort(path: str | Path = DEFAULT_MOCK) -> Cohort:
    data: Any = json.loads(Path(path).read_text(encoding="utf-8"))
    students = [_student(raw, i) for i, raw in enumerate(data)]
    return Cohort(
        students=tuple(students),
        projects=tuple(_projects()),
        activity_log=tuple(_activity(students)),
        monitoring=_monitoring(),
    )
