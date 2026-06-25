"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Copy,
  Database,
  FolderOpen,
  GitBranch,
  Scale,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";

import { Logo } from "@/components/aegis/logo";
import { ThemeToggle } from "@/components/aegis/theme-toggle";
import { IntroSplash } from "@/components/aegis/intro-splash";

const EASE = [0.16, 1, 0.3, 1] as const;
// Slide-only reveals (no opacity) so nothing can freeze invisible on load.
const rise = { hidden: { y: 14 }, show: { y: 0, transition: { duration: 0.55, ease: EASE } } };
const stagger = { hidden: {}, show: { transition: { staggerChildren: 0.07, delayChildren: 0.05 } } };

const FEATURES = [
  {
    icon: Sparkles,
    title: "Evidence-weighted skills",
    body: "Self-ratings are checked against real evidence, so confidence is earned — not just claimed.",
  },
  {
    icon: Scale,
    title: "Balanced teams",
    body: "Every team gets the critical skills it needs, with workload shared fairly across members.",
  },
  {
    icon: GitBranch,
    title: "Early warnings",
    body: "Disengagement, uneven effort, and at-risk teams surface before they derail a project.",
  },
  {
    icon: ShieldCheck,
    title: "Tamper-evident governance",
    body: "Every privileged action is recorded in a hash-chained log you can verify end to end.",
  },
];

/** Decorative "proof" card floated around the hero (desktop only). */
function FloatCard({
  className,
  delay = "0s",
  children,
}: {
  className?: string;
  delay?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      aria-hidden
      style={{ animationDelay: delay }}
      className={`animate-float absolute hidden w-max select-none rounded-2xl border border-border/60 bg-card p-3.5 shadow-card-lg lg:block ${className ?? ""}`}
    >
      {children}
    </div>
  );
}

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-muted/50 px-3 py-4 sm:px-5 sm:py-6">
      <IntroSplash />
      <div className="mx-auto max-w-6xl">
        {/* framed product card on the grey page */}
        <div className="relative overflow-hidden rounded-[1.75rem] border border-border/70 bg-card shadow-xl">
          {/* drifting "shader-style" aurora */}
          <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
            <div
              className="animate-aurora absolute -left-24 -top-32 h-[34rem] w-[34rem] rounded-full opacity-60 blur-3xl"
              style={{
                background:
                  "radial-gradient(closest-side, color-mix(in oklch, var(--primary) 26%, transparent), transparent)",
              }}
            />
            <div
              className="animate-aurora absolute -right-24 -top-16 h-[30rem] w-[30rem] rounded-full opacity-50 blur-3xl"
              style={{
                background:
                  "radial-gradient(closest-side, color-mix(in oklch, var(--chart-5) 24%, transparent), transparent)",
                animationDelay: "-9s",
              }}
            />
          </div>

          {/* nav */}
          <header className="relative flex items-center justify-between gap-4 px-5 py-4 sm:px-8">
            <Logo />
            <nav className="hidden items-center gap-7 text-sm font-medium text-muted-foreground md:flex">
              <a href="#features" className="transition-colors hover:text-foreground">Features</a>
              <a href="#integrations" className="transition-colors hover:text-foreground">Integrations</a>
              <Link href="/privacy" className="transition-colors hover:text-foreground">Privacy</Link>
            </nav>
            <div className="flex items-center gap-1.5 sm:gap-2.5">
              <ThemeToggle />
              <Link
                href="/login"
                className="hidden rounded-xl px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground sm:inline-flex"
              >
                Sign in
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-card transition-shadow hover:shadow-card-lg"
              >
                Get started
              </Link>
            </div>
          </header>

          {/* hero with floating proof cards */}
          <motion.section
            variants={stagger}
            initial="hidden"
            animate="show"
            className="relative px-5 pb-24 pt-14 text-center sm:px-8 sm:pb-32 sm:pt-20"
          >
            {/* — top-left: team health — */}
            <FloatCard className="left-5 top-8 -rotate-2 xl:left-12" delay="0s">
              <div className="flex items-center gap-3">
                <div
                  className="flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold tabular-nums"
                  style={{
                    color: "var(--healthy-ink)",
                    background: "color-mix(in oklch, var(--healthy) 16%, transparent)",
                  }}
                >
                  84
                </div>
                <div className="text-left">
                  <p className="text-xs font-medium text-foreground">Team health</p>
                  <p className="text-xs" style={{ color: "var(--healthy-ink)" }}>On track</p>
                </div>
              </div>
            </FloatCard>

            {/* — top-right: duplicate flag — */}
            <FloatCard className="right-5 top-12 rotate-2 xl:right-14" delay="-3s">
              <div className="flex items-center gap-2.5">
                <Copy className="h-4 w-4" style={{ color: "var(--at-risk-ink)" }} />
                <div className="text-left">
                  <p className="text-xs font-medium text-foreground">Similar proposals</p>
                  <p className="text-xs tabular-nums" style={{ color: "var(--at-risk-ink)" }}>
                    0.911 match · held for review
                  </p>
                </div>
              </div>
            </FloatCard>

            {/* — bottom-left: teams formed — */}
            <FloatCard className="bottom-12 left-6 -rotate-1 xl:left-16" delay="-1.5s">
              <div className="flex items-center gap-2.5">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary">
                  <Users className="h-4 w-4" />
                </div>
                <div className="text-left">
                  <p className="text-xs font-medium text-foreground">15 teams + 1 pool</p>
                  <p className="text-xs text-muted-foreground">from 70 students</p>
                </div>
              </div>
            </FloatCard>

            {/* — bottom-right: integrations — */}
            <FloatCard className="bottom-14 right-6 rotate-2 xl:right-16" delay="-4.5s">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Integrations
              </p>
              <div className="flex items-center gap-2">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-primary">
                  <Database className="h-4 w-4" />
                </span>
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-primary">
                  <FolderOpen className="h-4 w-4" />
                </span>
              </div>
            </FloatCard>

            {/* center hero */}
            <motion.div variants={rise} className="mx-auto flex max-w-2xl flex-col items-center">
              <span className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card px-3.5 py-1.5 text-xs font-medium text-muted-foreground shadow-card">
                <span className="h-1.5 w-1.5 rounded-full bg-[var(--healthy)]" />
                Capstone allocation, done fairly
              </span>
              <h1 className="mt-6 text-balance text-4xl font-bold tracking-tight sm:text-6xl sm:leading-[1.02]">
                <span className="text-foreground">Fair capstone teams,</span>
                <br />
                <span className="text-muted-foreground">backed by evidence</span>
              </h1>
              <p className="mx-auto mt-5 max-w-lg text-pretty text-lg leading-relaxed text-muted-foreground">
                AEGIS turns skill claims, preferences, and activity into balanced teams — and flags
                trouble before it derails a project, with an auditable governance layer.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
                <Link
                  href="/signup"
                  className="inline-flex items-center gap-2 rounded-2xl bg-primary px-6 py-3 text-sm font-semibold text-primary-foreground shadow-card transition-all hover:-translate-y-0.5 hover:shadow-card-lg"
                >
                  Create your account
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 rounded-2xl border border-border bg-card px-6 py-3 text-sm font-semibold text-foreground shadow-card transition-shadow hover:shadow-card-lg"
                >
                  Sign in
                </Link>
              </div>
            </motion.div>
          </motion.section>
        </div>

        {/* integrations strip */}
        <section id="integrations" className="px-2 pt-12 text-center">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Runs on your stack
          </p>
          <div className="mt-4 flex flex-wrap items-center justify-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-2xl border border-border/60 bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-card">
              <Database className="h-4 w-4 text-primary" /> Supabase &amp; Postgres RLS
            </span>
            <span className="inline-flex items-center gap-2 rounded-2xl border border-border/60 bg-card px-4 py-2.5 text-sm font-medium text-foreground shadow-card">
              <FolderOpen className="h-4 w-4 text-primary" /> Google Drive workspaces
            </span>
          </div>
        </section>

        {/* features */}
        <section id="features" className="px-2 pb-16 pt-16">
          <motion.div
            variants={stagger}
            initial="hidden"
            animate="show"
            className="grid grid-cols-1 gap-x-10 gap-y-9 sm:grid-cols-2"
          >
            {FEATURES.map((f) => (
              <motion.div key={f.title} variants={rise} className="flex gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <f.icon className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-semibold text-foreground">{f.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{f.body}</p>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </section>

        {/* footer */}
        <footer className="flex flex-col items-center justify-between gap-3 border-t border-border/60 px-2 py-6 text-sm text-muted-foreground sm:flex-row">
          <span>© 2026 AEGIS · Capstone allocation engine</span>
          <div className="flex items-center gap-5">
            <Link href="/privacy" className="transition-colors hover:text-foreground">Privacy Policy</Link>
            <Link href="/login" className="transition-colors hover:text-foreground">Sign in</Link>
          </div>
        </footer>
      </div>
    </main>
  );
}
