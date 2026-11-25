"""Deterministic verification of Devanagari numerals, dates, fees, and quotes."""

import io
import re
from datetime import date, datetime

import dateparser
import fitz

from app.schemas import ActionCardResponse, NoticeExtraction, QuoteLocation
from app.services.extractor import ExtractedDocument
from app.services.pii_guard import scan_and_block_pii

DEVANAGARI_DIGITS_TRANS = str.maketrans("०१२३४५६७८९", "0123456789")


def normalize_devanagari_digits(text: str) -> str:
    """Convert Devanagari numerals (०-९) to ASCII digits (0-9)."""
    return text.translate(DEVANAGARI_DIGITS_TRANS)


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_for_numeric_match(text: str) -> str:
    norm = normalize_devanagari_digits(text)
    norm = re.sub(r"[₹,]", "", norm)
    norm = re.sub(r"\b(?:rs\.?|inr)\s*", "", norm, flags=re.IGNORECASE)
    return _collapse_ws(norm).lower()


def _extract_numeric_token(amount_inr: str, amount_raw: str) -> str:
    norm_inr = normalize_devanagari_digits(amount_inr or "")
    digits = re.sub(r"[^\d.]", "", norm_inr)
    if digits:
        return digits.rstrip(".")
    norm_raw = _normalize_for_numeric_match(amount_raw or "")
    m = re.search(r"\d+(?:\.\d+)?", norm_raw)
    return m.group(0) if m else ""


def _date_variants(dt: date) -> set[str]:
    month_abbr = dt.strftime("%b").lower()
    month_full = dt.strftime("%B").lower()
    return {
        dt.strftime("%Y-%m-%d"),
        dt.strftime("%d/%m/%Y"),
        dt.strftime("%d-%m-%Y"),
        dt.strftime("%d.%m.%Y"),
        f"{dt.day}/{dt.month}/{dt.year}",
        f"{dt.day}-{dt.month}-{dt.year}",
        f"{dt.day}.{dt.month}.{dt.year}",
        dt.strftime("%d/%m/%y"),
        dt.strftime("%d-%m-%y"),
        f"{dt.day}/{dt.month}/{dt.strftime('%y')}",
        f"{dt.day:02d} {month_abbr} {dt.year}",
        f"{dt.day} {month_abbr} {dt.year}",
        f"{dt.day:02d} {month_full} {dt.year}",
        f"{dt.day} {month_full} {dt.year}",
    }


def _parse_deadline_date(iso_date: str, date_raw: str) -> date | None:
    if iso_date:
        clean_iso = normalize_devanagari_digits(iso_date.strip())
        try:
            return date.fromisoformat(clean_iso)
        except ValueError:
            pass
    if date_raw:
        clean_raw = normalize_devanagari_digits(date_raw.strip())
        parsed: datetime | None = dateparser.parse(
            clean_raw,
            settings={"DATE_ORDER": "DMY"},
        )
        if parsed is not None:
            return parsed.date()
    return None


def _locate_quote_pages(
    quotes: list[str],
    extracted_doc: ExtractedDocument,
    raw_pdf_bytes: bytes | None,
) -> list[QuoteLocation]:
    locations: list[QuoteLocation] = []
    normalized_pages = [
        _collapse_ws(normalize_devanagari_digits(p)).lower()
        for p in extracted_doc.page_texts
    ]

    doc: fitz.Document | None = None
    if raw_pdf_bytes is not None:
        try:
            doc = fitz.open(stream=io.BytesIO(raw_pdf_bytes), filetype="pdf")
        except Exception:
            doc = None

    try:
        for quote in quotes:
            clean_quote = quote.strip()
            if not clean_quote:
                continue
            matched_page: int | None = None

            if doc is not None:
                search_snippet = clean_quote[:120]
                for idx in range(min(len(doc), len(extracted_doc.page_texts) or len(doc))):
                    try:
                        rects = doc[idx].search_for(search_snippet)
                        if rects:
                            matched_page = idx + 1
                            break
                    except Exception:
                        continue

            if matched_page is None:
                norm_q = _collapse_ws(normalize_devanagari_digits(clean_quote)).lower()
                for idx, page_txt in enumerate(normalized_pages):
                    if norm_q and norm_q in page_txt:
                        matched_page = idx + 1
                        break

            locations.append(QuoteLocation(quote=clean_quote, page_number=matched_page))
    finally:
        if doc is not None:
            doc.close()

    return locations


def verify_extraction(
    extraction: NoticeExtraction,
    extracted_doc: ExtractedDocument,
    raw_pdf_bytes: bytes | None = None,
) -> tuple[str, list[str], list[QuoteLocation]]:
    """Run deterministic verification on digital PDFs or post-OCR PII check on scans."""
    if extracted_doc.input_type in {"scanned_pdf", "photo"}:
        # Screen AI-transcribed scan content before allowing caching or response
        combined_scan_text = "\n".join(
            [
                extraction.transcribed_text,
                extraction.circular_ref,
                extraction.issue_date,
                *extraction.verbatim_quotes,
                extraction.en.title,
                extraction.en.tldr,
                *extraction.en.action_steps,
            ]
        )
        scan_and_block_pii(combined_scan_text)
        quote_locs = [
            QuoteLocation(quote=q.strip(), page_number=None)
            for q in extraction.verbatim_quotes
            if q.strip()
        ]
        return "scan_extracted", [], quote_locs

    # Digital PDF verification
    norm_raw_text = _collapse_ws(
        normalize_devanagari_digits(extracted_doc.combined_text)
    ).lower()
    norm_numeric_text = _normalize_for_numeric_match(extracted_doc.combined_text)

    unverified_items: list[str] = []

    for fee in extraction.fees:
        num = _extract_numeric_token(fee.amount_inr, fee.amount_raw)
        if not num:
            if fee.amount_raw.strip():
                raw_norm = _collapse_ws(normalize_devanagari_digits(fee.amount_raw)).lower()
                if raw_norm not in norm_raw_text:
                    unverified_items.append(f"Fee: {fee.label} ({fee.amount_raw})")
            continue
        pattern = rf"(?<!\d){re.escape(num)}(?!\d)"
        if not re.search(pattern, norm_numeric_text):
            unverified_items.append(f"Fee: {fee.label} ({fee.amount_raw})")

    for deadline in extraction.deadlines:
        raw_norm = _collapse_ws(normalize_devanagari_digits(deadline.date_raw)).lower()
        parsed_dt = _parse_deadline_date(deadline.iso_date, deadline.date_raw)

        matched = bool(raw_norm and raw_norm in norm_raw_text)
        if not matched and parsed_dt is not None:
            variants = _date_variants(parsed_dt)
            matched = any(v in norm_raw_text for v in variants)

        if not matched:
            unverified_items.append(f"Deadline: {deadline.label} ({deadline.date_raw})")

    quote_locations = _locate_quote_pages(
        extraction.verbatim_quotes,
        extracted_doc,
        raw_pdf_bytes,
    )

    status = "source_matched" if not unverified_items else "verify_original"
    return status, unverified_items, quote_locations

