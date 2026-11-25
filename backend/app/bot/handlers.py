"""NoticeSetu aiogram v3 Telegram bot handlers (stateless privacy-first flow)."""

import html
import io
from typing import Literal

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import get_settings
from app.schemas import ActionCardResponse
from app.services.cache import get_cache
from app.services.extractor import UnreadableDocumentError
from app.services.pii_guard import PIIBlockedError
from app.services.security import MAX_FILE_BYTES, SecurityValidationError
from app.services.simplifier import SimplifierError, process_notice_bytes
from app.services.tts import TTSUnavailableError, get_or_create_audio

bot_router = Router(name="noticesetu_bot")

# Ephemeral in-memory consent set for runtime session only (never persisted or mapped to docs)
_consented_users: set[int] = set()

_bot_instance: Bot | None = None
_dp_instance: Dispatcher | None = None


def _consent_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="I Understand — Continue",
                    callback_data="consent:ok",
                )
            ]
        ]
    )


def _consent_text() -> str:
    return (
        "Public college circulars only — do not send hall tickets, merit lists, or personal IDs.\n"
        "NoticeSetu processes files strictly in memory with zero login or history."
    )


def _is_public_button_url(url: str) -> bool:
    lowered = url.lower()
    return lowered.startswith("https://") or (
        lowered.startswith("http://")
        and "localhost" not in lowered
        and "127.0.0.1" not in lowered
    )


def _card_keyboard(notice_hash: str, active_lang: Literal["en", "hi", "mr"]) -> InlineKeyboardMarkup:
    h16 = notice_hash[:16]
    settings = get_settings()
    card_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/notice/{notice_hash}"

    lang_labels = {
        "en": "✓ English" if active_lang == "en" else "English",
        "hi": "✓ हिंदी" if active_lang == "hi" else "हिंदी",
        "mr": "✓ मराठी" if active_lang == "mr" else "मराठी",
    }

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(text=lang_labels["en"], callback_data=f"l:en:{h16}"),
            InlineKeyboardButton(text=lang_labels["hi"], callback_data=f"l:hi:{h16}"),
            InlineKeyboardButton(text=lang_labels["mr"], callback_data=f"l:mr:{h16}"),
        ],
        [
            InlineKeyboardButton(
                text="Play Voice Note",
                callback_data=f"v:{active_lang}:{h16}",
            )
        ],
    ]
    if _is_public_button_url(card_url):
        rows[1].append(
            InlineKeyboardButton(
                text="Open Full Action Card & Calendar",
                url=card_url,
            )
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _verification_label(status: str) -> str:
    if status == "source_matched":
        return "Source-Matched (Digital PDF)"
    if status == "verify_original":
        return "Verify Original"
    return "Scan-Extracted — Verify Original"


def format_telegram_summary(
    card: ActionCardResponse,
    lang: Literal["en", "hi", "mr"] = "en",
) -> str:
    """Format Action Card into safe HTML strictly <= 4096 characters."""
    loc = getattr(card.extraction, lang)
    settings = get_settings()
    card_url = f"{settings.FRONTEND_BASE_URL.rstrip('/')}/notice/{card.notice_hash}"

    lines: list[str] = [
        f"<b>{html.escape(loc.title)}</b>",
        f"<i>{html.escape(_verification_label(card.verification_status))}</i>",
        f"Ref: {html.escape(card.extraction.circular_ref)} | Date: {html.escape(card.extraction.issue_date)}",
        "",
        html.escape(loc.tldr),
    ]

    if loc.action_steps:
        lines.append("")
        lines.append("<b>Action Steps:</b>")
        for idx, step in enumerate(loc.action_steps[:5], start=1):
            lines.append(f"{idx}. {html.escape(step)}")

    if card.extraction.deadlines:
        lines.append("")
        lines.append("<b>Deadlines:</b>")
        for dl in card.extraction.deadlines[:4]:
            lines.append(f"• {html.escape(dl.label)}: {html.escape(dl.date_raw)}")

    if card.extraction.fees:
        lines.append("")
        lines.append("<b>Fees:</b>")
        for fee in card.extraction.fees[:4]:
            lines.append(f"• {html.escape(fee.label)}: {html.escape(fee.amount_raw)}")

    footer_lines = [
        "",
        f"Full Action Card & Calendar: {html.escape(card_url)}",
        f"<i>{html.escape(card.disclaimer)}</i>",
    ]
    footer = "\n".join(footer_lines)
    body = "\n".join(lines)

    max_body = 4096 - len(footer) - 4
    if len(body) > max_body:
        body = body[: max(0, max_body - 3)].rstrip() + "..."
    return f"{body}{footer}"


@bot_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(_consent_text(), reply_markup=_consent_markup())


@bot_router.callback_query(F.data == "consent:ok")
async def on_consent(callback: CallbackQuery) -> None:
    if callback.from_user:
        _consented_users.add(callback.from_user.id)
    await callback.answer("Consent confirmed.")
    if callback.message:
        await callback.message.edit_text(
            "Ready. Forward a public college circular PDF (<= 10 MB) or snap a noticeboard photo."
        )


async def _handle_binary_notice(message: Message, file_id: str, file_size: int | None) -> None:
    user_id = message.from_user.id if message.from_user else None
    if user_id is None or user_id not in _consented_users:
        await message.answer(_consent_text(), reply_markup=_consent_markup())
        return

    if file_size is not None and file_size > MAX_FILE_BYTES:
        await message.answer(
            "File exceeds 10 MB limit. Please send a smaller PDF or clear photo."
        )
        return

    if message.bot is None:
        return

    status_msg = await message.answer("Reading circular...")
    buf = io.BytesIO()
    try:
        await message.bot.download(file_id, destination=buf)
        raw_bytes = buf.getvalue()
        card = await process_notice_bytes(raw_bytes, source_hint="telegram")
    except (SecurityValidationError, UnreadableDocumentError, PIIBlockedError, SimplifierError) as exc:
        await status_msg.edit_text(exc.message)
        return
    except Exception:
        await status_msg.edit_text(
            "Could not process this circular right now. Please try again or use the web hub."
        )
        return
    finally:
        buf.close()

    summary_html = format_telegram_summary(card, lang="en")
    await status_msg.edit_text(
        summary_html,
        parse_mode="HTML",
        reply_markup=_card_keyboard(card.notice_hash, "en"),
        disable_web_page_preview=True,
    )


@bot_router.message(F.document)
async def on_document(message: Message) -> None:
    doc = message.document
    if doc is None:
        return
    allowed_mimes = {"application/pdf", "image/jpeg", "image/png"}
    filename = (doc.file_name or "").lower()
    if doc.mime_type not in allowed_mimes and not filename.endswith((".pdf", ".jpg", ".jpeg", ".png")):
        await message.answer("Please send a PDF, JPEG, or PNG circular (<= 10 MB).")
        return
    await _handle_binary_notice(message, doc.file_id, doc.file_size)


@bot_router.message(F.photo)
async def on_photo(message: Message) -> None:
    if not message.photo:
        return
    largest = message.photo[-1]
    await _handle_binary_notice(message, largest.file_id, largest.file_size)


@bot_router.callback_query(F.data.startswith("l:"))
async def on_lang_switch(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":", 2)
    if len(parts) != 3 or parts[1] not in {"en", "hi", "mr"}:
        await callback.answer("Invalid language selection.")
        return

    lang: Literal["en", "hi", "mr"] = parts[1]  # type: ignore[assignment]
    h16 = parts[2]
    cache = get_cache()
    full_hash = await cache.resolve_hash_prefix(h16)
    if not full_hash:
        await callback.answer("Notice expired after 14 days. Please resend it.", show_alert=True)
        return

    card, _ = await cache.get_by_sha256(full_hash)
    if card is None:
        await callback.answer("Notice expired after 14 days. Please resend it.", show_alert=True)
        return

    if callback.message:
        await callback.message.edit_text(
            format_telegram_summary(card, lang=lang),
            parse_mode="HTML",
            reply_markup=_card_keyboard(card.notice_hash, lang),
            disable_web_page_preview=True,
        )
    await callback.answer()


@bot_router.callback_query(F.data.startswith("v:"))
async def on_voice_note(callback: CallbackQuery) -> None:
    parts = (callback.data or "").split(":", 2)
    if len(parts) != 3 or parts[1] not in {"en", "hi", "mr"}:
        await callback.answer("Invalid audio selection.")
        return

    lang: Literal["en", "hi", "mr"] = parts[1]  # type: ignore[assignment]
    h16 = parts[2]
    cache = get_cache()
    full_hash = await cache.resolve_hash_prefix(h16)
    if not full_hash:
        await callback.answer("Notice expired after 14 days. Please resend it.", show_alert=True)
        return

    card, _ = await cache.get_by_sha256(full_hash)
    if card is None:
        await callback.answer("Notice expired after 14 days. Please resend it.", show_alert=True)
        return

    voice_script = getattr(card.extraction, lang).voice_script
    try:
        audio_bytes = await get_or_create_audio(full_hash, lang, voice_script)
    except TTSUnavailableError as exc:
        await callback.answer(exc.message, show_alert=True)
        return

    await callback.answer("Sending voice note...")
    if callback.message:
        await callback.message.answer_audio(
            BufferedInputFile(audio_bytes, filename=f"noticesetu-{lang}.mp3"),
            title=getattr(card.extraction, lang).title[:60],
            performer="NoticeSetu",
        )


def get_bot_and_dispatcher() -> tuple[Bot | None, Dispatcher]:
    """Lazily initialize Bot and Dispatcher; returns (None, dp) if token is unset."""
    global _bot_instance, _dp_instance
    if _dp_instance is None:
        _dp_instance = Dispatcher()
        _dp_instance.include_router(bot_router)

    settings = get_settings()
    if settings.TELEGRAM_BOT_TOKEN and _bot_instance is None:
        _bot_instance = Bot(
            token=settings.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode="HTML"),
        )
    return _bot_instance, _dp_instance

