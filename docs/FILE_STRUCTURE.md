# NoticeSetu — Application & Code File Structure

**Document Status:** Architecture & Scaffolding Specification  
**Product Name:** NoticeSetu  
**Cross-References:** [docs/PRD.md](./PRD.md) | [docs/REQUIREMENTS.md](./REQUIREMENTS.md)  
**Maintainers:** Aditya Sanjay Naikwadi, Nihal Sunil Kene  

---

## 1. Complete Monorepo Directory Tree

```text
noticesetu/
├── docker-compose.yml
├── README.md
├── scripts/
│   └── scaffold.sh
├── docs/
│   ├── PRD.md
│   ├── REQUIREMENTS.md
│   └── FILE_STRUCTURE.md
├── backend/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── security.py
│   │   │   ├── cache.py
│   │   │   ├── extractor.py
│   │   │   ├── pii_guard.py
│   │   │   ├── simplifier.py
│   │   │   ├── verifier.py
│   │   │   ├── tts.py
│   │   │   └── calendar_ics.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── notices.py
│   │   └── bot/
│   │       ├── __init__.py
│   │       ├── handlers.py
│   │       └── run_polling.py
│   └── tests/
│       ├── __init__.py
│       └── test_core.py
└── frontend/
    ├── package.json
    ├── .env.example
    ├── public/
    │   └── widget.js
    └── src/
        ├── lib/
        │   └── api.ts
        ├── app/
        │   ├── layout.tsx
        │   ├── page.tsx
        │   ├── notice/
        │   │   └── [hash]/
        │   │       └── page.tsx
        │   ├── view/
        │   │   └── page.tsx
        │   └── widget-demo/
        │       └── page.tsx
        └── components/
            ├── ActionCard.tsx
            ├── AudioPlayer.tsx
            ├── NoticeQA.tsx
            ├── QrPosterModal.tsx
            └── PipelineStepper.tsx
```

---

## 2. File-by-File Architectural Contract Table

### 2.1 Root, Documentation & Infrastructure Files

| File Path | Single Responsibility | Key Functions / Exports / Artifacts | Strict Dependency & Data Boundaries |
| :--- | :--- | :--- | :--- |
| `docker-compose.yml` | Local multi-service container orchestration | Services: `backend` (`:8000`), `frontend` (`:3000`), `.env` wiring | Mounts no persistent upload volume for raw user files; enforces stateless RAM processing inside containers. |
| `README.md` | Developer setup and operations runbook | Local setup (`GEMINI_API_KEY` minimal run), `run_polling` vs. webhook instructions, 1-line `widget.js` snippet, `pytest` & `npm run build` commands | Must document zero-config Redis/Supabase memory fallbacks accurately without unverified performance claims. |
| `scripts/scaffold.sh` | Idempotent monorepo directory and stub generator | `ensure_file()`, `check_exists()`, 6-point verification check | Never overwrites existing files; validates `frontend/public/widget.js < 15360` bytes. |
| `docs/PRD.md` | Product specification and user journeys | User stories, UI/UX specs, Protected Campus Glossary, DPDP rules, pilot plan | Authoritative source for product copy, verification pill names, and explicit non-goals. |
| `docs/REQUIREMENTS.md` | Engineering specification and API contracts | `FR-01`–`FR-10`, Pydantic schemas, REST endpoints, `.env` matrix, 4-phase build gates | Locks Python/Next.js stack, prohibits deprecated `google-generativeai`, and defines test assertions. |
| `docs/FILE_STRUCTURE.md` | Module ownership and coupling contract | Directory tree, per-file contract table, acyclic dependency map | Prevents circular imports, route-to-bot coupling, and boundary drift across team members. |

### 2.2 Backend Core, Routes, Bot & Tests (`backend/`)

| File Path | Single Responsibility | Key Functions / Endpoints / Classes / Exports | Strict Dependency & Data Boundaries |
| :--- | :--- | :--- | :--- |
| `backend/requirements.txt` | Python 3.11+ dependency manifest | `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `python-multipart`, `httpx`, `PyMuPDF`, `dateparser`, `Pillow`, `imagehash`, `google-genai`, `upstash-redis`, `supabase`, `aiogram`, `pytest`, `pytest-asyncio` | Must include `google-genai` and `aiogram>=3.0,<4.0`; must NOT include deprecated `google-generativeai`. |
| `backend/Dockerfile` | Container build for FastAPI + PyMuPDF runtime | `python:3.11-slim`, dependency install, `uvicorn app.main:app --host 0.0.0.0 --port 8000` | Runs without writable upload directories; sets `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`. |
| `backend/.env.example` | Backend environment variable template | `GEMINI_API_KEY`, `TTS_PROVIDER`, `SARVAM_API_KEY`, `SARVAM_TTS_MODEL`, `SARVAM_TTS_SPEAKER`, `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `SUPABASE_URL`, `SUPABASE_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`, `FRONTEND_BASE_URL`, `ALLOWED_ORIGINS` | Contains placeholder keys only; never commits real secrets. |
| `backend/app/config.py` | Typed environment configuration | `Settings(BaseSettings)`, `get_settings()` | Reads `.env` once via `pydantic-settings`; exposes safe defaults so app boots when optional Redis/Supabase/Telegram keys are empty. |
| `backend/app/schemas.py` | Flat Pydantic v2 data and API contracts | `DeadlineItem`, `FeeItem`, `SourceQuote`, `LocalizedContent`, `NoticeExtraction`, `ActionCardResponse`, `QARequest`, `QAResponse`, `ErrorResponse` | Pure schema definitions with zero service imports; avoids recursive `$defs` and polymorphic unions for Gemini structured output compatibility. |
| `backend/app/main.py` | FastAPI application factory and health endpoint | `app`, `lifespan()`, `GET /health`, `CORSMiddleware` | Mounts `notices.router`; configures CORS strictly from `ALLOWED_ORIGINS`; never reads or writes user uploads directly. |
| `backend/app/services/security.py` | Hardened URL fetching and byte validation | `SSRFBlockedError`, `safe_fetch_url(url)`, `validate_file_bytes(data)` | Blocks non-`http`/`https`, ports outside `{80, 443}`, private/loopback/link-local/multicast/reserved IPs (`127.0.0.1`, `::1`, `10.x`, `172.16-31.x`, `192.168.x`, `169.254.169.254`), `> 3` redirects (`httpx.AsyncClient(follow_redirects=False, timeout=15.0)`), non-`PDF/JPEG/PNG` magic bytes (`400`), and `> 10 MB` payloads (`413`) inside `io.BytesIO`. |
| `backend/app/services/cache.py` | Two-tier caching and audio URL store | `NoticeCache`, `TTL_SECONDS = 1209600`, `get_by_sha256()`, `get_by_text_hash()`, `get_by_phash()`, `save_notice()`, `resolve_hash_prefix()`, `get_audio_bytes()`, `save_audio_bytes()` | Uses `upstash_redis.asyncio.Redis` with 14-day TTL and automatic in-memory TTL dict fallback when Upstash env vars are unset; enforces Hamming distance `<= 4` on `notice:phash:*` lookups; zero user-ID logging. |
| `backend/app/services/extractor.py` | Dual-path PDF and image parsing | `ExtractedPayload`, `UnreadableDocumentError`, `extract_document(data, filetype)` | Uses `fitz.open(stream=data, filetype="pdf")` capped at `10` pages (`>= 80` non-whitespace chars → `digital_pdf`, else up to `3` pages at `150` DPI PNG → `scanned_pdf`); resizes images `<= 2000px` with Pillow and computes `imagehash.phash` → `photo`; operates strictly on `io.BytesIO`. |
| `backend/app/services/pii_guard.py` | Deterministic pre-LLM PII screening | `PIIBlockedError`, `screen_text(text)`, `redact_sensitive_ids(text)` | Detects Indian mobile numbers, emails, 12-digit national IDs, PAN, dense roll/PRN/seat-number tables (`>= 5`), and sensitive record keywords (`merit list`, `defaulter list`, `hall ticket`, `admit card`, `fee receipt`) paired with `>= 3` personal IDs/names; raises `PIIBlockedError` → HTTP `422 PII_BLOCKED` before LLM calls while permitting `<= 2` incidental office helpdesk contacts. |
| `backend/app/services/simplifier.py` | Gemini 2.5 Flash extraction, Q&A, and shared pipeline | `process_notice_bytes(data, source_hint, source_url)`, `extract_action_card(payload)`, `answer_notice_question(card, question, lang)` | Uses `google.genai.Client` with `gemini-2.5-flash`, `ThinkingConfig(thinking_budget=0)`, `response_schema=NoticeExtraction`, Protected Campus Glossary prompt, `<= 380`-char `voice_script` enforcement, `asyncio.Semaphore(5)`, and `429` exponential backoff. Must never import `routes/` or `bot/`. |
| `backend/app/services/verifier.py` | Deterministic cross-checking and scan PII gate | `normalize_devanagari_digits(text)`, `verify_extraction(extraction, payload)` | Normalizes `०–९` to `0–9`, strips currency/commas, parses dates via `dateparser`, matches quotes via `page.search_for()`; sets `source_matched` or `verify_original` on `digital_pdf`; always sets `scan_extracted` on `scanned_pdf`/`photo` and runs `pii_guard.screen_text()` on extracted scan text before caching. |
| `backend/app/services/tts.py` | Cached regional voice brief synthesis | `get_or_create_audio(notice_hash, lang, script)` | Supports `TTS_PROVIDER` (`sarvam`, `bhashini`, `none`); posts to `https://api.sarvam.ai/text-to-speech` (`api-subscription-key`, `bulbul:v3` + `shubh` or configurable `bulbul:v4-flash` persona ID, `en-IN`/`hi-IN`/`mr-IN`, `mp3`, `<= 380` chars); stores MP3 once in Supabase Storage bucket `notice-audio` (`{notice_hash}/{lang}.mp3`) or in-memory fallback. |
| `backend/app/services/calendar_ics.py` | RFC-5545 calendar export generator | `generate_ics(card: ActionCardResponse) -> str` | Pure deterministic formatting in `Asia/Kolkata` timezone (`VEVENT`, `UID`, `SUMMARY`, `DESCRIPTION` with official disclaimer); performs zero network or AI calls. |
| `backend/app/routes/notices.py` | FastAPI REST routes and Telegram webhook endpoint | `router`, `POST /api/simplify`, `GET /api/notice/{hash}`, `POST /api/qa`, `GET /api/notice/{hash}/ics`, `GET /api/audio/{hash}/{lang}`, `POST /telegram/webhook` | Thin transport layer delegating business logic to `services/`; validates `X-Telegram-Bot-Api-Secret-Token` with `hmac.compare_digest` (`403` on failure); never accesses `bot/run_polling.py`. |
| `backend/app/bot/handlers.py` | `aiogram` v3 Telegram bot router | `bot_router`, `get_bot_and_dispatcher()`, `cmd_start()`, `on_consent()`, `on_document_or_photo()`, `on_lang_switch()`, `on_voice_note()` | Calls shared `process_notice_bytes()`, `tts.get_or_create_audio()`, and `cache`; enforces `<= 10 MB` pre-download check, `<= 64`-byte `callback_data`, `<= 4096`-char replies, and zero user-to-document persistence; never duplicates extraction/PII code. |
| `backend/app/bot/run_polling.py` | Standalone local Telegram polling runner | `main()` (`python -m app.bot.run_polling`) | Boots `Dispatcher.start_polling(bot)` for local testing without webhook tunneling; omitted during FastAPI-only web boots. |
| `backend/tests/test_core.py` | Phase 1 Gate automated test suite | 7 mandatory `pytest` cases (SSRF, `> 10 MB`, magic bytes, PII `422`, Devanagari/date verifier, `.ics` export, Tier-1 `SHA-256` cache hit) | Uses mocked Gemini/TTS calls where external keys are absent; validates zero disk writes and zero LLM calls on PII block. |

### 2.3 Frontend Application, Components & Widget (`frontend/`)

| File Path | Single Responsibility | Key Exports / Routes / Components | Strict Dependency & Data Boundaries |
| :--- | :--- | :--- | :--- |
| `frontend/package.json` | Frontend package manifest and scripts | `next`, `react`, `react-dom`, `tailwindcss`, `lucide-react`, `qrcode.react`, `typescript`, `dev`/`build`/`start`/`lint` | Keeps dependencies minimal; zero heavy UI component libraries that bloat mobile bundles. |
| `frontend/.env.example` | Frontend environment variable template | `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_URL` | Public build-time variables only; never exposes backend API secrets. |
| `frontend/public/widget.js` | Zero-dependency Shadow DOM portal embed script | Self-executing scanner, `MutationObserver`, Shadow DOM pill (`"Simplify (EN/हिं/म)"`), modal `<iframe src=".../view?url=...">` | Vanilla JS `< 15 KB`; must isolate all styles inside `attachShadow({ mode: "open" })` and avoid polluting host page globals or CSS. |
| `frontend/src/lib/api.ts` | Typed REST client and demo payload helpers | `simplifyFile()`, `simplifyUrl()`, `getNotice()`, `askNoticeQA()`, `getAudioUrl()`, `getIcsUrl()`, `ApiError`, demo fixture builders | Centralizes `NEXT_PUBLIC_API_BASE_URL` calls and structured `422 PII_BLOCKED` error parsing; components never hardcode fetch URLs. |
| `frontend/src/app/layout.tsx` | Next.js App Router root layout | `RootLayout`, metadata, `#F8FAFC` / `#0F172A` base typography | Sets mobile-first viewport and clean accessibility landmarks; contains zero authentication providers. |
| `frontend/src/app/page.tsx` | Web Student Hub (`/`) | Drag-and-drop uploader, URL bar, `PipelineStepper`, Privacy Block Screen, `"Try Sample Exam Circular"`, `"Test PII Protection (Mock Merit List)"` | Enforces client-side `<= 10 MB` check before upload; routes completed notices to `/notice/[hash]`. |
| `frontend/src/app/notice/[hash]/page.tsx` | Canonical Action Card route (`/notice/[hash]`) | Fetches `getNotice(hash)`, renders `ActionCard` or expired/not-found state | Handles 14-day TTL expiry cleanly with a direct CTA back to `/`. |
| `frontend/src/app/view/page.tsx` | Standalone CSP-safe notice viewer (`/view?url=...`) | Reads `?url=` query param, calls `simplifyUrl()`, renders `PipelineStepper`, Privacy Block Screen, or `ActionCard` | Works standalone in full tabs and inside `widget.js` iframes without requiring `widget.js` execution. |
| `frontend/src/app/widget-demo/page.tsx` | Live college portal embed showcase (`/widget-demo`) | Mock college noticeboard table with `.pdf` links and `<script src="/widget.js" defer>` | Intentionally uses legacy table styles to prove Shadow DOM isolation of `"Simplify (EN/हिं/म)"` pills. |
| `frontend/src/components/ActionCard.tsx` | Structured multilingual Action Card view | Governance banner, Ref No./Issue Date, verification pill, cache badge, `EN \| हिंदी \| मराठी` switcher, `AudioPlayer`, checklist, deadlines/fees + `.ics`, documents, verbatim quotes, `NoticeQA`, `QrPosterModal` trigger | Preserves verbatim quotes untranslated with page numbers; switches UI copy in browser memory without re-querying Gemini. |
| `frontend/src/components/AudioPlayer.tsx` | Inline regional voice brief player | Play/pause, progress scrub, duration readout, retry state | Binds `<audio>` to `getAudioUrl(hash, lang)`; stops and resets cleanly when user switches language. |
| `frontend/src/components/NoticeQA.tsx` | Collapsible circular-grounded Q&A drawer | Question input (`<= 300` chars), quick chips, citation badges, office-check fallback | Calls `askNoticeQA()`; enforces `300`-char limit and displays grounded page numbers. |
| `frontend/src/components/QrPosterModal.tsx` | A4 printable noticeboard QR poster modal | `QRCodeSVG` (`qrcode.react`), printable A4 layout (`@media print`), `"Print Poster"`, `"Copy Link"` | Encodes canonical `{NEXT_PUBLIC_APP_URL}/notice/{hash}` URL and mandatory official disclaimer. |
| `frontend/src/components/PipelineStepper.tsx` | Live pipeline stage indicator | 5-step status indicator (`Validating & Screening PII` → `Checking Instant Cache` → `Reading Circular Text` → `Generating Multilingual Action Card` → `Verifying Dates & Fees`) | Pure presentational state component driven by upload/URL workflow status. |

---

## 3. Cross-File Data Flow & Module Coupling Map

### 3.1 Acyclic Layering & Processing Pipeline
NoticeSetu follows a strict downward dependency hierarchy so no circular imports occur:

```text
Transport Layer:
  routes/notices.py ──────┐
  bot/handlers.py ────────┼──▶ Shared Orchestrator: services/simplifier.py (process_notice_bytes)
                          │
Service Layer (DAG):      ▼
  [1] services/security.py    (safe_fetch_url, validate_file_bytes -> io.BytesIO)
       │
       ▼
  [2] services/cache.py       (Tier-1 SHA-256 lookup; 14-day TTL)
       │  (on miss)
       ▼
  [3] services/extractor.py   (PyMuPDF digital vs. 150 DPI scan + Pillow pHash)
       │
       ▼
  [2b] services/cache.py      (Tier-2 normalized_text_sha256 / pHash <= 4 lookup)
       │  (on miss)
       ▼
  [4] services/pii_guard.py   (Pre-LLM deterministic block -> HTTP 422 PII_BLOCKED)
       │
       ▼
  [5] services/simplifier.py  (Gemini 2.5 Flash, thinking_budget=0, Semaphore(5))
       │
       ▼
  [6] services/verifier.py    (Devanagari/date/fee PyMuPDF match; scan_extracted PII check)
       │
       ▼
  [7] services/cache.py       (Persist ActionCardResponse JSON for 14 days)

On-Demand Output Services (called by routes/notices.py and bot/handlers.py):
  services/tts.py             (Sarvam/Bhashini/none -> Supabase Storage or memory fallback)
  services/calendar_ics.py    (Deterministic RFC-5545 .ics export in Asia/Kolkata)

Foundation Layer (imported by all layers, imports nothing internal):
  config.py, schemas.py
```

### 3.2 Shared Service Rule Between Web Routes and Telegram Bot
`backend/app/routes/notices.py` and `backend/app/bot/handlers.py` are strictly peer transport adapters. Neither module may import from the other, and neither may embed extraction, PII screening, caching, or Gemini logic:
- **Single source of truth for ingestion:** Both Web (`POST /api/simplify`) and Telegram (`on_document_or_photo`) pass raw in-memory `bytes` into `services.simplifier.process_notice_bytes()`. Security limits (`10 MB`, magic bytes), two-tier caching, pre-LLM PII blocking, Gemini extraction, and `PyMuPDF` verification execute identically across Web, Widget `/view`, and Telegram.
- **Single source of truth for outputs:** Both `GET /api/audio/{hash}/{lang}` and Telegram's `"Play Voice Note"` callback call `services.tts.get_or_create_audio()`, sharing the same Supabase/memory MP3 cache.
- **Zero-duplication benefit:** Any update to Protected Campus Glossary rules, PII detection patterns, or verification logic takes effect simultaneously across all distribution channels with zero logic drift.

---

## 4. Scaffolding Script (`scripts/scaffold.sh`) & Verification Checklist

### 4.1 Using `scripts/scaffold.sh`
Run from the repository root (`NoticeSetu/`) to create all directories and non-destructive starter files:

```bash
bash scripts/scaffold.sh
```

Script guarantees:
- **Idempotent execution:** Existing files (including `docs/PRD.md`, `docs/REQUIREMENTS.md`, `docs/FILE_STRUCTURE.md`, and completed modules) are skipped safely via `ensure_file()`.
- **Built-in validation:** Runs the 6-point check below automatically and exits with status `1` if any required artifact is missing or `widget.js` exceeds `15 KB`.

### 4.2 Six-Point Pre-Phase-1 Verification Checklist
Before starting Phase 1 implementation, confirm all six checks pass:

1. **Documentation & Script Presence:** `docs/PRD.md`, `docs/REQUIREMENTS.md`, `docs/FILE_STRUCTURE.md`, and `scripts/scaffold.sh` exist.
2. **Root Infrastructure Files:** `docker-compose.yml` and `README.md` exist at the repository root.
3. **Backend Core & Services:** `backend/requirements.txt`, `backend/Dockerfile`, `backend/.env.example`, `backend/app/{main,config,schemas}.py`, and all eight files in `backend/app/services/` (`security.py`, `cache.py`, `extractor.py`, `pii_guard.py`, `simplifier.py`, `verifier.py`, `tts.py`, `calendar_ics.py`) exist.
4. **Backend Routes, Bot & Tests:** `backend/app/routes/notices.py`, `backend/app/bot/{handlers,run_polling}.py`, and `backend/tests/test_core.py` exist.
5. **Frontend Routes & Components:** `frontend/package.json`, `frontend/.env.example`, `frontend/src/lib/api.ts`, all five App Router pages (`layout.tsx`, `page.tsx`, `notice/[hash]/page.tsx`, `view/page.tsx`, `widget-demo/page.tsx`), and all five UI components (`ActionCard.tsx`, `AudioPlayer.tsx`, `NoticeQA.tsx`, `QrPosterModal.tsx`, `PipelineStepper.tsx`) exist.
6. **Embed Widget Budget:** `frontend/public/widget.js` exists and measures `< 15,360` bytes (`< 15 KB`).

