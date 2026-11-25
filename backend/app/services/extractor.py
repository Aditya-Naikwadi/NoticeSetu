"""Dual-path in-memory document extractor using PyMuPDF and Pillow."""

import hashlib
import io
import re
from dataclasses import dataclass, field
from typing import Literal

import fitz
import imagehash
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_DIGITAL_PDF_PAGES = 10
MAX_SCAN_RENDER_PAGES = 3
MIN_DIGITAL_CHARS = 80
SCAN_RENDER_DPI = 150
MAX_IMAGE_EDGE_PX = 2000


class UnreadableDocumentError(Exception):
    """Raised when a PDF is encrypted/corrupted or an image cannot be decoded."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class ExtractedDocument:
    input_type: Literal["digital_pdf", "scanned_pdf", "photo"]
    raw_sha256: str
    normalized_text_sha256: str | None = None
    phash_hex: str | None = None
    page_texts: list[str] = field(default_factory=list)
    combined_text: str = ""
    image_parts: list[tuple[bytes, str]] = field(default_factory=list)


def _normalize_text_hash(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()


def extract_document(
    data: bytes,
    filetype: Literal["pdf", "jpeg", "png"],
) -> ExtractedDocument:
    """Extract text or normalized vision images strictly in memory."""
    raw_sha256 = hashlib.sha256(data).hexdigest()

    if filetype == "pdf":
        try:
            doc = fitz.open(stream=io.BytesIO(data), filetype="pdf")
        except Exception as exc:
            raise UnreadableDocumentError(
                "This PDF appears corrupted or unreadable. Please upload a valid PDF or clear photo."
            ) from exc

        try:
            if doc.needs_pass:
                raise UnreadableDocumentError(
                    "This PDF is password-protected. Please upload an unlocked PDF or clear photo."
                )
            if len(doc) == 0:
                raise UnreadableDocumentError(
                    "This PDF contains no pages."
                )

            max_pages = min(len(doc), MAX_DIGITAL_PDF_PAGES)
            page_texts: list[str] = []
            for page_idx in range(max_pages):
                page_texts.append(doc[page_idx].get_text("text") or "")

            combined_text = "\n\n".join(
                f"[Page {idx + 1}]\n{txt.strip()}"
                for idx, txt in enumerate(page_texts)
                if txt.strip()
            )
            non_ws_count = len(re.sub(r"\s+", "", combined_text))

            if non_ws_count >= MIN_DIGITAL_CHARS:
                return ExtractedDocument(
                    input_type="digital_pdf",
                    raw_sha256=raw_sha256,
                    normalized_text_sha256=_normalize_text_hash(combined_text),
                    page_texts=page_texts,
                    combined_text=combined_text,
                )

            scan_pages = min(len(doc), MAX_SCAN_RENDER_PAGES)
            rendered_images: list[tuple[bytes, str]] = []
            for page_idx in range(scan_pages):
                pixmap = doc[page_idx].get_pixmap(dpi=SCAN_RENDER_DPI)
                rendered_images.append((pixmap.tobytes("png"), "image/png"))

            return ExtractedDocument(
                input_type="scanned_pdf",
                raw_sha256=raw_sha256,
                page_texts=page_texts,
                combined_text=combined_text,
                image_parts=rendered_images,
            )
        finally:
            doc.close()

    # Photo / image branch
    try:
        with Image.open(io.BytesIO(data)) as verify_img:
            verify_img.verify()
        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)
            if img.mode != "RGB":
                img = img.convert("RGB")
            longest_edge = max(img.width, img.height)
            if longest_edge > MAX_IMAGE_EDGE_PX:
                img.thumbnail(
                    (MAX_IMAGE_EDGE_PX, MAX_IMAGE_EDGE_PX),
                    Image.Resampling.LANCZOS,
                )
            phash_hex = str(imagehash.phash(img))
            out_buf = io.BytesIO()
            img.save(out_buf, format="JPEG", quality=88, optimize=True)
            normalized_bytes = out_buf.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableDocumentError(
            "Unable to decode image. Upload a valid JPEG or PNG noticeboard photo."
        ) from exc

    return ExtractedDocument(
        input_type="photo",
        raw_sha256=raw_sha256,
        phash_hex=phash_hex,
        image_parts=[(normalized_bytes, "image/jpeg")],
    )

