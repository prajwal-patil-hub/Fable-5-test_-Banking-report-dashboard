"use client";

import { useEffect, type ReactNode } from "react";

/** Right-hand slide-over panel with a dimmed overlay. */
export function Drawer({
  open,
  onClose,
  title,
  label,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  label?: string;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  return (
    <div
      className={`fixed inset-0 z-50 ${open ? "" : "pointer-events-none"}`}
      aria-hidden={!open}
    >
      {/* Overlay */}
      <div
        className={`absolute inset-0 bg-ink/70 backdrop-blur-[2px] transition-opacity duration-300 ${
          open ? "opacity-100" : "opacity-0"
        }`}
        onClick={onClose}
      />
      {/* Panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`absolute inset-y-0 right-0 flex w-[480px] max-w-full flex-col border-l border-border bg-ink-2 shadow-2xl transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-start justify-between border-b border-border px-6 py-5">
          <div>
            {label ? (
              <div className="mb-1 text-xs uppercase tracking-[0.2em] text-gold/90">
                {label}
              </div>
            ) : null}
            <h2 className="font-serif text-xl text-text-primary">{title}</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="mt-1 border border-border px-2.5 py-1 text-xs uppercase tracking-[0.15em] text-text-secondary transition-colors hover:border-gold hover:text-gold"
          >
            Esc
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-6 py-6">{children}</div>
      </aside>
    </div>
  );
}
