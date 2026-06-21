"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { AlertTriangle, ShieldCheck, Users } from "lucide-react";

import { AppShell } from "@/components/aegis/app-shell";
import {
  SampleBadge,
  StatTile,
  StatTileSkeleton,
  TeamCard,
  TeamCardSkeleton,
  rise,
  stagger,
} from "@/components/dashboard";
import { SUMMARY } from "@/lib/labels";
import { routeFor } from "@/lib/nav";
import { useRun } from "@/lib/use-run";

export default function TeamsPage() {
  const router = useRouter();
  const { data, sample } = useRun(true);
  const count = (b: string) => data?.teams.filter((t) => t.band === b).length ?? 0;

  return (
    <AppShell active="teams" onNavigate={(key) => router.push(routeFor(key))}>
      <div className="flex flex-col gap-8">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Teams</h1>
            {sample && <SampleBadge />}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Every team formed this run, with its health and how the work is shared.
          </p>
        </div>

        {!data ? (
          <>
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
              {[0, 1, 2].map((i) => (
                <StatTileSkeleton key={i} />
              ))}
            </div>
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              {[0, 1, 2, 3, 4, 5].map((i) => (
                <TeamCardSkeleton key={i} />
              ))}
            </div>
          </>
        ) : (
          <>
            <motion.div
              variants={stagger}
              initial="hidden"
              animate="show"
              className="grid grid-cols-2 gap-4 lg:grid-cols-3"
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
            </motion.div>

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
          </>
        )}
      </div>
    </AppShell>
  );
}
