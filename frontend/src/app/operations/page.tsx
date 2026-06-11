"use client";

import { ModulePage } from "@/components/ModulePage";

export default function OperationsPage() {
  return (
    <ModulePage
      config={{
        category: "operations",
        label: "Module · Operations",
        title: "Operations",
        subtitle:
          "Cost discipline, productivity and distribution network efficiency.",
        trendCodes: ["cost_to_income", "cost_of_funds", "branches"],
      }}
    />
  );
}
