"use client";

import { ModulePage } from "@/components/ModulePage";

export default function LiquidityPage() {
  return (
    <ModulePage
      config={{
        category: "liquidity",
        label: "Module · Liquidity",
        title: "Liquidity",
        subtitle:
          "Funding stability, liquid asset cover and deposit franchise quality.",
        trendCodes: ["lcr", "casa_ratio", "nsfr"],
      }}
    />
  );
}
