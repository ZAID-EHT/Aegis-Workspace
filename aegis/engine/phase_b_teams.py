"""Phase B (2/3) — maximin team formation.

The SPA stage (``phase_b_match``) assigns students to projects (one project = one
team). This module turns that assignment into scored teams and runs a
local-search **swap pass** whose only accepted move is one that raises the
*minimum* team score — making it mathematically impossible to stack all the weak
students into one doomed group. Students in under-sized groups (or unmatched by
SPA) fall to a faculty-reviewed exception pool.

Pure: depends on domain + config + phase A only.
"""

from __future__ import annotations

import statistics
from collections.abc import Sequence

from aegis.domain.models import Cohort, Project, Student, Team
from aegis.engine import config
from aegis.engine.phase_a_scoring import skill_matrix
from aegis.engine.phase_b_match import Assignment


def _students_by_id(cohort: Cohort) -> dict[str, Student]:
    return {s.student_id: s for s in cohort.students}


def _projects_by_id(cohort: Cohort) -> dict[str, Project]:
    return {p.project_id: p for p in cohort.projects}


def _strength(student: Student) -> float:
    """A student's overall ability: mean adjusted score across declared disciplines."""
    adjusted = skill_matrix(student).adjusted
    return statistics.fmean(adjusted.values()) if adjusted else 0.0


def _covers(members: Sequence[Student], discipline: str) -> bool:
    return any(
        skill_matrix(m).adjusted.get(discipline, 0.0) >= config.SKILL_TARGET for m in members
    )


def covers_critical(members: Sequence[Student], project: Project) -> bool:
    """Every critical skill of the project is met by at least one member (Â ≥ target)."""
    return all(_covers(members, d) for d in project.critical_skills)


def team_score(team: Team, cohort: Cohort) -> float:
    """Score a team 0..100 across the README team-score components (config-weighted)."""
    students = _students_by_id(cohort)
    projects = _projects_by_id(cohort)
    project = projects[team.project_id]
    members = [students[mid] for mid in team.member_ids]
    if not members:
        return 0.0

    # critical-skill coverage
    if project.critical_skills:
        covered = sum(1 for d in project.critical_skills if _covers(members, d))
        critical = covered / len(project.critical_skills)
    else:
        critical = 1.0

    # schedule: union of member availability over the project's required slots
    if project.meeting_slots:
        union = set().union(*(set(m.availability) for m in members))
        schedule = len(union & set(project.meeting_slots)) / len(project.meeting_slots)
    else:
        schedule = 1.0

    # role coverage: members whose preferred role serves a required skill
    def _role(student: Student) -> float:
        discipline = config.ROLE_DISCIPLINE.get(student.preferred_role or "")
        return 1.0 if discipline in project.required_skills else 0.3

    role = statistics.fmean(_role(m) for m in members)

    # preference satisfaction: how high the assigned project sat on each member's list
    def _pref(student: Student) -> float:
        prefs = student.preferred_projects
        if team.project_id in prefs:
            return config.PREF_SAT.get(prefs.index(team.project_id), config.PREF_SAT_DEFAULT)
        return config.PREF_SAT_DEFAULT

    preference = statistics.fmean(_pref(m) for m in members)

    # workload balance: evenness of member capacity (1 - coefficient of variation)
    caps = [m.capacity_hours for m in members]
    mean_cap = statistics.fmean(caps)
    if len(caps) > 1 and mean_cap > 0:
        workload = max(0.0, 1.0 - statistics.pstdev(caps) / mean_cap)
    else:
        workload = 1.0

    # experience balance: closeness of team strength to the cohort's average
    cohort_mean = statistics.fmean(_strength(s) for s in cohort.students)
    team_mean = statistics.fmean(_strength(m) for m in members)
    experience = 1.0 - min(abs(team_mean - cohort_mean) / cohort_mean, 1.0) if cohort_mean else 1.0

    weights = config.TEAM_SCORE_WEIGHTS
    return float(
        weights["critical"] * critical
        + weights["schedule"] * schedule
        + weights["role"] * role
        + weights["preference"] * preference
        + weights["workload"] * workload
        + weights["experience"] * experience
    )


def min_team_score(teams: Sequence[Team], cohort: Cohort) -> float:
    return min((team_score(t, cohort) for t in teams), default=0.0)


def _hard_ok(teams: Sequence[Team], cohort: Cohort) -> bool:
    students = _students_by_id(cohort)
    projects = _projects_by_id(cohort)
    low, high = config.TEAM_SIZE
    for team in teams:
        if not (low <= len(team.member_ids) <= high):
            return False
        members = [students[mid] for mid in team.member_ids]
        if not covers_critical(members, projects[team.project_id]):
            return False
        # SPA hard constraint: a student may only sit on a project they ranked.
        # The maximin swap must not strand anyone on an unranked project.
        if any(team.project_id not in students[mid].preferred_projects for mid in team.member_ids):
            return False
    return True


def maximin_swap(teams: Sequence[Team], cohort: Cohort) -> list[Team]:
    """Repeatedly accept the first cross-team 1-for-1 swap that raises the minimum
    team score without breaking a hard constraint. Returns new Team objects."""
    working = [
        Team(t.team_id, t.project_id, list(t.member_ids), t.health_score, t.status) for t in teams
    ]
    for _ in range(config.MAX_SWAP_ITERATIONS):
        current_min = min_team_score(working, cohort)
        improved = False
        for a in range(len(working)):
            for b in range(a + 1, len(working)):
                ta, tb = working[a], working[b]
                for ia, sid_a in enumerate(ta.member_ids):
                    for ib, sid_b in enumerate(tb.member_ids):
                        ta.member_ids[ia], tb.member_ids[ib] = sid_b, sid_a  # try swap
                        raises_min = min_team_score(working, cohort) > current_min
                        if _hard_ok(working, cohort) and raises_min:
                            improved = True
                            break
                        ta.member_ids[ia], tb.member_ids[ib] = sid_a, sid_b  # revert
                    if improved:
                        break
                if improved:
                    break
            if improved:
                break
        if not improved:
            break
    return working


def form_teams(cohort: Cohort, assignment: Assignment) -> tuple[list[Team], list[str]]:
    """Build teams from the SPA assignment, route under-sized/unmatched students to
    the exception pool, then run the maximin swap pass. Returns (teams, exception_pool)."""
    low, high = config.TEAM_SIZE
    teams: list[Team] = []
    exception_pool: list[str] = list(assignment.unmatched)
    for pid, members in assignment.by_project.items():
        if not members:
            continue
        if low <= len(members) <= high:
            teams.append(Team(team_id=f"T::{pid}", project_id=pid, member_ids=list(members)))
        else:
            exception_pool.extend(members)  # under-sized (or over) -> faculty review
    teams = maximin_swap(teams, cohort)
    return teams, sorted(exception_pool)
