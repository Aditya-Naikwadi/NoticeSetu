"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertOctagon,
  FileUp,
  Link2,
  ShieldAlert,
  Sparkles,
  UploadCloud,
} from "lucide-react";
import { PipelineStepper } from "@/components/PipelineStepper";
import {
  ApiError,
  fetchSamplePdfFile,
  simplifyFile,
  simplifyUrl,
  type ActionCardResponse,
} from "@/lib/api";

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(["application/pdf", "image/jpeg", "image/png"]);

export default function HomePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [activeTab, setActiveTab] = useState<"upload" | "url">("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [noticeUrl, setNoticeUrl] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  const [isProcessing, setIsProcessing] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(0);
  const [errorState, setErrorState] = useState<{
    isPiiBlock: boolean;
    message: string;
  } | null>(null);

  function saveAndNavigate(card: ActionCardResponse) {
    try {
      sessionStorage.setItem(`noticesetu:${card.notice_hash}`, JSON.stringify(card));
    } catch {
      // Ignore sessionStorage quota issues
    }
    router.push(`/notice/${card.notice_hash}`);
  }

  function validateClientFile(file: File): string | null {
    if (file.size === 0) {
      return "Selected file is empty. Upload a valid PDF, JPEG, or PNG.";
    }
    if (file.size > MAX_BYTES) {
      return "File exceeds the 10 MB limit. Upload a smaller PDF or photo.";
    }
    const lowerName = file.name.toLowerCase();
    const hasAllowedExt =
      lowerName.endsWith(".pdf") ||
      lowerName.endsWith(".jpg") ||
      lowerName.endsWith(".jpeg") ||
      lowerName.endsWith(".png");
    if (!ACCEPTED_TYPES.has(file.type) && !hasAllowedExt) {
      return "Unsupported file. Upload a PDF, JPEG, or PNG under 10 MB.";
    }
    return null;
  }

  async function runWithStepper(task: () => Promise<ActionCardResponse>) {
    setErrorState(null);
    setIsProcessing(true);
    setPipelineStep(0);

    const timer = window.setInterval(() => {
      setPipelineStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 650);

    try {
      const card = await task();
      setPipelineStep(5);
      saveAndNavigate(card);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorState({
          isPiiBlock: err.code === "PII_BLOCKED",
          message: err.message,
        });
      } else if (err instanceof Error) {
        setErrorState({ isPiiBlock: false, message: err.message });
      } else {
        setErrorState({
          isPiiBlock: false,
          message: "Unable to process this circular right now.",
        });
      }
    } finally {
      window.clearInterval(timer);
      setIsProcessing(false);
    }
  }

  function handleFileChosen(file: File | undefined) {
    if (!file) return;
    const validationErr = validateClientFile(file);
    if (validationErr) {
      setSelectedFile(null);
      setErrorState({ isPiiBlock: false, message: validationErr });
      return;
    }
    setErrorState(null);
    setSelectedFile(file);
  }

  function handleUploadSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedFile || isProcessing) return;
    void runWithStepper(() => simplifyFile(selectedFile));
  }

  function handleUrlSubmit(event: React.FormEvent) {
    event.preventDefault();
    const trimmed = noticeUrl.trim();
    if (!trimmed || isProcessing) return;
    void runWithStepper(() => simplifyUrl(trimmed));
  }

  async function runDemo(
    path: "/samples/sample-exam-circular.pdf" | "/samples/mock-merit-list.pdf",
    filename: string
  ) {
    if (isProcessing) return;
    await runWithStepper(async () => {
      const file = await fetchSamplePdfFile(path, filename);
      return simplifyFile(file);
    });
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <div className="max-w-2xl">
          <h1 className="text-2xl font-bold tracking-tight text-[#0F172A] sm:text-3xl">
            Turn official college circulars into clear Action Cards
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-[#334155]">
            Upload an English, Hindi, or Marathi circular PDF, noticeboard photo, or public portal URL to get deadlines, fees, checklists, calendar export, and regional voice briefs with zero login.
          </p>
        </div>

        {/* Input Mode Tabs */}
        <div className="mt-5 inline-flex rounded-xl border border-slate-200 bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => setActiveTab("upload")}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              activeTab === "upload"
                ? "bg-[#0D9488] text-white shadow-sm"
                : "text-slate-700 hover:text-slate-900"
            }`}
          >
            <FileUp className="h-3.5 w-3.5" />
            Upload PDF / Photo
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("url")}
            className={`inline-flex items-center gap-1.5 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              activeTab === "url"
                ? "bg-[#0D9488] text-white shadow-sm"
                : "text-slate-700 hover:text-slate-900"
            }`}
          >
            <Link2 className="h-3.5 w-3.5" />
            Paste Public Notice URL
          </button>
        </div>

        {activeTab === "upload" ? (
          <form onSubmit={handleUploadSubmit} className="mt-4 space-y-4">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                handleFileChosen(e.dataTransfer.files?.[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-4 py-8 text-center transition ${
                isDragging
                  ? "border-[#0D9488] bg-teal-50"
                  : "border-slate-300 bg-slate-50 hover:border-teal-500"
              }`}
            >
              <UploadCloud className="h-8 w-8 text-[#0D9488]" />
              <p className="mt-2 text-sm font-semibold text-slate-900">
                {selectedFile
                  ? selectedFile.name
                  : "Drop PDF, JPEG, or PNG here, or click to choose"}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Max 10 MB • Processed strictly in memory (never written to disk)
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
                onChange={(e) => handleFileChosen(e.target.files?.[0])}
                className="hidden"
              />
            </div>

            <button
              type="submit"
              disabled={!selectedFile || isProcessing}
              className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-[#0D9488] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            >
              <Sparkles className="h-4 w-4" />
              Simplify Notice
            </button>
          </form>
        ) : (
          <form onSubmit={handleUrlSubmit} className="mt-4 space-y-3">
            <label htmlFor="notice-url" className="block text-xs font-semibold text-slate-700">
              Public college circular PDF or image URL
            </label>
            <div className="flex flex-col gap-2.5 sm:flex-row">
              <input
                id="notice-url"
                type="url"
                value={noticeUrl}
                onChange={(e) => setNoticeUrl(e.target.value)}
                placeholder="https://college.edu.in/notices/exam-circular.pdf"
                className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-[#0D9488] focus:outline-none"
                required
              />
              <button
                type="submit"
                disabled={!noticeUrl.trim() || isProcessing}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#0D9488] px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Sparkles className="h-4 w-4" />
                Simplify Notice
              </button>
            </div>
          </form>
        )}

        {/* Live Demo Shortcuts */}
        <div className="mt-6 border-t border-slate-200 pt-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Instant Live Demos
          </p>
          <div className="mt-2.5 flex flex-wrap gap-2.5">
            <button
              type="button"
              disabled={isProcessing}
              onClick={() =>
                void runDemo("/samples/sample-exam-circular.pdf", "sample-exam-circular.pdf")
              }
              className="rounded-lg border border-teal-300 bg-teal-50 px-3.5 py-2 text-xs font-semibold text-teal-900 hover:bg-teal-100 disabled:opacity-50"
            >
              Try Sample Exam Circular
            </button>
            <button
              type="button"
              disabled={isProcessing}
              onClick={() =>
                void runDemo("/samples/mock-merit-list.pdf", "mock-merit-list.pdf")
              }
              className="rounded-lg border border-red-200 bg-red-50 px-3.5 py-2 text-xs font-semibold text-red-900 hover:bg-red-100 disabled:opacity-50"
            >
              Test PII Protection (Mock Merit List)
            </button>
          </div>
        </div>
      </section>

      {isProcessing && <PipelineStepper activeStep={pipelineStep} />}

      {errorState && (
        <section
          role="alert"
          className={`rounded-2xl border p-5 ${
            errorState.isPiiBlock
              ? "border-red-300 bg-red-50 text-red-950"
              : "border-amber-300 bg-amber-50 text-amber-950"
          }`}
        >
          <div className="flex items-start gap-3">
            {errorState.isPiiBlock ? (
              <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-red-700" />
            ) : (
              <AlertOctagon className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
            )}
            <div>
              <h2 className="text-sm font-bold">
                {errorState.isPiiBlock
                  ? "Blocked for Student Privacy (Pre-LLM PII Guard)"
                  : "Could Not Process Notice"}
              </h2>
              <p className="mt-1 text-sm leading-relaxed">{errorState.message}</p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

