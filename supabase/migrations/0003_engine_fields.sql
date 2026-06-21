-- ============================================================================
-- AEGIS — engine fields
-- The base schema (0001) holds the relational core. The allocation engine also
-- consumes a few fields that aren't in a plain records model: ranked preferences
-- and availability per student, skill requirements + meeting slots + sprint hours
-- per project, a simulated-day activity shape, and per-team progress for the
-- health score. This migration adds them. Safe to run after 0001 + 0002.
-- ============================================================================

-- ── students: ranked project prefs, availability slots, preferred role ───────
alter table students add column if not exists availability       text[] not null default '{}';
alter table students add column if not exists preferred_projects  text[] not null default '{}';
alter table students add column if not exists preferred_role      text;

-- ── projects: what each project needs + when it meets + sprint workload ──────
alter table projects add column if not exists required_skills text[] not null default '{}';
alter table projects add column if not exists critical_skills text[] not null default '{}';
alter table projects add column if not exists meeting_slots   text[] not null default '{}';
alter table projects add column if not exists total_hours      numeric not null default 0;

-- ── activity_log: the engine works in simulated sprint days with task ownership
--    (author = student_id; assigned_to = the student who owns the task) ────────
alter table activity_log add column if not exists sim_day     int;
alter table activity_log add column if not exists event_type  text;
alter table activity_log add column if not exists assigned_to uuid references students(id) on delete set null;
alter table activity_log add column if not exists task_id     text;

-- ── per-team progress that raw activity can't give (feeds the health score) ──
create table if not exists team_monitoring (
  project_id      text primary key references projects(id) on delete cascade,
  tasks_assigned  int not null default 0 check (tasks_assigned >= 0),
  tasks_done      int not null default 0 check (tasks_done >= 0),
  milestones_due  int not null default 0 check (milestones_due >= 0),
  milestones_done int not null default 0 check (milestones_done >= 0)
);

-- RLS: default-deny like every other table; readable by any authed user, written
-- only by the backend (service_role bypasses RLS).
alter table team_monitoring enable row level security;
create policy team_monitoring_read on team_monitoring for select using (auth.uid() is not null);
