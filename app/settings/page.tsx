"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { LogOut, Mail, Palette, ShieldCheck, UserRound } from "lucide-react";

import { AppShell } from "@/components/aegis/app-shell";
import { ThemeToggle } from "@/components/aegis/theme-toggle";
import { useAccessGuard } from "@/components/auth/role-guard";
import { useUser } from "@/components/auth/user-provider";
import { Card } from "@/components/ui/card";
import { routeFor } from "@/lib/nav";

function Row({
  icon: Icon,
  label,
  children,
}: {
  icon: typeof Mail;
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-4 py-3.5">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <Icon className="h-4 w-4" />
        <span>{label}</span>
      </div>
      <div className="min-w-0 text-right text-sm font-medium text-foreground">{children}</div>
    </div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const ready = useAccessGuard("account");
  const { user, signOut } = useUser();

  if (!ready) return null;

  return (
    <AppShell active="account" onNavigate={(key) => router.push(routeFor(key))}>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Your account and how the dashboard looks.
          </p>
        </div>

        <motion.div
          initial={{ y: 12 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.4 }}
          className="grid grid-cols-1 gap-5 lg:grid-cols-2"
        >
          <Card className="p-6">
            <div className="mb-2 flex items-center gap-3">
              <div className="h-11 w-11 shrink-0 rounded-full bg-gradient-to-br from-chart-1 to-chart-5" />
              <div className="min-w-0">
                <p className="truncate text-base font-semibold text-foreground">
                  {user?.name ?? "Account"}
                </p>
                <p className="truncate text-xs capitalize text-muted-foreground">
                  {user?.role ?? "member"}
                </p>
              </div>
            </div>
            <div className="divide-y divide-border/60">
              <Row icon={UserRound} label="Name">
                {user?.name ?? "—"}
              </Row>
              <Row icon={Mail} label="Email">
                <span className="truncate">{user?.email ?? "—"}</span>
              </Row>
              <Row icon={ShieldCheck} label="Role">
                <span className="capitalize">{user?.role ?? "—"}</span>
              </Row>
            </div>
          </Card>

          <Card className="flex flex-col p-6">
            <h2 className="text-sm font-semibold text-foreground">Appearance</h2>
            <div className="divide-y divide-border/60">
              <Row icon={Palette} label="Theme">
                <ThemeToggle />
              </Row>
            </div>
            <div className="mt-auto pt-6">
              <button
                onClick={signOut}
                className="inline-flex w-full items-center justify-center gap-2 rounded-2xl border border-border/60 bg-card px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-secondary"
              >
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          </Card>
        </motion.div>
      </div>
    </AppShell>
  );
}
