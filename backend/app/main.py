"""NoticeSetu FastAPI application entrypoint, CORS, health check, and Telegram webhook."""

from contextlib import asynccontextmanager
import hmac

from aiogram import types as aiogram_types
from fastapi import FastAPI, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.bot.handlers import get_bot_and_dispatcher
from app.config import get_settings
from app.routes.notices import router as notices_router
from app.services.cache import get_cache

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    bot, _ = get_bot_and_dispatcher()
    if bot is not None:
        await bot.session.close()


app = FastAPI(
    title="NoticeSetu API",
    description="Zero-login multilingual campus notice intelligence platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(notices_router)


@app.get("/health")
async def health_check():
    """Lightweight readiness endpoint with zero external AI calls."""
    cfg = get_settings()
    cache = get_cache()
    supabase_status = (
        "connected" if (cfg.SUPABASE_URL and cfg.SUPABASE_KEY) else "memory_fallback"
    )
    return {
        "status": "ok",
        "redis": cache.backend_status,
        "supabase": supabase_status,
        "tts_provider": cfg.TTS_PROVIDER,
        "telegram_configured": bool(cfg.TELEGRAM_BOT_TOKEN),
    }


@app.post("/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
):
    """Receive Telegram updates after constant-time secret token verification."""
    cfg = get_settings()
    expected_secret = cfg.TELEGRAM_WEBHOOK_SECRET
    if not expected_secret or not x_telegram_bot_api_secret_token:
        return JSONResponse(
            status_code=403,
            content={"code": "FORBIDDEN", "message": "Invalid Telegram webhook secret token."},
        )
    if not hmac.compare_digest(x_telegram_bot_api_secret_token, expected_secret):
        return JSONResponse(
            status_code=403,
            content={"code": "FORBIDDEN", "message": "Invalid Telegram webhook secret token."},
        )

    bot, dp = get_bot_and_dispatcher()
    if bot is None:
        return JSONResponse(
            status_code=503,
            content={"code": "TELEGRAM_NOT_CONFIGURED", "message": "TELEGRAM_BOT_TOKEN is unset."},
        )

    payload = await request.json()
    update = aiogram_types.Update.model_validate(payload)
    await dp.feed_update(bot, update)
    return {"ok": True}
