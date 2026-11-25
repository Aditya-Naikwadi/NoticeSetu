"""Flat Pydantic v2 schemas for NoticeSetu structured extraction and REST APIs."""

from typing import Literal
from pydantic import BaseModel, Field


class DeadlineItem(BaseModel):
    label: str = Field(..., description="Short event label, e.g., Exam Form Submission")
    date_raw: str = Field(..., description="Exact date/time text as written in circular")
    iso_date: str = Field("", description="YYYY-MM-DD if exact calendar date exists, else empty string")
    applies_to: str = Field("", description="Who this deadline applies to, e.g., Regular & ATKT")


class FeeItem(BaseModel):
    label: str = Field(..., description="Fee description, e.g., Semester Exam Fee")
    amount_raw: str = Field(..., description="Exact fee phrase from circular, e.g., Rs. 500/-")
    amount_inr: str = Field("", description="ASCII digits only, e.g., 500")


class LocalizedContent(BaseModel):
    title: str = Field(..., description="Concise notice title in target language")
    tldr: str = Field(..., description="2-4 plain sentences summarizing who, what, and key action")
    action_steps: list[str] = Field(default_factory=list, description="Ordered student action steps")
    voice_script: str = Field(..., description="Spoken summary strictly <= 380 characters")


class NoticeExtraction(BaseModel):
    """Flat structured output schema compatible with Gemini 2.5 Flash JSON mode."""

    source_language: Literal["en", "hi", "mr", "mixed"] = "en"
    circular_ref: str = Field("Not specified", description="Official circular reference number or Not specified")
    issue_date: str = Field("Not specified", description="Issue date string or Not specified")
    deadlines: list[DeadlineItem] = Field(default_factory=list)
    fees: list[FeeItem] = Field(default_factory=list)
    eligibility_tags: list[str] = Field(default_factory=list)
    required_docs: list[str] = Field(default_factory=list)
    verbatim_quotes: list[str] = Field(default_factory=list, description="3-5 short verbatim substrings from the circular")
    transcribed_text: str = Field("", description="Plain transcribed circular text for scanned PDFs/photos")
    en: LocalizedContent
    hi: LocalizedContent
    mr: LocalizedContent


class QuoteLocation(BaseModel):
    quote: str
    page_number: int | None = None


class ActionCardResponse(BaseModel):
    notice_hash: str
    input_type: Literal["digital_pdf", "scanned_pdf", "photo"]
    verification_status: Literal["source_matched", "verify_original", "scan_extracted"]
    unverified_items: list[str] = Field(default_factory=list)
    quote_locations: list[QuoteLocation] = Field(default_factory=list)
    cache_hit: bool = False
    cache_tier: Literal["tier1_sha256", "tier2_text", "tier2_phash", "miss"] = "miss"
    cache_ttl_seconds: int = 1209600
    has_ics_deadlines: bool = False
    disclaimer: str = "Unofficial Assistive Summary — Confirm on the official circular."
    extraction: NoticeExtraction


class QARequest(BaseModel):
    notice_hash: str = Field(..., min_length=16, max_length=64)
    question: str = Field(..., min_length=1, max_length=300)
    lang: Literal["en", "hi", "mr"] = "en"


class QAResponse(BaseModel):
    answer: str
    found_in_notice: bool
    cited_pages: list[int] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    code: str
    message: str

