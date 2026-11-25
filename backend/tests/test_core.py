"""Phase 1 Gate automated pytest suite for NoticeSetu."""

import io
import socket
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import fitz
import pytest
from fastapi.testclient import TestClient

# Ensure `backend/` is importable when pytest runs from repo root or backend/
BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402
from app.schemas import (  # noqa: E402
    ActionCardResponse,
    DeadlineItem,
    FeeItem,
    LocalizedContent,
    NoticeExtraction,
)
from app.services.cache import get_cache  # noqa: E402
from app.services.calendar_ics import generate_ics  # noqa: E402
from app.services.extractor import extract_document  # noqa: E402
from app.services.security import (  # noqa: E402
    MAX_FILE_BYTES,
    SecurityValidationError,
    get_rate_limiter,
    safe_fetch_url,
    validate_file_bytes,
)
from app.services.verifier import verify_extraction  # noqa: E402


def _build_pdf_bytes(text: str) -> bytes:
    """Create a real single-page digital PDF strictly in memory via PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text, fontsize=11)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def _sample_extraction(
    date_raw: str = "15/03/2026",
    iso_date: str = "2026-03-15",
    amount_raw: str = "Rs. 1,500/-",
    amount_inr: str = "1500",
    quote: str = "Last date for Sem IV ATKT form submission is 15/03/2026.",
) -> NoticeExtraction:
    return NoticeExtraction(
        source_language="mixed",
        circular_ref="EXAM/2026/042",
        issue_date="01/03/2026",
        deadlines=[
            DeadlineItem(
                label="ATKT Exam Form Submission",
                date_raw=date_raw,
                iso_date=iso_date,
                applies_to="Sem IV ATKT Students",
            )
        ],
        fees=[
            FeeItem(
                label="ATKT Examination Fee",
                amount_raw=amount_raw,
                amount_inr=amount_inr,
            )
        ],
        eligibility_tags=["Sem IV", "ATKT"],
        required_docs=["Previous Marksheet", "College ID Card"],
        verbatim_quotes=[quote],
        transcribed_text="",
        en=LocalizedContent(
            title="Semester IV ATKT Exam Form Notice",
            tldr="Sem IV ATKT students must submit exam forms by 15/03/2026 with fee Rs. 1,500/-.",
            action_steps=["Fill exam form", "Pay Rs. 1,500/- fee", "Submit at Exam Cell"],
            voice_script="Sem IV ATKT exam forms close on 15 March 2026. Fee is Rs. 1,500. Confirm on the official circular.",
        ),
        hi=LocalizedContent(
            title="सेमेस्टर IV ATKT परीक्षा फॉर्म सूचना",
            tldr="सेमेस्टर IV ATKT (एटीकेटी) छात्रों को 15/03/2026 तक फॉर्म और 1,500 रुपये शुल्क जमा करना है।",
            action_steps=["फॉर्म भरें", "1,500 रुपये जमा करें"],
            voice_script="सेमेस्टर IV ATKT फॉर्म की अंतिम तिथि 15 मार्च 2026 है। आधिकारिक परिपत्र देखें।",
        ),
        mr=LocalizedContent(
            title="सेमिस्टर IV ATKT परीक्षा फॉर्म सूचना",
            tldr="सेमिस्टर IV ATKT (एटीकेटी) विद्यार्थ्यांनी 15/03/2026 पर्यंत फॉर्म व 1,500 रुपये शुल्क भरावे.",
            action_steps=["फॉर्म भरा", "1,500 रुपये भरा"],
            voice_script="सेमिस्टर IV ATKT फॉर्म भरण्याची अंतिम तारीख 15 मार्च 2026 आहे. मूळ परिपत्रक तपासा.",
        ),
    )


@pytest.fixture(autouse=True)
def _reset_cache():
    get_cache().clear_memory_for_tests()
    get_rate_limiter().reset_for_tests()
    yield
    get_cache().clear_memory_for_tests()
    get_rate_limiter().reset_for_tests()


# 1. SSRF private/loopback/metadata IP block
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "blocked_url",
    [
        "http://127.0.0.1/a.pdf",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal.pdf",
        "http://[::1]/secret.pdf",
    ],
)
async def test_ssrf_blocks_private_and_metadata_ips(blocked_url: str):
    with patch("httpx.AsyncClient.stream") as mock_stream:
        with pytest.raises(SecurityValidationError) as exc_info:
            await safe_fetch_url(blocked_url)
        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "SSRF_BLOCKED"
        mock_stream.assert_not_called()


@pytest.mark.asyncio
async def test_ssrf_blocks_dns_resolving_to_private_ip():
    fake_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.50", 443))]
    with patch("socket.getaddrinfo", return_value=fake_addr):
        with pytest.raises(SecurityValidationError) as exc_info:
            await safe_fetch_url("https://campus-rebind-test.example.com/notice.pdf")
        assert exc_info.value.code == "SSRF_BLOCKED"


# 2. File size > 10 MB rejection
def test_oversized_file_rejected_with_413():
    oversized = b"%PDF-1.4\n" + (b"0" * MAX_FILE_BYTES)
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_file_bytes(oversized)
    assert exc_info.value.status_code == 413

    client = TestClient(app)
    resp = client.post(
        "/api/simplify",
        files={"file": ("huge.pdf", oversized, "application/pdf")},
    )
    assert resp.status_code == 413
    assert resp.json()["code"] == "FILE_TOO_LARGE"


# 3. Invalid magic bytes rejection
def test_invalid_magic_bytes_rejected_with_400():
    spoofed_html = b"<html><body>Not a PDF</body></html>"
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_file_bytes(spoofed_html)
    assert exc_info.value.status_code == 400

    client = TestClient(app)
    resp = client.post(
        "/api/simplify",
        files={"file": ("fake.pdf", spoofed_html, "application/pdf")},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == "INVALID_FILE_TYPE"


# 4. Pre-LLM PII merit-list / roll-number block (zero Gemini calls)
def test_pii_merit_list_blocked_before_llm():
    merit_text = "\n".join(
        [
            "FIRST YEAR B.SC. MERIT LIST 2026-27",
            "101 PRN2026001 Aarav Sharma 94.2%",
            "102 PRN2026002 Diya Patil 93.8%",
            "103 PRN2026003 Rohan Deshmukh 92.5%",
            "104 PRN2026004 Sneha Kulkarni 91.9%",
            "105 PRN2026005 Kabir Joshi 91.0%",
            "106 PRN2026006 Meera Nair 90.4%",
        ]
    )
    pdf_bytes = _build_pdf_bytes(merit_text)
    client = TestClient(app)

    with patch(
        "app.services.simplifier.extract_notice_with_gemini",
        new=AsyncMock(),
    ) as mock_gemini:
        resp = client.post(
            "/api/simplify",
            files={"file": ("merit_list.pdf", pdf_bytes, "application/pdf")},
        )
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "PII_BLOCKED"
        mock_gemini.assert_not_called()


# 5. Devanagari numeral (०-९) & date normalization verification
def test_devanagari_numeral_and_date_verification():
    from app.services.extractor import ExtractedDocument

    # Verify Devanagari numeral normalization (०-९ -> 0-9) and date matching
    devanagari_text = (
        "EXAM CIRCULAR Ref: EXAM/2026/042 Date: 01/03/2026\n"
        "Last date for Sem IV ATKT form submission is १५/०३/२०२६.\n"
        "Examination fee for Regular and ATKT candidates is Rs. १,५००/-."
    )
    dev_doc = ExtractedDocument(
        input_type="digital_pdf",
        raw_sha256="b" * 64,
        page_texts=[devanagari_text],
        combined_text=devanagari_text,
    )
    extraction_ok = _sample_extraction(
        date_raw="15/03/2026",
        iso_date="2026-03-15",
        amount_raw="Rs. 1,500/-",
        amount_inr="1500",
        quote="Last date for Sem IV ATKT form submission is",
    )
    status, unverified, quote_locs = verify_extraction(extraction_ok, dev_doc)
    assert status == "source_matched"
    assert unverified == []
    assert quote_locs[0].page_number == 1

    # Also verify real PyMuPDF digital PDF extraction + page.search_for quote matching
    ascii_circular = (
        "EXAM CIRCULAR Ref: EXAM/2026/042 Date: 01/03/2026\n"
        "Last date for Sem IV ATKT form submission is 15 Mar 2026.\n"
        "Examination fee for Regular and ATKT candidates is Rs. 1,500/-."
    )
    pdf_bytes = _build_pdf_bytes(ascii_circular)
    extracted_doc = extract_document(pdf_bytes, "pdf")
    assert extracted_doc.input_type == "digital_pdf"
    status_pdf, unverified_pdf, pdf_quote_locs = verify_extraction(
        extraction_ok, extracted_doc, raw_pdf_bytes=pdf_bytes
    )
    assert status_pdf == "source_matched"
    assert unverified_pdf == []
    assert pdf_quote_locs[0].page_number == 1

    # Mismatched fee must trigger verify_original
    extraction_mismatch = _sample_extraction(amount_raw="Rs. 9,999/-", amount_inr="9999")
    status_bad, unverified_bad, _ = verify_extraction(
        extraction_mismatch, extracted_doc, raw_pdf_bytes=pdf_bytes
    )
    assert status_bad == "verify_original"
    assert any("9,999" in item for item in unverified_bad)


# 6. Valid RFC-5545 .ics file generation
def test_valid_rfc5545_ics_generation():
    extraction = _sample_extraction()
    card = ActionCardResponse(
        notice_hash="a" * 64,
        input_type="digital_pdf",
        verification_status="source_matched",
        has_ics_deadlines=True,
        extraction=extraction,
    )
    ics_payload = generate_ics(card)
    assert "BEGIN:VCALENDAR\r\n" in ics_payload
    assert "VERSION:2.0\r\n" in ics_payload
    assert "X-WR-TIMEZONE:Asia/Kolkata\r\n" in ics_payload
    assert "BEGIN:VEVENT\r\n" in ics_payload
    assert "DTSTART;VALUE=DATE:20260315\r\n" in ics_payload
    assert "UID:" in ics_payload
    assert "END:VCALENDAR\r\n" in ics_payload


# 7. Tier-1 SHA-256 cache hit returning cache_hit=True
def test_tier1_sha256_cache_hit():
    circular_text = (
        "UNIVERSITY EXAMINATION NOTICE Ref: EXAM/2026/042\n"
        "Last date for Sem IV ATKT form submission is 15/03/2026.\n"
        "ATKT fee Rs. 1,500/- at Exam Cell counter."
    )
    pdf_bytes = _build_pdf_bytes(circular_text)
    extraction = _sample_extraction()
    client = TestClient(app)

    with patch(
        "app.services.simplifier.extract_notice_with_gemini",
        new=AsyncMock(return_value=extraction),
    ) as mock_gemini:
        first = client.post(
            "/api/simplify",
            files={"file": ("exam.pdf", pdf_bytes, "application/pdf")},
        )
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["cache_hit"] is False
        assert first_body["cache_tier"] == "miss"
        assert mock_gemini.call_count == 1

        second = client.post(
            "/api/simplify",
            files={"file": ("exam_copy.pdf", pdf_bytes, "application/pdf")},
        )
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["cache_hit"] is True
        assert second_body["cache_tier"] == "tier1_sha256"
        assert second_body["notice_hash"] == first_body["notice_hash"]
        assert mock_gemini.call_count == 1


# 8. Phase 2 Gate: /health & Telegram webhook 403 secret check
def test_health_and_telegram_webhook_security(monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "top-secret-token")
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["telegram_configured"] is False

        missing_hdr = client.post("/telegram/webhook", json={"update_id": 1})
        assert missing_hdr.status_code == 403

        wrong_hdr = client.post(
            "/telegram/webhook",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )
        assert wrong_hdr.status_code == 403
    finally:
        get_settings.cache_clear()


# 9. Rate limiter enforcement
@pytest.mark.asyncio
async def test_rate_limiter_enforces_429():
    limiter = get_rate_limiter()
    await limiter.check("203.0.113.10", max_requests=2, window_seconds=60)
    await limiter.check("203.0.113.10", max_requests=2, window_seconds=60)
    with pytest.raises(SecurityValidationError) as exc_info:
        await limiter.check("203.0.113.10", max_requests=2, window_seconds=60)
    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "RATE_LIMIT_EXCEEDED"


