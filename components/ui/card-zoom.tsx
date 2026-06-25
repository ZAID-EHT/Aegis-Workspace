"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

import { cn } from "@/lib/utils";

const EASE = [0.16, 1, 0.3, 1] as const;

/**
 * CardZoom — click a card to open an enlarged copy centered on the page (over a
 * dimmed, blurred backdrop) with its full detail. Closes on backdrop click, the ×
 * button, or Escape. The overlay is portalled to <body>; body scroll is locked
 * while open. Motion is reduced-motion safe via the app-wide MotionConfig.
 */
export function CardZoom({
  children,
  preview,
  className,
}: {
  children: React.ReactNode;
  preview: React.ReactNode;
  className?: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => setMounted(true), []);

  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      window.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open]);

  return (
    <>
      <div
        className={cn("cursor-pointer", className)}
        role="button"
        tabIndex={0}
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            setOpen(true);
          }
        }}
      >
        {children}
      </div>

      {mounted &&
        createPortal(
          <AnimatePresence>
            {open && (
              <motion.div
                className="fixed inset-0 z-[var(--z-modal)] grid place-items-center p-6"
                role="dialog"
                aria-modal="true"
                onClick={() => setOpen(false)}
                initial={false}
                transition={{ duration: 0.18, ease: EASE }}
              >
                <div className="absolute inset-0 bg-foreground/35" />
                <motion.div
                  className="relative w-full max-w-md"
                  onClick={(e) => e.stopPropagation()}
                  initial={{ scale: 0.98, y: 12 }}
                  animate={{ scale: 1, y: 0 }}
                  exit={{ scale: 0.98, y: 8 }}
                  transition={{ duration: 0.26, ease: EASE }}
                >
                  {preview}
                  <button
                    type="button"
                    aria-label="Close"
                    onClick={() => setOpen(false)}
                    className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-muted-foreground transition-colors hover:bg-secondary/80 hover:text-foreground"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>,
          document.body,
        )}
    </>
  );
}
