"""Phase B (1/3) — project assignment via Abraham–Manlove SPA + cascade.

Students rank projects; each project ranks the students who chose it by
``Priority = Fit + RareSkillBonus`` (a +bonus when the student fills a scarce
critical skill). The Student-Project Allocation algorithm (student-optimal)
then produces a stable assignment, with oversubscribed projects cascading
released students to their next preference automatically.

One project = one team. This stage only assigns; the maximin rebalance and team
formation happen in ``phase_b_teams``. Depends on the ``matching`` library +
domain + phase A — no I/O, nothing from adapters/api.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

from matching.games import StudentAllocation

from aegis.domain.models import Cohort, Project, Student
from aegis.engine import config
from aegis.engine.phase_a_scoring import fit, skill_matrix


@dataclass(frozen=True)
class Assignment:
    """Result of the SPA stage: students grouped by project, plus the unmatched."""

    by_project: dict[str, list[str]]  # project_id -> [student_id]
    unmatched: list[str]  # students SPA could not place (empty/exhausted prefs)


def scarce_critical_skills(cohort: Cohort) -> set[str]:
    """Critical disciplines held (Â ≥ target) by ≤ RARE_SKILL_SCARCITY students."""
    critical = {d for p in cohort.projects for d in p.critical_skills}
    holders = dict.fromkeys(critical, 0)
    for student in cohort.students:
        adjusted = skill_matrix(student).adjusted
        for discipline in critical:
            if adjusted.get(discipline, 0.0) >= config.SKILL_TARGET:
                holders[discipline] += 1
    return {d for d in critical if holders[d] <= config.RARE_SKILL_SCARCITY}


def rare_skill_bonus(student: Student, project: Project, scarce: set[str]) -> float:
    """+RARE_SKILL_BONUS if the student covers any scarce critical skill of the project."""
    adjusted = skill_matrix(student).adjusted
    for discipline in project.critical_skills:
        if discipline in scarce and adjusted.get(discipline, 0.0) >= config.SKILL_TARGET:
            return float(config.RARE_SKILL_BONUS)
    return 0.0


def priority(student: Student, project: Project, scarce: set[str]) -> float:
    """Priority(i,p) = Fit(i,p) + RareSkillBonus(i,p) — how a project ranks students."""
    return fit(student, project) + rare_skill_bonus(student, project, scarce)


def assign_projects(cohort: Cohort) -> Assignment:
    students = {s.student_id: s for s in cohort.students}
    projects = {p.project_id: p for p in cohort.projects}
    scarce = scarce_critical_skills(cohort)

    # Students rank only projects that exist; those with no valid preference are unmatched.
    student_prefs = {
        sid: [pid for pid in s.preferred_projects if pid in projects]
        for sid, s in students.items()
    }
    student_prefs = {sid: prefs for sid, prefs in student_prefs.items() if prefs}

    # One supervisor per project (1:1), so supervisor capacity == project capacity.
    project_supervisors = {pid: f"SUP::{pid}" for pid in projects}
    project_capacities = {pid: p.capacity for pid, p in projects.items()}
    supervisor_capacities = {f"SUP::{pid}": p.capacity for pid, p in projects.items()}

    # Each project ranks the students who chose it, by Priority (desc). Ties broken
    # by student_id so the matching is deterministic.
    supervisor_prefs: dict[str, list[str]] = {}
    for pid, project in projects.items():
        rankers = [sid for sid, prefs in student_prefs.items() if pid in prefs]
        rankers.sort(key=lambda sid: (-priority(students[sid], project, scarce), sid))
        supervisor_prefs[f"SUP::{pid}"] = rankers

    # Projects nobody ranked (e.g. the duplicate P_03, the filler P_08) legitimately
    # have empty preference lists — that is expected, not a problem to surface.
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*empty preference list.*")
        game = StudentAllocation.create_from_dictionaries(
            student_prefs,
            supervisor_prefs,
            project_supervisors,
            project_capacities,
            supervisor_capacities,
        )
        solved = game.solve(optimal="student")

    by_project: dict[str, list[str]] = {pid: [] for pid in projects}
    matched: set[str] = set()
    for project_player, student_players in solved.items():
        pid = str(project_player.name)
        for sp in student_players:
            by_project[pid].append(str(sp.name))
            matched.add(str(sp.name))

    unmatched = [sid for sid in students if sid not in matched]
    return Assignment(by_project=by_project, unmatched=unmatched)
