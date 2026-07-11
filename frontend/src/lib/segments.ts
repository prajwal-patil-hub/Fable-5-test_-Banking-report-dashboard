import type { BankSegment } from "@/lib/api";

/** Indian banking cohort labels, shared by the top bar and benchmarking. */
export const SEGMENT_LABELS: Record<BankSegment, string> = {
  public: "Public Sector (PSU)",
  private: "Private Sector",
  sfb: "Small Finance Banks",
  foreign: "Foreign Banks",
  universal: "Universal",
};

export const SEGMENT_ORDER: BankSegment[] = [
  "public",
  "private",
  "sfb",
  "foreign",
  "universal",
];
