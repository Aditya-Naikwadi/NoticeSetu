"use client";

import { CheckCircle2, Circle, Loader2 } from "lucide-react";

const PIPELINE_STEPS = [
  "Validating & Screening PII",
  "Checking Instant Cache",
  "Reading Circular Text",
  "Generating Multilingual Action Card",
  "Verifying Dates & Fees",
] as const;

interface PipelineStepperProps {
  activeStep: number;
  isComplete?: boolean;
}

export function PipelineStepper({
  activeStep,
  isComplete = false,
}: PipelineStepperProps) {
  return (
    <div
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      role="status"
      aria-live="polite"
    >
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
        NoticeSetu Processing Pipeline
      </p>
      <ol className="space-y-2.5">
        {PIPELINE_STEPS.map((label, index) => {
          const done = isComplete || index < activeStep;
          const active = !isComplete && index === activeStep;
          return (
            <li key={label} className="flex items-center gap-3 text-sm">
              {done ? (
                <CheckCircle2 className="h-4 w-4 shrink-0 text-teal-600" />
              ) : active ? (
                <Loader2 className="h-4 w-4 shrink-0 animate-spin text-teal-600" />
              ) : (
                <Circle className="h-4 w-4 shrink-0 text-slate-300" />
              )}
              <span
                className={
                  done
                    ? "font-medium text-slate-900"
                    : active
                      ? "font-semibold text-teal-700"
                      : "text-slate-400"
                }
              >
                {label}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

