"""Pure domain types for AEGIS.

Frozen dataclasses for inputs (immutable cohort data loaded from seed); mutable
dataclasses for engine outputs (teams/results built up during a run). No I/O,
no logic, no third-party imports — this module is safe for ``engine/`` to depend on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Discipline vocabulary (the four skill pillars) ──────────────────────────
DISCIPLINES: tuple[str, ...] = (
    "technical",
    "ux",
    "management",
    "communication",
)

# Confidence-basis vocabulary — maps 1:1 to engine.config.CONFIDENCE keys.
CONFIDENCE_BASES: tuple[str, ...] = (
    "verified",
    "portfolio",
    "self_report",
    "contradicted",
)


# ── Inputs (immutable) ──────────────────────────────────────────────────────
@dataclass(frozen=True)
class SkillDeclaration:
    """One declared skill for one student, with the evidence behind it.

    ``confidence_basis`` selects the discount tier (engine.config.CONFIDENCE).
    The raw evidence fields are carried for display and the S_pillar formula.
    """

    discipline: str
    declared_level: float  # 1..5
    confidence_basis: str  # verified | portfolio | self_report | contradicted
    lms_grade: float | None = None
    portfolio_submitted: bool = False
    survey_score: float | None = None


@dataclass(frozen=True)
class Student:
    student_id: str
    name: str
    email: str
    capacity_hours: float
    skills: tuple[SkillDeclaration, ...]
    preferred_projects: tuple[str, ...] = ()
    preferred_teammate_id: str | None = None
    availability: tuple[str, ...] = ()  # time-slot labels, for AvailMatch
    preferred_role: str | None = None


@dataclass(frozen=True)
class Project:
    project_id: str
    title: str
    abstract: str  # full paragraph — TF-IDF dedupe needs real text
    capacity: int
    required_skills: tuple[str, ...] = ()
    critical_skills: tuple[str, ...] = ()  # subset weighted x2 / rare-skill bonus
    meeting_slots: tuple[str, ...] = ()
    supervisor_id: str | None = None
    total_hours: float = 0.0


@dataclass(frozen=True)
class ActivityEvent:
    """One workspace event in the seeded ``activity_log``.

    ``author_id`` did the work. ``assigned_to`` is the OWNER of the task the
    event is about — set on every task-attributable event (so an owner's own
    work has ``author_id == assigned_to``, and a carry has ``author_id !=
    assigned_to``). ``None`` means general/unattributed activity (e.g. a ping)
    not tied to a specific student's task. Sympathy-carry is then: of all events
    on a student's tasks, the share authored by someone else. Ghosting is the
    absence of any authored events across consecutive ``sim_day`` values.
    """

    author_id: str
    sim_day: int
    event_type: str  # commit | edit | ping
    assigned_to: str | None = None  # task owner; None => general/unattributed
    task_id: str | None = None


@dataclass(frozen=True)
class TeamMonitoring:
    """Per-team progress signals that aren't derivable from raw activity events.

    Keyed by project_id (one project = one team). Feeds the task_completion and
    milestone components of the health score; engagement and workload balance come
    from the ``activity_log``.
    """

    tasks_assigned: int
    tasks_done: int
    milestones_due: int
    milestones_done: int


@dataclass(frozen=True)
class Cohort:
    """Everything one allocation run consumes."""

    students: tuple[Student, ...]
    projects: tuple[Project, ...]
    activity_log: tuple[ActivityEvent, ...]
    monitoring: dict[str, TeamMonitoring] = field(default_factory=dict)


# ── Outputs (built up by the engine) ────────────────────────────────────────
@dataclass(frozen=True)
class SkillMatrix:
    """Phase A output: adjusted scores (Â = L x C) per discipline for a student."""

    student_id: str
    adjusted: dict[str, float]


@dataclass
class Task:
    task_id: str
    team_id: str
    title: str
    hours_estimated: float
    assignee_id: str | None = None
    status: str = "todo"


@dataclass
class Team:
    team_id: str
    project_id: str
    member_ids: list[str] = field(default_factory=list)
    health_score: float | None = None
    status: str = "formed"


@dataclass(frozen=True)
class HealthReport:
    team_id: str
    score: float  # 0..100
    band: str  # healthy | at_risk | critical
    components: dict[str, float]


@dataclass(frozen=True)
class Alert:
    severity: str  # INFO | WARNING | CRITICAL
    trigger_type: str  # ghosting_tier3 | sympathy_carry | burnout | duplicate_project | ...
    detail: str
    team_id: str | None = None
    student_id: str | None = None


@dataclass(frozen=True)
class DuplicateFlag:
    project_a: str
    project_b: str
    similarity: float


@dataclass(frozen=True)
class TaskAllocation:
    team_id: str
    project_id: str
    hours: dict[str, float]  # student_id -> assigned hours (after the guard)
    utilisation: dict[str, float]  # student_id -> U(i) = assigned / capacity
    overloaded: list[str] = field(default_factory=list)
    unallocated_hours: float = 0.0  # hours shed by the overload guard
    zero_capacity: list[str] = field(default_factory=list)  # members with no capacity


@dataclass
class AllocationResult:
    """The single object ``engine.pipeline`` returns for a full A->B->C run."""

    teams: list[Team] = field(default_factory=list)
    task_allocations: list[TaskAllocation] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    health: list[HealthReport] = field(default_factory=list)
    skill_matrices: list[SkillMatrix] = field(default_factory=list)
    duplicate_flags: list[DuplicateFlag] = field(default_factory=list)
    exception_pool: list[str] = field(default_factory=list)  # unplaceable student_ids
