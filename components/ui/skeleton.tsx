import * as React from "react";

import { cn } from "@/lib/utils";

/** Skeleton — pulsing placeholder block. The global prefers-reduced-motion rule
 *  stops the pulse, leaving a static placeholder. */
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("animate-pulse rounded-xl bg-muted", className)} {...props} />;
}

export { Skeleton };
