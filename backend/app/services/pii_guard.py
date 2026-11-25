"""Pre-LLM PII guard blocking personal student records and masking sensitive IDs."""

import re

MOBILE_RE = re.compile(r"(?:\+91[\s-]?)?[6-9]\d{9}")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
NATIONAL_ID_RE = re.compile(r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")

SENSITIVE_KEYWORDS = (
    "merit list",
    "defaulter list",
    "hall ticket",
    "admit card",
    "fee receipt",
)

# Matches rows containing student roll/PRN/seat identifiers paired with names or numeric scores
ROLL_ROW_RE = re.compile(
    r"(?im)^\s*(?:\d{1,4}[\s,|\t.\-]+)?"
    r"(?:(?:PRN|ROLL\s*(?:NO\.?)?|SEAT\s*(?:NO\.?)?|REG(?:N)?\.?\s*(?:NO\.?)?)[\s:#\-]*)?"
    r"(?:[A-Z]{1,4}\d{4,10}|\d{5,12})"
    r"(?:[\s,|\t\-]+[A-Za-z][A-Za-z.\s]{2,45})"
)

NAME_OR_ID_LINE_RE = re.compile(
    r"(?im)(?:name\s*[:\-]\s*[A-Za-z]{2,}|"
    r"(?:roll|seat|prn|regn?)\s*(?:no\.?|number|id)?\s*[:\-]?\s*[A-Z0-9\-]{4,}|"
    r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\s+\d{2,3}(?:\.\d+)?%?)"
)

PII_BLOCK_MESSAGE = (
    "This document appears to contain personal student records "
    "(such as a merit list, hall ticket, or personal IDs). "
    "NoticeSetu processes public circulars only to protect student privacy."
)


class PIIBlockedError(Exception):
    """Raised before external LLM calls when personal student records are detected."""

    def __init__(self, reason: str, message: str = PII_BLOCK_MESSAGE) -> None:
        super().__init__(message)
        self.code = "PII_BLOCKED"
        self.reason = reason
        self.message = message


def redact_sensitive_ids(text: str) -> str:
    """Mask stray personal 12-digit national IDs and PAN numbers before LLM calls."""
    masked = NATIONAL_ID_RE.sub("[REDACTED_ID]", text)
    masked = PAN_RE.sub("[REDACTED_PAN]", masked)
    return masked


def scan_and_block_pii(text: str) -> str:
    """Screen text deterministically for personal student records; return masked text."""
    if not text or not text.strip():
        return text

    lowered = text.lower()
    roll_rows = ROLL_ROW_RE.findall(text)
    national_ids = NATIONAL_ID_RE.findall(text)
    pans = PAN_RE.findall(text)
    mobiles = MOBILE_RE.findall(text)
    emails = EMAIL_RE.findall(text)
    name_or_id_hits = NAME_OR_ID_LINE_RE.findall(text)

    # 1. Dense student roll/PRN/seat-number tables
    if len(roll_rows) >= 5:
        raise PIIBlockedError(reason="dense_roll_number_table")

    # 2. Sensitive record keywords combined with personal IDs/names
    has_sensitive_keyword = any(kw in lowered for kw in SENSITIVE_KEYWORDS)
    personal_signal_count = (
        len(roll_rows)
        + len(name_or_id_hits)
        + len(national_ids)
        + len(pans)
        + len(mobiles)
        + len(emails)
    )
    if has_sensitive_keyword and personal_signal_count >= 3:
        raise PIIBlockedError(reason="sensitive_student_record_keyword")

    # 3. Multiple personal government/tax IDs
    if len(national_ids) + len(pans) >= 3:
        raise PIIBlockedError(reason="multiple_personal_ids")

    # 4. Bulk student mobile/email contact lists (1-2 office helpdesk contacts allowed)
    if len(mobiles) >= 5 or len(emails) >= 5 or (len(mobiles) + len(emails) >= 6):
        raise PIIBlockedError(reason="bulk_personal_contacts")

    return redact_sensitive_ids(text)

