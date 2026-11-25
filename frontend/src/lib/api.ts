export type LanguageCode = "en" | "hi" | "mr";

export interface DeadlineItem {
  label: string;
  date_raw: string;
  iso_date: string;
  applies_to: string;
}

export interface FeeItem {
  label: string;
  amount_raw: string;
  amount_inr: string;
}

export interface LocalizedContent {
  title: string;
  tldr: string;
  action_steps: string[];
  voice_script: string;
}

export interface NoticeExtraction {
  source_language: "en" | "hi" | "mr" | "mixed";
  circular_ref: string;
  issue_date: string;
  deadlines: DeadlineItem[];
  fees: FeeItem[];
  eligibility_tags: string[];
  required_docs: string[];
  verbatim_quotes: string[];
  transcribed_text: string;
  en: LocalizedContent;
  hi: LocalizedContent;
  mr: LocalizedContent;
}

export interface QuoteLocation {
  quote: string;
  page_number: number | null;
}

export interface ActionCardResponse {
  notice_hash: string;
  input_type: "digital_pdf" | "scanned_pdf" | "photo";
  verification_status: "source_matched" | "verify_original" | "scan_extracted";
  unverified_items: string[];
  quote_locations: QuoteLocation[];
  cache_hit: boolean;
  cache_tier: "tier1_sha256" | "tier2_text" | "tier2_phash" | "miss";
  cache_ttl_seconds: number;
  has_ics_deadlines: boolean;
  disclaimer: string;
  extraction: NoticeExtraction;
}

export interface QAResponse {
  answer: string;
  found_in_notice: boolean;
  cited_pages: number[];
}

export interface ErrorPayload {
  code?: string;
  message?: string;
  detail?: string;
}

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  return (configured && configured.trim()) || "http://localhost:8000";
}

export function getAppBaseUrl(): string {
  if (typeof window !== "undefined" && window.location.origin) {
    return window.location.origin;
  }
  const configured = process.env.NEXT_PUBLIC_APP_URL;
  return (configured && configured.trim()) || "http://localhost:3000";
}

async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as ErrorPayload;
    const message =
      data.message || data.detail || `Request failed with status ${response.status}.`;
    const code = data.code || `HTTP_${response.status}`;
    return new ApiError(response.status, code, message);
  } catch {
    return new ApiError(
      response.status,
      `HTTP_${response.status}`,
      `Request failed with status ${response.status}.`
    );
  }
}

export async function simplifyFile(file: File): Promise<ActionCardResponse> {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`${getApiBaseUrl()}/api/simplify`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return (await response.json()) as ActionCardResponse;
}

export async function simplifyUrl(url: string): Promise<ActionCardResponse> {
  const form = new FormData();
  form.append("url", url);

  const response = await fetch(`${getApiBaseUrl()}/api/simplify`, {
    method: "POST",
    body: form,
  });

  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return (await response.json()) as ActionCardResponse;
}

export async function getNotice(noticeHash: string): Promise<ActionCardResponse> {
  const response = await fetch(
    `${getApiBaseUrl()}/api/notice/${encodeURIComponent(noticeHash)}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return (await response.json()) as ActionCardResponse;
}

export async function askNoticeQA(
  noticeHash: string,
  question: string,
  lang: LanguageCode
): Promise<QAResponse> {
  const response = await fetch(`${getApiBaseUrl()}/api/qa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      notice_hash: noticeHash,
      question,
      lang,
    }),
  });
  if (!response.ok) {
    throw await parseErrorResponse(response);
  }
  return (await response.json()) as QAResponse;
}

export function getAudioUrl(noticeHash: string, lang: LanguageCode): string {
  return `${getApiBaseUrl()}/api/audio/${encodeURIComponent(noticeHash)}/${lang}`;
}

export function getIcsUrl(noticeHash: string): string {
  return `${getApiBaseUrl()}/api/notice/${encodeURIComponent(noticeHash)}/ics`;
}

export async function fetchSamplePdfFile(
  path: "/samples/sample-exam-circular.pdf" | "/samples/mock-merit-list.pdf",
  filename: string
): Promise<File> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error("Could not load bundled demo circular file.");
  }
  const blob = await response.blob();
  return new File([blob], filename, { type: "application/pdf" });
}

