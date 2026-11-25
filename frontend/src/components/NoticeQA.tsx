"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Loader2, MessageSquare, Send } from "lucide-react";
import { ApiError, askNoticeQA, type LanguageCode, type QAResponse } from "@/lib/api";

interface NoticeQAProps {
  noticeHash: string;
  lang: LanguageCode;
}

const QUICK_QUESTIONS: Record<LanguageCode, string[]> = {
  en: ["Is there a late fee?", "Who is eligible?", "What documents are required?"],
  hi: ["क्या लेट फीस लगेगी?", "कौन आवेदन कर सकता है?", "कौन से दस्तावेज़ जरूरी हैं?"],
  mr: ["लेट फी आहे का?", "कोण पात्र आहे?", "कोणती कागदपत्रे लागतील?"],
};

export function NoticeQA({ noticeHash, lang }: NoticeQAProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<QAResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function submitQuestion(text: string) {
    const trimmed = text.trim();
    if (!trimmed || trimmed.length > 300 || isLoading) return;

    setIsLoading(true);
    setError(null);
    try {
      const response = await askNoticeQA(noticeHash, trimmed, lang);
      setResult(response);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Unable to answer right now. Please confirm on the official circular.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    void submitQuestion(question);
  }

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex w-full items-center justify-between px-4 py-3.5 text-left"
        aria-expanded={isOpen}
      >
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-slate-900">
          <MessageSquare className="h-4 w-4 text-teal-600" />
          Ask About This Circular
        </span>
        {isOpen ? (
          <ChevronUp className="h-4 w-4 text-slate-500" />
        ) : (
          <ChevronDown className="h-4 w-4 text-slate-500" />
        )}
      </button>

      {isOpen && (
        <div className="border-t border-slate-200 px-4 py-4">
          <p className="mb-2.5 text-xs text-slate-600">
            Answers are grounded strictly in this circular. Anything absent is flagged for college office verification.
          </p>

          <div className="mb-3 flex flex-wrap gap-2">
            {QUICK_QUESTIONS[lang].map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => {
                  setQuestion(chip);
                  void submitQuestion(chip);
                }}
                className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium text-slate-700 hover:border-teal-300 hover:bg-teal-50"
              >
                {chip}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={question}
              maxLength={300}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about dates, fees, or eligibility..."
              className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-teal-600 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!question.trim() || isLoading}
              className="inline-flex items-center gap-1.5 rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
              Ask
            </button>
          </form>
          <p className="mt-1 text-right text-[11px] text-slate-400">
            {question.length}/300
          </p>

          {error && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
              {error}
            </div>
          )}

          {result && (
            <div
              className={`mt-3 rounded-lg border p-3.5 text-sm ${
                result.found_in_notice
                  ? "border-teal-200 bg-teal-50/50 text-slate-900"
                  : "border-amber-200 bg-amber-50 text-amber-900"
              }`}
            >
              <p className="leading-relaxed">{result.answer}</p>
              {result.cited_pages.length > 0 && (
                <p className="mt-2 text-xs font-medium text-slate-600">
                  Cited pages: {result.cited_pages.map((p) => `Page ${p}`).join(", ")}
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

