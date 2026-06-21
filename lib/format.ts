/** Presentation-only formatting — turns engine codes/ids into human, professional copy.
 *  No data is changed; this is purely how values are shown in the UI. */

import type { AlertView, StudentProfile, TeamView } from "@/lib/api";

export type Tone = "healthy" | "at_risk" | "critical" | "info" | "neutral";

/** Health band -> label + tone. */
export const BAND_LABEL: Record<string, string> = {
  healthy: "Healthy",
  at_risk: "At risk",
  critical: "Critical",
};

export function bandTone(band: string): Tone {
  if (band === "healthy") return "healthy";
  if (band === "at_risk") return "at_risk";
  return "critical";
}

/** Alert severity -> tone + friendly label. */
export function severityTone(severity: string): Tone {
  if (severity === "CRITICAL") return "critical";
  if (severity === "WARNING") return "at_risk";
  return "info";
}

export const SEVERITY_LABEL: Record<string, string> = {
  CRITICAL: "Critical",
  WARNING: "Warning",
  INFO: "Info",
};

/** Engine trigger code -> human headline. */
const TRIGGER_LABEL: Record<string, string> = {
  ghosting_tier3: "Disengagement — critical",
  ghosting_tier2: "Disengagement — escalating",
  ghosting_tier1: "Disengagement — early signs",
  sympathy_carry: "Uneven workload",
  burnout: "Burnout risk",
  health_critical: "Team health — critical",
  health_at_risk: "Team health — at risk",
  duplicate_project: "Duplicate proposal",
};

export function triggerLabel(trigger: string): string {
  return TRIGGER_LABEL[trigger] ?? trigger.replace(/_/g, " ");
}

/** Capitalise a discipline like "technical" -> "Technical". */
export function titleCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Utilisation as a friendly percentage. */
export function utilisationPct(u: number | null): string {
  return u == null ? "—" : `${Math.round(u * 100)}%`;
}

/** Build id -> human-name / team -> project-title lookups from a run result. */
export function makeLookups(students: StudentProfile[], teams: TeamView[]) {
  const nameOf = new Map(students.map((s) => [s.student_id, s.name]));
  const teamLabelOf = new Map(teams.map((t) => [t.team_id, t.project_title]));
  const projectTitleOf = new Map(teams.map((t) => [t.project_id, t.project_title]));
  return {
    name: (id: string | null) => (id ? (nameOf.get(id) ?? id) : ""),
    teamLabel: (id: string | null) => (id ? (teamLabelOf.get(id) ?? "Team") : ""),
    projectTitle: (id: string | null) => (id ? (projectTitleOf.get(id) ?? null) : null),
  };
}

/** A human one-liner for an alert, built from its parts (ignores the raw code string). */
export function describeAlert(
  alert: AlertView,
  lookups: ReturnType<typeof makeLookups>,
): { title: string; context: string } {
  const who = lookups.name(alert.student_id);
  const team = lookups.teamLabel(alert.team_id);
  const title = triggerLabel(alert.trigger_type);
  let context = "";
  switch (alert.trigger_type) {
    case "ghosting_tier3":
    case "ghosting_tier2":
    case "ghosting_tier1":
      context = who ? `${who} · ${team}` : team;
      break;
    case "sympathy_carry":
      context = who ? `${who}'s work is being absorbed by a teammate · ${team}` : team;
      break;
    case "burnout":
      context = who ? `${who} is carrying well above the team average · ${team}` : team;
      break;
    default:
      context = team;
  }
  return { title, context };
}
