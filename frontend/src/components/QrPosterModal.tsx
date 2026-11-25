"use client";

import { useState } from "react";
import { Check, Copy, Printer, X } from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { getAppBaseUrl, type ActionCardResponse } from "@/lib/api";

interface QrPosterModalProps {
  card: ActionCardResponse;
  isOpen: boolean;
  onClose: () => void;
}

export function QrPosterModal({ card, isOpen, onClose }: QrPosterModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const shareUrl = `${getAppBaseUrl().replace(/\/$/, "")}/notice/${card.notice_hash}`;

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/70 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="Printable Noticeboard QR Poster"
    >
      <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-2xl bg-white shadow-2xl">
        <div className="no-print flex items-center justify-between border-b border-slate-200 px-5 py-3.5">
          <h2 className="text-sm font-bold text-slate-900">
            Noticeboard QR Poster (A4 Print)
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            aria-label="Close modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div id="noticesetu-qr-poster" className="p-6 text-center">
          <p className="text-xs font-bold uppercase tracking-wider text-teal-700">
            NoticeSetu • English | हिंदी | मराठी
          </p>
          <h3 className="mt-2 text-lg font-bold text-slate-900">
            {card.extraction.en.title}
          </h3>
          <p className="mt-1 text-xs font-medium text-slate-600">
            Ref: {card.extraction.circular_ref || "Not specified"} • Date:{" "}
            {card.extraction.issue_date || "Not specified"}
          </p>

          <div className="my-5 inline-flex rounded-xl border-2 border-slate-900 bg-white p-4">
            <QRCodeSVG value={shareUrl} size={184} level="M" includeMargin={false} />
          </div>

          <p className="text-sm font-semibold text-slate-900">
            Scan to read this circular, listen to voice summary & add deadlines to calendar
          </p>
          <p className="mt-2 text-xs text-slate-700">{card.extraction.en.tldr}</p>

          <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[11px] font-medium text-amber-900">
            {card.disclaimer}
          </p>
        </div>

        <div className="no-print flex flex-wrap items-center justify-end gap-2 border-t border-slate-200 bg-slate-50 px-5 py-3.5">
          <button
            type="button"
            onClick={() => void handleCopy()}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100"
          >
            {copied ? <Check className="h-3.5 w-3.5 text-teal-600" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied Link" : "Copy Link"}
          </button>
          <button
            type="button"
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-xs font-semibold text-white hover:bg-teal-700"
          >
            <Printer className="h-3.5 w-3.5" />
            Print Poster
          </button>
        </div>
      </div>
    </div>
  );
}

