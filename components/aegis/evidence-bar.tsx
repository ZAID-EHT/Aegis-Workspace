"use client";

/**
 * EvidenceBar — makes Â = L × C legible.
 * A faint "declared" ghost bar sits behind the solid "adjusted" bar, with the
 * confidence factor as a chip. When C = 0.5 (claim contradicted by throughput),
 * the chip turns amber — that's the Dunning-Kruger correction firing, visible.
 *
 * <EvidenceBar discipline="Technical" declared={5} adjusted={2.5} confidence={0.5} />
 */

import * as React from "react";
import { motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

const C_BASIS: Record<string, string> = {
  "1": "Verified",
  "0.8": "Portfolio",
  "0.6": "Self-reported",
  "0.5": "Adjusted after review",
};

export interface EvidenceBarProps {
  discipline: string;
  declared: number;      // 1–5
  adjusted: number;      // 1–5 (= declared × confidence)
  confidence: 1 | 0.8 | 0.6 | 0.5;
  max?: number;          // scale max, default 5
  className?: string;
}

export function EvidenceBar({
  discipline,
  declared,
  adjusted,
  confidence,
  max = 5,
  className,
}: EvidenceBarProps) {
  const reduce = useReducedMotion();
  const declaredPct = Math.max(0, Math.min(100, (declared / max) * 100));
  const adjustedPct = Math.max(0, Math.min(100, (adjusted / max) * 100));
  const corrected = confidence === 0.5;
  const basis = C_BASIS[String(confidence)] ?? "Self-report";

  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-foreground">{discipline}</span>
        <span
          className={cn(
            "nums rounded-full px-2 py-0.5 text-xs font-medium",
            corrected
              ? "bg-[color-mix(in_oklch,var(--at-risk)_16%,transparent)] text-[var(--at-risk-ink)]"
              : "bg-muted text-muted-foreground",
          )}
          title={basis}
        >
          {basis}
        </span>
      </div>

      <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-muted">
        {/* declared — faint ghost showing the original (inflated) claim */}
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-foreground/12"
          initial={{ width: reduce ? `${declaredPct}%` : 0 }}
          animate={{ width: `${declaredPct}%` }}
          transition={{ duration: reduce ? 0 : 0.5, ease: [0.22, 1, 0.36, 1] }}
        />
        {/* adjusted — the trusted, evidence-weighted value */}
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full bg-primary"
          initial={{ width: reduce ? `${adjustedPct}%` : 0 }}
          animate={{ width: `${adjustedPct}%` }}
          transition={{ duration: reduce ? 0 : 0.7, ease: [0.22, 1, 0.36, 1], delay: reduce ? 0 : 0.08 }}
        />
      </div>

      <div className="nums flex justify-between text-xs text-muted-foreground">
        <span>Claimed {declared.toFixed(1)}</span>
        <span className={cn(corrected && "font-medium text-foreground")}>
          Counted {adjusted.toFixed(1)}
        </span>
      </div>
    </div>
  );
}
