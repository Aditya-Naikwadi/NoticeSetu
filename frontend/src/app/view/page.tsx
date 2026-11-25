"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ArrowLeft, ShieldAlert } from "lucide-react";
import { ActionCard } from "@/components/ActionCard";
import { PipelineStepper } from "@/components/PipelineStepper";
import {
  ApiError,
  fetchSamplePdfFile,
  simplifyFile,
  simplifyUrl,
  type ActionCardResponse,
} from "@/lib/api";

function ViewUrlContent() {
  const searchParams = useSearchParams();
  const targetUrl = searchParams.get("url")?.trim() || "";

  const [card, setCard] = useState<ActionCardResponse | null>(null);
  const [step, setStep] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [errorState, setErrorState] = useState<{
    isPiiBlock: boolean;
    message: string;
  } | null>(null);

  useEffect(() => {
    let active = true;

    if (!targetUrl) {
      setErrorState({
        isPiiBlock: false,
        message: "Missing ?url= circular parameter.",
      });
      setIsLoading(false);
      return;
    }

    const timer = window.setInterval(() => {
      setStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 650);

    async function processTarget() {
      try {
        let result: ActionCardResponse;
        const parsed = new URL(targetUrl, window.location.origin);
        if (
          parsed.origin === window.location.origin &&
          (parsed.pathname === "/samples/sample-exam-circular.pdf" ||
            parsed.pathname === "/samples/mock-merit-list.pdf")
        ) {
          const sampleFile = await fetchSamplePdfFile(
            parsed.pathname,
            parsed.pathname.split("/").pop() || "sample.pdf"
          );
          result = await simplifyFile(sampleFile);
        } else {
          result = await simplifyUrl(targetUrl);
        }
        if (active) {
          setStep(5);
          setCard(result);
        }
      } catch (err) {
        if (active) {
          if (err instanceof ApiError) {
            setErrorState({
              isPiiBlock: err.code === "PII_BLOCKED",
              message: err.message,
            });
          } else {
            setErrorState({
              isPiiBlock: false,
              message: "Could not load the linked circular URL.",
            });
          }
        }
      } finally {
        window.clearInterval(timer);
        if (active) setIsLoading(false);
      }
    }

    void processTarget();
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [targetUrl]);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-600">
          Fetching public circular: <span className="break-all font-medium text-slate-900">{targetUrl}</span>
        </div>
        <PipelineStepper activeStep={step} />
      </div>
    );
  }

  if (errorState || !card) {
    return (
      <div
        className={`rounded-2xl border p-6 ${
          errorState?.isPiiBlock
            ? "border-red-300 bg-red-50 text-red-950"
            : "border-amber-300 bg-amber-50 text-amber-950"
        }`}
      >
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <h1 className="text-base font-bold">
              {errorState?.isPiiBlock
                ? "Blocked for Student Privacy"
                : "Unable to Simplify Linked Circular"}
            </h1>
            <p className="mt-1 text-sm">{errorState?.message}</p>
            <Link
              href="/"
              className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#0F172A] px-3.5 py-2 text-xs font-semibold text-white"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Open NoticeSetu Hub
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return <ActionCard card={card} />;
}

export default function ViewUrlPage() {
  return (
    <Suspense
      fallback={
        <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-600">
          Preparing circular viewer...
        </div>
      }
    >
      <ViewUrlContent />
    </Suspense>
  );
}
