"use client";

/**
 * AppShell — premium SaaS layout.
 *   desktop (md+) : floating rounded sidebar | main | optional right rail (xl)
 *   mobile (<md)  : top bar with logo + menu button → slide-in drawer
 *
 * Pass `rail` to show the contextual right column. Nav contract (active/onNavigate)
 * is unchanged so page logic keeps working.
 */

import * as React from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { GitBranch, LayoutGrid, LogOut, Menu, Settings, ShieldAlert, Users, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Logo } from "@/components/aegis/logo";
import { ThemeToggle } from "@/components/aegis/theme-toggle";
import { useUser } from "@/lib/use-user";
import { cn } from "@/lib/utils";

interface NavItem {
  key: string;
  label: string;
  icon: LucideIcon;
}

const NAV: NavItem[] = [
  { key: "overview", label: "Overview", icon: LayoutGrid },
  { key: "teams", label: "Teams", icon: Users },
  { key: "alerts", label: "Alerts", icon: ShieldAlert },
  { key: "pipeline", label: "Pipeline", icon: GitBranch },
  { key: "settings", label: "Governance", icon: Settings },
];

export interface AppShellProps {
  active?: string;
  onNavigate?: (key: string) => void;
  rail?: React.ReactNode;
  children: React.ReactNode;
}

function UserCard({
  name,
  role,
  onSignOut,
}: {
  name: string;
  role: string;
  onSignOut: () => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-2xl bg-secondary/60 p-2.5">
      <div className="h-9 w-9 shrink-0 rounded-full bg-gradient-to-br from-chart-1 to-chart-5" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">{name}</p>
        <p className="truncate text-xs capitalize text-muted-foreground">{role}</p>
      </div>
      <button
        onClick={onSignOut}
        aria-label="Sign out"
        title="Sign out"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

export function AppShell({ active = "overview", onNavigate, rail, children }: AppShellProps) {
  const reduce = useReducedMotion();
  const [drawer, setDrawer] = React.useState(false);
  const { user, signOut } = useUser();
  const displayName = user?.name ?? "Account";
  const displayRole = user?.role ?? "Member";

  const NavButton = ({ item, layoutKey }: { item: NavItem; layoutKey: string }) => {
    const isActive = item.key === active;
    const Icon = item.icon;
    return (
      <button
        onClick={() => {
          onNavigate?.(item.key);
          setDrawer(false);
        }}
        aria-current={isActive ? "page" : undefined}
        className={cn(
          "group relative flex w-full items-center gap-3 rounded-2xl px-3.5 py-2.5 text-sm font-medium transition-colors",
          isActive
            ? "text-primary"
            : "text-muted-foreground hover:bg-secondary/70 hover:text-foreground",
        )}
      >
        {isActive && (
          <motion.span
            layoutId={layoutKey}
            className="absolute inset-0 -z-10 rounded-2xl bg-primary/10 ring-1 ring-primary/15"
            transition={reduce ? { duration: 0 } : { type: "spring", stiffness: 400, damping: 32 }}
          />
        )}
        <Icon className="h-[1.15rem] w-[1.15rem] shrink-0" />
        <span>{item.label}</span>
      </button>
    );
  };

  const SidebarInner = ({ layoutKey }: { layoutKey: string }) => (
    <>
      <div className="px-2 py-3">
        <Logo />
      </div>
      <nav className="mt-2 flex flex-col gap-1">
        {NAV.map((i) => (
          <NavButton key={i.key} item={i} layoutKey={layoutKey} />
        ))}
      </nav>
      <div className="mt-auto flex items-center gap-2">
        <div className="min-w-0 flex-1">
          <UserCard name={displayName} role={displayRole} onSignOut={signOut} />
        </div>
        <ThemeToggle />
      </div>
    </>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* soft brand wash at the top of the canvas */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-x-0 top-0 -z-10 h-72"
        style={{
          background:
            "radial-gradient(60rem 24rem at 50% -8rem, color-mix(in oklch, var(--primary) 12%, transparent), transparent)",
        }}
      />

      {/* MOBILE TOP BAR */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-border/60 bg-background/80 px-4 py-3 backdrop-blur-xl md:hidden">
        <Logo />
        <div className="flex items-center gap-1.5">
          <ThemeToggle />
          <button
            onClick={() => setDrawer(true)}
            aria-label="Open menu"
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-card shadow-card"
          >
            <Menu className="h-5 w-5 text-foreground" />
          </button>
        </div>
      </header>

      {/* MOBILE DRAWER */}
      <AnimatePresence>
        {drawer && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-foreground/30 backdrop-blur-sm md:hidden"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setDrawer(false)}
            />
            <motion.aside
              className="fixed inset-y-0 left-0 z-50 flex w-[270px] flex-col gap-1 bg-sidebar p-4 shadow-card-lg md:hidden"
              initial={{ x: reduce ? 0 : "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: reduce ? 0 : "-100%" }}
              transition={{ type: "spring", stiffness: 360, damping: 36 }}
            >
              <div className="mb-1 flex items-center justify-between px-2 py-1">
                <Logo />
                <button
                  onClick={() => setDrawer(false)}
                  aria-label="Close menu"
                  className="flex h-9 w-9 items-center justify-center rounded-xl hover:bg-secondary"
                >
                  <X className="h-5 w-5 text-muted-foreground" />
                </button>
              </div>
              <nav className="mt-1 flex flex-col gap-1">
                {NAV.map((i) => (
                  <NavButton key={i.key} item={i} layoutKey="nav-active-mobile" />
                ))}
              </nav>
              <div className="mt-auto">
                <UserCard name={displayName} role={displayRole} onSignOut={signOut} />
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      <div className="mx-auto flex w-full max-w-[1600px] gap-5 p-4 sm:p-6">
        {/* DESKTOP SIDEBAR */}
        <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-[248px] shrink-0 flex-col rounded-[1.75rem] border border-border/60 bg-sidebar/85 p-4 shadow-card backdrop-blur-xl md:flex">
          <SidebarInner layoutKey="nav-active" />
        </aside>

        {/* MAIN */}
        <main className="min-w-0 flex-1">{children}</main>

        {/* RIGHT RAIL */}
        {rail && (
          <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-[340px] shrink-0 overflow-y-auto xl:block">
            {rail}
          </aside>
        )}
      </div>
    </div>
  );
}
