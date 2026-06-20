"""Phase A — evidence-weighted scoring and student-project fit.

Pure functions over domain objects. The headline formula is the anti-misreporting
correction ``Â = L × C``: a declared level is discounted by how much evidence
backs it, so a confident-but-unsupported 5/5 (contradicted -> 0.5) lands at 2.5,
while a verified 5/5 is trusted at 5.0.
"""

from __future__ import annotations

from aegis.domain.models import Project, SkillDeclaration, SkillMatrix, Student
from aegis.engine import config


def adjusted(decl: SkillDeclaration) -> float:
    """Â(i,k) = L(i,k) × C(i,k) for a single declared skill."""
    return decl.declared_level * config.CONFIDENCE[decl.confidence_basis]


def skill_matrix(student: Student) -> SkillMatrix:
    """Collapse a student's declarations into adjusted score per discipline.

    If a discipline is declared more than once, the strongest adjusted score wins.
    """
    adj: dict[str, float] = {}
    for decl in student.skills:
        score = adjusted(decl)
        if score > adj.get(decl.discipline, float("-inf")):
            adj[decl.discipline] = score
    return SkillMatrix(student_id=student.student_id, adjusted=adj)


def _skill_match(student_adj: dict[str, float], project: Project) -> float:
    """Weighted coverage of project skills using Â, each capped at "requirement met".

    Critical skills are weighted ×2 — covering the project's needs beats raw
    brilliance in one area. Returns 0..1.
    """
    if not project.required_skills:
        return 1.0  # no skill constraint -> vacuously satisfied (cf. _avail_match)
    numerator = 0.0
    denominator = 0.0
    for discipline in project.required_skills:
        weight = config.CRITICAL_SKILL_MULT if discipline in project.critical_skills else 1.0
        coverage = min(student_adj.get(discipline, 0.0) / config.SKILL_TARGET, 1.0)
        numerator += weight * coverage
        denominator += weight
    return numerator / denominator


def _avail_match(student: Student, project: Project) -> float:
    """Overlap of student slots with project meeting times ÷ required, capped at 1."""
    if not project.meeting_slots:
        return 1.0  # no scheduling constraint -> not a limiting factor
    overlap = len(set(student.availability) & set(project.meeting_slots))
    return min(overlap / len(project.meeting_slots), 1.0)


def _role_match(student: Student, project: Project) -> float:
    """1.0 if the student's preferred role serves a critical skill, 0.6 a required
    skill, 0.3 otherwise (or if no/unknown role)."""
    if student.preferred_role is None:
        return config.ROLE_MATCH["none"]
    discipline = config.ROLE_DISCIPLINE.get(student.preferred_role)
    if discipline is None:
        return config.ROLE_MATCH["none"]
    if discipline in project.critical_skills:
        return config.ROLE_MATCH["primary"]
    if discipline in project.required_skills:
        return config.ROLE_MATCH["secondary"]
    return config.ROLE_MATCH["none"]


def fit(student: Student, project: Project) -> float:
    """Fit(i,p) = 100 × [0.50·SkillMatch + 0.30·AvailMatch + 0.20·RoleMatch], 0..100."""
    adj = skill_matrix(student).adjusted
    weights = config.FIT_WEIGHTS
    score = (
        weights["skill"] * _skill_match(adj, project)
        + weights["avail"] * _avail_match(student, project)
        + weights["role"] * _role_match(student, project)
    )
    return 100.0 * score
