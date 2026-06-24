"use client";

import { ExternalLink } from "lucide-react";

/** "Open workspace" — opens the team's Google Drive workspace in a new tab.
 *  Option B (WORKSPACE_GAP.md): a presentational link to ONE configured demo
 *  folder — no per-team provisioning, no drive_folder_id, no Google API. Renders
 *  nothing when the URL is unset, so the demo can never show a dead button. */
export function OpenWorkspaceButton({
  variant = "button",
  className,
}: {
  variant?: "button" | "link";
  className?: string;
}) {
  const url = process.env.NEXT_PUBLIC_DEMO_WORKSPACE_URL;
  if (!url) return null; // graceful: hidden when unconfigured (never a broken link)

  if (variant === "link") {
    return (
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className={`inline-flex items-center gap-1.5 text-xs font-medium text-primary transition-opacity hover:opacity-80 ${className ?? ""}`}
      >
        <ExternalLink className="h-3.5 w-3.5" /> Workspace
      </a>
    );
  }
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-flex items-center gap-2 rounded-2xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-card transition-shadow hover:shadow-card-lg ${className ?? ""}`}
    >
      <ExternalLink className="h-4 w-4" /> Open workspace
    </a>
  );
}
