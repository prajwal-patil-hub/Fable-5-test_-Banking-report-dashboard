"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_SECTIONS: {
  label: string;
  items: { href: string; label: string }[];
}[] = [
  {
    label: "Intelligence",
    items: [{ href: "/", label: "Executive Overview" }],
  },
  {
    label: "Modules",
    items: [
      { href: "/financial", label: "Financial Performance" },
      { href: "/asset-quality", label: "Asset Quality" },
      { href: "/capital", label: "Capital Adequacy" },
      { href: "/liquidity", label: "Liquidity" },
      { href: "/operations", label: "Operations" },
    ],
  },
  {
    label: "Market",
    items: [{ href: "/benchmarking", label: "Peer Benchmarking" }],
  },
  {
    label: "Library",
    items: [
      { href: "/documents", label: "Documents" },
      { href: "/reports", label: "Executive Deliverables" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-ink-2">
      {/* Wordmark */}
      <Link href="/" className="block border-b border-border px-6 py-7">
        <div className="font-serif text-2xl tracking-[0.25em] text-gold">
          SOVEREIGN
        </div>
        <div className="mt-1.5 text-[10px] uppercase tracking-[0.3em] text-text-secondary">
          Indian Banking Intelligence
        </div>
      </Link>

      <nav className="flex-1 overflow-y-auto px-4 py-6">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-7">
            <div className="mb-2.5 px-2 text-[10px] uppercase tracking-[0.3em] text-bronze">
              {section.label}
            </div>
            <ul className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href;
                return (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className={`flex items-center gap-2.5 border-l px-3 py-2 text-[13px] transition-colors ${
                        active
                          ? "border-gold bg-card/70 text-gold"
                          : "border-transparent text-text-secondary hover:border-border hover:text-text-primary"
                      }`}
                    >
                      <span
                        className={`inline-block size-1 rotate-45 ${
                          active ? "bg-gold" : "bg-border"
                        }`}
                      />
                      {item.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </nav>

      <div className="border-t border-border px-6 py-4 text-[10px] uppercase tracking-[0.2em] text-text-secondary/70">
        Private &amp; Confidential
      </div>
    </aside>
  );
}
