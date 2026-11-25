# NoticeSetu

**Zero-login multilingual campus notice intelligence for Indian colleges and universities.**

NoticeSetu turns official college and university circulars (English, Hindi, or Marathi PDFs, noticeboard photos, or public portal URLs) into structured, source-checked **Action Cards** in **English, Hindi, and Marathi**, paired with cached regional voice briefs, deterministic `.ics` calendar export, grounded Q&A, Telegram Bot delivery, and a 1-line Shadow DOM website embed widget (`widget.js` + `/view?url=...` CSP fallback).

> **Permanent Governance Stance:** Every Action Card carries the non-dismissible banner **"Unofficial Assistive Summary — Confirm on the official circular."** NoticeSetu requires zero student logins, processes all uploaded files and downloaded URLs strictly in `io.BytesIO`, and never writes raw user uploads to disk or stores user-to-document logs.

---

## Deterministic Guarantees vs. AI-Assisted Outputs

NoticeSetu makes no claim of 100% accuracy or freedom from extraction errors. Deterministic engineering gates wrap probabilistic AI extraction:

| Layer | Behavior Type | Exact Guarantee / Boundary |
| :--- | :--- | :--- |
| URL & File Validation (`security.py`) | Deterministic | Blocks non-`http`/`https`, ports outside `{80, 443}`, private/loopback/link-local/metadata IPs (`127.0.0.1`, `::1`, `10.x`, `172.16-31.x`, `192.168.x`, `169.254.169.254`), `> 3` redirects, non-`PDF/JPEG/PNG` magic bytes (`400`), and `> 10 MB` payloads (`413`). |
| Pre-LLM PII Guard (`pii_guard.py`) | Deterministic | Blocks merit lists, defaulter lists, hall tickets, admit cards, fee receipts, dense roll/PRN/seat-number tables, and multiple personal IDs with `HTTP 422 PII_BLOCKED` before external AI calls. |
| Two-Tier Cache (`cache.py`) | Deterministic | 14-day TTL (`1,209,600s`) across Tier-1 `SHA-256`, Tier-2 normalized text, and Tier-2 `pHash` (`<= 4` Hamming distance), with automatic in-memory fallback. |
| Digital Cross-Check (`verifier.py`) | Deterministic | Normalizes Devanagari digits (`०–९` → `0–9`) and dates (`dateparser`) against `PyMuPDF` text (`source_matched` vs. `verify_original`); scans/photos always render `scan_extracted` (*Scan-Extracted — Verify Original*). |
| Calendar Export (`calendar_ics.py`) | Deterministic | Builds RFC-5545 `.ics` files in `Asia/Kolkata` timezone directly from parsed circular deadlines. |
| Action Card Extraction & Q&A (`simplifier.py`) | AI-Assisted | Uses `google-genai` (`gemini-2.5-flash`) with Protected Campus Glossary rules, `<= 380`-char voice briefs, and circular-only Q&A refusal when facts are absent. |

*Campus outcome metrics (reading-time reduction, repeat weekly usage, real-world cache hit ratio, and user-reported extraction error rate) are **To be validated in campus pilot**.*

---

## System Architecture & Tech Stack

### End-to-End Request Flow

```text
Entry Surfaces:
  Web Hub (/) • Action Card (/notice/[hash]) • CSP Viewer (/view?url=...)
  Portal Widget (/widget-demo, public/widget.js) • Telegram Bot (aiogram v3)
        │
        ▼
  [1] Hardened FastAPI Gate (security.py)
      • SSRF DNS/IP check, <= 3 redirect hops, 10 MB io.BytesIO cap, magic bytes
        │
        ▼
  [2] Two-Tier Cache Lookup (cache.py — Upstash Redis 14-day TTL / memory fallback)
      • Tier-1: notice:sha256:{hash}
        │ (on miss)
        ▼
  [3] Dual-Path Extractor (extractor.py)
      • Digital PDF (>= 80 non-whitespace chars via PyMuPDF, <= 10 pages)
      • Scanned PDF (<= 3 pages rendered at 150 DPI PNG) or Photo (Pillow <= 2000px + pHash)
      • Tier-2 check: notice:text:{hash} or notice:phash:{hex} (Hamming <= 4)
        │ (on miss)
        ▼
  [4] Pre-LLM PII Scrubber (pii_guard.py)
      • Blocks personal records (HTTP 422 PII_BLOCKED); masks stray IDs/PANs
        │
        ▼
  [5] Gemini 2.5 Flash Simplifier (simplifier.py — google-genai)
      • ThinkingConfig(thinking_budget=0), flat schema, asyncio.Semaphore(5)
      • Protected Campus Glossary: ATKT, KT, Hall Ticket, Bonafide, GR,
        Revaluation, PRN, Provisional Admission, Semester
        │
        ▼
  [6] Deterministic Verifier (verifier.py)
      • Devanagari ०-९ -> 0-9, currency/dateParser match, page.search_for()
      • Scans/photos re-screened via pii_guard before caching
        │
        ▼
  [7] Outputs & On-Demand Services
      • Cached Regional TTS (tts.py): Sarvam AI (bulbul:v3 / bulbul:v4-flash)
        + Bhashini / none fallback -> Supabase Storage (notice-audio/{hash}/{lang}.mp3) or memory
      • Calendar Export (calendar_ics.py): RFC-5545 .ics
      • Grounded Q&A (POST /api/qa): Circular-only answers + office-check fallback
```

### Technology Stack
- **Backend (`backend/`):** Python `3.11+`, FastAPI, Uvicorn, Pydantic v2, `pydantic-settings`, `httpx`, `PyMuPDF`, `dateparser`, `Pillow`, `imagehash`, `google-genai` (`gemini-2.5-flash`), `upstash-redis`, `supabase`, `aiogram` v3, `pytest`.
- **Frontend (`frontend/`):** Next.js (App Router, TypeScript), Tailwind CSS, `lucide-react`, `qrcode.react`.
- **Embed Widget (`frontend/public/widget.js`):** Vanilla JavaScript (`~7.6 KB`, `< 15 KB` limit, zero dependencies, Shadow DOM isolated).

---

## Step-by-Step Setup, Local Run & Deployment Guide

### 1. Local Backend Setup (`backend/`)

NoticeSetu runs locally with **only `GEMINI_API_KEY`** configured. When `UPSTASH_REDIS_REST_*` or `SUPABASE_*` are omitted, the backend automatically uses in-memory 14-day TTL caching and in-memory audio storage.

```bash
cd backend
python -m venv .venv

# macOS / Linux:
source .venv/bin/activate
# Windows PowerShell:
# .\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env
# Edit backend/.env and set GEMINI_API_KEY=your_key_here
```

Run the automated test suite:
```bash
pytest tests/test_core.py -v
```

Start the FastAPI server:
```bash
uvicorn app.main:app --reload --port 8000
```

Verify readiness:
```bash
curl http://localhost:8000/health
```

**Telegram Bot (Optional Local Testing):**
Set `TELEGRAM_BOT_TOKEN` in `backend/.env` and run long polling without HTTPS or ngrok:
```bash
cd backend
python -m app.bot.run_polling
```

For production webhook deployments, set both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET`, then point Telegram's `setWebhook` to `https://<backend-domain>/telegram/webhook` with matching `secret_token`.

### 2. Local Frontend Setup (`frontend/`)

```bash
cd frontend
npm ci
cp .env.example .env.local
# Default NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

npm run build
npm run dev
```

Open `http://localhost:3000`:
- **Student Hub (`/`):** Drag and drop a PDF/JPEG/PNG (`<= 10 MB`), paste a public notice URL, or click `"Try Sample Exam Circular"` / `"Test PII Protection (Mock Merit List)"`.
- **Action Card (`/notice/[hash]`):** Switch `English | हिंदी | मराठी`, play cached voice briefs, export `.ics` deadlines, ask grounded Q&A, or print an A4 noticeboard QR poster.
- **College Widget Demo (`/widget-demo`):** Demonstrates `public/widget.js` injecting Teal `"Simplify (EN/हिं/म)"` Shadow DOM pills next to `.pdf` links.
- **CSP Fallback (`/view?url=...`):** Standalone URL simplifier for strict-CSP college websites.

### 3. Docker Compose Startup

From the repository root:
```bash
cp backend/.env.example backend/.env
# Add GEMINI_API_KEY (and optional Sarvam/Upstash/Supabase/Telegram keys) in backend/.env
docker compose up --build
```

Services start on `http://localhost:8000` (backend) and `http://localhost:3000` (frontend) with zero host upload volumes.

### 4. Cloud Deployment Guide (Render/VPS + Vercel + Upstash + Supabase)

1. **Upstash Redis:** Provision a Redis database and copy `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` into backend environment variables.
2. **Supabase Storage:** Create a bucket named `notice-audio` (`SUPABASE_AUDIO_BUCKET=notice-audio`) and set `SUPABASE_URL` and `SUPABASE_KEY`.
3. **Backend (Render / Railway / VPS):** Deploy `backend/Dockerfile` on port `8000` with:
   - `GEMINI_API_KEY`, `TTS_PROVIDER=sarvam`, `SARVAM_API_KEY`
   - `SARVAM_TTS_MODEL=bulbul:v3`, `SARVAM_TTS_SPEAKER=shubh` (or `bulbul:v4-flash` paired with a compatible v4 persona ID)
   - `ALLOWED_ORIGINS=https://<your-frontend-domain>`
   - `FRONTEND_BASE_URL=https://<your-frontend-domain>`
   - `TELEGRAM_BOT_TOKEN` and `TELEGRAM_WEBHOOK_SECRET` (if webhook mode is active)
4. **Frontend (Vercel / Cloudflare Pages):** Deploy `frontend/` with:
   - `NEXT_PUBLIC_API_BASE_URL=https://<your-backend-domain>`
   - `NEXT_PUBLIC_APP_URL=https://<your-frontend-domain>`
5. **1-Line College Website Embed:** Add to any public noticeboard page:
   ```html
   <script src="https://<your-frontend-domain>/widget.js" defer></script>
   ```

### 5. Pre-Demo Warmup & Backup Video Checklist
- Hit `GET https://<your-backend-domain>/health` 2 minutes before presenting to wake free-tier instances and confirm `"status": "ok"`.
- Run `"Try Sample Exam Circular"` once beforehand if demonstrating Tier-1 `SHA-256` cache hits live.
- Run `"Test PII Protection (Mock Merit List)"` to verify `HTTP 422 PII_BLOCKED` renders cleanly.
- Record a 60-second local backup screen capture covering Web Hub, Action Card EN/HI/MR toggle, `.ics` export, Telegram Bot, and `/widget-demo`.

---

## Case Studies & Real-World Campus Scenarios

### Case Study 1: Bilingual Exam & Fee Circular (Digital PDF)
- **Scenario:** A university publishes a multi-paragraph Semester IV Regular & ATKT Exam Form PDF mixing English headings with Marathi/Hindi fee clauses and terms like `ATKT`, `Hall Ticket`, `Bonafide`, and `Revaluation`.
- **Flow:** `extractor.py` detects `>= 80` non-whitespace characters via `PyMuPDF` (`digital_pdf`). `simplifier.py` extracts structured deadlines (`15/03/2026`, `22/03/2026`), fees (`Rs. 1,500/-`, `Rs. 850/-`), eligibility tags, and required documents across `en`, `hi`, and `mr` while keeping `ATKT`, `Hall Ticket`, and `Bonafide` natural rather than stiffly translated. `verifier.py` checks extracted figures against raw `PyMuPDF` text (including Devanagari digits `०–९`), marks `Source-Matched (Digital PDF)`, locates quote page numbers, and enables one-click `.ics` calendar download.

### Case Study 2: Crooked Noticeboard Photo & Corrigendum / Cache Reuse
- **Scenario:** A student photographs a pinned paper notice on campus and forwards it to the NoticeSetu Telegram Bot. Another student later forwards a slightly recompressed copy of the same notice, while the college office issues a separate corrigendum PDF the following week.
- **Flow:** `extractor.py` corrects EXIF rotation, resizes the image (`<= 2000px`), and computes a perceptual hash (`pHash`). Because the source is an image, `verifier.py` always assigns **Scan-Extracted — Verify Original** and runs `pii_guard` on transcribed text before caching. The second student's recompressed image matches within Hamming distance `<= 4` (`tier2_phash`) inside the 14-day TTL window. The new corrigendum PDF has distinct bytes and normalized text, so it misses cache and generates a fresh Action Card while expired notices drop automatically after 14 days.

### Case Study 3: Accidental Merit List / Student ID Upload (PII Guardrail)
- **Scenario:** A student or clerk accidentally uploads a Provisional Merit List PDF containing roll numbers, PRNs, full names, and percentage scores (or a hall ticket / fee receipt).
- **Flow:** Before any text leaves the server for Gemini, `pii_guard.py` detects the `"merit list"` keyword and dense roll/PRN rows (`>= 5` student rows), raises `PIIBlockedError`, and returns `HTTP 422 PII_BLOCKED`. Zero external AI calls are made, the `io.BytesIO` buffer is discarded immediately, and no user-to-document record is logged, protecting minors and students under India's DPDP Rules 2025.

### Case Study 4: Strict-CSP College Portal Link
- **Scenario:** A college website wants to simplify PDF circulars on its existing notice table without touching legacy CMS templates, while a sister institute enforces a strict Content Security Policy that blocks third-party scripts and iframes.
- **Flow:** On compatible portals, pasting `<script src="https://<domain>/widget.js" defer></script>` injects a Shadow DOM-isolated Teal `"Simplify (EN/हिं/म)"` pill next to every `.pdf` link and opens an overlay pointing to `/view?url={encoded_pdf_url}`. On strict-CSP portals, webmasters or students link directly to `/view?url={encoded_pdf_url}`, which fetches the PDF through `safe_fetch_url` (enforcing SSRF IP blocking, `<= 3` redirect checks, and the `10 MB` cap) and renders the full Action Card standalone.

---

## Troubleshooting & FAQ

- **Can I run NoticeSetu without Upstash Redis, Supabase, or Sarvam keys?**  
  Yes. Only `GEMINI_API_KEY` is required for circular extraction and Q&A. Missing Redis/Supabase keys activate in-memory 14-day TTL and MP3 fallbacks; missing `SARVAM_API_KEY` or `TTS_PROVIDER=none` returns `HTTP 503` on audio requests while keeping all text, `.ics`, Q&A, and QR features operational.
- **Why did a public URL fail with HTTP 400 (`SSRF_BLOCKED`)?**  
  `security.py` blocks `http://127.0.0.1`, `localhost`, `::1`, private LAN ranges (`10.x`, `172.16-31.x`, `192.168.x`), cloud metadata IPs (`169.254.169.254`), non-`80/443` ports, and `> 3` redirects. Test URL ingestion with publicly routable `http://` or `https://` notice URLs.
- **Why did an upload return HTTP 413 or HTTP 422 (`PII_BLOCKED`)?**  
  `HTTP 413` means the PDF/image exceeded the `10 MB` memory cap. `HTTP 422 PII_BLOCKED` means `pii_guard.py` detected a merit list, defaulter list, hall ticket, admit card, fee receipt, or dense student roll/ID table and blocked the file before AI processing.
- **Sarvam TTS returns HTTP 400 on speaker mismatch:**  
  Ensure `SARVAM_TTS_MODEL` matches `SARVAM_TTS_SPEAKER`: use `bulbul:v3` with classic speakers like `shubh`/`priya`, or `bulbul:v4-flash` with a matching v4 persona ID.
- **Telegram webhook returns HTTP 403:**  
  `POST /telegram/webhook` requires `TELEGRAM_WEBHOOK_SECRET` to be set and matched by the `X-Telegram-Bot-Api-Secret-Token` header. For local testing without HTTPS, run `python -m app.bot.run_polling` instead.
- **Free-tier backend takes 30+ seconds on first request:**  
  Cloud free tiers spin down idle containers. Call `GET /health` before demos to warm up Uvicorn without invoking Gemini.
