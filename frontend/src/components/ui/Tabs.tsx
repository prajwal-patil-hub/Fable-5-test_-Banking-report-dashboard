"use client";

export interface TabItem {
  key: string;
  label: string;
}

export function Tabs({
  items,
  active,
  onChange,
  className = "",
}: {
  items: TabItem[];
  active: string;
  onChange: (key: string) => void;
  className?: string;
}) {
  return (
    <div
      role="tablist"
      className={`flex items-center gap-1 border-b border-border ${className}`}
    >
      {items.map((item) => {
        const isActive = item.key === active;
        return (
          <button
            key={item.key}
            role="tab"
            type="button"
            aria-selected={isActive}
            onClick={() => onChange(item.key)}
            className={`-mb-px border-b px-4 py-2.5 text-xs uppercase tracking-[0.2em] transition-colors ${
              isActive
                ? "border-gold text-gold"
                : "border-transparent text-text-secondary hover:text-text-primary"
            }`}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
