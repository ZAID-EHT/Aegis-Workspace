"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { motion, type Variants } from "framer-motion";
import {
  AlertTriangle,
  Copy,
  Inbox,
  Play,
  Loader2,
  ShieldCheck,
  UserRound,
  Users,
} from "lucide-react";

import { AppShell } from "@/components/aegis/app-shell";
import { EvidenceBar } from "@/components/aegis/evidence-bar";
import { HealthRing } from "@/components/aegis/health-ring";
import { PipelineStepper } from "@/components/aegis/pipeline-stepper";
import { Card } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { type RunResponse, type StudentProfile, type TeamView, runPipeline } from "@/lib/api";
import { makeLookups, titleCase, utilisationPct } from "@/lib/format";
import {
  PIPELINE_STEPS,
  RECOMMENDATION,
  SUMMARY,
  band,
  friendlyAlert,
} from "@/lib/labels";
import { sampleRun } from "@/lib/sample-run";

type Status = "idle" | "running" | "done";
type Lookups = ReturnType<typeof makeLookups>;

const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;
const asConfidence = (c: number): 1 | 0.8 | 0.6 | 0.5 =>
  near(c, 1) ? 1 : near(c, 0.8) ? 0.8 : near(c, 0.5) ? 0.5 : 0.6;

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];
const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.03 } },
};
const rise: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } },
};

// ── summary tile ────────────────────────────────────────────────────────────
function StatTile({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Users;
  label: string;
  value: React.ReactNode;
}) {
  return (
    <Card className="flex items-center gap-4 p-5">
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

// ── team card ─────────────────────────────────────────────────────────────────
function TeamCard({ team }: { team: TeamView }) {
  const status = band(team.band);
  const needsBalancing = team.unallocated_hours > 0 || team.members.some((m) => m.overloaded);
  return (
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
              <span
                className="shrink-0 text-xs font-medium"
                style={{ color: "var(--at-risk-ink)" }}
              >
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
}

// ── skill check (evidence-weighted) ──────────────────────────────────────────
function SkillCheck({ student }: { student: StudentProfile }) {
  const adjusted = student.skills.some((s) => s.corrected);
  return (
    <Card className="flex flex-col gap-5 p-6">
      <div>
        <h3 className="text-base font-semibold text-foreground">Skill check · {student.name}</h3>
        <p className="mt-1 text-sm text-muted-foreground">
          {adjusted
            ? "One self-reported skill was adjusted to match the evidence on record."
            : "Skills checked against the evidence on record."}
        </p>
      </div>
      <div className="flex flex-col gap-4">
        {student.skills.map((s) => (
          <EvidenceBar
            key={s.discipline}
            discipline={titleCase(s.discipline)}
            declared={s.declared}
            adjusted={s.adjusted}
            confidence={s.corrected ? 0.5 : asConfidence(s.confidence)}
          />
        ))}
      </div>
    </Card>
  );
}

// ── things to review ──────────────────────────────────────────────────────────
function ReviewPanel({ data, lookups }: { data: RunResponse; lookups: Lookups }) {
  const dup = data.duplicate_flags[0];
  const titleA = dup ? lookups.projectTitle(dup.project_a) : null;
  const titleB = dup ? lookups.projectTitle(dup.project_b) : null;
  return (
    <Card className="flex flex-col gap-5 p-6">
      <h3 className="text-base font-semibold text-foreground">Things to review</h3>

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
              <StatusBadge tone="at_risk">{Math.round(dup.similarity * 100)}% match</StatusBadge>
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
    </Card>
  );
}

// ── attention list (right rail) ──────────────────────────────────────────────
function AlertRow({ alert, lookups }: { alert: RunResponse["alerts"][number]; lookups: Lookups }) {
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

function AttentionList({ alerts, lookups }: { alerts: RunResponse["alerts"]; lookups: Lookups }) {
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

// ── page ─────────────────────────────────────────────────────────────────────
export default function Page() {
  const router = useRouter();
  const [status, setStatus] = React.useState<Status>("idle");
  const [stage, setStage] = React.useState(1);
  const [data, setData] = React.useState<RunResponse | null>(null);
  const [sample, setSample] = React.useState(false);

  const runAllocation = React.useCallback(async () => {
    setStatus("running");
    setStage(1);
    const ticker = setInterval(() => setStage((s) => Math.min(s + 1, 5)), 450);
    try {
      const result = await runPipeline();
      setSample(false);
      setData(result);
    } catch {
      // Live service unavailable — fall back to the clean sample dataset (clearly labelled).
      setSample(true);
      setData(sampleRun);
    } finally {
      clearInterval(ticker);
      setStage(5);
      setStatus("done");
    }
  }, []);

  const lookups = React.useMemo(
    () => (data ? makeLookups(data.student_profiles, data.teams) : null),
    [data],
  );
  const spotlight = data?.student_profiles.find((p) => p.skills.some((s) => s.corrected));
  const count = (b: string) => data?.teams.filter((t) => t.band === b).length ?? 0;

  return (
    <AppShell
      active="overview"
      onNavigate={(key) => router.push(key === "settings" ? "/admin" : "/")}
      rail={data && lookups ? <AttentionList alerts={data.alerts} lookups={lookups} /> : undefined}
    >
      <div className="flex flex-col gap-8">
        {/* header */}
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight text-foreground">Allocation overview</h1>
              {sample && (
                <span className="rounded-full bg-secondary px-2.5 py-1 text-xs font-medium text-muted-foreground">
                  Sample data
                </span>
              )}
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Balanced teams at a glance — and anything that needs your attention.
            </p>
          </div>
          <motion.button
            onClick={runAllocation}
            disabled={status === "running"}
            whileTap={{ scale: 0.97 }}
            transition={{ duration: 0.12, ease: EASE }}
            className="inline-flex items-center gap-2 rounded-2xl bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-shadow hover:shadow-card-lg disabled:opacity-60"
          >
            {status === "running" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {status === "running" ? "Working…" : "Run allocation"}
          </motion.button>
        </div>

        <PipelineStepper stages={PIPELINE_STEPS} current={stage} done={status === "done"} />

        {status === "idle" && (
          <Card className="border-dashed bg-secondary/30 p-12 text-center">
            <ShieldCheck className="mx-auto h-8 w-8 text-primary/60" />
            <p className="mx-auto mt-3 max-w-sm text-sm text-muted-foreground">
              Run an allocation to form balanced teams and surface anything that needs a closer look.
            </p>
          </Card>
        )}

        {data && lookups && (
          <>
            {/* summary */}
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="show"
              className="grid grid-cols-2 gap-4 lg:grid-cols-4"
            >
              <motion.div variants={rise}>
                <StatTile icon={Users} label={SUMMARY.teams} value={data.teams.length} />
              </motion.div>
              <motion.div variants={rise}>
                <StatTile icon={ShieldCheck} label={SUMMARY.onTrack} value={count("healthy")} />
              </motion.div>
              <motion.div variants={rise}>
                <StatTile
                  icon={AlertTriangle}
                  label={SUMMARY.attention}
                  value={count("at_risk") + count("critical")}
                />
              </motion.div>
              <motion.div variants={rise}>
                <StatTile icon={Inbox} label={SUMMARY.alerts} value={data.alerts.length} />
              </motion.div>
            </motion.div>

            {/* teams */}
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3"
            >
              {data.teams.map((t) => (
                <motion.div
                  key={t.team_id}
                  variants={rise}
                  whileHover={{ y: -4 }}
                  transition={{ type: "spring", stiffness: 380, damping: 30 }}
                >
                  <TeamCard team={t} />
                </motion.div>
              ))}
            </motion.div>

            {/* skill check + review */}
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 gap-5 lg:grid-cols-2"
            >
              <motion.div variants={rise}>
                {spotlight ? (
                  <SkillCheck student={spotlight} />
                ) : (
                  <Card className="flex h-full items-center p-6 text-sm text-muted-foreground">
                    No skill adjustments were needed this run.
                  </Card>
                )}
              </motion.div>
              <motion.div variants={rise}>
                <ReviewPanel data={data} lookups={lookups} />
              </motion.div>
            </motion.div>

            {/* attention list inline below xl */}
            <div className="xl:hidden">
              <AttentionList alerts={data.alerts} lookups={lookups} />
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
