"use client";

/** Student workspace — a student sees ONLY their own team: the running allocation
 *  result for their team, its health, who they're working with, and why they were
 *  placed there. No other teams, no cross-team management (that's staff-only). */

import * as React from "react";
import { motion } from "framer-motion";
import { AlertTriangle, Sparkles, Target, Users } from "lucide-react";

import { HealthRing } from "@/components/aegis/health-ring";
import { OpenWorkspaceButton } from "@/components/aegis/open-workspace-button";
import { SampleDataBanner } from "@/components/aegis/sample-data-banner";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EASE, SampleBadge } from "@/components/dashboard";
import type { StudentProfile, TeamView } from "@/lib/api";
import { utilisationPct } from "@/lib/format";
import { HEALTH_COMPONENT, RECOMMENDATION, band } from "@/lib/labels";

// Slide-only entrance (no opacity) so content can never freeze invisible if the
// animation is gated by tab-focus/viewport. Visible by default; slide is enhancement.
const rise = {
  hidden: { y: 12 },
  show: { y: 0, transition: { duration: 0.45, ease: EASE } },
};

const BAND_COLOR: Record<string, string> = {
  healthy: "var(--healthy)",
  at_risk: "var(--at-risk)",
  critical: "var(--critical)",
};

/** Pull a friendly "preference #N" out of the engine rationale without leaking IDs. */
function preferenceRank(rationale?: string): number | null {
  const m = rationale?.match(/preference #(\d+)/i);
  return m ? Number(m[1]) : null;
}

function HealthBar({ score, bandKey }: { score: number; bandKey: string }) {
  const pct = Math.min(100, Math.max(0, score));
  const color = BAND_COLOR[bandKey] ?? BAND_COLOR.at_risk;
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-xs">
        <span className="font-medium text-muted-foreground">Team health</span>
        <span className="tabular-nums font-semibold text-foreground">{Math.round(score)} / 100</span>
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: EASE }}
        />
      </div>
    </div>
  );
}

function PlacementCard({
  team,
  profile,
}: {
  team: TeamView;
  profile: StudentProfile | null;
}) {
  const rank = preferenceRank(profile?.rationale);
  const fit = profile?.fit;
  return (
    <Card className="flex flex-col gap-4 p-6">
      <div className="flex items-center gap-2">
        <Target className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">Why you&apos;re here</h3>
      </div>
      <p className="text-sm leading-relaxed text-muted-foreground">
        You were placed on <span className="font-medium text-foreground">{team.project_title}</span>
        {rank ? (
          <>
            {" "}
            — your{" "}
            <span className="font-medium text-foreground">
              #{rank} preference
            </span>
          </>
        ) : null}
        .
      </p>
      {fit != null && (
        <div>
          <div className="mb-1.5 flex items-center justify-between text-xs">
            <span className="font-medium text-muted-foreground">Your fit for this project</span>
            <span className="tabular-nums font-semibold text-foreground">{Math.round(fit)}%</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${Math.min(100, Math.max(0, fit))}%` }}
            />
          </div>
        </div>
      )}
    </Card>
  );
}

function MyTeamCard({ team }: { team: TeamView }) {
  const status = band(team.band);
  const components = Object.entries(team.components ?? {});
  const needsBalancing = team.unallocated_hours > 0 || team.members.some((m) => m.overloaded);

  return (
    <Card className="flex flex-col gap-6 p-7">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2 className="text-xl font-bold tracking-tight text-foreground">{team.project_title}</h2>
          <div className="mt-2">
            <StatusBadge tone={status.tone} dot>
              {status.label}
            </StatusBadge>
          </div>
          <OpenWorkspaceButton variant="button" className="mt-3" />
        </div>
        <HealthRing value={team.health_score} size={104} strokeWidth={11} showBand={false} />
      </div>

      <HealthBar score={team.health_score} bandKey={team.band} />

      {components.length > 0 && (
        <div className="flex flex-col gap-2.5 border-t border-border/60 pt-4">
          <p className="text-xs font-medium text-muted-foreground">What goes into this score</p>
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

function TeammatesCard({ team, studentId }: { team: TeamView; studentId: string | null }) {
  return (
    <Card className="flex flex-col gap-4 p-6">
      <div className="flex items-center gap-2">
        <Users className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold text-foreground">My team</h3>
        <span className="ml-auto rounded-full bg-secondary px-2 py-0.5 text-xs text-muted-foreground">
          {team.members.length}
        </span>
      </div>
      <ul className="flex flex-col gap-2.5">
        {team.members.map((m) => {
          const isMe = studentId != null && m.student_id === studentId;
          return (
            <li key={m.student_id} className="flex items-center justify-between gap-3 text-sm">
              <span className="truncate text-foreground">
                {m.name}
                {isMe && (
                  <span className="ml-2 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                    You
                  </span>
                )}
              </span>
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
          );
        })}
      </ul>
    </Card>
  );
}

function EmptyState({ name }: { name: string }) {
  return (
    <Card className="border-dashed bg-secondary/30 p-12 text-center">
      <Users className="mx-auto h-8 w-8 text-primary/60" />
      <p className="mx-auto mt-3 max-w-sm text-sm text-muted-foreground">
        {name ? `${name}, you` : "You"} aren&apos;t assigned to a team yet. Once allocation runs,
        your team and its health will appear here.
      </p>
    </Card>
  );
}

function WorkspaceSkeleton() {
  return (
    <Card className="flex flex-col gap-5 p-7">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2.5">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-6 w-24 rounded-full" />
        </div>
        <Skeleton className="h-[104px] w-[104px] rounded-full" />
      </div>
      <Skeleton className="h-2.5 w-full rounded-full" />
      <div className="space-y-3 border-t border-border/60 pt-4">
        {[0, 1, 2, 3].map((i) => (
          <div key={i} className="flex items-center justify-between">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-4 w-9" />
          </div>
        ))}
      </div>
    </Card>
  );
}

export function StudentWorkspace({
  team,
  profile,
  studentId,
  name,
  loading,
  sample,
}: {
  team: TeamView | null;
  profile: StudentProfile | null;
  studentId: string | null;
  name: string;
  loading: boolean;
  sample: boolean;
}) {
  const firstName = name?.split(" ")[0] ?? "";
  return (
    <div className="flex flex-col gap-8">
      {sample && <SampleDataBanner />}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">My workspace</h1>
            {sample && <SampleBadge />}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {firstName ? `Welcome back, ${firstName}. ` : ""}Your team and how the work is shared.
          </p>
        </div>
        {team && (
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <Sparkles className="h-3.5 w-3.5" /> Allocation complete
          </span>
        )}
      </div>

      {loading ? (
        <WorkspaceSkeleton />
      ) : team ? (
        <motion.div
          variants={{ show: { transition: { staggerChildren: 0.06 } } }}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 gap-5 lg:grid-cols-3"
        >
          <motion.div variants={rise} className="lg:col-span-2">
            <MyTeamCard team={team} />
          </motion.div>
          <div className="flex flex-col gap-5">
            <motion.div variants={rise}>
              <PlacementCard team={team} profile={profile} />
            </motion.div>
            <motion.div variants={rise}>
              <TeammatesCard team={team} studentId={studentId} />
            </motion.div>
          </div>
        </motion.div>
      ) : (
        <EmptyState name={name} />
      )}
    </div>
  );
}
