import type { ValidationStatus } from "@/lib/api";

const TONES = {
  gold: "border-gold/50 text-gold",
  bronze: "border-bronze/60 text-bronze",
  success: "border-success/60 text-success",
  warning: "border-warning/60 text-warning",
  risk: "border-risk/70 text-[#C98A8A]",
  neutral: "border-border text-text-secondary",
} as const;

export type BadgeTone = keyof typeof TONES;

export function Badge({
  tone = "neutral",
  children,
  className = "",
}: {
  tone?: BadgeTone;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 border px-2 py-0.5 text-[10px] uppercase tracking-[0.15em] ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

const VALIDATION_TONE: Record<ValidationStatus, BadgeTone> = {
  passed: "success",
  warning: "warning",
  failed: "risk",
  unvalidated: "neutral",
};

const VALIDATION_LABEL: Record<ValidationStatus, string> = {
  passed: "Validated",
  warning: "Warning",
  failed: "Failed",
  unvalidated: "Unvalidated",
};

export function ValidationBadge({
  status,
  className = "",
}: {
  status: ValidationStatus;
  className?: string;
}) {
  return (
    <Badge tone={VALIDATION_TONE[status]} className={className}>
      <span className="inline-block size-1.5 rounded-full bg-current" />
      {VALIDATION_LABEL[status]}
    </Badge>
  );
}
