"""The single source of every weight and threshold in AEGIS.

Hard rule: no magic numbers anywhere else in ``engine/``. Tuning the engine means
editing this file only — never formula code. Values mirror the build plan (§2);
keep them in sync with the README/PDF language used at viva.
"""

from __future__ import annotations

from typing import Final

# ── Phase A — evidence-confidence weighting (Â = L x C) ─────────────────────
# Keys map 1:1 to domain.SkillDeclaration.confidence_basis.
CONFIDENCE: Final[dict[str, float]] = {
    "verified": 1.0,  # institutional grade / assessed record
    "portfolio": 0.8,  # portfolio or prior work submitted
    "self_report": 0.6,  # self-report only (default, no LMS)
    "contradicted": 0.5,  # self-report contradicted by observed throughput
}

# ── Phase A — Student-Project Fit(i,p) ──────────────────────────────────────
FIT_WEIGHTS: Final[dict[str, float]] = {"skill": 0.50, "avail": 0.30, "role": 0.20}
SKILL_TARGET: Final[float] = 3.0  # adjusted Â at/above which a skill requirement is "met"
CRITICAL_SKILL_MULT: Final[float] = 2.0  # critical skills weighted x2 in SkillMatch
ROLE_MATCH: Final[dict[str, float]] = {"primary": 1.0, "secondary": 0.6, "none": 0.3}
# Maps a student's preferred role to the discipline it leans on (for RoleMatch).
ROLE_DISCIPLINE: Final[dict[str, str]] = {
    "tech_lead": "technical",
    "qa_lead": "technical",
    "ux_lead": "ux",
    "research_lead": "management",
    "doc_lead": "communication",
    "management": "management",
}

# ── Phase B — dedupe + match ────────────────────────────────────────────────
DEDUPE_THRESHOLD: Final[float] = 0.75  # cosine similarity -> flag for review
SIMILARITY_PRECISION: Final[int] = 4  # decimal places reported for cosine similarity
RARE_SKILL_BONUS: Final[int] = 15  # Priority bump when filling a scarce critical skill
RARE_SKILL_SCARCITY: Final[int] = 2  # a critical skill is "scarce" if held by <= this many

# ── Phase B — team formation ────────────────────────────────────────────────
TEAM_SIZE: Final[tuple[int, int]] = (4, 5)  # permitted (min, max)
# TeamScore components (weights sum to 100 -> score is 0..100). Mirrors the
# README "Team Score Components" table.
TEAM_SCORE_WEIGHTS: Final[dict[str, int]] = {
    "critical": 30,  # critical-skill coverage (Â >= target)
    "schedule": 20,  # common meeting-slot coverage
    "role": 15,  # role coverage across members
    "preference": 15,  # project-preference satisfaction
    "workload": 10,  # evenness of member capacity
    "experience": 10,  # closeness to cohort skill level (anti-sandbox)
}
# Preference satisfaction by rank index of the assigned project in a student's list.
PREF_SAT: Final[dict[int, float]] = {0: 1.0, 1: 0.7, 2: 0.4}
PREF_SAT_DEFAULT: Final[float] = 0.1  # ranked 4th+ or not listed
MAX_SWAP_ITERATIONS: Final[int] = 100  # local-search safety bound

# ── Phase B — task allocation / utilisation ─────────────────────────────────
UTIL_TARGET: Final[tuple[float, float]] = (0.7, 1.0)  # target utilisation band
OVERLOAD: Final[float] = 1.2  # U > 1.2 -> rebalance

# ── Phase C — health score (4-component; attendance folded into engagement) ──
# DEVIATION FROM SUBMITTED PDF: the PDF froze 5 components incl. attendance_rate.
# Per Integration Guide §7 we drop attendance (Calendar = RSVP, not presence; same
# source as engagement) and fold its 0.15 into engagement -> 0.30. Document at viva.
HEALTH_WEIGHTS: Final[dict[str, float]] = {
    "task_completion": 0.30,
    "workload_balance": 0.25,
    "engagement": 0.30,
    "milestone": 0.15,
}
HEALTH_BANDS: Final[dict[str, int]] = {"healthy": 75, "at_risk": 50}  # >=75 / 50-74 / <50

# ── Phase C — behavioural flags ─────────────────────────────────────────────
SYMPATHY_RATIO: Final[float] = 0.95  # contribution ratio on someone else's task
BURNOUT_MULT: Final[float] = 2.0  # U(i) >= 2x team avg -> sympathy-carry risk
GHOST_TIER: Final[dict[str, float]] = {
    "tier1_drop": 0.40,  # active footprint drops >= 40% -> soft nudge
    "tier2_days": 6,  # 6 consecutive zero-input days -> redistribute tasks
    "tier3_days": 10,  # 10 consecutive zero-input days -> faculty critical alert
}
