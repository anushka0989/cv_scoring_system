"""
parser.py
=========
Low-level extraction for the fixed "INFRACON / MoRTH — VIEW CONSULTANT
DETAILS" CV export format (the standard NHAI/highway-personnel CV format
this project now works with, per Devesh's uploaded samples).

The exported page is one continuous bordered grid per PDF page (or one
Word table, if saved as .docx). pdfplumber / python-docx return each row
as a list of cells, where:
  - `None`   = a pure layout/spanning artifact (no real cell there) —
               always safe to drop.
  - `""`     = a real table cell that is simply empty (e.g. "Enrollment
               Number" left blank) — must be KEPT so column position
               stays aligned with the header row.

`iter_grid_rows()` yields each row as a compressed list of strings
(None-cells removed, empty-string cells kept, whitespace/newlines
collapsed), in document order. cv_parser.py turns that row stream into
structured candidate data using a small state machine.

Scanned / photographed CVs
---------------------------
Some CVs arrive as image-only PDFs (a scanned or photographed document
saved as .pdf, with no real text layer). pdfplumber's `extract_tables()`
finds nothing on those pages because there is no vector/text grid to
detect. For any page where no text and no table is found, this module
falls back to OCR (Tesseract, via pytesseract):

  1. The page is rasterised to an image (via pdfplumber, no extra
     dependency needed beyond the bundled pypdfium2 backend).
  2. Tesseract's word-level output (with bounding boxes) is grouped into
     lines, and each line is split into "cells" wherever the horizontal
     gap between neighbouring words is wide enough to look like a column
     boundary rather than a word space.

This reconstructs a row stream in the same `list[str]` shape as the
born-digital path, so `cv_parser.py` needs no changes to consume it.
OCR is inherently less reliable than a real text/table layer (skewed
scans, low resolution, and merged/split columns can all cause errors),
so callers should treat OCR'd pages as lower-confidence input — pass an
`ocr_pages` list to `iter_grid_rows()` to find out which pages, if any,
were OCR'd, and surface that to the user for a quick sanity check.
"""

from __future__ import annotations

import re
import statistics
from typing import Iterator, Optional

import pdfplumber
from docx import Document

try:
    import pytesseract
    from pytesseract import Output

    OCR_AVAILABLE = True
except ImportError:  # pytesseract not installed
    OCR_AVAILABLE = False


# If Tesseract isn't on PATH (common on Windows), point pytesseract at it
# explicitly, e.g.:
#   import parser
#   parser.set_tesseract_path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
def set_tesseract_path(path: str) -> None:
    if not OCR_AVAILABLE:
        raise RuntimeError("pytesseract is not installed (pip install pytesseract).")
    pytesseract.pytesseract.tesseract_cmd = path


_WS_RE = re.compile(r"\s{2,}")
_OCR_RESOLUTION = 300          # dpi for rasterising a scanned page
_OCR_MIN_CONFIDENCE = 40       # discard low-confidence OCR words as noise
_OCR_GAP_MULTIPLIER = 2.2      # gap > this * word height => new column
_OCR_MIN_GAP_PT = 10           # ...but never less than this many PDF points
                                # (words are converted to point space so
                                # they line up with pdfplumber's own
                                # coordinates — this is NOT pixels)


def _clean_cell(value) -> str:
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    return _WS_RE.sub(" ", text)


def _compress(row) -> list[str]:
    """Drop None (layout) cells; keep '' (real empty data) cells."""
    out = []
    for cell in row:
        if cell is None:
            continue
        out.append(_clean_cell(cell))
    return out


def _page_has_text(page) -> bool:
    """True if the page has a real, selectable text layer (born-digital).

    Checked via `page.chars` rather than `extract_tables()` succeeding:
    some PDF generators draw real vector table borders (rects/lines) but
    flatten the actual text into vector outlines or a raster image with
    no embedded glyphs. In that case `extract_tables()` still finds a
    grid shape, but every cell comes back empty — so table-detection
    alone is not a safe signal that there's real text to read.
    """
    if page.chars:
        return True
    text = page.extract_text() or ""
    return len(text.strip()) >= 20


def _ocr_words(page) -> list[dict]:
    """Run Tesseract on a rasterised page and return word boxes in PDF
    point space (so they line up directly with pdfplumber's own
    coordinates, regardless of OCR resolution)."""
    if not OCR_AVAILABLE:
        raise RuntimeError(
            "This CV appears to be a scanned/image-only document. OCR "
            "support requires the 'pytesseract' package and a Tesseract "
            "OCR install — run `pip install pytesseract` and install the "
            "Tesseract engine (see README), then try again."
        )
    scale = _OCR_RESOLUTION / 72
    image = page.to_image(resolution=_OCR_RESOLUTION).original
    data = pytesseract.image_to_data(image, output_type=Output.DICT)

    words: list[dict] = []
    for i in range(len(data["text"])):
        text = data["text"][i].strip()
        if not text:
            continue
        try:
            conf = float(data["conf"][i])
        except (ValueError, TypeError):
            conf = -1
        if conf != -1 and conf < _OCR_MIN_CONFIDENCE:
            continue
        left = data["left"][i] / scale
        top = data["top"][i] / scale
        width = data["width"][i] / scale
        height = data["height"][i] / scale
        words.append({
            "text": text, "left": left, "top": top,
            "width": width, "height": height,
            "cx": left + width / 2, "cy": top + height / 2,
        })
    return words


def _order_multiline(words: list[dict]) -> list[dict]:
    """Order a bag of words the way a person would read them: top-to-
    bottom in visual sub-lines (tolerant of a few px of jitter, so a
    single logical cell whose text wraps across 2-3 printed lines still
    comes out in the right order), then left-to-right within each line."""
    if not words:
        return []
    words = sorted(words, key=lambda w: w["top"])
    median_h = statistics.median(w["height"] for w in words)
    tol = max(0.6 * median_h, 4)

    lines: list[list[dict]] = [[words[0]]]
    line_top = words[0]["top"]
    for w in words[1:]:
        if abs(w["top"] - line_top) <= tol:
            lines[-1].append(w)
            line_top = min(line_top, w["top"])
        else:
            lines.append([w])
            line_top = w["top"]

    ordered: list[dict] = []
    for line in lines:
        ordered.extend(sorted(line, key=lambda w: w["left"]))
    return ordered


def _gap_split(ordered: list[dict]) -> list[str]:
    """Split an already-ordered word sequence into cells wherever the
    horizontal gap looks like a column boundary rather than a word
    space."""
    if not ordered:
        return []
    median_h = statistics.median(w["height"] for w in ordered)
    gap_threshold = max(_OCR_GAP_MULTIPLIER * median_h, _OCR_MIN_GAP_PT)

    cells: list[list[dict]] = [[ordered[0]]]
    for prev_w, cur_w in zip(ordered, ordered[1:]):
        gap = cur_w["left"] - (prev_w["left"] + prev_w["width"])
        if gap > gap_threshold:
            cells.append([cur_w])
        else:
            cells[-1].append(cur_w)
    return [_clean_cell(" ".join(w["text"] for w in cell)) for cell in cells]


def _ocr_page_rows_freeform(page, words: Optional[list[dict]] = None) -> list[list[str]]:
    """OCR reconstruction with no table geometry to lean on at all (a
    genuinely flat scanned/photographed page with no vector lines):
    group words into visual lines by y-position, then split each line
    into cells by horizontal gap size."""
    if words is None:
        words = _ocr_words(page)
    if not words:
        return []

    words_sorted = sorted(words, key=lambda w: (w["top"], w["left"]))
    median_h = statistics.median(w["height"] for w in words_sorted)
    line_tol = max(0.6 * median_h, 8)

    lines: list[list[dict]] = [[words_sorted[0]]]
    line_top = words_sorted[0]["top"]
    for w in words_sorted[1:]:
        if abs(w["top"] - line_top) <= line_tol:
            lines[-1].append(w)
            line_top = min(line_top, w["top"])
        else:
            lines.append([w])
            line_top = w["top"]

    rows: list[list[str]] = []
    for line_words in lines:
        row = _gap_split(sorted(line_words, key=lambda w: w["left"]))
        if row:
            rows.append(row)
    return rows


def _ocr_page_rows(page) -> list[list[str]]:
    """OCR a single (scanned) pdfplumber page into pseudo-grid rows.

    Two strategies, depending on what's actually usable on the page:

    - If pdfplumber can detect a real vector table grid (`find_tables()`
      — common when a "print to PDF"/scan-and-flatten tool preserved the
      table's border lines but not its text), each row's real vertical
      span is used to gather all OCR'd words for that logical row —
      including ones that wrap across 2-3 printed lines within a single
      cell, which a naive line-by-line OCR read would otherwise split
      into several bogus rows. Rows with 3+ real columns then use the
      table's own column boundaries to assign words to the right column
      (reliable for genuine multi-column data grids); rows with 1-2
      columns (typical of a "label: value" layout, where the real
      column line often doesn't land exactly where the value text
      starts) fall back to splitting by horizontal gap size instead.

    - If there's no vector table grid at all (a flat scanned/photographed
      page), there's no real geometry to lean on, so the whole page is
      reconstructed by grouping words into visual lines by y-position and
      splitting each line by gap size.
    """
    words = _ocr_words(page)
    if not words:
        return []

    tables = page.find_tables()
    if not tables:
        return _ocr_page_rows_freeform(page, words=words)

    rows: list[list[str]] = []
    for table in tables:
        for table_row in table.rows:
            real_cells = [c for c in table_row.cells if c is not None]
            if not real_cells:
                continue
            row_top = min(c[1] for c in real_cells)
            row_bottom = max(c[3] for c in real_cells)
            row_words = [w for w in words if row_top - 1 <= w["cy"] <= row_bottom + 1]
            if not row_words:
                continue

            if len(real_cells) <= 2:
                row = _gap_split(_order_multiline(row_words))
            else:
                row = []
                for x0, _top, x1, _bottom in real_cells:
                    cell_words = [w for w in row_words if x0 - 1 <= w["cx"] <= x1 + 1]
                    ordered = _order_multiline(cell_words)
                    row.append(_clean_cell(" ".join(w["text"] for w in ordered)))
            if row:
                rows.append(row)
    return rows


def _iter_pdf_rows(file_path: str, ocr_pages: Optional[list[int]] = None) -> Iterator[list[str]]:
    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            if _page_has_text(page):
                for table in page.extract_tables():
                    for row in table:
                        compressed = _compress(row)
                        if compressed:
                            yield compressed
                continue

            # No real text layer — even if pdfplumber's line/rect detection
            # thinks it sees a table (vector-drawn borders around image or
            # outlined text are common), there's nothing to read from it.
            # Fall back to OCR instead of trusting an empty "table".
            if ocr_pages is not None:
                ocr_pages.append(page_num)
            for row in _ocr_page_rows(page):
                yield row


def _iter_docx_rows(file_path: str) -> Iterator[list[str]]:
    doc = Document(file_path)
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text for cell in row.cells]
            compressed = _compress(cells)
            if compressed:
                yield compressed


def iter_grid_rows(file_path: str, ocr_pages: Optional[list[int]] = None) -> Iterator[list[str]]:
    """Yield compressed rows from a fixed-format CV file (.pdf or .docx),
    in document order.

    If `ocr_pages` is passed (an empty list), it is populated in-place
    with the 1-indexed page numbers that had no text/table layer and had
    to be read via OCR, so callers can warn the user to double-check
    those pages.
    """
    lower = file_path.lower()
    if lower.endswith(".pdf"):
        yield from _iter_pdf_rows(file_path, ocr_pages=ocr_pages)
    elif lower.endswith(".docx"):
        yield from _iter_docx_rows(file_path)
    else:
        raise ValueError(
            f"Unsupported file type: {file_path}. Only .pdf and .docx are supported."
        )


def extract_text(file_path: str) -> str:
    """Plain-text dump of the grid (kept for debugging / display only —
    structured parsing should always go through iter_grid_rows)."""
    lines = []
    for row in iter_grid_rows(file_path):
        lines.append(" | ".join(row))
    return "\n".join(lines)
