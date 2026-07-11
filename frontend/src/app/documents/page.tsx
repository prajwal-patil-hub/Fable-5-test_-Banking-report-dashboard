"use client";

import { useRef, useState, type FormEvent } from "react";
import { api, type BankSegment, type UploadResponse } from "@/lib/api";
import { useApi } from "@/lib/hooks";
import { useBank } from "@/context/BankContext";
import { formatCount, formatDateTime, humanize } from "@/lib/format";
import { SEGMENT_LABELS, SEGMENT_ORDER } from "@/lib/segments";
import { Card, PageHeading, SectionLabel } from "@/components/ui/Card";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";

const DOC_TYPES = [
  "annual_report",
  "investor_presentation",
  "financial_statements",
  "basel_disclosures",
  "other",
];

function statusTone(status: string): BadgeTone {
  const s = status.toLowerCase();
  if (["processed", "ready", "completed", "complete", "ok"].includes(s))
    return "success";
  if (["processing", "pending", "queued", "uploading"].includes(s))
    return "warning";
  if (["failed", "error"].includes(s)) return "risk";
  return "neutral";
}

const inputClass =
  "w-full border border-border bg-ink px-3 py-2 text-sm text-text-primary outline-none transition-colors placeholder:text-text-secondary/50 hover:border-gold/40 focus:border-gold";

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const { bank, fiscalYear, banks } = useBank();
  const [docType, setDocType] = useState(DOC_TYPES[0]);
  const [fy, setFy] = useState("");
  const [bankId, setBankId] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const effectiveBankId = bankId === "" ? (bank?.id ?? "") : bankId;
  const effectiveFy = fy || fiscalYear || "";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setResult(null);
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setError("Choose a file to upload.");
      return;
    }
    if (effectiveBankId === "" || !effectiveFy) {
      setError("Select an institution and fiscal year.");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    form.append("bank_id", String(effectiveBankId));
    form.append("doc_type", docType);
    form.append("fiscal_year", effectiveFy);
    setSubmitting(true);
    try {
      const res = await api.uploadDocument(form);
      setResult(res);
      if (fileRef.current) fileRef.current.value = "";
      onUploaded();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-7">
      <SectionLabel className="mb-5">Submit a Document</SectionLabel>
      <form onSubmit={onSubmit} className="space-y-5">
        <div>
          <label className="mb-1.5 block text-[10px] uppercase tracking-[0.25em] text-bronze">
            File
          </label>
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.xlsx,.xls,.csv"
            className={`${inputClass} file:mr-4 file:border file:border-gold/50 file:bg-transparent file:px-3 file:py-1 file:text-[10px] file:uppercase file:tracking-[0.2em] file:text-gold`}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-[10px] uppercase tracking-[0.25em] text-bronze">
            Institution
          </label>
          <select
            className={`sovereign-select ${inputClass} pr-8`}
            value={effectiveBankId}
            onChange={(e) => setBankId(Number(e.target.value))}
          >
            {banks.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="mb-1.5 block text-[10px] uppercase tracking-[0.25em] text-bronze">
              Document Type
            </label>
            <select
              className={`sovereign-select ${inputClass} pr-8`}
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
            >
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {humanize(t)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-[10px] uppercase tracking-[0.25em] text-bronze">
              Fiscal Year
            </label>
            <input
              type="text"
              placeholder={fiscalYear ?? "FY2024"}
              value={effectiveFy}
              onChange={(e) => setFy(e.target.value)}
              className={inputClass}
            />
          </div>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full border border-gold/70 px-4 py-2.5 text-xs uppercase tracking-[0.25em] text-gold transition-colors hover:bg-gold hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Processing…" : "Upload & Extract"}
        </button>
      </form>

      {error ? (
        <p className="mt-4 border border-risk/50 bg-risk/10 px-4 py-3 text-xs text-risk">
          {error}
        </p>
      ) : null}

      {result ? (
        <div className="mt-5 border border-success/40 bg-success/10 p-5">
          <SectionLabel className="mb-3 text-success">
            Ingestion Complete — Document #{result.document_id}
          </SectionLabel>
          <div className="mb-3 flex items-center gap-3">
            <Badge tone={statusTone(result.status)}>{result.status}</Badge>
            <span className="text-sm text-text-secondary">
              {formatCount(result.extracted_count)} values extracted
            </span>
          </div>
          <div className="grid grid-cols-3 divide-x divide-border border-t border-border/60 pt-3">
            {(
              [
                ["Passed", result.validation.passed, "text-success"],
                ["Warnings", result.validation.warnings, "text-warning"],
                ["Failed", result.validation.failed, "text-risk"],
              ] as const
            ).map(([label, value, cls]) => (
              <div key={label} className="px-4 first:pl-0">
                <div className={`font-serif text-2xl ${cls}`}>{value}</div>
                <div className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                  {label}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </Card>
  );
}

function RegisterBankForm() {
  const { retry, setBankId } = useBank();
  const [name, setName] = useState("");
  const [segment, setSegment] = useState<BankSegment>("private");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    if (!name.trim()) {
      setError("Enter the institution's name.");
      return;
    }
    setSubmitting(true);
    try {
      const bank = await api.createBank(name.trim(), segment);
      setMessage(`${bank.name} registered — now upload its annual report above.`);
      setName("");
      retry(); // refresh the global bank list
      setBankId(bank.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="p-7">
      <SectionLabel className="mb-2">Institution not listed?</SectionLabel>
      <p className="mb-5 text-xs text-text-secondary">
        Register any bank and upload its filings — all analytics apply
        automatically once its first document is processed.
      </p>
      <form onSubmit={onSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-[10px] uppercase tracking-[0.25em] text-bronze">
            Institution Name
          </label>
          <input
            type="text"
            value={name}
            placeholder="e.g. Saurashtra Gramin Bank"
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label className="mb-1.5 block text-[10px] uppercase tracking-[0.25em] text-bronze">
            Category
          </label>
          <select
            className={`sovereign-select ${inputClass} pr-8`}
            value={segment}
            onChange={(e) => setSegment(e.target.value as BankSegment)}
          >
            {SEGMENT_ORDER.map((s) => (
              <option key={s} value={s}>
                {SEGMENT_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full border border-border px-4 py-2.5 text-xs uppercase tracking-[0.25em] text-text-secondary transition-colors hover:border-gold hover:text-gold disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Registering…" : "Register Institution"}
        </button>
      </form>
      {error ? (
        <p className="mt-4 border border-risk/50 bg-risk/10 px-4 py-3 text-xs text-risk">
          {error}
        </p>
      ) : null}
      {message ? (
        <p className="mt-4 border border-success/40 bg-success/10 px-4 py-3 text-xs text-success">
          {message}
        </p>
      ) : null}
    </Card>
  );
}

export default function DocumentsPage() {
  const { banks } = useBank();
  const docsState = useApi(() => api.getDocuments(), []);
  const bankName = (id: number) =>
    banks.find((b) => b.id === id)?.name ?? `Bank #${id}`;

  return (
    <>
      <PageHeading
        label="Library · Documents"
        title="Document Library"
        subtitle="Source filings under management — every KPI in the platform traces back to a page in one of these documents."
      />

      <div className="grid items-start gap-6 xl:grid-cols-3">
        {/* Documents table */}
        <Card className="overflow-hidden xl:col-span-2">
          <div className="flex items-center justify-between border-b border-border px-6 py-4">
            <SectionLabel>Filed Documents</SectionLabel>
            {docsState.data ? (
              <span className="text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                {docsState.data.documents.length} on record
              </span>
            ) : null}
          </div>
          {docsState.loading ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : docsState.error ? (
            <div className="p-6">
              <ErrorState
                message={docsState.error}
                onRetry={docsState.retry}
                compact
              />
            </div>
          ) : docsState.data && docsState.data.documents.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-[10px] uppercase tracking-[0.2em] text-text-secondary">
                  <th className="px-6 py-3 font-normal">Title</th>
                  <th className="px-3 py-3 font-normal">Type</th>
                  <th className="px-3 py-3 font-normal">FY</th>
                  <th className="px-3 py-3 text-right font-normal">Pages</th>
                  <th className="px-3 py-3 font-normal">Status</th>
                  <th className="px-6 py-3 font-normal">Uploaded</th>
                </tr>
              </thead>
              <tbody>
                {docsState.data.documents.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-border/50 align-top last:border-0"
                  >
                    <td className="px-6 py-3.5">
                      <div className="text-text-primary">{doc.title}</div>
                      <div className="mt-0.5 text-[11px] text-text-secondary">
                        {bankName(doc.bank_id)}
                      </div>
                    </td>
                    <td className="px-3 py-3.5 text-text-secondary">
                      {humanize(doc.doc_type)}
                    </td>
                    <td className="px-3 py-3.5 font-serif text-text-primary">
                      {doc.fiscal_year}
                    </td>
                    <td className="px-3 py-3.5 text-right text-text-secondary">
                      {formatCount(doc.pages)}
                    </td>
                    <td className="px-3 py-3.5">
                      <Badge tone={statusTone(doc.status)}>{doc.status}</Badge>
                    </td>
                    <td className="px-6 py-3.5 text-text-secondary">
                      {formatDateTime(doc.uploaded_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-sm text-text-secondary">
              No documents on record yet. Submit the first filing alongside.
            </div>
          )}
        </Card>

        {/* Upload + registration */}
        <div className="space-y-6">
          <UploadForm onUploaded={docsState.retry} />
          <RegisterBankForm />
        </div>
      </div>
    </>
  );
}
