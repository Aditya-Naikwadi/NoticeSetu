"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CalendarPlus,
  CheckCircle2,
  Database,
  FileText,
  QrCode,
  Quote,
  ShieldCheck,
} from "lucide-react";
import { AudioPlayer } from "@/components/AudioPlayer";
import { NoticeQA } from "@/components/NoticeQA";
import { QrPosterModal } from "@/components/QrPosterModal";
import { getIcsUrl, type ActionCardResponse, type LanguageCode } from "@/lib/api";

interface ActionCardProps {
  card: ActionCardResponse;
}

const CACHE_BADGE_MAP: Record<ActionCardResponse["cache_tier"], string> = {
  tier1_sha256: "Instant Cache Hit (Tier-1 SHA-256)",
  tier2_text: "Instant Cache Hit (Tier-2 Text)",
  tier2_phash: "Instant Cache Hit (Tier-2 Image)",
  miss: "Fresh Extraction",
};

export function ActionCard({ card }: ActionCardProps) {
  const [lang, setLang] = useState<LanguageCode>("en");
  const [checkedSteps, setCheckedSteps] = useState<Record<number, boolean>>({});
  const [posterOpen, setPosterOpen] = useState(false);

  const loc = card.extraction[lang];

  function toggleStep(idx: number) {
    setCheckedSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }

  return (
    <article className="space-y-4">
      {/* Permanent Mandatory Governance Banner */}
      <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-xs font-semibold text-amber-950">
        {card.disclaimer}
      </div>

      {/* Pinned Metadata + Verification Pill + Cache Indicator */}
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            {card.verification_status === "source_matched" ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
                <ShieldCheck className="h-3.5 w-3.5" />
                Source-Matched (Digital PDF)
              </span>
            ) : card.verification_status === "verify_original" ? (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">
                <AlertTriangle className="h-3.5 w-3.5" />
                Verify Original
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-900">
                <AlertTriangle className="h-3.5 w-3.5" />
                Scan-Extracted — Verify Original
              </span>
            )}

            <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700">
              <Database className="h-3.5 w-3.5 text-slate-500" />
              {CACHE_BADGE_MAP[card.cache_tier]}
            </span>
          </div>

          <button
            type="button"
            onClick={() => setPosterOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 hover:bg-slate-50"
          >
            <QrCode className="h-3.5 w-3.5 text-teal-600" />
            Print Noticeboard QR Poster
          </button>
        </div>

        <div className="mt-3 grid gap-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-700 sm:grid-cols-2">
          <div>
            <span className="font-semibold text-slate-900">Circular Ref No.: </span>
            <span>{card.extraction.circular_ref || "Not specified"}</span>
          </div>
          <div>
            <span className="font-semibold text-slate-900">Issue Date: </span>
            <span>{card.extraction.issue_date || "Not specified"}</span>
          </div>
          <p className="text-[11px] text-slate-600 sm:col-span-2">
            Check your college portal/noticeboard for subsequent corrigenda. Cached copies expire automatically after 14 days.
          </p>
        </div>

        {card.unverified_items.length > 0 && (
          <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            <p className="font-semibold">
              Items needing manual check against the original PDF:
            </p>
            <ul className="mt-1 list-disc pl-5">
              {card.unverified_items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Language Toggle */}
        <div
          className="mt-4 inline-flex rounded-xl border border-slate-200 bg-slate-100 p-1"
          role="tablist"
          aria-label="Output language"
        >
          {(
            [
              ["en", "English"],
              ["hi", "हिंदी"],
              ["mr", "मराठी"],
            ] as const
          ).map(([code, label]) => (
            <button
              key={code}
              type="button"
              role="tab"
              aria-selected={lang === code}
              onClick={() => setLang(code)}
              className={`rounded-lg px-4 py-1.5 text-xs font-semibold transition ${
                lang === code
                  ? "bg-teal-600 text-white shadow-sm"
                  : "text-slate-700 hover:text-slate-900"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Title & Eligibility Tags */}
        <h1 className="mt-4 text-xl font-bold leading-snug text-slate-900 sm:text-2xl">
          {loc.title}
        </h1>

        {card.extraction.eligibility_tags.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-2">
            {card.extraction.eligibility_tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-800"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Plain-Language TL;DR */}
        <div className="mt-4 rounded-xl bg-slate-50 p-4">
          <h2 className="text-xs font-bold uppercase tracking-wide text-slate-500">
            Plain-Language Summary
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-slate-800">{loc.tldr}</p>
        </div>

        {/* Cached Voice Brief */}
        <div className="mt-4">
          <AudioPlayer
            noticeHash={card.notice_hash}
            lang={lang}
            voiceScript={loc.voice_script}
          />
        </div>
      </div>

      {/* Action Checklist */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <h2 className="text-sm font-bold text-slate-900">Action Checklist</h2>
        {loc.action_steps.length === 0 ? (
          <p className="mt-2 text-sm text-slate-600">No explicit action steps listed.</p>
        ) : (
          <ul className="mt-3 space-y-2.5">
            {loc.action_steps.map((step, idx) => (
              <li key={`${idx}-${step}`} className="flex items-start gap-3">
                <input
                  id={`step-${idx}`}
                  type="checkbox"
                  checked={Boolean(checkedSteps[idx])}
                  onChange={() => toggleStep(idx)}
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-600"
                />
                <label
                  htmlFor={`step-${idx}`}
                  className={`text-sm leading-relaxed ${
                    checkedSteps[idx]
                      ? "text-slate-400 line-through"
                      : "text-slate-800"
                  }`}
                >
                  {step}
                </label>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Deadlines & Fees + .ics Download */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-sm font-bold text-slate-900">Deadlines & Fees</h2>
          {card.has_ics_deadlines ? (
            <a
              href={getIcsUrl(card.notice_hash)}
              download
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-3.5 py-2 text-xs font-semibold text-white hover:bg-teal-700"
            >
              <CalendarPlus className="h-4 w-4" />
              Add to Calendar (.ics)
            </a>
          ) : (
            <span className="text-xs text-slate-500">
              No calendar deadlines found in this circular
            </span>
          )}
        </div>

        <div className="mt-3 space-y-3">
          {card.extraction.deadlines.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-semibold">Event</th>
                    <th className="py-2 pr-3 font-semibold">Date</th>
                    <th className="py-2 font-semibold">Applies To</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {card.extraction.deadlines.map((dl, idx) => (
                    <tr key={`${dl.label}-${idx}`}>
                      <td className="py-2 pr-3 font-medium">{dl.label}</td>
                      <td className="py-2 pr-3">{dl.date_raw}</td>
                      <td className="py-2 text-slate-600">{dl.applies_to || "All eligible"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {card.extraction.fees.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-200 text-slate-500">
                    <th className="py-2 pr-3 font-semibold">Fee Item</th>
                    <th className="py-2 font-semibold">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-800">
                  {card.extraction.fees.map((fee, idx) => (
                    <tr key={`${fee.label}-${idx}`}>
                      <td className="py-2 pr-3 font-medium">{fee.label}</td>
                      <td className="py-2 font-semibold text-slate-900">{fee.amount_raw}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-xs text-slate-600">No fee mentioned in circular.</p>
          )}
        </div>
      </section>

      {/* Required Documents */}
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
        <h2 className="inline-flex items-center gap-2 text-sm font-bold text-slate-900">
          <FileText className="h-4 w-4 text-teal-600" />
          Required Documents
        </h2>
        {card.extraction.required_docs.length > 0 ? (
          <ul className="mt-2.5 space-y-1.5 text-sm text-slate-800">
            {card.extraction.required_docs.map((doc) => (
              <li key={doc} className="flex items-start gap-2">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
                <span>{doc}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            No specific documents listed in circular.
          </p>
        )}
      </section>

      {/* Verbatim Source Quotes */}
      {card.quote_locations.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <h2 className="inline-flex items-center gap-2 text-sm font-bold text-slate-900">
            <Quote className="h-4 w-4 text-teal-600" />
            Verbatim Source Quotes
          </h2>
          <div className="mt-3 space-y-2.5">
            {card.quote_locations.map((item, idx) => (
              <blockquote
                key={`${idx}-${item.quote}`}
                className="rounded-lg border-l-4 border-teal-600 bg-slate-50 px-3.5 py-2.5 text-xs leading-relaxed text-slate-800"
              >
                <p>&ldquo;{item.quote}&rdquo;</p>
                <footer className="mt-1 font-semibold text-slate-500">
                  {item.page_number ? `Page ${item.page_number}` : "Source excerpt"}
                </footer>
              </blockquote>
            ))}
          </div>
        </section>
      )}

      {/* Grounded Q&A Drawer */}
      <NoticeQA noticeHash={card.notice_hash} lang={lang} />

      <QrPosterModal
        card={card}
        isOpen={posterOpen}
        onClose={() => setPosterOpen(false)}
      />
    </article>
  );
}

