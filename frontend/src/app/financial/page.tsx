"use client";

import { ModulePage } from "@/components/ModulePage";

export default function FinancialPage() {
  return (
    <ModulePage
      config={{
        category: "financial",
        label: "Module · Financial",
        title: "Financial Performance",
        subtitle:
          "Profitability, margins and earnings power across the fiscal year.",
        trendCodes: ["roe", "roa", "nim"],
      }}
    />
  );
}
