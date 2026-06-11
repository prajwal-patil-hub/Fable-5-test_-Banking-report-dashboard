import type { NarrativeSection } from "@/lib/api";
import { Card, SectionLabel } from "@/components/ui/Card";

function BulletList({
  items,
  marker = "—",
  markerClass = "text-gold",
}: {
  items: string[];
  marker?: string;
  markerClass?: string;
}) {
  return (
    <ul className="space-y-2.5">
      {items.map((item, i) => (
        <li key={i} className="flex gap-3 text-sm leading-relaxed text-text-secondary">
          <span className={`select-none font-serif ${markerClass}`}>{marker}</span>
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

/** Consulting-style narrative block: headline, diagnostic, takeaways, recommendations. */
export function NarrativePanel({ section }: { section: NarrativeSection }) {
  return (
    <Card className="p-7">
      <SectionLabel className="mb-3 text-gold/90">
        Executive Commentary
      </SectionLabel>
      <h3 className="mb-3 font-serif text-2xl leading-snug text-text-primary">
        {section.headline}
      </h3>
      <p className="mb-6 max-w-4xl text-sm leading-relaxed text-text-secondary">
        {section.commentary}
      </p>

      <div className="grid gap-8 lg:grid-cols-2">
        {section.takeaways.length > 0 ? (
          <div>
            <SectionLabel className="mb-3">Key Takeaways</SectionLabel>
            <BulletList items={section.takeaways} />
          </div>
        ) : null}
        {section.recommendations.length > 0 ? (
          <div>
            <SectionLabel className="mb-3">Recommendations</SectionLabel>
            <BulletList
              items={section.recommendations}
              marker="¶"
              markerClass="text-bronze"
            />
          </div>
        ) : null}
      </div>
    </Card>
  );
}
