"""Project deduplication gate — TF-IDF cosine similarity on abstracts.

Submitted abstracts are vectorised and compared pairwise. Any pair at or above
``DEDUPE_THRESHOLD`` is *flagged for faculty review* (not hard-blocked) so an
override path is preserved. This lives in the engine and depends only on
scikit-learn + config — no I/O.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from aegis.domain.models import DuplicateFlag, Project
from aegis.engine import config


def duplicate_flags(projects: Sequence[Project]) -> list[DuplicateFlag]:
    """Return flagged near-duplicate project pairs, highest similarity first.

    Returns [] for <2 projects or when no abstract carries content words (an
    all-stopword / empty corpus would otherwise raise "empty vocabulary").
    """
    if len(projects) < 2:
        return []
    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        matrix = vectorizer.fit_transform(p.abstract for p in projects)
    except ValueError:
        # empty vocabulary (every abstract is blank or stopwords-only) -> nothing to compare
        return []
    sims = cosine_similarity(matrix)

    flags: list[DuplicateFlag] = []
    for i, j in combinations(range(len(projects)), 2):
        similarity = float(sims[i, j])
        if similarity >= config.DEDUPE_THRESHOLD:
            flags.append(
                DuplicateFlag(
                    project_a=projects[i].project_id,
                    project_b=projects[j].project_id,
                    similarity=round(similarity, config.SIMILARITY_PRECISION),
                )
            )
    # deterministic order: highest similarity first, then by id pair to break ties.
    flags.sort(key=lambda f: (-f.similarity, f.project_a, f.project_b))
    return flags
