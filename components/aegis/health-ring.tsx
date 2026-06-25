"use client";

/**
 * HealthRing — animated progress donut with a count-up centre value.
 * Maps the reference's "My learning" donuts onto AEGIS team-health and
 * contribution scores. Colour is driven by the health band, never decoration.
 *
 * <HealthRing value={82} label="Team health" />
 */

import * as React from "react";
import { motion, useMotionValue, useReducedMotion, animate } from "framer-motion";
import { cn } from "@/lib/utils";

type Band = "healthy" | "at-risk" | "critical";

function bandFor(value: number): Band {
  if (value >= 75) return "healthy";
  if (value >= 50) return "at-risk";
  return "critical";
}

const BAND_STROKE: Record<Band, string> = {
  healthy: "var(--healthy)",
  "at-risk": "var(--at-risk)",
  critical: "var(--critical)",
};

const BAND_LABEL: Record<Band, string> = {
  healthy: "Healthy",
  "at-risk": "At risk",
  critical: "Critical",
};

export interface HealthRingProps {
  value: number;            // 0–100
  label?: string;
  size?: number;            // px
  strokeWidth?: number;     // px
  showBand?: boolean;
  className?: string;
}

export function HealthRing({
  value,
  label,
  size = 132,
  strokeWidth = 12,
  showBand = true,
  className,
}: HealthRingProps) {
  const clamped = Math.max(0, Math.min(100, value));
  const band = bandFor(clamped);
  const reduce = useReducedMotion();

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const target = circumference * (1 - clamped / 100);

  // Initialize at the real score so first paint never flashes "0 Health".
  const mv = useMotionValue(clamped);
  const [display, setDisplay] = React.useState(clamped);
  React.useEffect(() => {
    setDisplay(Math.round(clamped));
    mv.set(clamped);
    const controls = animate(mv, clamped, {
      duration: reduce ? 0 : 0.9,
      ease: [0.22, 1, 0.36, 1],
      onUpdate: (v) => setDisplay(Math.round(v)),
    });
    return controls.stop;
  }, [clamped, mv, reduce]);

  return (
    <div className={cn("inline-flex flex-col items-center gap-2", className)}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--muted)"
            strokeWidth={strokeWidth}
          />
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={BAND_STROKE[band]}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: reduce ? target : circumference }}
            animate={{ strokeDashoffset: target }}
            transition={{ duration: reduce ? 0 : 1, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="nums text-3xl font-semibold tabular-nums text-foreground">
            {display}
          </span>
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Health
          </span>
        </div>
      </div>

      {label && (
        <span className="text-sm font-medium text-foreground">{label}</span>
      )}
      {showBand && (
        <span
          className="rounded-full px-2.5 py-0.5 text-xs font-medium"
          style={{
            backgroundColor: `color-mix(in oklch, ${BAND_STROKE[band]} 14%, transparent)`,
            color: BAND_STROKE[band],
          }}
        >
          {BAND_LABEL[band]}
        </span>
      )}
    </div>
  );
}
