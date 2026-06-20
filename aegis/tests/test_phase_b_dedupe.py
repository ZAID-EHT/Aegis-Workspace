"""Golden tests for the TF-IDF cosine dedupe gate."""

from __future__ import annotations

from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from aegis.domain.models import Cohort
from aegis.engine import config
from aegis.engine.phase_b_dedupe import duplicate_flags


def test_engineered_pair_is_flagged(cohort: Cohort) -> None:
    flags = duplicate_flags(cohort.projects)
    pairs = {frozenset((f.project_a, f.project_b)) for f in flags}
    assert frozenset(("P_02", "P_03")) in pairs


def test_all_flags_meet_threshold(cohort: Cohort) -> None:
    for flag in duplicate_flags(cohort.projects):
        assert flag.similarity >= config.DEDUPE_THRESHOLD


def test_no_accidental_duplicates(cohort: Cohort) -> None:
    """Only the engineered pair trips the gate — distinct topics stay below 0.75."""
    pairs = {frozenset((f.project_a, f.project_b)) for f in duplicate_flags(cohort.projects)}
    assert pairs == {frozenset(("P_02", "P_03"))}


def test_flags_sorted_desc(cohort: Cohort) -> None:
    flags = duplicate_flags(cohort.projects)
    sims = [f.similarity for f in flags]
    assert sims == sorted(sims, reverse=True)


def test_fewer_than_two_projects_no_flags(cohort: Cohort) -> None:
    assert duplicate_flags(cohort.projects[:1]) == []
    assert duplicate_flags(()) == []


def test_gate_calibration(cohort: Cohort) -> None:
    """Pin the similarity band so the gate's calibration is itself tested.

    The engineered pair must sit well above the 0.75 threshold, and every other
    pair well below it — otherwise a mis-tuned threshold (or a P_03 edit toward
    distinct wording) would silently change which pairs flag.
    """
    projects = cohort.projects
    matrix = TfidfVectorizer(stop_words="english").fit_transform(p.abstract for p in projects)
    sims = cosine_similarity(matrix)
    engineered = -1.0
    runner_up = -1.0
    for i, j in combinations(range(len(projects)), 2):
        pair = {projects[i].project_id, projects[j].project_id}
        value = float(sims[i, j])
        if pair == {"P_02", "P_03"}:
            engineered = value
        else:
            runner_up = max(runner_up, value)
    assert engineered > 0.90  # clearly a duplicate
    assert runner_up < 0.60  # everything else is clearly distinct
    assert runner_up < config.DEDUPE_THRESHOLD < engineered  # threshold sits in the gap
