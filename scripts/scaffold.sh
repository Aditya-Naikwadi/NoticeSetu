#!/usr/bin/env bash
# NoticeSetu — Idempotent Monorepo Scaffolding Script
# Creates the full directory tree and non-destructive starter stubs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

echo "[NoticeSetu] Scaffolding monorepo structure under: ${ROOT_DIR}"

# 1. Create directory tree
mkdir -p \
  docs \
  scripts \
  backend/app/services \
  backend/app/routes \
  backend/app/bot \
  backend/tests \
  frontend/public \
  frontend/src/lib \
  "frontend/src/app/notice/[hash]" \
  frontend/src/app/view \
  frontend/src/app/widget-demo \
  frontend/src/components

# Non-destructive file helper: writes starter content only if file does not exist
ensure_file() {
  local target_path="$1"
  local content="$2"

  if [ -f "${target_path}" ]; then
    echo "  [skip] ${target_path} (already exists)"
  else
    printf '%s\n' "${content}" > "${target_path}"
    echo "  [create] ${target_path}"
  fi
}

# 2. Root files
ensure_file "docker-compose.yml" "# NoticeSetu Docker Compose configuration"
ensure_file "README.md" "# NoticeSetu"

# 3. Backend configuration & packaging stubs
ensure_file "backend/requirements.txt" "# NoticeSetu Python 3.11+ dependencies (use google-genai, aiogram v3, PyMuPDF)"
ensure_file "backend/Dockerfile" "# NoticeSetu Backend Dockerfile (Python 3.11-slim)"
ensure_file "backend/.env.example" "GEMINI_API_KEY=
TTS_PROVIDER=sarvam
SARVAM_API_KEY=
SARVAM_TTS_MODEL=bulbul:v3
SARVAM_TTS_SPEAKER=shubh
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
SUPABASE_URL=
SUPABASE_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
FRONTEND_BASE_URL=http://localhost:3000
ALLOWED_ORIGINS=http://localhost:3000"

# 4. Backend Python package & app modules
ensure_file "backend/app/__init__.py" '"""NoticeSetu backend package."""'
ensure_file "backend/app/config.py" '"""NoticeSetu runtime settings loaded via pydantic-settings."""'
ensure_file "backend/app/schemas.py" '"""NoticeSetu Pydantic v2 flat data schemas."""'
ensure_file "backend/app/main.py" '"""NoticeSetu FastAPI entrypoint, CORS, and health check."""'

ensure_file "backend/app/services/__init__.py" '"""NoticeSetu domain services."""'
ensure_file "backend/app/services/security.py" '"""SSRF-hardened URL fetching and magic-byte validation in io.BytesIO."""'
ensure_file "backend/app/services/cache.py" '"""Two-tier Upstash Redis and in-memory 14-day TTL cache."""'
ensure_file "backend/app/services/extractor.py" '"""PyMuPDF dual-path extraction and Pillow pHash processing."""'
ensure_file "backend/app/services/pii_guard.py" '"""Pre-LLM PII screening and PIIBlockedError gate."""'
ensure_file "backend/app/services/simplifier.py" '"""Gemini 2.5 Flash extraction, Q&A, and shared notice pipeline."""'
ensure_file "backend/app/services/verifier.py" '"""Deterministic Devanagari, date, fee, and quote cross-checking."""'
ensure_file "backend/app/services/tts.py" '"""Cached regional voice brief synthesis and audio storage."""'
ensure_file "backend/app/services/calendar_ics.py" '"""Deterministic RFC-5545 .ics calendar export generator."""'

ensure_file "backend/app/routes/__init__.py" '"""NoticeSetu HTTP route modules."""'
ensure_file "backend/app/routes/notices.py" '"""Notice API endpoints and Telegram webhook handler."""'

ensure_file "backend/app/bot/__init__.py" '"""NoticeSetu aiogram v3 Telegram bot package."""'
ensure_file "backend/app/bot/handlers.py" '"""Telegram bot consent flow, document/photo intake, and callbacks."""'
ensure_file "backend/app/bot/run_polling.py" '"""Local Telegram long-polling runner: python -m app.bot.run_polling."""'

ensure_file "backend/tests/__init__.py" '"""NoticeSetu backend test suite."""'
ensure_file "backend/tests/test_core.py" '"""Phase 1 Gate pytest suite for NoticeSetu."""'

# 5. Frontend configuration & app files
ensure_file "frontend/package.json" '{
  "name": "noticesetu-frontend",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  }
}'
ensure_file "frontend/.env.example" "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_APP_URL=http://localhost:3000"
ensure_file "frontend/public/widget.js" "/* NoticeSetu Shadow DOM Embed Widget (< 15 KB, zero dependencies) */"
ensure_file "frontend/src/lib/api.ts" "// NoticeSetu typed REST API client and demo helpers"

ensure_file "frontend/src/app/layout.tsx" "// NoticeSetu root Next.js App Router layout"
ensure_file "frontend/src/app/page.tsx" "// NoticeSetu Web Student Hub (/)"
ensure_file "frontend/src/app/notice/[hash]/page.tsx" "// NoticeSetu Action Card view (/notice/[hash])"
ensure_file "frontend/src/app/view/page.tsx" "// NoticeSetu standalone CSP-safe URL viewer (/view?url=...)"
ensure_file "frontend/src/app/widget-demo/page.tsx" "// NoticeSetu college portal widget demo (/widget-demo)"

ensure_file "frontend/src/components/ActionCard.tsx" "// NoticeSetu Action Card component"
ensure_file "frontend/src/components/AudioPlayer.tsx" "// NoticeSetu cached regional AudioPlayer component"
ensure_file "frontend/src/components/NoticeQA.tsx" "// NoticeSetu collapsible grounded Q&A drawer"
ensure_file "frontend/src/components/QrPosterModal.tsx" "// NoticeSetu A4 printable QR noticeboard poster modal"
ensure_file "frontend/src/components/PipelineStepper.tsx" "// NoticeSetu live processing PipelineStepper"

# 6. Six-point verification check
echo ""
echo "[NoticeSetu] Running 6-point scaffold verification..."
MISSING=0

check_exists() {
  if [ ! -e "$1" ]; then
    echo "  [FAIL] Missing required path: $1"
    MISSING=1
  fi
}

# Check 1: Docs & scripts
for p in docs/PRD.md docs/REQUIREMENTS.md docs/FILE_STRUCTURE.md scripts/scaffold.sh; do
  check_exists "$p"
done

# Check 2: Root infra files
for p in docker-compose.yml README.md; do
  check_exists "$p"
done

# Check 3: Backend core & services
for p in \
  backend/requirements.txt backend/Dockerfile backend/.env.example \
  backend/app/main.py backend/app/config.py backend/app/schemas.py \
  backend/app/services/security.py backend/app/services/cache.py \
  backend/app/services/extractor.py backend/app/services/pii_guard.py \
  backend/app/services/simplifier.py backend/app/services/verifier.py \
  backend/app/services/tts.py backend/app/services/calendar_ics.py; do
  check_exists "$p"
done

# Check 4: Backend routes, bot & tests
for p in \
  backend/app/routes/notices.py \
  backend/app/bot/handlers.py backend/app/bot/run_polling.py \
  backend/tests/test_core.py; do
  check_exists "$p"
done

# Check 5: Frontend app routes & components
for p in \
  frontend/package.json frontend/.env.example frontend/src/lib/api.ts \
  frontend/src/app/layout.tsx frontend/src/app/page.tsx \
  "frontend/src/app/notice/[hash]/page.tsx" frontend/src/app/view/page.tsx \
  frontend/src/app/widget-demo/page.tsx \
  frontend/src/components/ActionCard.tsx frontend/src/components/AudioPlayer.tsx \
  frontend/src/components/NoticeQA.tsx frontend/src/components/QrPosterModal.tsx \
  frontend/src/components/PipelineStepper.tsx; do
  check_exists "$p"
done

# Check 6: Widget asset presence & size (< 15 KB)
check_exists "frontend/public/widget.js"
if [ -f "frontend/public/widget.js" ]; then
  WIDGET_BYTES=$(wc -c < "frontend/public/widget.js" | tr -d '[:space:]')
  if [ "${WIDGET_BYTES}" -ge 15360 ]; then
    echo "  [FAIL] frontend/public/widget.js exceeds 15 KB (${WIDGET_BYTES} bytes)"
    MISSING=1
  fi
fi

if [ "${MISSING}" -ne 0 ]; then
  echo "[NoticeSetu] Scaffold verification FAILED."
  exit 1
fi

echo "[NoticeSetu] Scaffold verification PASSED (all required paths and constraints verified)."

