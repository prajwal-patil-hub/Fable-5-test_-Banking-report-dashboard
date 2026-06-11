import type { HTMLAttributes, ReactNode } from "react";

export function Card({
  className = "",
  children,
  ...rest
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`border border-border bg-card/80 ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

/** Uppercase, letter-spaced small-caps section label. */
export function SectionLabel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`text-xs uppercase tracking-[0.2em] text-text-secondary ${className}`}
    >
      {children}
    </div>
  );
}

/** Page-level heading block: tracked label + large serif title. */
export function PageHeading({
  label,
  title,
  subtitle,
}: {
  label: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <header className="mb-8">
      <SectionLabel className="mb-2 text-gold/90">{label}</SectionLabel>
      <h1 className="font-serif text-3xl text-text-primary">{title}</h1>
      {subtitle ? (
        <p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-secondary">
          {subtitle}
        </p>
      ) : null}
      <div className="gilt-rule mt-6" />
    </header>
  );
}
