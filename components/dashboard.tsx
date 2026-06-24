"use client";

/** Reusable dashboard pieces shared by Overview / Teams / Alerts / Pipeline. */

import * as React from "react";
import { motion, type Variants } from "framer-motion";
import { AlertTriangle, Copy, Inbox, UserRound } from "lucide-react";

import { EvidenceBar } from "@/components/aegis/evidence-bar";
import { HealthRing } from "@/components/aegis/health-ring";
import { OpenWorkspaceButton } from "@/components/aegis/open-workspace-button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { CardZoom } from "@/components/ui/card-zoom";
import { Skeleton } from "@/components/ui/skeleton";
import type { AlertView, RunResponse, StudentProfile, TeamView } from "@/lib/api";
import { type makeLookups, titleCase, utilisationPct } from "@/lib/format";
import { HEALTH_COMPONENT, RECOMMENDATION, band, friendlyAlert } from "@/lib/labels";

export type Lookups = ReturnType<typeof makeLookups>;

// ── motion ────────────────────────────────────────────────────────────────────
export const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
export const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.03 } },
};
// Entrance reveal: SLIDE ONLY — never animate opacity, so content can never freeze
// invisible if the animation is gated by tab-focus/viewport. Visible by default;
// the slide is pure enhancement. Reduced-motion is handled globally (globals.css).
export const rise: Variants = {
  hidden: { y: 12 },
  show: { y: 0, transition: { duration: 0.45, ease: EASE } },
};

const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;
const asConfidence = (c: number): 1 | 0.8 | 0.6 | 0.5 =>
  near(c, 1) ? 1 : near(c, 0.8) ? 0.8 : near(c, 0.5) ? 0.5 : 0.6;

// ── summary tile ──────────────────────────────────────────────────────────────
export function StatTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Inbox;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <Card className="flex items-center gap-4 p-5 transition-shadow hover:shadow-card-lg">
      <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-2xl font-semibold tracking-tight tabular-nums text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </Card>
  );
}

// ── team card (hover for the full breakdown) ─────────────────────────────────
function memberRight(m: TeamView["members"][number]) {
  return m.overloaded ? (
    <span className="shrink-0 text-xs font-medium" style={{ color: "var(--at-risk-ink)" }}>
      Over capacity
    </span>
  ) : (
    <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
      {utilisationPct(m.utilisation)}
    </span>
  );
}

function TeamCardZoom({ team }: { team: TeamView }) {
  const status = band(team.band);
  const components = Object.entries(team.components ?? {});
  const needsBalancing = team.unallocated_hours > 0 || team.members.some((m) => m.overloaded);
  return (
    <Card className="flex flex-col gap-5 p-7">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-xl font-bold tracking-tight text-foreground">{team.project_title}</h3>
          <div className="mt-2">
            <StatusBadge tone={status.tone} dot>
              {status.label}
            </StatusBadge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Team health {Math.round(team.health_score)} of 100.
          </p>
        </div>
        <HealthRing value={team.health_score} size={104} strokeWidth={11} showBand={false} />
      </div>

      {components.length > 0 && (
        <div className="flex flex-col gap-2.5">
          {components.map(([key, value]) => {
            const pct = Math.min(100, Math.max(0, value * 100));
            return (
              <div key={key}>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{HEALTH_COMPONENT[key] ?? key}</span>
                  <span className="tabular-nums text-foreground">{Math.round(pct)}%</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${pct}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex flex-col gap-2 border-t border-border/60 pt-4">
        <p className="text-xs font-medium text-muted-foreground">Members</p>
        {team.members.map((m) => (
          <div key={m.student_id} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate text-foreground">{m.name}</span>
            {memberRight(m)}
          </div>
        ))}
      </div>

      {needsBalancing && (
        <p
          className="flex items-center gap-1.5 rounded-xl bg-[color-mix(in_oklch,var(--at-risk)_12%,transparent)] px-3 py-2 text-xs"
          style={{ color: "var(--at-risk-ink)" }}
        >
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {RECOMMENDATION.overload}
          {team.unallocated_hours > 0 ? ` · ${Math.round(team.unallocated_hours)} h unassigned` : ""}
        </p>
      )}
    </Card>
  );
}

export function TeamCard({ team }: { team: TeamView }) {
  const status = band(team.band);
  const needsBalancing = team.unallocated_hours > 0 || team.members.some((m) => m.overloaded);
  const summary = (
    <Card className="flex flex-col gap-5 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="truncate text-base font-semibold text-foreground">{team.project_title}</h3>
          <div className="mt-2">
            <StatusBadge tone={status.tone} dot>
              {status.label}
            </StatusBadge>
          </div>
        </div>
        <HealthRing value={team.health_score} size={84} strokeWidth={9} showBand={false} />
      </div>

      <div className="h-px bg-border/60" />

      <ul className="flex flex-col gap-2.5">
        {team.members.map((m) => (
          <li key={m.student_id} className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate text-foreground">{m.name}</span>
            {m.overloaded ? (
              <span className="shrink-0 text-xs font-medium" style={{ color: "var(--at-risk-ink)" }}>
                Over capacity
              </span>
            ) : (
              <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                {utilisationPct(m.utilisation)}
              </span>
            )}
          </li>
        ))}
      </ul>

      <OpenWorkspaceButton variant="link" className="self-end" />

      {needsBalancing && (
        <p
          className="flex items-center gap-1.5 rounded-xl bg-[color-mix(in_oklch,var(--at-risk)_12%,transparent)] px-3 py-2 text-xs"
          style={{ color: "var(--at-risk-ink)" }}
        >
          <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
          {RECOMMENDATION.overload}
        </p>
      )}
    </Card>
  );
  return <CardZoom preview={<TeamCardZoom team={team} />}>{summary}</CardZoom>;
}

// ── skill check (evidence-weighted, C=0.5 in amber) ──────────────────────────
export function SkillCheck({ student }: { student: StudentProfile }) {
  const adjusted = student.skills.some((s) => s.corrected);
  return (
    <Card>
      <CardHeader>
        <CardTitle>Skill check · {student.name}</CardTitle>
        <CardDescription>
          {adjusted
            ? "One self-reported skill was adjusted to match the evidence on record."
            : "Skills checked against the evidence on record."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {student.skills.map((s) => (
          <EvidenceBar
            key={s.discipline}
            discipline={titleCase(s.discipline)}
            declared={s.declared}
            adjusted={s.adjusted}
            confidence={s.corrected ? 0.5 : asConfidence(s.confidence)}
          />
        ))}
      </CardContent>
    </Card>
  );
}

// ── things to review (duplicate proposals + exceptions) ──────────────────────
export function ReviewPanel({ data, lookups }: { data: RunResponse; lookups: Lookups }) {
  const dup = data.duplicate_flags[0];
  const titleA = dup ? lookups.projectTitle(dup.project_a) : null;
  const titleB = dup ? lookups.projectTitle(dup.project_b) : null;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Things to review</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <div className="flex flex-col gap-2">
          <span className="flex items-center gap-2 text-sm text-foreground">
            <Copy className="h-4 w-4 text-muted-foreground" /> Similar project ideas
          </span>
        {dup ? (
          <div className="rounded-2xl bg-[color-mix(in_oklch,var(--at-risk)_11%,transparent)] p-3.5">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold" style={{ color: "var(--at-risk-ink)" }}>
                Two proposals overlap
              </span>
              <StatusBadge tone="at_risk"><span className="tabular-nums">{Math.round(dup.similarity * 100)}%</span> match</StatusBadge>
            </div>
            <ul className="mt-2 flex flex-col gap-1 text-sm text-foreground">
              <li className="truncate">{titleA ?? "Project A"}</li>
              <li className="truncate">{titleB ?? "Project B"}</li>
            </ul>
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">None flagged.</p>
        )}
      </div>

      <div className="flex items-center justify-between gap-3 border-t border-border/60 pt-4">
        <span className="flex items-center gap-2 text-sm text-foreground">
          <UserRound className="h-4 w-4 text-muted-foreground" /> Needs manual placement
        </span>
        <span className="text-sm text-muted-foreground">
          {data.exception_pool.length === 0 ? "Everyone placed" : `${data.exception_pool.length}`}
        </span>
        </div>
      </CardContent>
    </Card>
  );
}

// ── attention list (alerts) ───────────────────────────────────────────────────
export function AlertRow({ alert, lookups }: { alert: AlertView; lookups: Lookups }) {
  const a = friendlyAlert(alert, lookups);
  return (
    <motion.div
      variants={rise}
      className="rounded-2xl border border-border/60 bg-card p-4 shadow-card"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-semibold text-foreground">{a.title}</span>
        <StatusBadge tone={a.tone} dot>
          {a.severity}
        </StatusBadge>
      </div>
      <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{a.description}</p>
      {a.context && <p className="mt-1.5 text-xs font-medium text-foreground/70">{a.context}</p>}
    </motion.div>
  );
}

export function AttentionList({ alerts, lookups }: { alerts: AlertView[]; lookups: Lookups }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2 px-1">
        <Inbox className="h-4 w-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">Needs your attention</h2>
        <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
          {alerts.length}
        </span>
      </div>
      {alerts.length === 0 ? (
        <Card className="p-5 text-sm text-muted-foreground">All clear — nothing to review.</Card>
      ) : (
        <motion.div variants={stagger} initial="hidden" animate="show" className="flex flex-col gap-3">
          {alerts.map((a, i) => (
            <AlertRow key={`${a.trigger_type}-${i}`} alert={a} lookups={lookups} />
          ))}
        </motion.div>
      )}
    </div>
  );
}

// ── shared run button ─────────────────────────────────────────────────────────
export function SampleBadge() {
  return (
    <span className="rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-muted-foreground">
      Sample data
    </span>
  );
}

// ── loading skeletons (shape-matched to the real cards) ──────────────────────
export function StatTileSkeleton() {
  return (
    <Card className="flex items-center gap-4 p-5">
      <Skeleton className="h-11 w-11 rounded-2xl" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-6 w-10" />
        <Skeleton className="h-3 w-20" />
      </div>
    </Card>
  );
}

export function TeamCardSkeleton() {
  return (
    <Card className="flex flex-col gap-5 p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2.5">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
        <Skeleton className="h-[84px] w-[84px] rounded-full" />
      </div>
      <div className="h-px bg-border/60" />
      <div className="space-y-3">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-9" />
          </div>
        ))}
      </div>
    </Card>
  );
}

export function AlertRowSkeleton() {
  return (
    <div className="rounded-2xl border border-border/60 bg-card p-4 shadow-card">
      <div className="flex items-center justify-between gap-2">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="mt-2.5 h-3 w-full" />
      <Skeleton className="mt-1.5 h-3 w-2/3" />
    </div>
  );
}
