"use client";

import { exportUrl } from "@/lib/api";
import { useBank } from "@/context/BankContext";
import { Card, PageHeading, SectionLabel } from "@/components/ui/Card";
import { PageGate } from "@/components/PageGate";

const DELIVERABLES: {
  kind: "excel" | "pptx" | "pdf";
  ext: string;
  title: string;
  description: string;
  contents: string[];
}[] = [
  {
    kind: "excel",
    ext: ".xlsx",
    title: "Excel Data Pack",
    description:
      "The full KPI warehouse for the selected institution and fiscal year — every value with lineage and validation status, ready for further modelling.",
    contents: ["All KPI values & YoY deltas", "Source lineage per figure", "Validation results"],
  },
  {
    kind: "pptx",
    ext: ".pptx",
    title: "Board Presentation",
    description:
      "A board-ready slide deck: headline indicators, peer standing and the executive narrative, composed for the boardroom.",
    contents: ["Headline KPI summary", "Peer benchmarking charts", "Module-by-module commentary"],
  },
  {
    kind: "pdf",
    ext: ".pdf",
    title: "Annual Intelligence Report",
    description:
      "The long-form intelligence dossier — diagnostics, takeaways and recommendations across all five analytical modules.",
    contents: ["Executive summary", "Full narrative sections", "Data assurance appendix"],
  },
];

export default function ReportsPage() {
  const { bank } = useBank();
  return (
    <>
      <PageHeading
        label="Library · Deliverables"
        title="Executive Deliverables"
        subtitle={
          bank
            ? `Premium artefacts generated from the ${bank.name} intelligence warehouse for the selected fiscal year.`
            : "Premium artefacts generated from the intelligence warehouse."
        }
      />
      <PageGate>
        {(bank, fiscalYear) => (
          <div className="grid grid-cols-3 gap-6">
            {DELIVERABLES.map((d) => (
              <Card
                key={d.kind}
                className="flex flex-col p-8 transition-colors hover:border-gold/50"
              >
                <div className="mb-6 flex items-baseline justify-between">
                  <span className="font-serif text-4xl text-gold/80">
                    {d.ext}
                  </span>
                  <SectionLabel>{fiscalYear}</SectionLabel>
                </div>
                <h3 className="mb-3 font-serif text-2xl text-text-primary">
                  {d.title}
                </h3>
                <p className="mb-6 text-sm leading-relaxed text-text-secondary">
                  {d.description}
                </p>
                <ul className="mb-8 space-y-2">
                  {d.contents.map((line) => (
                    <li
                      key={line}
                      className="flex items-center gap-2.5 text-xs text-text-secondary"
                    >
                      <span className="size-1 rotate-45 bg-bronze" />
                      {line}
                    </li>
                  ))}
                </ul>
                <div className="mt-auto">
                  <div className="gilt-rule mb-6" />
                  <a
                    href={exportUrl(d.kind, bank.id, fiscalYear)}
                    className="block border border-gold/70 px-4 py-3 text-center text-xs uppercase tracking-[0.25em] text-gold transition-colors hover:bg-gold hover:text-ink"
                  >
                    Download {d.ext}
                  </a>
                  <p className="mt-3 text-center text-[10px] uppercase tracking-[0.15em] text-text-secondary/60">
                    {bank.code} · {fiscalYear}
                  </p>
                </div>
              </Card>
            ))}
          </div>
        )}
      </PageGate>
    </>
  );
}
