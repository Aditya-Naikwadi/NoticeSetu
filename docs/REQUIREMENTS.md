# NoticeSetu — Technical Requirements Specification

**Document Status:** Engineering Build Specification  
**Product Name:** NoticeSetu  
**Cross-Reference:** [docs/PRD.md](./PRD.md)  
**Compliance Target:** Digital Personal Data Protection (DPDP) Rules 2025 (India)  

---

## 0. Strict Technology Stack & Architecture Lock

This specification defines the exact runtime dependencies, schemas, security gates, endpoints, and build checks for **NoticeSetu**. Coding agents must implement these interfaces without substituting deprecated SDKs or introducing disk persistence.

### 0.1 Locked Runtime Stack
- **Backend (`backend/`):**
  - Python `3.11+`
  - Web & API: `fastapi`, `uvicorn[standard]`, `pydantic` (v2), `pydantic-settings`, `python-multipart`
  - Networking & Parsing: `httpx`, `PyMuPDF` (`fitz`), `dateparser`, `Pillow`, `imagehash`
  - AI SDK: `google-genai` (Model: `gemini-2.5-flash`). **Prohibited:** `google-generativeai` (deprecated) must never be imported or installed.
  - State & Storage: `upstash-redis` (`upstash_redis.asyncio.Redis`), `supabase` (Storage client)
  - Bot: `aiogram` (`>=3.0,<4.0`)
  - Testing: `pytest`, `pytest-asyncio`
- **Frontend (`frontend/`):**
  - Next.js (App Router, TypeScript, React)
  - Tailwind CSS
  - `lucide-react`, `qrcode.react`
- **Embed Widget (`frontend/public/widget.js`):**
  - Vanilla JavaScript (`< 15 KB` uncompressed, zero external dependencies, Shadow DOM isolated)

### 0.2 Zero-Config Local Fallbacks & Memory Isolation
- **Local Development Mode:** If `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` or `SUPABASE_URL` / `SUPABASE_KEY` are unset, the backend falls back automatically to an in-memory TTL cache and an in-memory audio byte store. The full application must start and pass core flows locally with only `GEMINI_API_KEY` configured.
- **Zero Disk Persistence:** All uploaded files and remote URL downloads must be processed exclusively inside `io.BytesIO` memory buffers. Raw user files are never written to local disk or object storage.

---

## 1. Exact Monorepo Directory Structure

```text
NoticeSetu/
├── docs/
│   ├── PRD.md
│   └── REQUIREMENTS.md
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                  # FastAPI app, CORS, lifespan, router registration, /health
│   │   ├── config.py                # pydantic-settings BaseSettings & env validation
│   │   ├── schemas.py               # Flat Pydantic v2 models (Gemini schema + API contracts)
│   │   ├── bot/
│   │   │   ├── __init__.py
│   │   │   ├── handlers.py          # aiogram v3 Router (/start, consent, doc/photo, callbacks)
│   │   │   └── run_polling.py       # Local dev entry: python -m app.bot.run_polling
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── notices.py           # /api/* & /telegram/webhook HTTP endpoints
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── security.py          # safe_fetch_url (SSRF) + validate_file_bytes (magic bytes)
│   │       ├── cache.py             # Two-tier Upstash Redis + in-memory 14-day TTL fallback
│   │       ├── extractor.py         # PyMuPDF dual-path PDF text/render + Pillow pHash
│   │       ├── pii_guard.py         # Pre-LLM PII detection, PIIBlockedError, ID masking
│   │       ├── simplifier.py        # google-genai Gemini 2.5 Flash extraction, Q&A, pipeline
│   │       ├── verifier.py          # Devanagari/date/fee PyMuPDF cross-check + scan guard
│   │       ├── tts.py               # Sarvam/Bhashini/none TTS + Supabase/memory audio store
│   │       └── calendar_ics.py      # Deterministic RFC-5545 .ics calendar generator
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_core.py             # Phase 1 Gate automated pytest suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── public/
│   │   └── widget.js                # < 15 KB vanilla JS Shadow DOM embed widget
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx           # Root layout, metadata, mobile-first viewport
│   │   │   ├── page.tsx             # Web Student Hub (/), dropzone, URL input, demo shortcuts
│   │   │   ├── notice/
│   │   │   │   └── [hash]/
│   │   │   │       └── page.tsx     # Action Card page (/notice/[hash])
│   │   │   ├── view/
│   │   │   │   └── page.tsx         # Standalone CSP-safe URL viewer (/view?url=...)
│   │   │   └── widget-demo/
│   │   │       └── page.tsx         # Mock college noticeboard showcasing widget.js
│   │   ├── components/
│   │   │   ├── ActionCard.tsx       # Governance banners, verification pills, EN/HI/MR card body
│   │   │   ├── AudioPlayer.tsx      # Inline regional voice brief player
│   │   │   ├── NoticeQA.tsx         # Collapsible circular-grounded Q&A drawer
│   │   │   ├── QrPosterModal.tsx    # A4 printable QR noticeboard poster modal
│   │   │   └── PipelineStepper.tsx  # Live multi-stage processing progress indicator
│   │   └── lib/
│   │       └── api.ts               # Typed API client, error mapping, demo payload helpers
│   ├── package.json
│   └── .env.example
├── docker-compose.yml
└── README.md
```

---

## 2. Functional Requirements (`FR-01` to `FR-10`)

### `FR-01` Hardened Ingestion (`backend/app/services/security.py`)
Cross-references [PRD §3.1 Feature A1](./PRD.md#feature-a1-notice-ingestion-hub-) and [PRD §6](./PRD.md#6-privacy-trust--dpdp-governance-requirements).

- **`safe_fetch_url(url: str) -> tuple[bytes, str]`:**
  1. Parse URL with `urllib.parse.urlparse`. Allow only schemes `http` and `https`. Reject empty hostnames or embedded `username`/`password`.
  2. Enforce port allowlist: implicit default or explicit port in `{80, 443}`. Reject all other ports with HTTP `400`.
  3. Resolve DNS records via `socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)`. Reject unresolvable hosts with HTTP `400`.
  4. Validate every resolved IP using `ipaddress.ip_address(ip)`. Reject if any flag is `True`: `is_private`, `is_loopback`, `is_link_local`, `is_multicast`, `is_reserved`, or `is_unspecified` (blocks `127.0.0.1`, `::1`, `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`, `169.254.169.254`, `0.0.0.0`, `fe80::/10`). Raise `SSRFBlockedError` → HTTP `400`.
  5. Execute `httpx.AsyncClient(follow_redirects=False, timeout=15.0)` streaming request.
  6. Manually handle up to `3` redirect hops (`301`, `302`, `303`, `307`, `308`). Resolve `Location` against the current URL via `urllib.parse.urljoin` and re-run steps 1–4 on every hop. Exceeding 3 hops raises HTTP `400`.
  7. Check `Content-Length` header if present; abort immediately with HTTP `413` if `> 10 * 1024 * 1024` bytes (`10 MB`).
  8. Stream chunks into `io.BytesIO()`. Incrementally track total bytes and abort immediately with HTTP `413` if accumulated size exceeds `10 * 1024 * 1024` bytes.
  9. Reject upstream HTTP errors (`status_code >= 400`) or network timeouts with HTTP `502`. Return `(buffer.getvalue(), content_type)`.

- **`validate_file_bytes(data: bytes) -> Literal["pdf", "jpeg", "png"]`:**
  1. Reject `len(data) == 0` with HTTP `400`.
  2. Reject `len(data) > 10 * 1024 * 1024` with HTTP `413`.
  3. Inspect leading magic bytes:
     - `data.startswith(b"%PDF-")` → `"pdf"`
     - `data.startswith(b"\xff\xd8\xff")` → `"jpeg"`
     - `data.startswith(b"\x89PNG\r\n\x1a\n")` → `"png"`
  4. Reject all other byte signatures with HTTP `400` (`"Unsupported file format. Upload a PDF, JPEG, or PNG under 10 MB."`).

### `FR-02` Two-Tier Caching (`backend/app/services/cache.py`)
Cross-references [PRD §3.1 Feature A1](./PRD.md#feature-a1-notice-ingestion-hub-) and [PRD §6.4](./PRD.md#6-privacy-trust--dpdp-governance-requirements).

- **Client & Fallback:** Uses `upstash_redis.asyncio.Redis(url=..., token=...)` when both `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` are non-empty. When either is unset, uses an in-memory TTL store guarded by `asyncio.Lock` with identical key semantics and expiration checks.
- **TTL:** All notice, hash-index, and audio cache entries use a strict 14-day TTL: `TTL_SECONDS = 1209600` (`14 * 24 * 60 * 60`).
- **Cache Keys:**
  - `notice:sha256:{raw_sha256}` — Tier-1 primary key storing serialized `ActionCardResponse` JSON.
  - `notice:text:{normalized_text_sha256}` — Tier-2 key for re-saved digital PDFs; maps to canonical `raw_sha256`.
  - `notice:phash:{phash_hex}` — Tier-2 key for recompressed camera photos/images; maps to canonical `raw_sha256`. Maintain an active index key `notice:phash:index` (JSON list or Redis set of `{phash_hex, sha256}`, pruned on read/expiry) so incoming images match any stored `phash_hex` within Hamming distance `<= 4` (`(int(h1, 16) ^ int(h2, 16)).bit_count() <= 4`).
  - `notice:prefix:{raw_sha256[:16]}` — 16-char hash prefix pointer to full 64-char `raw_sha256` (enables compact Telegram `callback_data <= 64` bytes).
  - `audio:url:{notice_hash}:{lang}` — Cached audio endpoint path or signed storage URL.
- **Return Metadata:** Every cache lookup returns `(cached_card | None, cache_hit: bool, cache_tier: Literal["tier1_sha256", "tier2_text", "tier2_phash", "miss"])`.

### `FR-03` Dual-Path Extraction (`backend/app/services/extractor.py`)
Cross-references [PRD §1.4](./PRD.md#14-deterministic-vs-ai-assisted-system-boundaries) and [PRD §4.2](./PRD.md#42-mandatory-top-governance-elements).

- **PDF Input (`filetype == "pdf"`):**
  1. Open strictly in memory via `fitz.open(stream=data, filetype="pdf")`. If opening fails or `doc.needs_pass` is `True`, raise `UnreadableDocumentError` → HTTP `422`.
  2. Cap iteration at `max_pages = min(len(doc), 10)`.
  3. Extract page text via `page.get_text("text")` for pages `0..max_pages-1`. Compute total non-whitespace character count across extracted pages (`len(re.sub(r"\s+", "", combined_text))`).
  4. **Digital PDF branch (`non_whitespace_chars >= 80`):**
     - `source_type = "digital_pdf"`
     - Compute `normalized_text_sha256` from lowercased, single-space-collapsed text for Tier-2 cache lookup.
     - Retain per-page `raw_pages: list[str]` for downstream `page.search_for()` verification.
  5. **Scanned PDF branch (`non_whitespace_chars < 80`):**
     - `source_type = "scanned_pdf"`
     - Render up to `3` pages (`min(len(doc), 3)`) at `150` DPI PNG (`page.get_pixmap(dpi=150).tobytes("png")`) into in-memory `list[bytes]`.
- **Image Input (`filetype in {"jpeg", "png"}`):**
  1. Open via `PIL.Image.open(io.BytesIO(data))`, run `.verify()`, re-open and apply `ImageOps.exif_transpose(img)` to correct mobile photo orientation.
  2. Convert palette/CMYK modes to `"RGB"`.
  3. Resize preserving aspect ratio so `max(width, height) <= 2000` (`Image.Resampling.LANCZOS`).
  4. Compute perceptual hash: `phash_hex = str(imagehash.phash(img))`.
  5. Export normalized image bytes into `io.BytesIO()` (`PNG` or `JPEG`) and set `source_type = "photo"`.

### `FR-04` Pre-LLM PII Guard (`backend/app/services/pii_guard.py`)
Cross-references [PRD §2.3](./PRD.md#23-explicit-non-goals-out-of-scope) and [PRD §6.3](./PRD.md#6-privacy-trust--dpdp-governance-requirements).

- **Detection Patterns:**
  - Indian 10-digit mobile numbers: `r"(?:\+91[\s-]?)?[6-9]\d{9}"`
  - Email addresses: `r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"`
  - 12-digit national ID patterns: `r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b"`
  - PAN numbers: `r"\b[A-Z]{5}\d{4}[A-Z]\b"`
  - Sensitive personal-record keywords (case-insensitive): `"merit list"`, `"defaulter list"`, `"hall ticket"`, `"admit card"`, `"fee receipt"`
  - Candidate roll / PRN / seat-number row patterns: lines containing tabular roll/seat/PRN tokens (e.g., alphanumeric roll/seat codes `>= 5` digits or `PRN`/`Roll No`/`Seat No` columns paired with student names/marks).
- **Blocking Rules (Raises `PIIBlockedError` → HTTP `422` `{"code": "PII_BLOCKED", "message": "..."}`):**
  1. `>= 5` distinct roll/PRN/seat-number rows detected, OR
  2. Any sensitive keyword (`"merit list"`, `"defaulter list"`, `"hall ticket"`, `"admit card"`, `"fee receipt"`) paired with `>= 3` personal IDs/names/mobile/email matches, OR
  3. `>= 3` personal 12-digit national IDs or PANs, OR `>= 5` personal mobile numbers/emails (excluding single official helpdesk lines).
- **Incidental Contact Allowance & Redaction:**
  - Public circulars often list `1` or `2` college office helpline numbers or official domain emails. `pii_guard` permits `<= 2` incidental office contact matches when no roll-number table or personal-record keyword rule triggers.
  - Before sending permitted text to Gemini, `redact_sensitive_ids(text)` masks any stray 12-digit national ID (`[REDACTED_ID]`) or PAN (`[REDACTED_PAN]`).

### `FR-05` Gemini 2.5 Flash Simplification (`backend/app/services/simplifier.py`)
Cross-references [PRD §3.1](./PRD.md#31-journey-a--web-student-hub----noticehash), [PRD §5](./PRD.md#5-multilingual--protected-campus-glossary-rules), and [PRD §3.1 Feature A5](./PRD.md#feature-a5-collapsible-grounded-qa-drawer).

- **SDK & Client:** Uses `from google import genai` and `from google.genai import types`. Initialize `genai.Client(api_key=settings.GEMINI_API_KEY)`.
- **Model & Structured Output Config:**
  - Model ID: `"gemini-2.5-flash"`
  - Config:
    ```python
    types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=NoticeExtraction,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        temperature=0.1,
        system_instruction=PROTECTED_GLOSSARY_SYSTEM_PROMPT,
    )
    ```
- **Protected Campus Glossary Prompt Rules:**
  - System instruction mandates source-agnostic parsing (`en`, `hi`, `mr`, or mixed bilingual) and outputs in all three languages (`en`, `hi`, `mr`).
  - Explicitly locks campus terms (`ATKT`, `KT`, `Hall Ticket`, `Bonafide`, `GR`, `Revaluation`, `PRN`, `Provisional Admission`, `Semester`) to natural English/Devanagari transliterated or inline bilingual forms as specified in [PRD §5.2](./PRD.md#52-protected-campus-glossary).
  - Instructs `voice_script` per language to remain `<= 380` characters. Deterministic Python post-processing enforces `len(voice_script) <= 380` at sentence/word boundaries before caching.
- **Concurrency & Rate-Limit Resilience:**
  - Wrap all `client.aio.models.generate_content(...)` calls with a module-level `asyncio.Semaphore(5)`.
  - Retry on HTTP `429` / resource-exhausted responses up to `3` attempts using exponential backoff (`1s`, `2s`, `4s` + small random jitter). If exhausted, raise `UpstreamRateLimitError` → HTTP `429`.
- **Shared Pipeline Entrypoint:** `process_notice_bytes(data: bytes, source_hint: str = "upload", source_url: str | None = None) -> ActionCardResponse` orchestrates `FR-01` → `FR-02` (Tier-1 SHA-256) → `FR-03` → `FR-02` (Tier-2 text/pHash) → `FR-04` → `FR-05` → `FR-06` → `FR-02` (write cache). Both `routes/notices.py` and `bot/handlers.py` invoke this function.

### `FR-06` Deterministic Verification (`backend/app/services/verifier.py`)
Cross-references [PRD §4.2](./PRD.md#42-mandatory-top-governance-elements).

- **Normalization Helpers:**
  - Translate Devanagari digits `०१२३४५६७८९` → ASCII `0123456789` via `str.maketrans("०१२३४५६७८९", "0123456789")`.
  - Strip currency symbols (`₹`, `Rs.`, `Rs`, `INR`) and commas (`,`) when comparing numeric fee values.
  - Parse extracted date strings via `dateparser.parse(raw_date, settings={"DATE_ORDER": "DMY"})` and generate normalized date match variants (`DD/MM/YYYY`, `DD-MM-YYYY`, `D/M/YYYY`, `YYYY-MM-DD`, `DD MMM YYYY`, `DD MMMM YYYY`).
- **Digital PDF Path (`source_type == "digital_pdf"`):**
  1. Cross-check every `FeeItem.amount_numeric` / `FeeItem.raw_amount` and every `DeadlineItem.date_iso` / `DeadlineItem.raw_date` against normalized `PyMuPDF` raw text.
  2. For each `SourceQuote`, locate matching page numbers using `page.search_for(quote_snippet)` across `PyMuPDF` pages (falling back to whitespace-normalized substring matching per page when line wraps split a phrase). Update `page_number` deterministically when matched.
  3. Set `verification_status = "source_matched"` if all extracted fees and deadlines match raw text (or if none were extracted and no unverified numbers exist); otherwise set `verification_status = "verify_original"` and list mismatched descriptions in `unverified_items`.
- **Scanned PDF / Photo Path (`source_type in {"scanned_pdf", "photo"}`):**
  1. Always set `verification_status = "scan_extracted"`.
  2. Concatenate all AI-extracted text (`raw_extracted_text`, `quotes`, `tldr`, `checklist`, `deadlines`, `fees`) and run `pii_guard.screen_text(...)` BEFORE caching or returning. If `PIIBlockedError` is raised, discard extraction immediately and return HTTP `422` (`PII_BLOCKED`).

### `FR-07` Grounded Notice Q&A (`backend/app/routes/notices.py` + `backend/app/services/simplifier.py`)
Cross-references [PRD §3.1 Feature A5](./PRD.md#feature-a5-collapsible-grounded-qa-drawer).

- `POST /api/qa` accepts `QARequest(notice_hash, question, lang)` where `1 <= len(question.strip()) <= 300` and `lang in {"en", "hi", "mr"}`.
- Looks up cached `ActionCardResponse` + stored circular context by `notice_hash` (`HTTP 404` if missing or expired).
- Calls `gemini-2.5-flash` (`thinking_budget=0`, `asyncio.Semaphore(5)`) with strict circular-only grounding instructions, untrusted-input wrapping around the user question, and target language `lang`.
- When the answer is absent from the circular, returns `found_in_notice=False` and the exact refusal string (`"This information is not mentioned in the circular — please check with your college office"` in `en`, or its natural `hi`/`mr` translation alongside the refusal intent).

### `FR-08` Cached Regional TTS (`backend/app/services/tts.py`)
Cross-references [PRD §3.1 Feature A3](./PRD.md#feature-a3-cached-regional-voice-brief-audioplayer).

- **Provider Selection:** Controlled by `TTS_PROVIDER` (`"sarvam"` | `"bhashini"` | `"none"`). Default `"sarvam"` when `SARVAM_API_KEY` is present, or graceful fallback when `"none"` / key missing (returns HTTP `503` on `/api/audio/{hash}/{lang}` without disrupting text Action Card endpoints).
- **Sarvam TTS Integration:**
  - Endpoint: `POST https://api.sarvam.ai/text-to-speech`
  - Header: `api-subscription-key: <SARVAM_API_KEY>`
  - Payload:
    - `text`: cached `voice_script` for `lang`, strictly `<= 380` chars (well under Sarvam's `450`-char limit)
    - `target_language_code`: `{"en": "en-IN", "hi": "hi-IN", "mr": "mr-IN"}[lang]`
    - `model`: `settings.SARVAM_TTS_MODEL` (default `"bulbul:v3"`)
    - `speaker`: `settings.SARVAM_TTS_SPEAKER` (default `"shubh"`; operators selecting `"bulbul:v4-flash"` configure matching v4 persona IDs via `SARVAM_TTS_SPEAKER`)
    - `output_audio_codec`: `"mp3"`
- **Storage & Caching:**
  - Decode base64 `audios[0]` to MP3 `bytes`.
  - If `SUPABASE_URL` and `SUPABASE_KEY` are configured: upload once to Supabase Storage bucket `notice-audio` at path `{notice_hash}/{lang}.mp3` (`content-type: audio/mpeg`) and store reference in Redis (`audio:url:{notice_hash}:{lang}`, TTL `1209600`s).
  - If Supabase is unset: store MP3 bytes in the in-memory audio TTL dict (`(notice_hash, lang)` → bytes, TTL `1209600`s).
  - `GET /api/audio/{hash}/{lang}` serves `audio/mpeg` bytes with `Cache-Control: public, max-age=86400`.

### `FR-09` RFC-5545 Calendar Export (`calendar_ics.py`) & Telegram Bot (`bot/`)
Cross-references [PRD §3.1 Feature A4](./PRD.md#feature-a4-one-click-ics-calendar-export) and [PRD §3.3](./PRD.md#33-journey-c--telegram-bot-zero-upload-mobile-flow).

- **Calendar Export (`calendar_ics.py`):**
  - `generate_ics(card: ActionCardResponse) -> str` builds a compliant RFC-5545 `VCALENDAR` (`VERSION:2.0`, `PRODID:-//NoticeSetu//Circular Deadlines//EN`, `CALSCALE:GREGORIAN`).
  - Filters `card.deadlines` for valid `date_iso` (`YYYY-MM-DD`). If zero valid dates exist, `GET /api/notice/{hash}/ics` returns HTTP `404` (`"No calendar deadlines found in this circular."`).
  - Emits one `VEVENT` per valid deadline using `UID:{notice_hash}-{index}@noticesetu`, `DTSTAMP`, all-day `DTSTART;VALUE=DATE:{YYYYMMDD}` (or `DTSTART;TZID=Asia/Kolkata:{YYYYMMDD}T{HHMMSS}` when `time_24h` is present), `SUMMARY`, and `DESCRIPTION` containing `ref_no`, `issue_date`, and `"Unofficial Assistive Summary — Confirm on the official circular."`. Lines are folded at `75` octets with `\r\n` endings.
- **Telegram Bot (`app/bot/handlers.py`, `app/bot/run_polling.py`):**
  - Built on `aiogram` v3 (`Bot`, `Dispatcher`, `Router`, `BufferedInputFile`).
  - `/start`: Replies with `"Public college circulars only — do not send hall tickets, merit lists, or personal IDs."` and inline button `"I Understand — Continue"` (`callback_data="consent:ok"`).
  - Consent state kept in an ephemeral in-memory `set[int]` (cleared on restart; never persisted to disk/database and never logged against `notice_hash` or phone numbers, upholding DPDP rules).
  - Accepts Telegram `document` (MIME `application/pdf`, pre-checked `file_size <= 10 * 1024 * 1024`) and `photo` (largest `PhotoSize`, `file_size <= 10 * 1024 * 1024`). Downloads into `io.BytesIO()` and calls `process_notice_bytes()`.
  - Formats response strictly `<= 4096` characters with inline keyboard:
    - Row 1: `English` (`l:en:{h16}`) | `हिंदी` (`l:hi:{h16}`) | `मराठी` (`l:mr:{h16}`)
    - Row 2: `"Play Voice Note"` (`v:{active_lang}:{h16}`) | `"Open Full Action Card & Calendar"` (URL `{FRONTEND_BASE_URL}/notice/{notice_hash}`)
  - Callback `"Play Voice Note"` calls `tts.get_or_create_audio(notice_hash, lang)` and sends `BufferedInputFile(audio_bytes, filename=f"noticesetu_{lang}.mp3")` via `answer_audio` / `answer_voice`.
  - Webhook route `POST /telegram/webhook`: verifies `X-Telegram-Bot-Api-Secret-Token` header against `settings.TELEGRAM_WEBHOOK_SECRET` using `hmac.compare_digest`. Missing/invalid header or unset secret returns HTTP `403`.
  - `python -m app.bot.run_polling`: starts long polling when `TELEGRAM_BOT_TOKEN` is set; FastAPI server boots cleanly even when `TELEGRAM_BOT_TOKEN` is empty.

### `FR-10` Next.js Frontend & Shadow DOM Widget
Cross-references [PRD §3.1](./PRD.md#31-journey-a--web-student-hub----noticehash), [PRD §3.2](./PRD.md#32-journey-b--live-demo-shortcuts-built-into-), [PRD §3.4](./PRD.md#34-journey-d--college-website-1-line-widget-widget-demo--publicwidgetjs--csp-fallback-viewurl), and [PRD §4](./PRD.md#4-action-card-information-architecture--design-system).

- **Routes (`frontend/src/app/`):**
  - `/`: Drag-and-drop file dropzone (`.pdf`, `.jpg`, `.jpeg`, `.png`, client-side `<= 10 MB` check), URL input + `"Simplify Notice"` button, live `PipelineStepper`, inline Privacy Block Screen on `422 PII_BLOCKED`, and Journey B demo buttons (`"Try Sample Exam Circular"` and `"Test PII Protection (Mock Merit List)"`).
  - `/notice/[hash]`: Fetches `GET /api/notice/{hash}` and renders `ActionCard` (with `AudioPlayer`, `NoticeQA`, `.ics` download, and `QrPosterModal`).
  - `/view?url=...`: Standalone CSP-safe route. Extracts `url` search param, invokes `POST /api/simplify` with `url`, shows `PipelineStepper` / Privacy Block Screen, and renders the resulting `ActionCard` cleanly in full-page or iframe contexts.
  - `/widget-demo`: Mock college noticeboard table with realistic conflicting host CSS and `<script src="/widget.js" defer></script>` loaded live.
- **Embed Widget (`frontend/public/widget.js`):**
  - Vanilla JS `< 15 KB` (`15,360` bytes), zero runtime dependencies.
  - On `DOMContentLoaded` (and via `MutationObserver`), locates `a[href$=".pdf" i], a[href*=".pdf?" i]`, skips anchors marked `data-noticesetu-attached="true"`, resolves absolute URL via `new URL(href, window.location.href).href`, and injects a `<span>` host with `attachShadow({ mode: "open" })` rendering a `#0D9488` `"Simplify (EN/हिं/म)"` pill.
  - Clicking opens an isolated Shadow DOM modal overlay containing `<iframe src="{origin}/view?url={encoded}">`, an `"Open in New Tab"` anchor fallback, and `Esc`/close button handling.

---

## 3. Exact Data Models & REST API Contracts

### 3.1 Flat Pydantic v2 Schemas (`backend/app/schemas.py`)
All Gemini `response_schema` models avoid recursive `$defs`, `Any`, and polymorphic unions so `gemini-2.5-flash` compiles schemas cleanly.

```python
from typing import Literal
from pydantic import BaseModel, Field


class DeadlineItem(BaseModel):
    title: str = Field(..., description="Short event label, e.g., Exam Form Submission")
    raw_date: str = Field(..., description="Exact date/time phrase as written in circular")
    date_iso: str = Field("", description="YYYY-MM-DD if exact calendar date exists, else empty string")
    time_24h: str = Field("", description="HH:MM in 24h IST if stated, else empty string")
    fee_note: str = Field("", description="Associated fee or late-fee note if applicable")


class FeeItem(BaseModel):
    label: str = Field(..., description="Fee category, e.g., Regular Exam Fee")
    raw_amount: str = Field(..., description="Exact amount phrase from circular, e.g., Rs. 500/-")
    amount_numeric: str = Field("", description="ASCII digits only, e.g., 500")


class SourceQuote(BaseModel):
    quote: str = Field(..., description="Verbatim untranslated excerpt from the circular")
    page_number: int = Field(1, ge=1, description="1-based page number")


class LocalizedContent(BaseModel):
    title: str
    tldr: str = Field(..., description="2-4 plain sentences summarizing the notice")
    eligibility_tags: list[str]
    checklist: list[str]
    required_documents: list[str]
    voice_script: str = Field(..., description="Spoken brief strictly <= 380 characters")


class NoticeExtraction(BaseModel):
    circular_ref_no: str = Field("", description="Official Ref No. or empty string if absent")
    issue_date: str = Field("", description="Issue date string or empty string if absent")
    detected_source_languages: list[str]
    raw_extracted_text: str = Field("", description="For scans/photos: transcribed circular text for PII guard")
    deadlines: list[DeadlineItem]
    fees: list[FeeItem]
    quotes: list[SourceQuote]
    en: LocalizedContent
    hi: LocalizedContent
    mr: LocalizedContent


class ActionCardResponse(BaseModel):
    notice_hash: str
    source_type: Literal["digital_pdf", "scanned_pdf", "photo"]
    verification_status: Literal["source_matched", "verify_original", "scan_extracted"]
    unverified_items: list[str] = Field(default_factory=list)
    cache_hit: bool = False
    cache_tier: Literal["tier1_sha256", "tier2_text", "tier2_phash", "miss"] = "miss"
    cache_ttl_seconds: int = 1209600
    has_ics_deadlines: bool = False
    disclaimer: str = "Unofficial Assistive Summary — Confirm on the official circular."
    extraction: NoticeExtraction


class QARequest(BaseModel):
    notice_hash: str = Field(..., min_length=16, max_length=64)
    question: str = Field(..., min_length=1, max_length=300)
    lang: Literal["en", "hi", "mr"] = "en"


class QAResponse(BaseModel):
    answer: str
    found_in_notice: bool
    cited_pages: list[int] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str
```

### 3.2 REST API Endpoints

| Method & Path | Request Format | Success Response | Error Codes |
| :--- | :--- | :--- | :--- |
| `GET /health` | None | `200 OK`: `{"status": "ok", "redis": "connected" \| "memory_fallback", "supabase": "connected" \| "memory_fallback", "tts_provider": str, "telegram_configured": bool}` | — |
| `POST /api/simplify` | `multipart/form-data` with either `file` (`UploadFile`) OR `url` (`Form[str]`) | `200 OK`: `ActionCardResponse` JSON | `400` (invalid file/URL/SSRF), `413` (`> 10 MB`), `422` (`PII_BLOCKED` or encrypted/unreadable PDF), `429` (rate limit), `502` (upstream fetch/AI failure) |
| `GET /api/notice/{hash}` | Path param `hash` (64-char hex `SHA-256`) | `200 OK`: `ActionCardResponse` JSON (`cache_hit: true`) | `400` (malformed hash), `404` (not found or 14-day TTL expired) |
| `POST /api/qa` | `application/json`: `QARequest` | `200 OK`: `QAResponse` JSON | `400` (validation error), `404` (notice not found/expired), `429`, `502` |
| `GET /api/notice/{hash}/ics` | Path param `hash` | `200 OK`: `text/calendar; charset=utf-8` (`Content-Disposition: attachment; filename="noticesetu-{hash[:12]}.ics"`) | `404` (notice missing or zero valid calendar deadlines) |
| `GET /api/audio/{hash}/{lang}` | Path params `hash`, `lang` (`en` \| `hi` \| `mr`) | `200 OK`: `audio/mpeg` byte stream (`Cache-Control: public, max-age=86400`) | `400` (invalid `lang`), `404` (notice missing), `502` (TTS upstream failure), `503` (`TTS_PROVIDER=none` or missing TTS credentials) |
| `POST /telegram/webhook` | Telegram `Update` JSON + header `X-Telegram-Bot-Api-Secret-Token` | `200 OK`: `{"ok": true}` | `403` (missing or invalid secret token) |

---

## 4. Non-Functional Requirements

### 4.1 Security
- **SSRF Hardening:** Enforce scheme/port allowlists, DNS resolution IP checks prior to connecting, manual redirect hop inspection (`<= 3`), and streaming `10 MB` byte ceilings.
- **Magic-Byte Inspection:** Never trust `Content-Type` headers or filename extensions for file classification.
- **Webhook Authentication:** Validate `X-Telegram-Bot-Api-Secret-Token` on `POST /telegram/webhook` with constant-time comparison (`hmac.compare_digest`); return `403` on mismatch or unconfigured secret.
- **CORS Allowlist:** Configure FastAPI `CORSMiddleware` strictly from `ALLOWED_ORIGINS` (never wildcard `*` with credentials).
- **Widget Isolation:** All injected DOM and modal styles live inside `ShadowRoot`; host URLs are strictly URL-encoded before embedding in `/view?url=...`.

### 4.2 Privacy & DPDP Compliance
- **Zero Accounts:** No login, cookies tracking users, phone-number storage, or user profile tables.
- **Zero User-to-Document Mapping:** Logs must never associate a Telegram user ID, IP address, or session with any `notice_hash` or extracted notice content. Strip raw `?url=` query parameters from server request logs where feasible.
- **Strict RAM Processing:** Input files reside solely in `io.BytesIO()` and are garbage-collected after request completion.
- **14-Day TTL:** All cached notices, hash indices, and audio files expire automatically at `1,209,600` seconds.

### 4.3 Operational Resilience
- **Cold-Start Readiness:** `GET /health` responds in `< 100 ms` without invoking external Gemini or TTS APIs.
- **Graceful Degradation:** Missing Upstash Redis, Supabase Storage, Sarvam TTS, or Telegram credentials degrade only their optional subsystem to local fallbacks or clean `503` responses without crashing core web extraction.
- **Bounded Concurrency:** `asyncio.Semaphore(5)` prevents Gemini burst spikes; `429` retry backoff handles transient quota pressure.

---

## 5. Environment Variables Contract (`.env.example`)

### 5.1 Backend (`backend/.env.example`)

| Variable | Required | Default | Fallback / Purpose |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | **Yes** | — | Required for `google-genai` `gemini-2.5-flash` extraction and Q&A. |
| `TTS_PROVIDER` | No | `sarvam` | `"sarvam"` \| `"bhashini"` \| `"none"`. If `"none"`, audio endpoint returns `503`. |
| `SARVAM_API_KEY` | Conditional | `""` | Required when `TTS_PROVIDER=sarvam`; if empty, audio degrades cleanly (`503`). |
| `SARVAM_TTS_MODEL` | No | `bulbul:v3` | Sarvam TTS model ID (`bulbul:v3` or `bulbul:v4-flash`). |
| `SARVAM_TTS_SPEAKER` | No | `shubh` | Speaker voice compatible with selected `SARVAM_TTS_MODEL`. |
| `UPSTASH_REDIS_REST_URL` | No | `""` | If unset, uses in-memory 14-day TTL cache fallback. |
| `UPSTASH_REDIS_REST_TOKEN` | No | `""` | Paired auth token for Upstash Redis REST API. |
| `SUPABASE_URL` | No | `""` | If unset, uses in-memory MP3 audio store fallback. |
| `SUPABASE_KEY` | No | `""` | Service/storage key for Supabase bucket `notice-audio`. |
| `TELEGRAM_BOT_TOKEN` | No | `""` | Required only to activate Telegram bot webhook/polling; FastAPI boots without it. |
| `TELEGRAM_WEBHOOK_SECRET` | No | `""` | Required for `POST /telegram/webhook`; unset causes webhook requests to fail closed (`403`). |
| `FRONTEND_BASE_URL` | No | `http://localhost:3000` | Base URL used by Telegram bot `"Open Full Action Card & Calendar"` links. |
| `ALLOWED_ORIGINS` | No | `http://localhost:3000` | Comma-separated CORS origin allowlist for FastAPI. |

### 5.2 Frontend (`frontend/.env.example`)

| Variable | Required | Default | Purpose |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | **Yes** | `http://localhost:8000` | Base URL for backend REST API calls from Next.js client/server components. |
| `NEXT_PUBLIC_APP_URL` | No | `http://localhost:3000` | Canonical origin used to build QR poster URLs and widget demo links. |

---

## 6. Automated Verification & 4-Phase Build Gates

An AI coding agent must satisfy each phase gate before advancing to the next phase:

### Phase 1 Gate — Backend Core & Security (`pytest backend/tests/test_core.py`)
Must contain and pass all **7 mandatory automated tests** (using mocked Gemini/TTS clients where external keys are absent):
1. **SSRF Block Test:** `safe_fetch_url` rejects `http://127.0.0.1/a.pdf`, `http://169.254.169.254/latest/meta-data/`, and `http://10.0.0.1/internal.pdf` (plus DNS resolutions returning private/loopback IPs) before issuing outbound HTTP requests.
2. **Oversized File Rejection:** `validate_file_bytes` (and `POST /api/simplify`) rejects payloads `> 10 * 1024 * 1024` bytes with HTTP `413`.
3. **Invalid Magic Bytes Rejection:** `validate_file_bytes` rejects non-PDF/JPEG/PNG bytes (e.g., `.exe` or `.html` renamed to `.pdf`) with HTTP `400`.
4. **Pre-LLM PII Block Test:** `pii_guard` blocks a synthetic merit list / dense roll-number table and `POST /api/simplify` returns HTTP `422` with `code == "PII_BLOCKED"` while making `0` calls to `google-genai`.
5. **Devanagari & Date Normalization Test:** `verifier.py` converts Devanagari digits (`०१२३४५६७८९` → `0123456789`), strips `₹`/`Rs.`/commas, parses Indian dates via `dateparser`, and produces `source_matched` when digital `PyMuPDF` text matches and `verify_original` when a figure is absent.
6. **RFC-5545 `.ics` Generation Test:** `calendar_ics.generate_ics` outputs valid `BEGIN:VCALENDAR` / `BEGIN:VEVENT` / `END:VCALENDAR` blocks containing `Asia/Kolkata` timezone metadata, deterministic `UID`, and the official disclaimer.
7. **Tier-1 SHA-256 Cache Hit Test:** Submitting identical valid circular bytes twice invokes `simplifier` once and returns `cache_hit=True` and `cache_tier="tier1_sha256"` on the second call.

### Phase 2 Gate — Telegram Bot & Webhook Security
- `python -c "import app.main, app.bot.handlers"` succeeds cleanly whether `TELEGRAM_BOT_TOKEN` is set or empty.
- FastAPI application boots and serves `GET /health` with `200 OK` when `TELEGRAM_BOT_TOKEN` is omitted.
- `POST /telegram/webhook` returns `403` when `X-Telegram-Bot-Api-Secret-Token` is missing or mismatched.

### Phase 3 Gate — Frontend & Shadow DOM Widget
- `npm run build` in `frontend/` completes with exit code `0` and zero TypeScript or ESLint errors.
- `frontend/public/widget.js` file size is strictly `< 15,360` bytes (`< 15 KB`) with zero third-party script dependencies.
- `/`, `/notice/[hash]`, `/view?url=...`, and `/widget-demo` render cleanly on `360px` mobile and desktop viewports.

### Phase 4 Gate — Containerization & Runbook
- `backend/Dockerfile` builds cleanly with non-root execution or minimal Python `3.11-slim` base and required `PyMuPDF`/Pillow system libs.
- `docker-compose.yml` wires `backend` (`:8000`) and `frontend` (`:3000`) with `.env` configuration.
- `README.md` documents exact local run steps (only `GEMINI_API_KEY` required), Telegram polling (`python -m app.bot.run_polling`) vs. webhook setup, widget 1-line embed snippet, and test execution commands.

