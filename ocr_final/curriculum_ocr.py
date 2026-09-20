#!/usr/bin/env python3
"""
Curriculum OCR (P2)
====================
Extracts Thai/English text from university curriculum PDFs and images,
parses out structured course entities (Course Code, Course Name TH/EN,
Credits, Prerequisites), and stores everything in an SQLite database
(`curriculum.db`) designed to later back a RAG pipeline.

Pipeline:
    PDF/Image --> render pages to images (PyMuPDF) --> OCR (EasyOCR, th+en)
              --> entity parsing (regex) --> SQLite storage
              --> search helpers for RAG retrieval

--------------------------------------------------------------------
INSTALLATION
--------------------------------------------------------------------
    pip install easyocr PyMuPDF Pillow numpy

Notes:
- EasyOCR is chosen over pytesseract because it ships a Thai model
  (`th`) that you install with a single pip package -- no need to
  separately install the Tesseract binary + `tha.traineddata` language
  pack, which is a common source of setup pain, especially on Windows
  or in a container. EasyOCR also tends to handle mixed Thai/English
  lines (very common in curriculum docs, e.g. "องค์ประกอบคอมพิวเตอร์
  (Computer Organization)") more gracefully out of the box.
- PyMuPDF (`fitz`) is used to rasterize PDF pages to images. It's a
  pure pip-installable wheel (no external `poppler` binary needed,
  unlike `pdf2image`), which keeps deployment simple.
- First run will download EasyOCR's th/en model weights (~200MB),
  which requires internet access once. After that it's fully offline.
- If you later find EasyOCR too slow for a large batch of scanned
  documents, an LLM-vision OCR approach (e.g. sending page images to
  a multimodal model and asking for structured JSON output) can beat
  classic OCR on messy tables/columns, at the cost of API calls and
  latency. Worth considering for the hardest documents but treat
  EasyOCR as the free/local baseline for the whole corpus.
--------------------------------------------------------------------
USAGE
--------------------------------------------------------------------
    # Ingest every PDF/image in a folder into curriculum.db
    python curriculum_ocr.py ingest ./curriculum_docs

    # Ingest a single file
    python curriculum_ocr.py ingest ./curriculum_docs/CS_curriculum.pdf

    # Search
    python curriculum_ocr.py search "01418111"
    python curriculum_ocr.py search "Database"
"""

from __future__ import annotations

import argparse
import gc
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

# --------------------------------------------------------------------------
# Third-party deps -- imported lazily-ish with a friendly error if missing,
# since OCR isn't needed for search-only invocations.
# --------------------------------------------------------------------------
try:
    import numpy as np
except ImportError:
    np = None

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import easyocr
except ImportError:
    easyocr = None

try:
    import cv2
except ImportError:
    cv2 = None

# curriculum_engine.py is a local module (not a pip package) -- must sit
# next to this file or be on PYTHONPATH. Imported lazily like the OCR
# deps above: `search`-only usage and unit tests on parse_course_block()
# should keep working even if it's missing, just without synthetic slot
# codes / ambiguous-credit flags (parse_course_block falls back to the
# old regex-only behavior in that case -- see its docstring).
try:
    from curriculum_engine import (
        CodeRule,
        CodeRuleRegistry,
        CreditParseError,
        CreditParser,
        ValidationFlag,
    )
except ImportError:
    CodeRule = CodeRuleRegistry = CreditParser = ValidationFlag = None
    CreditParseError = Exception
    logging.getLogger("curriculum_ocr").warning(
        "curriculum_engine.py not found -- falling back to legacy "
        "regex-only code/credit parsing (no wildcard slot codes, no "
        "ValidationFlag diagnostics). Put curriculum_engine.py next to "
        "this file to enable it."
    )


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------
DB_PATH = Path("curriculum.db")
SUPPORTED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
SUPPORTED_PDF_EXT = {".pdf"}
PDF_RENDER_DPI = 400  # higher DPI = better OCR accuracy but MUCH more RAM per page.
MAX_IMAGE_DIMENSION = 4800  # downscale any page wider/taller than this (pixels).
                             # Note: an A4 page at 400 DPI is ~4700px tall, so this
                             # cap must stay above that or it silently undoes the
                             # DPI increase. Raise further only if you push DPI higher.

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("curriculum_ocr")


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------
@dataclass
class CourseRecord:
    """Structured representation of one parsed course entry."""
    course_code: Optional[str] = None
    course_name_en: Optional[str] = None
    course_name_th: Optional[str] = None
    credits: Optional[str] = None
    credit_lecture_h: Optional[int] = None
    credit_lab_h: Optional[int] = None
    credit_self_h: Optional[int] = None
    prerequisites: Optional[str] = None
    raw_text: str = ""
    source_file: str = ""
    page_number: int = 0
    extracted_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    # Diagnostic flags from CodeRuleRegistry/CreditParser (curriculum_engine),
    # e.g. "SYNTHETIC_CODE_ASSIGNED", "CREDIT_AMBIGUOUS". Empty when the
    # engine wasn't available or nothing was flagged for this record.
    flags: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# 1. OCR EXTRACTION
# --------------------------------------------------------------------------
class OCREngine:
    """
    Thin wrapper around EasyOCR configured for Thai + English.
    Lazily initialized because loading the model is slow (~seconds)
    and unnecessary for non-OCR commands (e.g. `search`).
    """

    _reader = None  # class-level cache so we only load the model once

    @classmethod
    def get_reader(cls):
        if cls._reader is None:
            if easyocr is None:
                raise RuntimeError(
                    "easyocr is not installed. Run: pip install easyocr"
                )

            use_gpu = cls._resolve_gpu_flag()
            logger.info(
                f"Loading EasyOCR model (th + en) on {'GPU' if use_gpu else 'CPU'}... "
                f"this can take a while on first run."
            )
            try:
                cls._reader = easyocr.Reader(["th", "en"], gpu=use_gpu)
            except Exception as exc:
                if use_gpu:
                    # GPU init can fail for reasons that only show up at model-load
                    # time (e.g. a CUDA build that doesn't yet support a brand-new
                    # GPU's compute capability). Don't take down the whole run --
                    # fall back to CPU instead.
                    logger.warning(f"GPU load failed ({exc}); falling back to CPU.")
                    cls._reader = easyocr.Reader(["th", "en"], gpu=False)
                else:
                    raise
        return cls._reader

    @staticmethod
    def _resolve_gpu_flag() -> bool:
        """
        Use CUDA if it's actually available; otherwise fall back to CPU
        with a clear log message instead of EasyOCR silently doing it.
        """
        try:
            import torch
            if torch.cuda.is_available():
                logger.info(f"CUDA GPU detected: {torch.cuda.get_device_name(0)}")
                return True
            logger.warning(
                "GPU requested but torch.cuda.is_available() is False "
                "(no CUDA-enabled torch build, or driver/CUDA mismatch). Using CPU."
            )
            return False
        except ImportError:
            logger.warning("torch not installed; using CPU. Run: pip install torch")
            return False

    @classmethod
    def ocr_image(cls, image) -> str:
        """
        Run OCR on a single image (PIL.Image or numpy array) and return
        the extracted text, roughly preserving reading order top-to-bottom.
        """
        reader = cls.get_reader()
        arr = np.array(image) if (Image is not None and isinstance(image, Image.Image)) else image

        results = reader.readtext(arr, detail=1, paragraph=False)
        # results: list of (bbox, text, confidence). Sort by vertical position
        # (top y-coordinate) then horizontal, to approximate natural reading order.
        results.sort(key=lambda r: (round(r[0][0][1] / 10), r[0][0][0]))
        lines = [text for (_bbox, text, _conf) in results]

        # Drop the large intermediates explicitly rather than waiting for the
        # next garbage-collection cycle -- readtext() internally allocates
        # several intermediate arrays/tensors that we don't need anymore.
        del arr, results
        return "\n".join(lines)


def _downscale_if_needed(img, max_dim: int = MAX_IMAGE_DIMENSION):
    """
    Cap a PIL image's largest dimension. A single unnecessarily huge page
    (e.g. a scanner default of 600 DPI) can use 5-10x the RAM of a
    reasonably-sized one for no OCR-accuracy benefit, so this is a cheap
    safety net regardless of what DPI the page was rendered/scanned at.
    """
    if max(img.size) <= max_dim:
        return img
    scale = max_dim / max(img.size)
    new_size = (int(img.width * scale), int(img.height * scale))
    resized = img.resize(new_size, Image.LANCZOS)
    img.close()  # release the original's memory immediately
    return resized


# --------------------------------------------------------------------------
# Image preprocessing -- cleans up the page BEFORE OCR ever sees it.
# Rendering at a higher DPI only gives you a bigger image; it does nothing
# about low contrast, scanner noise, or a slightly skewed page, which are
# the actual cause of garbled OCR output like "phacilce" instead of
# "practice". This step targets those problems directly.
# --------------------------------------------------------------------------
def preprocess_image(img, enable: bool = True):
    """
    Clean up a page image before OCR: grayscale -> denoise -> deskew ->
    contrast boost (CLAHE) -> mild sharpen. Returns a PIL.Image.

    Deliberately conservative: this does NOT binarize (hard black/white
    threshold). Binarization can look cleaner to the eye but tends to hurt
    EasyOCR's accuracy on Thai script, where strokes are thin and glyphs
    are complex -- thresholding can clip details the model relies on.
    Grayscale + contrast + denoise is a safer default; feel free to add a
    thresholding step yourself if you find it helps on a specific document.

    Falls back to returning the original image untouched if cv2 isn't
    installed, or if anything about a specific page fails -- preprocessing
    should never be the reason a whole ingest run crashes.
    """
    if not enable or cv2 is None or np is None:
        return img

    try:
        arr = np.array(img)  # RGB
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        # 1. Denoise -- removes scanner speckle/grain without blurring text
        #    edges much, using a mild strength so thin Thai strokes survive.
        gray = cv2.fastNlMeansDenoising(gray, h=7, templateWindowSize=7, searchWindowSize=21)

        # 2. Deskew -- estimate the page's rotation from the text mass and
        #    correct it. A page just 1-2 degrees off can noticeably hurt
        #    line-detection and reading order.
        gray = _deskew(gray)

        # 3. Contrast boost (CLAHE) -- adaptive, local contrast enhancement.
        #    Works much better than a flat contrast stretch on scans with
        #    uneven lighting/shadowing across the page.
        clahe = cv2.createCLAHE(clipLimit = 3.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

        # 4. Mild sharpen (unsharp mask) -- crisps up character edges that
        #    denoising may have softened slightly.
        blurred = cv2.GaussianBlur(gray, (0, 0), sigmaX=1.0)
        gray = cv2.addWeighted(gray, 1.5, blurred, -0.5, 0)

        rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        return Image.fromarray(rgb)

    except Exception as exc:
        logger.warning(f"Preprocessing failed on a page, using original image instead: {exc}")
        return img


def _deskew(gray_arr):
    """
    Estimate and correct small rotational skew using the minimum-area
    bounding rectangle of dark (text) pixels. Only corrects small angles
    (<15 degrees) -- a bigger detected "skew" is more likely a mostly-blank
    page or a false read, so it's left alone rather than risking a bad
    rotation.
    """
    try:
        # Invert + threshold so text pixels are the "foreground" (white)
        thresh = cv2.threshold(gray_arr, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        coords = cv2.findNonZero(thresh)
        if coords is None or len(coords) < 50:
            return gray_arr  # not enough text detected to estimate skew reliably

        angle = cv2.minAreaRect(coords)[-1]
        # cv2.minAreaRect's angle convention needs normalizing to a
        # human-meaningful rotation in the range [-45, 45).
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.1 or abs(angle) > 15:
            return gray_arr  # negligible skew, or an unreliable large estimate

        (h, w) = gray_arr.shape
        center = (w // 2, h // 2)
        rot_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            gray_arr, rot_matrix, (w, h),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
        )
    except Exception:
        return gray_arr


def iter_pdf_pages(pdf_path: Path, dpi: int = PDF_RENDER_DPI, preprocess: bool = True):
    """
    Yield (page_number, PIL.Image) one page at a time instead of rendering
    the whole PDF into a list up front. This is the single biggest memory
    saver for multi-page curriculum PDFs -- previously every page's
    full-resolution bitmap was held in RAM simultaneously before OCR even
    started. Each page is only rendered right before it's consumed, and the
    caller is expected to discard/close it once OCR on that page is done.
    """
    if fitz is None:
        raise RuntimeError("PyMuPDF is not installed. Run: pip install PyMuPDF")
    if Image is None:
        raise RuntimeError("Pillow is not installed. Run: pip install Pillow")

    zoom = dpi / 72  # PDF default resolution is 72 dpi
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(pdf_path) as doc:
        page_count = doc.page_count
        for i in range(page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            img = _downscale_if_needed(img)
            img = preprocess_image(img, enable=preprocess)
            yield i + 1, page_count, img
            # Explicitly release the PyMuPDF pixmap/page before moving on --
            # these hold raw bitmap buffers that Python's GC doesn't always
            # reclaim promptly on its own.
            pix = None
            page = None


def extract_text_from_file(
    file_path: Path, dpi: int = PDF_RENDER_DPI, preprocess: bool = True
) -> list[tuple[int, str]]:
    """
    Extract OCR text from a PDF or image file, one page at a time, so
    memory use stays roughly constant regardless of how many pages the
    document has (instead of scaling with page count).
    Returns a list of (page_number, raw_text) tuples -- page_number is
    always 1 for plain images.
    """
    ext = file_path.suffix.lower()
    pages_text: list[tuple[int, str]] = []

    try:
        if ext in SUPPORTED_PDF_EXT:
            logger.info(f"Rendering + OCR-ing PDF pages one at a time: {file_path.name}")
            for page_num, page_count, img in iter_pdf_pages(file_path, dpi=dpi, preprocess=preprocess):
                logger.info(f"  OCR page {page_num}/{page_count}")
                text = OCREngine.ocr_image(img)
                pages_text.append((page_num, text))

                # Free this page's image before rendering the next one, and
                # nudge garbage collection every few pages -- EasyOCR/torch
                # can leave sizeable temporary buffers around otherwise.
                img.close()
                del img
                if page_num % 5 == 0:
                    gc.collect()

        elif ext in SUPPORTED_IMAGE_EXT:
            logger.info(f"OCR image: {file_path.name}")
            img = Image.open(file_path).convert("RGB")
            img = _downscale_if_needed(img)
            img = preprocess_image(img, enable=preprocess)
            text = OCREngine.ocr_image(img)
            pages_text.append((1, text))
            img.close()
            del img

        else:
            logger.warning(f"Unsupported file type, skipping: {file_path}")

    except Exception as exc:
        # Never let a single bad file crash a batch ingest job
        logger.error(f"Failed to OCR {file_path.name}: {exc}")

    finally:
        gc.collect()

    return pages_text


# --------------------------------------------------------------------------
# 2. TEXT CLEANING & ENTITY STRUCTURING
# --------------------------------------------------------------------------
# Thai university course codes are typically all-digit (e.g. 01418111) or
# an alpha prefix + digits (e.g. "CS101", "SC123456"). Adjust the pattern
# below to match your institution's actual code format.
COURSE_CODE_RE = re.compile(r"\b(\d{5,8}|[A-Z]{2,6}\d{3,6})\b")

# Stricter variant used only to decide block *boundaries*: a course code
# is expected to sit at the START of its row/line in most curriculum
# layouts. Using the looser COURSE_CODE_RE for splitting would wrongly
# treat digits inside a "Prerequisite: 01418112" line as a new course.
COURSE_CODE_LINE_START_RE = re.compile(r"^\s*(\d{5,8}|[A-Z]{2,6}\d{3,6})\b")

# Broader than COURSE_CODE_RE: also catches wildcard elective-slot
# placeholders that sometimes survive OCR verbatim as printed text (e.g.
# "06026xxx", "9064xxxx" in a curriculum book's plan table). Used only to
# decide whether a block contains *something* code-shaped worth routing
# through the resolver -- NOT for splitting, and NOT for the final code
# value (that still comes from CodeRuleRegistry.resolve()).
CODE_CANDIDATE_RE = re.compile(
    r"\b(\d{5,8}|[A-Z]{2,6}\d{3,6}|\d{2,6}[xX]{2,8}\d{0,3})\b"
)


def ocr_code_registry() -> "CodeRuleRegistry":
    """
    Code-resolution rules for this pipeline's OCR text -- mirrors what
    COURSE_CODE_RE matched ad hoc before (5-8 digit codes, or a short
    alpha prefix + digits), now routed through the shared
    CodeRuleRegistry so malformed/wildcard tokens get an explicit
    ValidationFlag and a synthetic ELEC-... slot code instead of
    silently becoming course_code=None.

    Build ONE of these per document (see process_document) and thread it
    through every block -- the registry's slot counters must persist
    across the whole document so repeated wildcard patterns (the same
    "06026xxx" appearing at several different points in a plan table)
    get distinct synthetic codes instead of colliding.
    """
    reg = CodeRuleRegistry()
    reg.register(CodeRule(name="digit_code", pattern=re.compile(r"\d{5,8}"), kind="real"))
    reg.register(CodeRule(name="alpha_digit_code",
                           pattern=re.compile(r"[A-Z]{2,6}\d{3,6}"), kind="real"))
    return reg

# Credit formats commonly seen: "3(3-0-6)", "3 หน่วยกิต", "Credits: 3"
CREDITS_RE = re.compile(
    r"(\d\s?\(\s?\d\s?-\s?\d\s?-\s?\d\s?\))"      # e.g. 3(3-0-6)
    r"|(\d+\s*หน่วยกิต)"                            # e.g. 3 หน่วยกิต
    r"|(?:credits?\s*[:\-]?\s*(\d+))",              # e.g. Credits: 3
    re.IGNORECASE,
)

# Prerequisite lines, TH or EN
PREREQ_RE = re.compile(
    r"(?:วิชาบังคับก่อน|Pre-?requisite[s]?)\s*[:\-]?\s*(.+)",
    re.IGNORECASE,
)

# A Thai course-name line usually contains Thai script; an English name
# line is mostly Latin letters. Used to split a "TH (EN)" combined line.
THAI_CHARS_RE = re.compile(r"[\u0E00-\u0E7F]")


def clean_text(raw_text: str) -> str:
    """Basic normalization: strip stray whitespace, collapse blank lines."""
    lines = [ln.strip() for ln in raw_text.splitlines()]
    lines = [ln for ln in lines if ln]  # drop empty lines
    return "\n".join(lines)


def parse_course_block(
    block_text: str,
    source_file: str,
    page_number: int,
    registry: "CodeRuleRegistry | None" = None,
    credit_parser: "CreditParser | None" = None,
) -> CourseRecord:
    """
    Given a chunk of OCR text believed to describe ONE course entry,
    extract structured fields with regex heuristics. Falls back to
    None for any field it can't confidently find -- callers can still
    keep raw_text for full-text / RAG search even if structured
    extraction is incomplete.

    When `registry`/`credit_parser` are supplied (see ocr_code_registry()
    and curriculum_engine.CreditParser), code and credit extraction go
    through the shared resolver instead of raw regex-only matching:
      - a wildcard/malformed code token (e.g. "06026xxx") gets a
        synthetic ELEC-... slot code instead of becoming course_code=None
      - "3(3-0-6) หรือ 3(2-2-5)"-style ambiguous credits get the first
        option plus a CREDIT_AMBIGUOUS flag, instead of one regex group
        picked with no record that an alternative existed
      - every anomaly is recorded on `record.flags` for diagnostics,
        rather than silently disappearing
    Passing neither reproduces the exact previous (pre-engine) behavior,
    so this function still works standalone if curriculum_engine.py
    isn't available.
    """
    text = clean_text(block_text)
    record = CourseRecord(raw_text=text, source_file=source_file, page_number=page_number)

    # --- Course code ---
    # CODE_CANDIDATE_RE (superset of COURSE_CODE_RE, also matches wildcard
    # placeholders) decides whether this block has *anything* code-shaped
    # worth resolving. A block with no code-like token at all (e.g. a
    # stray heading/footer line) is left with course_code=None exactly as
    # before -- we don't mint a synthetic code for text that was never
    # claiming to be a course in the first place.
    candidate_match = CODE_CANDIDATE_RE.search(text)
    if candidate_match and registry is not None:
        resolved_code, flag = registry.resolve(candidate_match.group(0))
        record.course_code = resolved_code
        if flag is not None:
            record.flags.append(flag.value)
    elif candidate_match:
        # Legacy path: no registry supplied, reproduce old strict matching
        # (COURSE_CODE_RE, not the broader wildcard-aware candidate regex).
        code_match = COURSE_CODE_RE.search(text)
        record.course_code = code_match.group(0) if code_match else None
    # else: no code-like token found at all -> course_code stays None.

    # --- Credits ---
    if registry is not None and credit_parser is not None:
        # Only attempt structured credit parsing on blocks we believe are
        # actually course entries (i.e. a code-like token was found) --
        # otherwise every non-course paragraph would get flagged as
        # "credit unparsable" for simply not mentioning credits.
        #
        # Pass the whole block `text`, not a CREDITS_RE.search() extract:
        # CREDITS_RE's first alternative matches only "3(3-0-6)" and stops
        # there, silently truncating "3(3-0-6) หรือ 3(2-2-5)" before the
        # "หรือ" -- so CreditParser would never see the second option and
        # CREDIT_AMBIGUOUS could never fire. CreditParser does its own
        # internal search per alt-split chunk, so it can safely take the
        # full block and find the credit expression(s) wherever they are.
        if candidate_match:
            try:
                spec = credit_parser.parse(text)
                record.credits = str(spec.total)
                record.credit_lecture_h = spec.lecture
                record.credit_lab_h = spec.lab
                record.credit_self_h = spec.self_study
                if spec.ambiguous:
                    record.flags.append(ValidationFlag.CREDIT_AMBIGUOUS.value)
            except CreditParseError:
                record.flags.append(ValidationFlag.CREDIT_UNPARSABLE.value)
    else:
        credits_match = CREDITS_RE.search(text)
        if credits_match:
            record.credits = next(g for g in credits_match.groups() if g)

    # --- Prerequisites ---
    prereq_match = PREREQ_RE.search(text)
    if prereq_match:
        record.prerequisites = prereq_match.group(1).strip()

    # --- Course name (TH / EN) ---
    # Heuristic: look for a "Thai text (English text)" pattern on one line,
    # common in Thai curriculum tables, e.g.:
    #   "โครงสร้างข้อมูลและอัลกอริทึม (Data Structures and Algorithms)"
    name_line_match = re.search(r"([^\n(]{3,80})\(([^)]{3,80})\)", text)
    if name_line_match:
        part_a, part_b = name_line_match.group(1).strip(), name_line_match.group(2).strip()
        # Strip a leading course code (and separating whitespace) that often
        # prefixes the Thai name on the same OCR line, e.g. "01418111 โครงสร้าง..."
        part_a = COURSE_CODE_LINE_START_RE.sub("", part_a).strip()
        if THAI_CHARS_RE.search(part_a):
            record.course_name_th, record.course_name_en = part_a, part_b
        elif THAI_CHARS_RE.search(part_b):
            record.course_name_en, record.course_name_th = part_a, part_b
        else:
            record.course_name_en = part_a
    else:
        # Fallback: grab first Thai-containing line and first mostly-Latin line
        for ln in text.splitlines():
            if THAI_CHARS_RE.search(ln) and not record.course_name_th:
                record.course_name_th = ln.strip()
            elif re.search(r"[A-Za-z]{3,}", ln) and not record.course_name_en:
                record.course_name_en = ln.strip()

    return record


def split_into_course_blocks(full_text: str) -> list[str]:
    """
    Splits a page's full OCR text into per-course chunks, using the
    presence of a course-code-looking token as the split boundary.
    This is a heuristic and should be tuned to your document's layout
    (e.g. some curricula list one course per table row, others per
    paragraph).
    """
    lines = clean_text(full_text).splitlines()
    blocks: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if COURSE_CODE_LINE_START_RE.match(line) and current:
            blocks.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append(current)

    return ["\n".join(b) for b in blocks if b]


# --------------------------------------------------------------------------
# 3. SQLITE INTEGRATION
# --------------------------------------------------------------------------
def init_db(db_path: Path = DB_PATH) -> None:
    """Create the database schema if it doesn't already exist."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS courses (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                course_code       TEXT,
                course_name_en    TEXT,
                course_name_th    TEXT,
                credits           TEXT,
                credit_lecture_h  INTEGER,
                credit_lab_h      INTEGER,
                credit_self_h     INTEGER,
                prerequisites     TEXT,
                raw_text          TEXT NOT NULL,
                source_file       TEXT,
                page_number       INTEGER,
                extracted_at      TEXT,
                flags             TEXT
            )
            """
        )
        # Indices for fast lookup -- the RAG layer will typically query
        # by course_code or do a LIKE search on the names.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_course_code ON courses(course_code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_course_name_en ON courses(course_name_en)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_course_name_th ON courses(course_name_th)")

        # Migration: a curriculum.db created by an older version of this
        # script won't have these columns -- CREATE TABLE IF NOT EXISTS
        # above is a no-op on an already-existing table, so without this
        # step insert_courses() would fail with "no such column" the
        # first time it runs against an old database.
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(courses)")}
        for col, coltype in (
            ("credit_lecture_h", "INTEGER"),
            ("credit_lab_h", "INTEGER"),
            ("credit_self_h", "INTEGER"),
            ("flags", "TEXT"),
        ):
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE courses ADD COLUMN {col} {coltype}")
                logger.info(f"Migrated existing database: added column '{col}'")

        # Full-text search virtual table -- much faster than LIKE '%...%'
        # for free-text RAG-style retrieval over raw_text.
        conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS courses_fts USING fts5(
                course_code, course_name_en, course_name_th, raw_text,
                content='courses', content_rowid='id'
            )
            """
        )
        # Keep the FTS index in sync with the main table automatically.
        conn.executescript(
            """
            CREATE TRIGGER IF NOT EXISTS courses_ai AFTER INSERT ON courses BEGIN
              INSERT INTO courses_fts(rowid, course_code, course_name_en, course_name_th, raw_text)
              VALUES (new.id, new.course_code, new.course_name_en, new.course_name_th, new.raw_text);
            END;
            CREATE TRIGGER IF NOT EXISTS courses_ad AFTER DELETE ON courses BEGIN
              INSERT INTO courses_fts(courses_fts, rowid, course_code, course_name_en, course_name_th, raw_text)
              VALUES ('delete', old.id, old.course_code, old.course_name_en, old.course_name_th, old.raw_text);
            END;
            CREATE TRIGGER IF NOT EXISTS courses_au AFTER UPDATE ON courses BEGIN
              INSERT INTO courses_fts(courses_fts, rowid, course_code, course_name_en, course_name_th, raw_text)
              VALUES ('delete', old.id, old.course_code, old.course_name_en, old.course_name_th, old.raw_text);
              INSERT INTO courses_fts(rowid, course_code, course_name_en, course_name_th, raw_text)
              VALUES (new.id, new.course_code, new.course_name_en, new.course_name_th, new.raw_text);
            END;
            """
        )
        conn.commit()
    logger.info(f"Database ready at {db_path.resolve()}")


def delete_by_source_file(source_file: str, db_path: Path = DB_PATH) -> int:
    """
    Remove all existing rows for a given source_file. Used before
    re-ingesting the same document so re-running `ingest` (e.g. after
    changing --dpi) replaces that file's data instead of appending a
    second copy of it on top of the first.
    """
    with sqlite3.connect(db_path) as conn:
        cur = conn.execute("DELETE FROM courses WHERE source_file = ?", (source_file,))
        conn.commit()
        return cur.rowcount


def insert_courses(records: Iterable[CourseRecord], db_path: Path = DB_PATH) -> int:
    """
    Bulk-insert parsed course records efficiently using executemany
    inside a single transaction. Returns the number of rows inserted.
    """
    rows = [
        (
            r.course_code,
            r.course_name_en,
            r.course_name_th,
            r.credits,
            r.credit_lecture_h,
            r.credit_lab_h,
            r.credit_self_h,
            r.prerequisites,
            r.raw_text,
            r.source_file,
            r.page_number,
            r.extracted_at,
            ",".join(r.flags) if r.flags else None,
        )
        for r in records
    ]
    if not rows:
        return 0

    try:
        with sqlite3.connect(db_path) as conn:
            conn.executemany(
                """
                INSERT INTO courses (
                    course_code, course_name_en, course_name_th,
                    credits, credit_lecture_h, credit_lab_h, credit_self_h,
                    prerequisites, raw_text, source_file,
                    page_number, extracted_at, flags
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()
        logger.info(f"Inserted {len(rows)} course record(s) into {db_path.name}")
        return len(rows)
    except sqlite3.Error as exc:
        logger.error(f"Database insert failed: {exc}")
        return 0


def search_courses(query: str, db_path: Path = DB_PATH, limit: int = 20) -> list[dict]:
    """
    Search for courses by code or name. Tries an exact/prefix match on
    course_code first (fast, indexed), then falls back to full-text
    search across names and raw OCR text (useful for RAG retrieval,
    e.g. "find courses about databases").
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        # 1. Exact or prefix match on course_code
        rows = conn.execute(
            "SELECT * FROM courses WHERE course_code LIKE ? LIMIT ?",
            (f"{query}%", limit),
        ).fetchall()

        # 2. Fall back to full-text search over names + raw OCR text
        if not rows:
            try:
                rows = conn.execute(
                    """
                    SELECT courses.* FROM courses
                    JOIN courses_fts ON courses.id = courses_fts.rowid
                    WHERE courses_fts MATCH ?
                    LIMIT ?
                    """,
                    (query, limit),
                ).fetchall()
            except sqlite3.OperationalError:
                # FTS query syntax error (e.g. special characters) --
                # fall back to a plain LIKE search as a last resort.
                like_query = f"%{query}%"
                rows = conn.execute(
                    """
                    SELECT * FROM courses
                    WHERE course_name_en LIKE ? OR course_name_th LIKE ?
                    LIMIT ?
                    """,
                    (like_query, like_query, limit),
                ).fetchall()

        return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# 4. PIPELINE ORCHESTRATION
# --------------------------------------------------------------------------
def process_document(file_path: Path, dpi: int = PDF_RENDER_DPI, preprocess: bool = True) -> list[CourseRecord]:
    """Full pipeline for one document: OCR -> split -> parse into records."""
    pages = extract_text_from_file(file_path, dpi=dpi, preprocess=preprocess)
    all_records: list[CourseRecord] = []

    # One registry per DOCUMENT, not per block/page: its slot counters must
    # persist across the whole file so a wildcard pattern recurring at
    # several different points (e.g. "06026xxx" appearing four separate
    # times across a plan table) gets four distinct synthetic codes
    # instead of colliding on the first one minted.
    registry = ocr_code_registry() if CodeRuleRegistry is not None else None
    credit_parser = CreditParser() if CreditParser is not None else None

    for page_number, raw_text in pages:
        if not raw_text.strip():
            logger.warning(f"No text extracted from {file_path.name} page {page_number}")
            continue

        blocks = split_into_course_blocks(raw_text)
        for block in blocks:
            record = parse_course_block(
                block, source_file=file_path.name, page_number=page_number,
                registry=registry, credit_parser=credit_parser,
            )
            all_records.append(record)

    return all_records


def summarize_flags(records: Iterable[CourseRecord]) -> dict[str, int]:
    """
    Catalog-level diagnostic summary: counts of each ValidationFlag seen
    across a batch of records, plus how many records got no code at all.

    This is deliberately NOT the same thing as curriculum_engine's
    ReconciliationEngine report -- this pipeline never extracts
    year/semester, so there is no study-plan structure here to check a
    declared total-credits figure against (that's what lab7b/lab8b's
    table-structured extraction is for). What this *can* tell you: how
    many entries needed a synthetic slot code, how many credit strings
    were ambiguous or unparsable, and how many blocks had no code-like
    token at all (likely non-course text that slipped through the block
    splitter).
    """
    counts: dict[str, int] = {}
    no_code = 0
    for r in records:
        if r.course_code is None:
            no_code += 1
        for f in r.flags:
            counts[f] = counts.get(f, 0) + 1
    counts["NO_CODE_TOKEN_FOUND"] = no_code
    return counts


def ingest_path(
    input_path: Path,
    db_path: Path = DB_PATH,
    dpi: int = PDF_RENDER_DPI,
    replace: bool = True,
    preprocess: bool = True,
) -> None:
    """
    Ingest a single file or every supported file in a directory.
    Errors on individual files are logged and skipped so a batch job
    can complete even if one document is corrupted or unreadable.
    Results are inserted into SQLite file-by-file (not accumulated for
    the whole batch) and memory is explicitly reclaimed between files,
    so a large folder of PDFs doesn't grow RAM usage over time.

    replace=True (default): before ingesting a file, any existing rows
    for that exact source filename are deleted first. This makes
    re-running `ingest` on the same file (e.g. after tuning --dpi)
    idempotent instead of silently duplicating that file's data on
    every run.
    """
    init_db(db_path)

    if input_path.is_dir():
        files = [
            p for p in sorted(input_path.iterdir())
            if p.suffix.lower() in (SUPPORTED_PDF_EXT | SUPPORTED_IMAGE_EXT)
        ]
    elif input_path.is_file():
        files = [input_path]
    else:
        logger.error(f"Path not found: {input_path}")
        return

    if not files:
        logger.warning(f"No supported PDF/image files found in {input_path}")
        return

    total_inserted = 0
    for f in files:
        logger.info(f"--- Processing {f.name} ---")
        try:
            if replace:
                removed = delete_by_source_file(f.name, db_path)
                if removed:
                    logger.info(f"Replacing {removed} existing row(s) previously ingested from {f.name}")
            records = process_document(f, dpi=dpi, preprocess=preprocess)
            summary = summarize_flags(records)
            if any(summary.values()):
                summary_str = ", ".join(f"{k}={v}" for k, v in summary.items() if v)
                logger.info(f"  diagnostics for {f.name}: {summary_str}")
            total_inserted += insert_courses(records, db_path)
        except Exception as exc:
            # Isolate failures per-file so a bad document doesn't kill the batch
            logger.error(f"Unexpected error processing {f.name}: {exc}")
        finally:
            # Release this file's records/images before starting the next one.
            gc.collect()

    logger.info(f"Ingest complete. {total_inserted} record(s) inserted from {len(files)} file(s).")


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Curriculum OCR -> SQLite pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_p = subparsers.add_parser("ingest", help="OCR + parse + store a file or folder")
    ingest_p.add_argument("path", type=str, help="Path to a PDF/image file or a folder of them")
    ingest_p.add_argument("--db", type=str, default=str(DB_PATH), help="SQLite DB path")
    ingest_p.add_argument(
        "--dpi", type=int, default=PDF_RENDER_DPI,
        help=f"PDF render resolution (default {PDF_RENDER_DPI}). Lower = less RAM & faster, "
             f"at some cost to OCR accuracy on small text.",
    )
    ingest_p.add_argument(
        "--append", action="store_true",
        help="Append instead of replacing: keep existing rows for a file being "
             "re-ingested rather than deleting them first. Off by default -- "
             "re-running ingest on the same file normally should replace, not "
             "duplicate, its data.",
    )

    search_p = subparsers.add_parser("search", help="Search stored courses")
    search_p.add_argument("query", type=str, help="Course code or keyword to search for")
    search_p.add_argument("--db", type=str, default=str(DB_PATH), help="SQLite DB path")
    search_p.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()

    if args.command == "ingest":
        ingest_path(Path(args.path), db_path=Path(args.db), dpi=args.dpi, replace=not args.append)

    elif args.command == "search":
        db_path = Path(args.db)
        if not db_path.exists():
            logger.error(f"Database not found at {db_path}. Run `ingest` first.")
            sys.exit(1)
        results = search_courses(args.query, db_path=db_path, limit=args.limit)
        if not results:
            print(f"No matches found for '{args.query}'.")
        else:
            print(f"\nFound {len(results)} result(s) for '{args.query}':\n")
            for r in results:
                print(f"[{r['course_code'] or '?'}] {r['course_name_en'] or ''} / {r['course_name_th'] or ''}")
                print(f"   Credits: {r['credits'] or '-'}   Prerequisites: {r['prerequisites'] or '-'}")
                print(f"   Source: {r['source_file']} (page {r['page_number']})")
                print("-" * 60)


if __name__ == "__main__":
    main()
