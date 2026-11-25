"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import { ActionCard } from "@/components/ActionCard";
import { ApiError, getNotice, type ActionCardResponse } from "@/lib/api";

export default function NoticeDetailPage() {
  const params = useParams<{ hash: string }>();
  const hash = params?.hash || "";

  const [card, setCard] = useState<ActionCardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    async function load() {
      if (!hash) {
        setError("Missing circular identifier.");
        setIsLoading(false);
        return;
      }

      try {
        const cachedFresh = sessionStorage.getItem(`noticesetu:${hash}`);
        if (cachedFresh) {
          sessionStorage.removeItem(`noticesetu:${hash}`);
          const parsed = JSON.parse(cachedFresh) as ActionCardResponse;
          if (active) {
            setCard(parsed);
            setIsLoading(false);
          }
          return;
        }
      } catch {
        // Fallback to backend fetch
      }

      try {
        const fetched = await getNotice(hash);
        if (active) setCard(fetched);
      } catch (err) {
        if (active) {
          if (err instanceof ApiError) {
            setError(err.message);
          } else {
            setError("Notice not found or expired after the 14-day retention window.");
          }
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, [hash]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center rounded-2xl border border-slate-200 bg-white py-16">
        <Loader2 className="mr-2 h-5 w-5 animate-spin text-[#0D9488]" />
        <span className="text-sm font-medium text-slate-700">Loading Action Card...</span>
      </div>
    );
  }

  if (error || !card) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 text-center shadow-sm">
        <h1 className="text-lg font-bold text-slate-900">Notice Not Available</h1>
        <p className="mt-2 text-sm text-slate-600">
          {error || "This Action Card could not be found or has expired after 14 days."}
        </p>
        <Link
          href="/"
          className="mt-4 inline-flex items-center gap-1.5 rounded-xl bg-[#0D9488] px-4 py-2.5 text-xs font-semibold text-white hover:bg-teal-700"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to NoticeSetu Hub
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Link
        href="/"
        className="no-print inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Simplify another notice
      </Link>
      <ActionCard card={card} />
    </div>
  );
}

