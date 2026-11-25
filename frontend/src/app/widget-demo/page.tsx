"use client";

import Script from "next/script";
import { Code2, ExternalLink } from "lucide-react";

const SAMPLE_EMBED_SNIPPET = '<script src="https://your-noticesetu-domain.com/widget.js" defer></script>';

export default function WidgetDemoPage() {
  return (
    <div className="space-y-6">
      <Script src="/widget.js" strategy="afterInteractive" />

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-xl font-bold text-[#0F172A]">
              College Noticeboard 1-Line Widget Demo
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Below is a mock college noticeboard table. <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">public/widget.js</code> scans <code className="rounded bg-slate-100 px-1.5 py-0.5 text-xs">.pdf</code> links and injects an isolated Shadow DOM pill next to each notice.
            </p>
          </div>
        </div>

        <div className="mt-4 rounded-xl bg-[#0F172A] p-3.5 text-xs text-teal-300">
          <div className="mb-1 flex items-center gap-1.5 font-semibold text-slate-200">
            <Code2 className="h-3.5 w-3.5" />
            1-Line Embed Snippet for Any College Portal
          </div>
          <code className="block break-all font-mono">{SAMPLE_EMBED_SNIPPET}</code>
        </div>
      </section>

      {/* Intentionally traditional college table styling to demonstrate Shadow DOM isolation */}
      <section className="rounded-2xl border-2 border-slate-300 bg-white p-5 shadow-sm">
        <h2 className="border-b-2 border-slate-800 pb-2 font-serif text-lg font-bold text-slate-900">
          XYZ Institute of Arts, Science & Commerce — Official Noticeboard
        </h2>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full border border-slate-300 text-left text-sm">
            <thead className="bg-slate-200 text-xs uppercase text-slate-800">
              <tr>
                <th className="border border-slate-300 px-3 py-2">Date</th>
                <th className="border border-slate-300 px-3 py-2">Circular Title & PDF</th>
                <th className="border border-slate-300 px-3 py-2">CSP Fallback</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="border border-slate-300 px-3 py-3 text-xs font-medium">
                  01 Mar 2026
                </td>
                <td className="border border-slate-300 px-3 py-3">
                  <a
                    href="/samples/sample-exam-circular.pdf"
                    className="font-semibold text-blue-700 underline"
                  >
                    Semester IV Regular & ATKT Exam Form Circular (PDF)
                  </a>
                </td>
                <td className="border border-slate-300 px-3 py-3 text-xs">
                  <a
                    href="/view?url=%2Fsamples%2Fsample-exam-circular.pdf"
                    className="inline-flex items-center gap-1 font-medium text-teal-700 hover:underline"
                  >
                    Open /view fallback
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
              </tr>
              <tr className="bg-slate-50">
                <td className="border border-slate-300 px-3 py-3 text-xs font-medium">
                  02 Mar 2026
                </td>
                <td className="border border-slate-300 px-3 py-3">
                  <a
                    href="/samples/mock-merit-list.pdf"
                    className="font-semibold text-blue-700 underline"
                  >
                    First Year Provisional Merit List (PII Block Demo PDF)
                  </a>
                </td>
                <td className="border border-slate-300 px-3 py-3 text-xs">
                  <a
                    href="/view?url=%2Fsamples%2Fmock-merit-list.pdf"
                    className="inline-flex items-center gap-1 font-medium text-teal-700 hover:underline"
                  >
                    Open /view fallback
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
