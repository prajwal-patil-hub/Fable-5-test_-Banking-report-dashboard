"use client";

import { ModulePage } from "@/components/ModulePage";

export default function AssetQualityPage() {
  return (
    <ModulePage
      config={{
        category: "asset_quality",
        label: "Module · Asset Quality",
        title: "Asset Quality",
        subtitle:
          "Non-performing assets, provisioning cover and credit cost discipline.",
        trendCodes: ["gnpa_ratio", "nnpa_ratio", "pcr"],
      }}
    />
  );
}
