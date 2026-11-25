"""Deterministic RFC-5545 .ics calendar generator for extracted notice deadlines."""

from datetime import date, datetime, timedelta, timezone

import dateparser

from app.schemas import ActionCardResponse
from app.services.verifier import normalize_devanagari_digits


def _escape_ics_text(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
    )


def _fold_ics_line(line: str) -> str:
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    chunks: list[str] = []
    current = ""
    current_bytes = 0
    for ch in line:
        ch_bytes = len(ch.encode("utf-8"))
        limit = 75 if not chunks else 74
        if current_bytes + ch_bytes > limit:
            chunks.append(current)
            current = " " + ch
            current_bytes = 1 + ch_bytes
        else:
            current += ch
            current_bytes += ch_bytes
    if current:
        chunks.append(current)
    return "\r\n".join(chunks)


def _parse_iso_or_raw_date(iso_date: str, date_raw: str) -> date | None:
    if iso_date:
        try:
            return date.fromisoformat(normalize_devanagari_digits(iso_date.strip()))
        except ValueError:
            pass
    if date_raw:
        parsed = dateparser.parse(
            normalize_devanagari_digits(date_raw.strip()),
            settings={"DATE_ORDER": "DMY"},
        )
        if parsed is not None:
            return parsed.date()
    return None


def extract_valid_ics_events(card: ActionCardResponse) -> list[tuple[date, str, str]]:
    """Return list of (date, summary, description) tuples for actionable deadlines."""
    events: list[tuple[date, str, str]] = []
    ref = card.extraction.circular_ref or "Not specified"
    issue = card.extraction.issue_date or "Not specified"

    for item in card.extraction.deadlines:
        dt = _parse_iso_or_raw_date(item.iso_date, item.date_raw)
        if dt is None:
            continue
        summary = f"NoticeSetu: {item.label}"
        desc_parts = [
            f"Notice: {card.extraction.en.title}",
            f"Deadline: {item.date_raw}",
        ]
        if item.applies_to:
            desc_parts.append(f"Applies to: {item.applies_to}")
        desc_parts.append(f"Circular Ref: {ref} | Issue Date: {issue}")
        desc_parts.append(card.disclaimer)
        events.append((dt, summary, "\n".join(desc_parts)))
    return events


def generate_ics(card: ActionCardResponse) -> str:
    """Generate a valid RFC-5545 .ics calendar payload in Asia/Kolkata context."""
    events = extract_valid_ics_events(card)
    if not events:
        raise ValueError("No calendar deadlines found in this circular.")

    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//NoticeSetu//Circular Deadlines//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:NoticeSetu Deadlines",
        "X-WR-TIMEZONE:Asia/Kolkata",
    ]

    for idx, (dt, summary, description) in enumerate(events):
        dtstart = dt.strftime("%Y%m%d")
        dtend = (dt + timedelta(days=1)).strftime("%Y%m%d")
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{card.notice_hash}-{idx}@noticesetu",
                f"DTSTAMP:{dtstamp}",
                f"DTSTART;VALUE=DATE:{dtstart}",
                f"DTEND;VALUE=DATE:{dtend}",
                f"SUMMARY:{_escape_ics_text(summary)}",
                f"DESCRIPTION:{_escape_ics_text(description)}",
                "END:VEVENT",
            ]
        )

    lines.append("END:VCALENDAR")
    folded = [_fold_ics_line(line) for line in lines]
    return "\r\n".join(folded) + "\r\n"

