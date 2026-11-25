# NoticeSetu — Product Requirements Document (PRD)

**Document Status:** Build Specification  
**Product Name:** NoticeSetu  
**Compliance Target:** Digital Personal Data Protection (DPDP) Rules 2025 (India)  

---

## 1. Executive Summary & Product Vision

### 1.1 Problem Statement
College and university students across India miss deadlines, pay avoidable late fees, or arrive at administrative counters without required paperwork because official circulars are difficult to parse and act on:
- **Bureaucratic phrasing:** Notices rely on dense administrative templates, cross-referenced Government Resolutions (GRs), and buried fee or eligibility conditions.
- **Unstructured source formats:** Institutions publish notices as digital PDFs, scanned images, crooked photographs of physical noticeboards, or links on legacy college portals.
- **Language barriers:** Circulars frequently appear only in English, only in regional languages (Hindi or Marathi), or in mixed bilingual text, leaving students unable to verify exact action steps in their preferred language.

### 1.2 Product Vision
**NoticeSetu** is a zero-login, source-agnostic notice intelligence platform that converts official college and university circulars (English, Hindi, or Marathi PDFs, noticeboard photos, or public portal URLs) into structured, source-checked **Action Cards** in **English, Hindi, and Marathi**. Each Action Card includes cached regional voice briefs, deterministic `.ics` calendar export, verbatim source quotes with page numbers, grounded Q&A, Telegram Bot delivery, and a 1-line college website embed widget.

### 1.3 Core Differentiation
1. **Zero-upload distribution:** Students reach simplified notices where notices already live, via Telegram forwarding, a 1-line college portal widget, or a scannable noticeboard QR poster.
2. **Action-first structured cards:** Outputs extract eligibility, deadlines, fees, required documents, and step-by-step checklists instead of literal translated paragraphs.
3. **Protected Campus Glossary:** Preserves standard Indian campus terms (`ATKT`, `KT`, `Hall Ticket`, `Bonafide`, `GR`, `Revaluation`, `PRN`, `Provisional Admission`, `Semester`) in natural bilingual or transliterated form rather than stiff literal translations.
4. **Independent digital-PDF cross-checking:** Extracted deadlines and fee figures are checked deterministically against raw `PyMuPDF` text and surfaced through honest verification badges rather than blind confidence scores.
5. **Pre-LLM PII protection:** Personal student records and dense roll-number tables are blocked in memory before any document content reaches an LLM.

### 1.4 Deterministic vs. AI-Assisted System Boundaries
NoticeSetu separates deterministic software guarantees from probabilistic AI-assisted extraction. AI outputs are assistive summaries and carry no guarantee of infallibility or complete freedom from extraction errors; every Action Card directs students to confirm details on the official circular.

| Capability | Classification | Exact System Behavior |
| :--- | :--- | :--- |
| File validation & memory isolation | Deterministic | Validates MIME type/magic bytes (`PDF`, `JPEG`, `PNG`), enforces `<= 10 MB` limit, and reads strictly into `BytesIO` without disk writes. |
| Content hashing & caching | Deterministic | Computes `SHA-256` of normalized input bytes to power `/notice/[hash]` routing and 14-day TTL cache lookups. |
| Pre-LLM PII screening | Deterministic | Runs regex, keyword, and structural table-density rules before LLM calls; blocks personal records with HTTP `422` and a privacy explanation. |
| Digital vs. scan detection | Deterministic | Inspects `PyMuPDF` selectable text density per page to distinguish digital PDFs from scanned PDFs and camera photos. |
| Digital-PDF cross-checking | Deterministic | Normalizes dates and fee strings to check whether every extracted date and fee appears in raw `PyMuPDF` text (`source_matched` vs. `verify_original`). |
| Calendar file generation (`.ics`) | Deterministic | Generates RFC 5545 `.ics` files in `Asia/Kolkata` timezone directly from structured deadline fields. |
| Voice brief length enforcement | Deterministic | Caps spoken brief scripts at `<= 380` characters per language (`en`, `hi`, `mr`) prior to TTS synthesis and audio caching. |
| Structured Action Card extraction | AI-Assisted | Extracts TL;DR, eligibility tags, checklist steps, deadlines, fees, documents, and verbatim quotes across `en`, `hi`, and `mr`. |
| OCR / vision reading on scans | AI-Assisted | Reads skewed photos and scanned PDFs; always labeled `scan_extracted` (*Scan-Extracted — Verify Original*). |
| Grounded Q&A synthesis | AI-Assisted | Answers user questions strictly from extracted circular context and returns a fixed office-check fallback when facts are absent. |

---

## 2. Target Users & Explicit Non-Goals

### 2.1 Primary User: Student
- **Profile:** Junior college, undergraduate, postgraduate, or first-year students (including under-18 minors).
- **Need:** Fast, reliable answers on eligibility, fee amounts, required documents, and submission deadlines in English, Hindi, or Marathi.
- **Constraint:** Must work on low-to-mid-range mobile devices over campus cellular connections with **zero account creation, zero phone-number capture, and zero login**.

### 2.2 Secondary User: College Staff / Admin
- **Profile:** Department clerk, exam cell coordinator, or portal webmaster.
- **Need:** Print a scannable QR poster for a physical noticeboard or paste a single `<script>` tag onto a public college notice page without modifying backend portal code.
- **Constraint:** Zero admin dashboard onboarding, zero authentication setup, and zero interference with existing portal stylesheets.

### 2.3 Explicit Non-Goals (Out of Scope)
1. **No student accounts or history:** No sign-up, passwords, OAuth, saved profiles, or personal document history.
2. **No personal student records:** NoticeSetu refuses merit lists, defaulter lists, hall tickets, admit cards, and fee receipts.
3. **No legal replacement of official circulars:** Action Cards are assistive reading aids; official college circulars remain the sole authoritative source.
4. **No WhatsApp Bot in this build:** Excluded to avoid Meta's 2026 general AI bot restrictions, sandbox limits, and per-message billing.

---

## 3. Core User Journeys & Feature Specifications

### 3.1 Journey A — Web Student Hub (`/` → `/notice/[hash]`)

#### Feature A1: Notice Ingestion Hub (`/`)
- **User Story:** As a student, I want to upload a PDF/photo or paste a public notice link without logging in so that I can turn any college circular into a clear Action Card in my language.
- **UI/UX Behavior:**
  - Single-column, mobile-first hero on `/` with a drag-and-drop dropzone (accepting `.pdf`, `.jpg`, `.jpeg`, `.png` up to `10 MB`) and an inline URL input field with a `"Simplify Notice"` primary Teal (`#0D9488`) button.
  - Below the primary input sit the two Live Demo Shortcut buttons (Journey B) and brief trust indicators (zero login, in-memory processing, English/Hindi/Marathi output).
  - Submitting triggers an inline `PipelineStepper` showing live deterministic and AI stages:
    1. `Validating & Screening PII` (file signature check, `<= 10 MB` check, SHA-256 hash, pre-LLM PII scan)
    2. `Checking Instant Cache` (Tier-1 SHA-256 lookup; skips remaining extraction steps on hit)
    3. `Reading Circular Text` (`PyMuPDF` digital text extraction or Vision/OCR path)
    4. `Generating Multilingual Action Card` (structured EN/HI/MR extraction + Protected Campus Glossary)
    5. `Verifying Dates & Fees` (deterministic cross-check against `PyMuPDF` raw text)
  - On completion, the browser redirects directly to `/notice/[hash]`.
- **Edge Cases:**
  - **Unsupported file type or spoofed extension:** Validate actual file magic bytes (`%PDF`, JPEG `FF D8 FF`, PNG `89 50 4E 47`), not filename extension alone; show inline error *"Unsupported file. Upload a PDF, JPEG, or PNG under 10 MB."*
  - **Oversized file (`> 10 MB`):** Reject client-side and server-side (`HTTP 413`) before buffering full upload where possible.
  - **Password-protected or corrupted PDF:** Return `HTTP 422` with message *"This PDF is password-protected or unreadable. Upload an unlocked PDF or clear photo."*
  - **Empty or unreadable image/blank PDF:** Prompt user to retake photo in brighter light or upload the original digital PDF.
  - **SSRF or unreachable URL:** Reject non-`http`/`https` schemes, `localhost`, private/loopback/link-local IP ranges (`10.0.0.0/8`, `127.0.0.0/8`, `169.254.0.0/16`, `172.16.0.0/12`, `192.168.0.0/16`, `::1`), cap redirects (`<= 3`), enforce `15s` fetch timeout, verify fetched `Content-Type` and `<= 10 MB` size, and surface clear upstream fetch errors (`403`/`404`/timeout).
  - **Concurrent identical uploads:** Deduplicate or safely overwrite by `notice_hash` without corrupting cache state.
- **Acceptance Criteria:**
  - **Given** a valid public college circular PDF (`<= 10 MB`) is dropped onto `/`, **When** the student submits it, **Then** `PipelineStepper` updates stage-by-stage and redirects to `/notice/[hash]` displaying the structured Action Card.
  - **Given** the exact same circular bytes are submitted again within the 14-day TTL, **When** `Checking Instant Cache` runs, **Then** the system skips LLM extraction and redirects to `/notice/[hash]` with the `Instant Cache Hit (Tier-1 SHA-256)` badge.
  - **Given** a student pastes `http://127.0.0.1/secret.pdf` or a non-PDF/non-image URL, **When** they click `"Simplify Notice"`, **Then** the request is blocked pre-fetch with a clear validation message.

#### Feature A2: Action Card View (`/notice/[hash]`)
- **User Story:** As a student, I want to read eligibility, deadlines, fees, required documents, and original quotes in English, Hindi, or Marathi so that I know what action to take without misreading bureaucratic text.
- **UI/UX Behavior:**
  - Top sticky/prominent governance stack: permanent disclaimer banner, pinned Circular Ref No. and Issue Date with corrigendum reminder, Honest Verification Pill, and Cache Indicator Badge.
  - Segmented language toggle (`English | हिंदी | मराठी`) that switches all Action Card text (`TL;DR`, eligibility tags, checklist, deadlines/fees labels, documents, and voice player target language) instantaneously in place without re-running extraction.
  - Verbatim Source Quotes remain in the circular's original script/language alongside page numbers (`Page 1`, `Page 2`) so students can verify exact wording regardless of selected output language.
  - If `hash` is not found or expired (`> 14` days), show an empty/expired notice state with a CTA back to `/` to re-upload the circular.
- **Edge Cases:**
  - **Missing Circular Ref No. or Issue Date:** Display `"Not stated in circular"` explicitly instead of fabricating metadata.
  - **Zero fees or zero documents mentioned:** Render `"No fee mentioned in circular"` or `"No documents listed in circular"` rather than hiding section context silently.
  - **Mixed bilingual circular:** Preserve verbatim quotes in original script/text; extract clean localized summaries into all three output languages (`en`, `hi`, `mr`).
- **Acceptance Criteria:**
  - **Given** an extracted notice at `/notice/[hash]`, **When** the student toggles between `English`, `हिंदी`, and `मराठी`, **Then** all card sections switch immediately to the selected language while preserving Protected Campus Glossary terms and keeping verbatim source quotes intact with page numbers.
  - **Given** a notice hash older than 14 days or nonexistent, **When** `/notice/[hash]` is opened, **Then** the page displays a clear expired/not-found message and a button linking to `/`.

#### Feature A3: Cached Regional Voice Brief (`AudioPlayer`)
- **User Story:** As a student who prefers listening or has low reading fluency in dense text, I want to play a concise voice brief in English, Hindi, or Marathi directly inside the Action Card.
- **UI/UX Behavior:**
  - Compact inline `AudioPlayer` bar directly beneath the language toggle and TL;DR.
  - Shows active language label, Play/Pause button, progress scrub bar, elapsed/total duration, and loading spinner during first-time synthesis.
  - Audio is synthesized on demand per `(notice_hash, lang)` from the pre-extracted `<= 380`-character spoken brief and cached for the remaining 14-day TTL. Subsequent plays load immediately from cache.
- **Edge Cases:**
  - **LLM spoken brief exceeds 380 characters:** Deterministic post-processor trims cleanly at the last complete sentence or word boundary `<= 380` characters before TTS synthesis.
  - **TTS provider timeout or temporary error:** Show inline retry message (*"Voice brief unavailable right now — tap to retry"*) without blocking the text Action Card.
  - **User switches language mid-playback:** Pause current audio stream cleanly, reset progress to `0:00`, and bind player to the newly selected language brief.
- **Acceptance Criteria:**
  - **Given** a student is viewing `/notice/[hash]` in `हिंदी`, **When** they tap Play on `AudioPlayer`, **Then** the Hindi spoken brief (`<= 380` characters) plays inline and is cached for subsequent `(notice_hash, hi)` requests.
  - **Given** the user switches the card to `मराठी` while Hindi audio is playing, **When** the toggle updates, **Then** Hindi playback stops and `AudioPlayer` switches to the Marathi brief.

#### Feature A4: One-Click `.ics` Calendar Export
- **User Story:** As a student, I want to add circular deadlines to my phone calendar in one tap so that I do not forget exam form or fee cutoffs.
- **UI/UX Behavior:**
  - Deadlines & Fees table displays each extracted deadline with date, time (if stated), description, and fee amount.
  - Primary `"Add to Calendar (.ics)"` button triggers a deterministic download of `noticesetu-{short_hash}.ics` containing VEVENT entries for all actionable dates in the circular (plus optional per-row `.ics` trigger if multiple deadlines exist).
  - Each VEVENT uses `TZID=Asia/Kolkata` (all-day `VALUE=DATE` when no clock time is stated; timed event when exact time is stated), deterministic `UID` (`{notice_hash}-{index}@noticesetu`), `SUMMARY`, and `DESCRIPTION` containing Circular Ref No. and the mandatory disclaimer *"Unofficial Assistive Summary — Confirm on the official circular."*
- **Edge Cases:**
  - **No actionable deadlines extracted:** Hide or disable the `.ics` export button and display *"No calendar deadlines found in this circular."*
  - **Ambiguous or partial date (e.g., "last week of March" without calendar date):** Do not invent a calendar date; list the text in the Deadlines table with a `"Verify Original"` note and exclude unparseable non-dates from `.ics` generation.
- **Acceptance Criteria:**
  - **Given** an Action Card with one or more parsed calendar deadlines, **When** the student clicks `"Add to Calendar (.ics)"`, **Then** the browser downloads a valid RFC 5545 `.ics` file in `Asia/Kolkata` timezone containing each deadline and the assistive disclaimer.
  - **Given** a circular with zero calendar dates, **When** the Action Card renders, **Then** no broken `.ics` download is offered.

#### Feature A5: Collapsible Grounded Q&A Drawer
- **User Story:** As a student with a specific question (such as whether late fees apply to ATKT candidates), I want to ask a question and get an answer grounded strictly in the circular without guessing.
- **UI/UX Behavior:**
  - Collapsible drawer/panel at the bottom of the Action Card labeled `"Ask About This Circular"` with a text input (`<= 300` characters), suggested quick chips (e.g., *"Is there a late fee?"*, *"Who is eligible?"*), and `"Ask"` button.
  - Displays answer in the currently active language (`en` / `hi` / `mr`), citing supporting page number(s) when present.
  - If the circular does not contain the requested fact, the system responds with: *"This information is not mentioned in the circular — please check with your college office"* (localized for `hi` / `mr` views).
- **Edge Cases:**
  - **Out-of-scope or personal questions (e.g., asking for weather, coding help, or personal exam seat number):** Reject/ground strictly to circular facts and return the standard office-check fallback.
  - **Empty or whitespace-only query / > 300 characters:** Disable submit on empty input and enforce `300`-character limit on input and API.
  - **Prompt-injection attempt inside question or circular:** Treat circular text as untrusted data and enforce system-level circular-only answering policy.
- **Acceptance Criteria:**
  - **Given** a student asks a question whose answer is present in the circular, **When** the Q&A endpoint responds, **Then** it answers concisely in the selected UI language with page citation(s).
  - **Given** a student asks about a fee or rule absent from the circular, **When** the Q&A endpoint responds, **Then** it returns *"This information is not mentioned in the circular — please check with your college office"* (or localized equivalent) without inventing details.

#### Feature A6: Printable Noticeboard QR Poster Modal
- **User Story:** As a college clerk or student coordinator, I want to print a single-page QR poster for a physical noticeboard so that passing students can scan and read the notice in English, Hindi, or Marathi on their phones.
- **UI/UX Behavior:**
  - `"Print Noticeboard QR Poster"` button in the Action Card header/toolbar opens a modal preview styled for A4 portrait printing.
  - Poster contains: Notice Title, Circular Ref No. & Issue Date, concise summary points, high-contrast QR code encoding the canonical `https://<host>/notice/[hash]` URL, language availability tag (`English | हिंदी | मराठी`), and the permanent disclaimer *"Unofficial Assistive Summary — Confirm on the official circular."*
  - Modal actions: `"Print Poster"` (triggers `window.print()` with `@media print` CSS isolating the poster), `"Copy Link"`, and `"Close"`.
- **Edge Cases:**
  - **Long notice title or multi-line ref number:** Clamp/wrap text gracefully within A4 printable bounds so QR code remains unclipped and scannable.
  - **Local/relative deployment host:** Resolve QR target URL dynamically from configured public base URL or active request origin so QR scans work on real phones.
- **Acceptance Criteria:**
  - **Given** an Action Card at `/notice/[hash]`, **When** the user clicks `"Print Noticeboard QR Poster"`, **Then** a modal opens with a scannable QR code pointing to `/notice/[hash]`, metadata, and the mandatory disclaimer, and clicking `"Print Poster"` opens the browser print dialog showing only the poster layout.

---

### 3.2 Journey B — Live Demo Shortcuts (Built into `/`)

- **User Story:** As a first-time visitor, reviewer, or college staff member, I want one-click live demo actions on the homepage so that I can verify both real bilingual extraction and pre-LLM PII blocking immediately without hunting for sample PDFs.
- **UI/UX Behavior:**
  - Positioned clearly below the main dropzone/URL bar on `/` as two secondary action buttons:
    1. **Button 1: `"Try Sample Exam Circular"`**
       - Submits a bundled, realistic bilingual (English + Marathi/Hindi) college exam circular fixture through the real ingestion and extraction pipeline (not a static hardcoded mock screen; hits real `PipelineStepper`, caching, verification, and `/notice/[hash]` route).
    2. **Button 2: `"Test PII Protection (Mock Merit List)"`**
       - Submits a synthetic student roll-number merit list fixture (with realistic synthetic roll numbers/names) to the real pre-LLM PII screening endpoint, triggering and rendering the live **Privacy Block Screen** explaining why personal student records are rejected before any LLM processing.
- **Edge Cases:**
  - **Demo fixtures missing from bundle:** Build/startup health check ensures both fixture assets exist; UI handles unexpected failure with a clear error banner.
  - **Repeated clicks on Button 1:** First run extracts (or warms cache); subsequent clicks demonstrate `Instant Cache Hit (Tier-1 SHA-256)`.
- **Acceptance Criteria:**
  - **Given** a visitor is on `/`, **When** they click `"Try Sample Exam Circular"`, **Then** the real `PipelineStepper` runs on the bilingual exam fixture and redirects to `/notice/[hash]` with working language toggles, verification badge, voice brief, and `.ics` download.
  - **Given** a visitor is on `/`, **When** they click `"Test PII Protection (Mock Merit List)"`, **Then** the pre-LLM screener blocks the fixture before any LLM API call and renders the live Privacy Block Screen explaining what was detected and why it was blocked.

---

### 3.3 Journey C — Telegram Bot (Zero-Upload Mobile Flow)

- **User Story:** As a student who receives circulars on college Telegram channels, I want to forward a PDF or noticeboard photo directly to a Telegram bot and receive an instant multilingual summary, voice note, and calendar link without opening a browser to upload files.
- **UI/UX Behavior:**
  1. **First interaction (`/start`):** Bot sends a 2-line privacy consent notice:
     *"Public college circulars only — do not send hall tickets, merit lists, or personal IDs."*
     Paired with an inline keyboard button: `"I Understand — Continue"`.
  2. **Consent acknowledgement:** Tapping `"I Understand — Continue"` unlocks circular submissions (stored ephemerally or verified via bot state without logging user-to-document mappings or phone numbers). If a user sends a file before confirming consent, the bot reminds them with the same consent card and discards the file from memory.
  3. **Document / Photo submission:** User forwards a PDF (`<= 10 MB`) or sends a photo (`<= 10 MB`). Bot sends an immediate `"Reading circular..."` status message, downloads bytes strictly into `BytesIO`, runs PII screening + extraction + verification, and edits/replies with:
     - Verification badge label + Circular Ref No. & Issue Date
     - Formatted summary (defaulting to English, switchable in-chat)
     - Mandatory disclaimer line: *"Unofficial Assistive Summary — Confirm on the official circular."*
     - Inline keyboard controls:
       - Language row: `English` | `हिंदी` | `मराठी`
       - Action row: `"Play Voice Note"` | `"Open Full Action Card & Calendar"` (web link to `/notice/[hash]`)
  4. **Language switch callback:** Tapping `English`, `हिंदी`, or `मराठी` edits the bot message in place to display the chosen language summary while keeping message length within Telegram's `4096`-character limit.
  5. **Voice Note callback:** Tapping `"Play Voice Note"` fetches or generates the cached `<= 380`-character audio brief for `(notice_hash, active_lang)` and sends it as a Telegram voice/audio message.
- **Edge Cases:**
  - **PDF > 10 MB:** Bot checks Telegram `file_size` metadata before downloading and replies immediately: *"File exceeds 10 MB limit. Please send a smaller PDF or clear photo."*
  - **Telegram 64-byte `callback_data` limit:** Encode callback payloads compactly (e.g., `l:hi:<16-char-hash-prefix>` or `v:mr:<16-char-hash-prefix>`) mapped deterministically to cached `notice_hash`.
  - **Telegram 4096-character message limit:** Cap formatted chat summary cleanly (truncating secondary bullets if needed while always preserving Ref No., Issue Date, deadlines, disclaimer, and `"Open Full Action Card & Calendar"` link).
  - **PII detected in forwarded file:** Bot discards `BytesIO` buffer immediately, makes zero LLM calls, and replies with the plain-language privacy block explanation.
  - **Media groups (multiple photos sent at once):** Inform the user cleanly to send one notice photo per message (or handle single-page notice photos sequentially) to avoid merging unrelated circulars.
- **Acceptance Criteria:**
  - **Given** a user sends `/start` to the NoticeSetu Telegram Bot, **When** the welcome message renders, **Then** it displays *"Public college circulars only — do not send hall tickets, merit lists, or personal IDs"* and the `"I Understand — Continue"` inline button.
  - **Given** a consented user forwards a valid circular PDF (`<= 10 MB`) or photo, **When** processing completes, **Then** the bot replies with the summary, inline `English | हिंदी | मराठी` switcher, `"Play Voice Note"` button, and `"Open Full Action Card & Calendar"` URL pointing to `/notice/[hash]`.
  - **Given** a user taps `मराठी` and then `"Play Voice Note"`, **When** callbacks fire, **Then** the bot message updates to Marathi and sends the Marathi audio brief without logging user identity against `notice_hash`.

---

### 3.4 Journey D — College Website 1-Line Widget (`/widget-demo` & `public/widget.js`) + CSP Fallback (`/view?url=...`)

- **User Story:** As a college portal coordinator, I want to paste a single `<script>` tag onto our existing public noticeboard page so students see an inline `"Simplify (EN/हिं/म)"` button next to every PDF link without breaking our site's layout or security policy.
- **UI/UX Behavior:**
  - **1-Line Embed Snippet:**
    ```html
    <script src="https://<noticesetu-domain>/widget.js" defer></script>
    ```
  - **Link Scanning:** On `DOMContentLoaded` (and via `MutationObserver` for dynamically rendered tables), `public/widget.js` scans `<a>` tags whose `href` points to `.pdf` (case-insensitive, including query strings like `.pdf?id=12`).
  - **Shadow DOM Pill Injection:** Adjacent to each matching link, `widget.js` attaches an isolated `ShadowRoot` containing a Teal (`#0D9488`) pill button labeled `"Simplify (EN/हिं/म)"`. Shadow DOM isolation ensures host college CSS cannot distort the pill and widget styles cannot alter the host page.
  - **Modal & Fallback Flow:** Clicking `"Simplify (EN/हिं/म)"` opens an accessible Shadow DOM modal overlay containing an `<iframe>` pointed at `https://<noticesetu-domain>/view?url={encoded_pdf_url}` plus a visible `"Open in New Tab"` header link and `"Close"` (`Esc` key supported) button.
  - **Standalone `/view?url=...` Route:** Works independently as a full-page viewer for strict-CSP college portals that disallow external scripts or iframe embedding. Fetching the encoded PDF URL runs the standard NoticeSetu pipeline (SSRF check, `<= 10 MB`, PII check, cache lookup, extraction) and renders or redirects to the Action Card experience.
  - **Demo Showcase (`/widget-demo`):** Hosts a realistic mock college noticeboard HTML table (styled with legacy/conflicting CSS) with `public/widget.js` loaded live so staff and reviewers can test pill injection, modal framing, and `/view?url=...` behavior end to end.
- **Edge Cases:**
  - **Duplicate injection on re-scans:** Mark processed anchor elements with a `data-noticesetu-attached="true"` attribute so `MutationObserver` never injects duplicate pills.
  - **Relative PDF links on host portal:** Resolve `anchor.getAttribute('href')` against `window.location.href` before URL-encoding into `/view?url=...`.
  - **Strict `X-Frame-Options` or `CSP frame-ancestors`:** If iframe rendering is blocked or slow, the modal header's `"Open in New Tab"` link routes directly to `/view?url={encoded_pdf_url}`.
  - **Invalid or missing `url` query parameter on `/view`:** Show a clean validation error and link back to `/`.
- **Acceptance Criteria:**
  - **Given** a webpage includes `<script src="/widget.js" defer></script>` and contains `.pdf` links (such as `/widget-demo`), **When** the page loads, **Then** each `.pdf` link displays a single Teal `"Simplify (EN/हिं/म)"` pill inside an isolated Shadow DOM without altering host CSS.
  - **Given** a student clicks the pill next to a PDF link, **When** the modal opens, **Then** it loads `/view?url={encoded_pdf_url}` and renders the simplified Action Card (or PII block screen if applicable).
  - **Given** a portal enforces a strict CSP blocking third-party scripts or iframes, **When** a student opens `/view?url={encoded_pdf_url}` directly in a browser tab, **Then** the standalone route fetches, checks, and displays the Action Card cleanly.

---

## 4. Action Card Information Architecture & Design System

### 4.1 Visual Language & Color Tokens
The interface uses a clean, high-contrast civic-utility palette built mobile-first (`360px` minimum viewport width) and compliant with WCAG AA contrast ratios (`>= 4.5:1` for body text, `>= 3:1` for large UI controls):

| Token | Hex | Usage |
| :--- | :--- | :--- |
| Deep Navy | `#0F172A` | Primary headings, top governance header accents, primary dark text |
| Off-White | `#F8FAFC` | Page canvas background, card surface contrast |
| Slate | `#334155` | Body copy, table text, secondary labels |
| Teal | `#0D9488` | Primary CTAs (`Simplify Notice`, active language pill, `Add to Calendar`, widget pill) |
| Emerald/Teal Tint | `#ECFDF5` / `#065F46` | `source_matched` verification badge background and text |
| Amber Tint | `#FFFBEB` / `#92400E` | `verify_original` and `scan_extracted` caution badges, corrigendum reminder |
| Crimson Tint | `#FEF2F2` / `#991B1B` | Pre-LLM PII block screen and hard validation errors |

### 4.2 Mandatory Top Governance Elements
Every Action Card (`/notice/[hash]` and `/view?url=...`) MUST display these four elements above the Action Card body:
1. **Permanent Disclaimer Banner:** Persistent, non-dismissible strip reading verbatim:
   `Unofficial Assistive Summary — Confirm on the official circular.`
2. **Pinned Metadata & Corrigendum Reminder:**
   - **Circular Ref No.** (pinned; shows `"Not stated in circular"` if absent)
   - **Issue Date** (pinned; shows `"Not stated in circular"` if absent)
   - **Corrigendum & Expiry Reminder:** Concise notice reminding students to check the college noticeboard/portal for later corrigenda, paired with the cache expiry indicator (`Cached for 14 days from extraction`).
3. **Honest Verification Pill (Strictly 3 Mutual-Exclusive States):**
   - `source_matched` (Green/Teal): **Source-Matched (Digital PDF)** — shown only when input is a digital PDF and every extracted deadline date and fee amount is verified independently against `PyMuPDF` raw text.
   - `verify_original` (Amber): **Verify Original** — shown on a digital PDF when one or more extracted dates or fees could not be matched deterministically in `PyMuPDF` raw text.
   - `scan_extracted` (Amber): **Scan-Extracted — Verify Original** — always shown on camera photos and scanned/image-only PDFs, regardless of extraction confidence.
4. **Cache Indicator Badge:**
   - Displays `Instant Cache Hit (Tier-1 SHA-256)` when served from cache, or `Fresh Extraction` when newly processed.

### 4.3 Action Card Body Sections (Top-to-Bottom Order)
1. **Language Switcher & Voice Brief Bar:** `English | हिंदी | मराठी` segmented control + inline `AudioPlayer`.
2. **Eligibility Tags:** Compact chips indicating target audience (e.g., `B.Sc. Sem IV`, `ATKT Students`, `Open / Reserved Category`, `All UG Departments`).
3. **Plain-Language TL;DR:** 2 to 4 plain sentences summarizing what changed, who is affected, and the core action required.
4. **Action Checklist:** Numbered or checkable step-by-step actions (interactive local checkboxes in browser state only; no server persistence).
5. **Deadlines & Fees Table + `.ics` Download:** Structured rows (`Event / Item`, `Date / Cutoff`, `Fee / Amount`, `Notes`) paired with the deterministic `"Add to Calendar (.ics)"` export button.
6. **Required Documents:** Bulleted list of certificates, forms, or IDs students must carry or upload.
7. **Verbatim Source Quotes:** Exact untranslated excerpts from the original circular tagged with page numbers (`Page 1`, `Page 2`) for fast manual audit.
8. **Collapsible Grounded Q&A Drawer:** Circular-only Q&A panel with strict office-check fallback.
9. **Printable Noticeboard QR Poster Trigger:** Button opening the A4 QR poster modal.

---

## 5. Multilingual & Protected Campus Glossary Rules

### 5.1 Source-Agnostic Input & Output Languages
- **Input:** Accepts circulars written in English, Hindi, Marathi, or mixed bilingual text (such as English headers with Marathi body clauses). The pipeline never assumes English-only input.
- **Output:** Every Action Card generates structured fields in all three output languages:
  - English (`en`)
  - Contemporary Hindi (`hi`) — natural everyday campus Hindi
  - Contemporary Marathi (`mr`) — natural everyday campus Marathi

### 5.2 Protected Campus Glossary
Translations into Hindi and Marathi must preserve standard Indian university and college terms naturally (using Devanagari transliteration or bilingual inline forms) instead of stiff Sanskritized literal translations. Both the extraction prompt and deterministic post-checks enforce these mappings:

| English Term | Protected Hindi (`hi`) Form | Protected Marathi (`mr`) Form | Disallowed Stiff Translation Example |
| :--- | :--- | :--- | :--- |
| `ATKT` | `ATKT (एटीकेटी)` | `ATKT (एटीकेटी)` | Literal expansion into obscure academic phrases |
| `KT` | `KT (केटी)` | `KT (केटी)` | Literal translation of "kept term" |
| `Hall Ticket` | `हॉल टिकट (Hall Ticket)` | `हॉल तिकीट (Hall Ticket)` | `प्रवेश कक्ष पत्र` |
| `Bonafide` | `बोनाफाइड (Bonafide)` | `बोनाफाईड (Bonafide)` | `सद्भाव प्रमाणपत्र` |
| `GR` | `GR / शासन निर्णय` | `GR / शासन निर्णय` | Dropping `GR` acronym |
| `Revaluation` | `रिवैल्यूएशन (Revaluation / पुनर्मूल्यांकन)` | `रिव्हॅल्युएशन (Revaluation / पुनर्मूल्यांकन)` | Removing recognizable `Revaluation` term |
| `PRN` | `PRN (पीआरएन)` | `PRN (पीआरएन)` | `स्थायी पंजीकरण क्रमांक` alone without `PRN` |
| `Provisional Admission` | `प्रोविजनल एडमिशन (Provisional Admission)` | `प्रोव्हिजनल ॲडमिशन (Provisional Admission)` | Purely formal Sanskritized phrasing |
| `Semester` | `सेमेस्टर (Semester)` | `सेमिस्टर (Semester)` | `सत्र` alone when circular specifies semester |

### 5.3 Voice Brief Rules
- Each Action Card generates three spoken scripts (`voice_brief.en`, `voice_brief.hi`, `voice_brief.mr`).
- **Hard Length Cap:** Each spoken script MUST be `<= 380` characters (including spaces and punctuation) to keep playback concise (`~20–30` seconds) and lightweight on mobile networks.
- **Deterministic Enforcement:** Before calling TTS or saving to cache, the backend checks `len(script) <= 380`. If an LLM response exceeds 380 characters, a deterministic trimmer shortens it cleanly at the last sentence or word boundary within 380 characters.
- **Content Rule:** Voice briefs open with the core action, main deadline, and fee (if any), and close with a short reminder to verify the official circular.

---

## 6. Privacy, Trust & DPDP Governance Requirements

NoticeSetu is built for college and junior-college students (including minors under 18) and enforces data minimization aligned with India's Digital Personal Data Protection (DPDP) Rules 2025:

1. **Zero Login & Zero User-to-Document Logging:**
   - No user accounts, phone numbers, email addresses, cookies tracking individuals, or student identifiers are collected.
   - Telegram bot handlers must NEVER log or store `telegram_user_id`, username, or phone number mapped to any `notice_hash` or uploaded file.
   - Server access logs must strip query strings containing raw URLs or redact PII before persistence.

2. **Strict In-Memory File Processing (`BytesIO`):**
   - Uploaded PDFs, camera photos, and URL-fetched files are held solely in RAM (`BytesIO` / in-memory byte buffers) during validation, PII screening, and extraction.
   - Raw uploaded files are NEVER written to local disk, temporary OS folders, or object storage. Buffers are released immediately after processing completes or blocks.

3. **Pre-LLM PII Screening (Deterministic Gate):**
   - Runs BEFORE any bytes or text are sent to an external or hosted LLM.
   - **Blocked Document Categories:** Merit lists, defaulter lists, hall tickets, admit cards, fee receipts, attendance shortage lists, and individual scorecards.
   - **Deterministic Detection Signals (Configurable Thresholds):**
     - Document title/header keywords: `merit list`, `defaulter`, `hall ticket`, `admit card`, `fee receipt`, `marksheet`, `seat number`, `roll no.` paired with student name columns.
     - Structured personal IDs: Aadhaar-like 12-digit patterns (`\b\d{4}\s?\d{4}\s?\d{4}\b` with identity context), PAN (`[A-Z]{5}\d{4}[A-Z]`), personal mobile numbers (`+91` / 10-digit student contact lists), or email lists (`>= 3` personal emails).
     - Dense roll-number / seat-number tables: `>= 5` distinct candidate roll/PRN/seat-number rows with adjacent names or marks.
     - Image/scan fallback: For camera photos or scanned PDFs lacking `PyMuPDF` selectable text, lightweight local OCR/text-density screening (or filename/header check where OCR runs locally in memory) screens for the same blocked patterns before external LLM vision calls; if local pre-scan detects blocked personal-record headers or dense roll tables, block immediately.
   - **Block UX:** Returns `HTTP 422` (`code: "PII_BLOCKED"`) and renders a clear Privacy Block Screen stating which category/signal triggered the block (*"Blocked for Student Privacy: This document looks like a personal record or student list (e.g., merit list, hall ticket, or roll-number table). NoticeSetu only processes public circulars and never sends personal records to AI models."*).

4. **14-Day Cache TTL:**
   - Cached Action Cards (`notice_hash`), URL-to-hash lookups, and cached regional voice briefs expire strictly after **14 days (`1,209,600` seconds)**.
   - Expired entries are deleted or treated as cache misses on read so outdated circulars or superseded fee schedules do not persist indefinitely.

---

## 7. Acceptance Criteria & Pilot Validation Plan

### 7.1 Release-Blocking Acceptance Criteria (Must Pass Before Demo)
All checks below must pass on the target build prior to release:

1. **Ingestion & Limits:**
   - Web upload accepts `.pdf`, `.jpg`, `.jpeg`, `.png` (`<= 10 MB`) and rejects invalid magic bytes or `> 10 MB` files cleanly.
   - Public URL ingestion resolves valid PDFs/images and blocks private/loopback SSRF targets (`127.0.0.1`, `169.254.169.254`, `10.x.x.x`).
2. **In-Memory Processing & PII Gate:**
   - Zero raw uploaded files exist on disk during or after processing (`BytesIO` only).
   - Clicking `"Test PII Protection (Mock Merit List)"` blocks the submission pre-LLM (`0` LLM calls issued) and renders the Privacy Block Screen.
   - Submitting a mock hall ticket or fee receipt triggers the same pre-LLM privacy block.
3. **Verification Pills & Cross-Check:**
   - Digital PDF with matching dates/fees renders `source_matched` (**Source-Matched (Digital PDF)**).
   - Digital PDF with an unverified/mismatched figure renders `verify_original` (**Verify Original**).
   - Camera photo or scanned PDF always renders `scan_extracted` (**Scan-Extracted — Verify Original**).
4. **Action Card Governance & Features:**
   - Permanent disclaimer banner, pinned Circular Ref No. & Issue Date, corrigendum reminder, and Cache Indicator Badge render above the card body.
   - `English | हिंदी | मराठी` toggle updates all extracted sections and preserves Protected Campus Glossary terms (`ATKT`, `Hall Ticket`, `Bonafide`, `PRN`, `GR`, `Revaluation`, `Semester`).
   - Voice brief scripts are `<= 380` characters per language; `AudioPlayer` plays and caches audio per `(notice_hash, lang)`.
   - `.ics` export downloads a valid RFC 5545 file in `Asia/Kolkata` timezone when deadlines exist.
   - Q&A Drawer answers circular-present questions with page numbers and returns *"This information is not mentioned in the circular — please check with your college office"* when absent.
   - Printable Noticeboard QR Poster modal renders a working QR code to `/notice/[hash]` and prints cleanly.
5. **Caching & TTL:**
   - Re-uploading the sample circular produces `Instant Cache Hit (Tier-1 SHA-256)` without triggering a fresh LLM extraction.
   - Cache entries include a 14-day (`1,209,600s`) TTL.
6. **Telegram Bot:**
   - `/start` presents the 2-line privacy notice and `"I Understand — Continue"` button.
   - Forwarding a PDF (`<= 10 MB`) or photo returns the formatted summary, `English | हिंदी | मराठी` inline buttons, `"Play Voice Note"` button, and `"Open Full Action Card & Calendar"` web link.
   - Zero user-to-document mappings or phone numbers are persisted.
7. **Website Widget & CSP Fallback:**
   - `/widget-demo` loads `public/widget.js`, detects `.pdf` links, and injects Teal `"Simplify (EN/हिं/म)"` pills inside isolated Shadow DOMs.
   - Clicking a pill opens the modal pointing to `/view?url={encoded_pdf_url}`.
   - Opening `/view?url={encoded_pdf_url}` directly in a fresh browser tab works standalone without widget script execution.

### 7.2 Post-Hackathon Pilot Validation Plan
The following campus outcomes are **unvalidated** (*To be validated in campus pilot*) and must not be stated as measured product claims before pilot completion:

| Outcome Metric | Validation Method | Target Scope |
| :--- | :--- | :--- |
| Reading-time reduction | Timed comprehension task comparing raw bilingual PDFs vs. NoticeSetu Action Cards across student volunteers | *To be validated in campus pilot* |
| Repeat weekly usage | Anonymous aggregate session/route telemetry (no user IDs or cookies) during exam/admission cycles | *To be validated in campus pilot* |
| Real-world cache hit ratio | Aggregate counter comparing Tier-1 SHA-256 cache hits against total fresh extractions over 14-day TTL windows | *To be validated in campus pilot* |
| User-reported extraction errors | Optional anonymous `"Report an inaccuracy"` flag on Action Cards audited against official PDFs | *To be validated in campus pilot* |
