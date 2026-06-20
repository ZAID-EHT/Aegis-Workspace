"""Phase 0 smoke test: the seed loads, and the engineered cases are present.

This is not a golden engine test (those arrive per phase). It guards the scaffold:
the seed parses into domain objects and contains the demo cases the later phases rely on.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from aegis.adapters.repo_seed import load_cohort
from aegis.domain.models import CONFIDENCE_BASES, DISCIPLINES, Cohort
from aegis.engine import config


def test_cohort_loads(cohort: Cohort) -> None:
    assert len(cohort.students) == 12
    assert len(cohort.projects) == 8
    assert len(cohort.activity_log) > 0


def test_confidence_tier_spread(cohort: Cohort) -> None:
    """Headline tier (basis of each student's highest declared skill) — exact counts.

    Build plan §3 demands >=2 verified, >=2 portfolio, >=3 self_report, 1-2
    contradicted. The engineered seed pins these at 3/3/4/2; assert exactly so
    that any drift in a student's evidence basis is caught.
    """
    headline: Counter[str] = Counter()
    for s in cohort.students:
        top = max(s.skills, key=lambda sk: sk.declared_level)
        headline[top.confidence_basis] += 1
    assert headline == Counter(
        {"self_report": 4, "verified": 3, "portfolio": 3, "contradicted": 2}
    )


def test_c05_hero_present(cohort: Cohort) -> None:
    """STU_08 declares technical 5 on contradicted evidence -> 5 x 0.5 = 2.5."""
    hero = next(s for s in cohort.students if s.student_id == "STU_08")
    tech = next(sk for sk in hero.skills if sk.discipline == "technical")
    assert tech.declared_level == 5
    assert tech.confidence_basis == "contradicted"
    adjusted = tech.declared_level * config.CONFIDENCE[tech.confidence_basis]
    assert adjusted == 2.5


def test_disciplines_are_closed(cohort: Cohort) -> None:
    """No skill or project references a discipline outside the four pillars."""
    for s in cohort.students:
        for sk in s.skills:
            assert sk.discipline in DISCIPLINES
    for p in cohort.projects:
        for d in (*p.required_skills, *p.critical_skills):
            assert d in DISCIPLINES


def test_confidence_bases_are_known(cohort: Cohort) -> None:
    for s in cohort.students:
        for sk in s.skills:
            assert sk.confidence_basis in config.CONFIDENCE


def test_confidence_vocab_in_sync() -> None:
    """domain.CONFIDENCE_BASES and engine.config.CONFIDENCE keys must stay 1:1.

    They are hand-maintained in two layers (vocab in domain, discount values in
    config). Drift between them silently breaks Phase A scoring.
    """
    assert set(CONFIDENCE_BASES) == set(config.CONFIDENCE)


def test_loader_rejects_unknown_vocab(tmp_path: Path) -> None:
    """A typo'd discipline/basis must fail loudly at load, not silently score 0."""
    bad = {
        "students": [
            {
                "student_id": "STU_X",
                "name": "Typo",
                "email": "x@aegis.test",
                "capacity_hours": 8.0,
                "skills": [
                    {"discipline": "techncial", "declared_level": 4, "confidence_basis": "verified"}
                ],
            }
        ],
        "projects": [],
        "activity_log": [],
    }
    path = tmp_path / "bad_seed.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="unknown discipline 'techncial'"):
        load_cohort(path)


def test_ghosting_case_present(cohort: Cohort) -> None:
    """STU_07 has zero activity across every sim-day -> Tier 3 later."""
    authors = {e.author_id for e in cohort.activity_log}
    assert "STU_07" not in authors


def test_sympathy_carry_case_present(cohort: Cohort) -> None:
    """Of all work on STU_05's tasks, >=95% is authored by someone else (STU_01).

    Keyed on task ownership (assigned_to == owner), so if STU_05 genuinely did
    his own work it would appear in the denominator and drop the ratio below the
    threshold — this assertion can actually fail, it is not a tautology. STU_05
    and his carrier STU_01 share team P_01 in the final allocation.
    """
    on_05 = [e for e in cohort.activity_log if e.assigned_to == "STU_05"]
    assert on_05, "expected events on STU_05's tasks"
    by_others = [e for e in on_05 if e.author_id != "STU_05"]
    ratio = len(by_others) / len(on_05)
    assert ratio >= config.SYMPATHY_RATIO
    # the carried student is still present via general activity -> not a ghost
    assert "STU_05" in {e.author_id for e in cohort.activity_log}


def test_activity_tagging_coherent(cohort: Cohort) -> None:
    """Every task-attributable event carries assigned_to, and vice-versa — so the
    sympathy-carry denominator can't be silently diluted by untagged task work."""
    for e in cohort.activity_log:
        assert (e.task_id is None) == (e.assigned_to is None)


def test_duplicate_pair_distinct_projects(cohort: Cohort) -> None:
    """The engineered near-duplicate pair exists as two separate submissions."""
    ids = {p.project_id for p in cohort.projects}
    assert {"P_02", "P_03"} <= ids


def test_oversubscription_first_choice(cohort: Cohort) -> None:
    """More students rank P_01 first than its capacity -> cascade later."""
    p01 = next(p for p in cohort.projects if p.project_id == "P_01")
    first_choice = sum(
        1 for s in cohort.students if s.preferred_projects and s.preferred_projects[0] == "P_01"
    )
    assert first_choice > p01.capacity


def test_health_weights_are_four_and_sum_to_one() -> None:
    assert set(config.HEALTH_WEIGHTS) == {
        "task_completion",
        "workload_balance",
        "engagement",
        "milestone",
    }
    assert abs(sum(config.HEALTH_WEIGHTS.values()) - 1.0) < 1e-9
