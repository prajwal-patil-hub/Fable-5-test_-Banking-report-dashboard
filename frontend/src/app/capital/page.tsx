"use client";

import { ModulePage } from "@/components/ModulePage";

export default function CapitalPage() {
  return (
    <ModulePage
      config={{
        category: "capital",
        label: "Module · Capital",
        title: "Capital Adequacy",
        subtitle:
          "Regulatory capital strength, buffers and leverage under Basel norms.",
        trendCodes: ["cet1_ratio", "tier1_ratio", "car"],
      }}
    />
  );
}
