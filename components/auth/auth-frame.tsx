"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";

import { ThemeToggle } from "@/components/aegis/theme-toggle";

/** Shared centered frame for the login / signup pages, on the brand wash. */
export function AuthFrame({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-background">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(48rem 28rem at 50% -8%, color-mix(in oklch, var(--primary) 16%, transparent), transparent)",
        }}
      />
      <div className="absolute right-4 top-4">
        <ThemeToggle />
      </div>

      <div className="mx-auto flex min-h-screen w-full max-w-[26rem] flex-col justify-center px-5 py-12">
        <div className="mb-8 flex justify-center">
          <Link href="/" aria-label="AEGIS — home" className="inline-block">
            <Image
              src="/aegis-logo.png"
              alt="AEGIS — capstone allocation"
              width={144}
              height={144}
              priority
              className="h-auto w-28 object-contain sm:w-32 dark:rounded-2xl dark:bg-white dark:p-3 dark:ring-1 dark:ring-black/5"
            />
          </Link>
        </div>

        <motion.div
          initial={{ y: 14 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="rounded-3xl border border-border/60 bg-card p-8 shadow-card-lg"
        >
          <h1 className="text-2xl font-bold tracking-tight text-foreground">{title}</h1>
          {subtitle && <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{subtitle}</p>}
          <div className="mt-6">{children}</div>
        </motion.div>

        {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
      </div>
    </main>
  );
}

/** Shared field style for the role <select> (other fields use the Input component). */
export const FIELD =
  "w-full rounded-xl border border-border bg-background px-3.5 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none transition-shadow focus-visible:ring-2 focus-visible:ring-primary/40";
