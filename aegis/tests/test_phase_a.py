"""Golden tests for Phase A — Â = L × C and Fit(i,p)."""

from __future__ import annotations

import pytest

from aegis.domain.models import Cohort, Project, SkillDeclaration, Student
from aegis.engine.phase_a_scoring import adjusted, fit, skill_matrix


def _student(cohort: Cohort, sid: str) -> Student:
    return next(s for s in cohort.students if s.student_id == sid)


def _project(cohort: Cohort, pid: str) -> Project:
    return next(p for p in cohort.projects if p.project_id == pid)


def _skill(student: Student, discipline: str) -> SkillDeclaration:
    return next(sk for sk in student.skills if sk.discipline == discipline)


# ── Â = L × C ────────────────────────────────────────────────────────────────
def test_dunning_kruger_correction(cohort: Cohort) -> None:
    """The hero: declared technical 5, contradicted evidence -> 5 × 0.5 = 2.5."""
    assert adjusted(_skill(_student(cohort, "STU_08"), "technical")) == pytest.approx(2.5)


def test_verified_not_punished(cohort: Cohort) -> None:
    """A verified 5 is trusted at full weight -> 5 × 1.0 = 5.0."""
    assert adjusted(_skill(_student(cohort, "STU_01"), "technical")) == pytest.approx(5.0)


def test_portfolio_and_selfreport_tiers(cohort: Cohort) -> None:
    assert adjusted(_skill(_student(cohort, "STU_03"), "ux")) == pytest.approx(4.0)  # 5 × 0.8
    assert adjusted(_skill(_student(cohort, "STU_05"), "technical")) == pytest.approx(1.8)  # 3×0.6


def test_skill_matrix_shape(cohort: Cohort) -> None:
    matrix = skill_matrix(_student(cohort, "STU_08"))
    assert matrix.adjusted["technical"] == pytest.approx(2.5)
    assert set(matrix.adjusted) == {"technical", "ux", "management", "communication"}


# ── Fit(i,p) ─────────────────────────────────────────────────────────────────
def test_fit_bounded(cohort: Cohort) -> None:
    for s in cohort.students:
        for p in cohort.projects:
            assert 0.0 <= fit(s, p) <= 100.0


def test_fit_rewards_real_coverage(cohort: Cohort) -> None:
    """On a technical-critical project, verified-strong STU_01 beats weak-tech STU_06."""
    p = _project(cohort, "P_01")  # critical skill: technical
    assert fit(_student(cohort, "STU_01"), p) > fit(_student(cohort, "STU_06"), p)


def test_inflated_claim_loses_when_the_skill_is_what_matters(cohort: Cohort) -> None:
    """The correction's effect on placement: on a project that needs ONLY technical
    (critical), STU_01's verified 5 (->5.0) outranks STU_08's inflated 5 (->2.5).

    Note: on a broad multi-skill project, Fit rewards coverage breadth, so an
    inflated-but-rounded profile can still rank well — the discount bites exactly
    where the discounted skill is the one the project depends on.
    """
    technical_only = Project(
        project_id="P_TEST",
        title="Technical-only",
        abstract="needs a strong, verified technical lead",
        capacity=4,
        required_skills=("technical",),
        critical_skills=("technical",),
        meeting_slots=("mon_am", "wed_pm"),
    )
    verified = _student(cohort, "STU_01")  # technical 5 verified -> 5.0
    inflated = _student(cohort, "STU_08")  # technical 5 contradicted -> 2.5
    assert fit(verified, technical_only) > fit(inflated, technical_only)


def test_fit_exact_values(cohort: Cohort) -> None:
    """Pin hand-computed Fit values so a swapped weight or uniform scaling fails loudly.

    STU_01 on P_01 (req technical[crit]/ux/communication; slots mon_am,wed_pm):
      SkillMatch = (2·min(5.0/3,1)+min(1.2/3,1)+min(1.8/3,1))/4 = (2.0+0.4+0.6)/4 = 0.75
      AvailMatch = 2/2 = 1.0 ; RoleMatch = 1.0 (tech_lead -> critical technical)
      Fit = 100·(0.5·0.75 + 0.3·1.0 + 0.2·1.0) = 87.5
    STU_08 (inflated technical -> 2.5, rounded ux/comm 2.4): Fit = 90.8333…
    """
    p = _project(cohort, "P_01")
    assert fit(_student(cohort, "STU_01"), p) == pytest.approx(87.5)
    assert fit(_student(cohort, "STU_08"), p) == pytest.approx(90.83333, abs=1e-4)


def test_vacuous_skill_requirement_is_satisfied(cohort: Cohort) -> None:
    """A project with no required skills doesn't penalise the SkillMatch component."""
    no_skill = Project(
        project_id="P_NONE",
        title="No skill constraint",
        abstract="anything",
        capacity=4,
        required_skills=(),
        meeting_slots=("mon_am", "wed_pm"),
    )
    s = _student(cohort, "STU_01")  # mon_am+wed_pm available, tech_lead
    # SkillMatch=1.0, AvailMatch=1.0, RoleMatch=0.3 (no critical/required skills to serve)
    assert fit(s, no_skill) == pytest.approx(100.0 * (0.5 + 0.3 + 0.2 * 0.3))
