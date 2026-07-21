"""
cv_parser.py
============
Structured parser for the fixed INFRACON / MoRTH "VIEW CONSULTANT DETAILS"
CV export format. This is NOT a general "guess any CV layout" parser —
it expects CVs in this one specific, system-generated format and reads
them by their fixed section titles / column headers, which this export
always uses verbatim (see parser.py for how the underlying grid rows are
extracted).

If a file isn't in this format, `parse_cv()` returns as much as it could
find plus a `warnings` list explaining what's missing, rather than
guessing at values.
"""

from __future__ import annotations

import difflib
import re
from datetime import date, datetime
from typing import Optional

from parser import iter_grid_rows

# ---------------------------------------------------------------------------
# Section titles (matched as a substring, case-insensitive, against a
# row that compresses down to a single cell)
# ---------------------------------------------------------------------------

_SECTION_MARKERS = [
    ("basic", "BASIC DETAILS"),
    ("qualification", "QUALIFICATION DETAILS"),
    ("companies", "COMPANIES DETAILS"),
    ("work", "DETAILED WORK DETAILS"),
    ("positions", "IMPORTANT POSITIONS HELD"),
]

# Basic-details label (row[0], lowercased) -> output field name
_BASIC_LABELS = {
    "name": "name",
    "dob": "dob",
    "mother name": "mother_name",
    "email": "email",
    "current state": "current_state",
    "current district": "current_district",
    "current address": "current_address",
    "current pin code / zip code": "current_pincode",
    "permanent state": "permanent_state",
    "permanent district": "permanent_district",
    "permanent address": "permanent_address",
    "permanent pin code / zip code": "permanent_pincode",
    "pan number": "pan_number",
    "passport number": "passport_number",
    "mobile": "mobile",
    "alternate mobile": "alternate_mobile",
    "landline number": "landline_number",
}

_JUNK_TAIL_RE = re.compile(
    r"\s*(View Uploaded File)?\s*\|\|?\s*Supporting Documents?.*$", re.IGNORECASE
)
_TRAILING_VIEW_RE = re.compile(r"\s*View$", re.IGNORECASE)
_NOT_UPLOADED_RE = re.compile(r"^\s*Not Uploaded\s*$", re.IGNORECASE)


def _clean_value(value: str) -> str:
    value = _JUNK_TAIL_RE.sub("", value)
    value = _TRAILING_VIEW_RE.sub("", value)
    if _NOT_UPLOADED_RE.match(value):
        return ""
    return value.strip(" :-|")


# ---------------------------------------------------------------------------
# Table header -> canonical field mapping (matched by best-effort keyword
# containment so minor wording drift in the source export doesn't break
# parsing outright)
# ---------------------------------------------------------------------------

_TABLE_FIELD_KEYWORDS = {
    "qualification": [
        ("level", "level"),
        ("qualification level", "qualification_level"),
        ("topic", "topic"),
        ("college", "college"),
        ("university", "university"),
        ("year of passing", "year_of_passing"),
        ("percentage", "percentage"),
        ("enrollment number", "enrollment_number"),
        ("certificate details", "certificate_details"),
    ],
    "companies": [
        ("sno", "sno"),
        ("company name", "company_name"),
        ("from year", "from_date"),
        ("to year", "to_date"),
    ],
    "work": [
        ("sno", "sno"),
        ("work name", "work_name"),
        ("client", "client"),
        ("designation", "designation"),
        ("project", "project_cost_cr"),
        ("start date", "start_date"),
        ("completion date", "completion_date"),
        ("country", "country"),
    ],
    "positions": [
        ("s.no", "sno"),
        ("position", "position"),
        ("from", "from_date"),
        ("to", "to_date"),
        ("details", "details"),
    ],
}


def _map_header(state: str, header_row: list[str]) -> list[Optional[str]]:
    """Map each header cell to a canonical field name using keyword
    containment (order-preserving, first match wins).

    Falls back to a fuzzy match (via difflib) when no keyword is directly
    contained in the cell text — this covers minor OCR misreads of a
    header cell (e.g. "Coilege" for "College") on scanned CVs, without
    weakening matching on clean, born-digital text.
    """
    keywords = _TABLE_FIELD_KEYWORDS[state]
    used = set()
    mapped: list[Optional[str]] = []
    for cell in header_row:
        cell_l = cell.lower()
        field = None
        for kw, name in keywords:
            if name in used:
                continue
            if kw in cell_l:
                field = name
                used.add(name)
                break
        if field is None and cell_l.strip():
            best_ratio = 0.0
            best_name = None
            for kw, name in keywords:
                if name in used:
                    continue
                ratio = difflib.SequenceMatcher(None, kw, cell_l).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_name = name
            if best_ratio >= 0.75:
                field = best_name
                used.add(best_name)
        mapped.append(field)
    return mapped


_PLACEHOLDER_ROW_RE = re.compile(r"no records? found", re.IGNORECASE)


def _row_to_record(header_fields: list[Optional[str]], row: list[str]) -> Optional[dict]:
    if len(row) == 1 and _PLACEHOLDER_ROW_RE.search(row[0]):
        return None
    record = {}
    for field, value in zip(header_fields, row):
        if field:
            record[field] = _clean_value(value)
    return record or None


# ---------------------------------------------------------------------------
# Main parse
# ---------------------------------------------------------------------------

def parse_cv(file_path: str) -> dict:
    """Parse a fixed-format CV file into structured candidate data.

    Returns a dict with: basic fields, `qualifications` (list of dict),
    `companies` (list of dict), `work_history` (list of dict),
    `positions_held` (list of dict), plus derived fields
    (`experience_years`, `latest_designation`, `all_designations`,
    `highest_qualification`, `certifications`) and a `warnings` list.
    """
    basic: dict = {}
    qualifications: list[dict] = []
    companies: list[dict] = []
    work_history: list[dict] = []
    positions_held: list[dict] = []
    warnings: list[str] = []

    state: Optional[str] = None
    header_fields: Optional[list[Optional[str]]] = None
    expect_header = False
    saw_section = {"basic": False, "qualification": False, "companies": False,
                   "work": False, "positions": False}

    ocr_pages: list[int] = []
    for row in iter_grid_rows(file_path, ocr_pages=ocr_pages):

        # ---- section-header marker anywhere in the row? ----------------
        # Normally a section title is its own standalone single-cell row.
        # But OCR reconstruction of a scanned page can occasionally bundle
        # a section banner into the same row-band as adjacent noise near a
        # page or table boundary (e.g. trailing "Supporting Documents"
        # text from the previous table). Scanning every cell (not just
        # len(row) == 1 rows) for a marker catches that case too, without
        # any real risk of a false match — these marker phrases are long,
        # specific, all-caps section titles that won't appear by chance.
        matched_marker = False
        for cell in row:
            cell_u = cell.upper()
            for key, marker in _SECTION_MARKERS:
                if marker in cell_u:
                    state = key
                    saw_section[key] = True
                    expect_header = key != "basic"
                    header_fields = None
                    matched_marker = True
                    break
            if matched_marker:
                break
        if matched_marker:
            continue

        # ---- section-header row? (compresses to one cell) -------------
        if len(row) == 1:
            # length-1 rows that aren't a known marker (banner, "Photo",
            # placeholder rows) are just noise in whatever state we're in
            if _PLACEHOLDER_ROW_RE.search(row[0]):
                continue
            if state is None:
                continue
            # fall through to table handling below only if we're expecting
            # a header/data row shaped like a single cell (rare) — usually
            # safe to just ignore
            continue

        # ---- basic details (key/value rows) ----------------------------
        if state == "basic":
            label = row[0].strip().lower()
            field = _BASIC_LABELS.get(label)
            if field:
                value = _clean_value(" ".join(row[1:]).strip())
                basic[field] = value
            continue

        # ---- table sections ---------------------------------------------
        if state in ("qualification", "companies", "work", "positions"):
            if expect_header:
                header_fields = _map_header(state, row)
                expect_header = False
                continue
            if header_fields is None:
                continue
            record = _row_to_record(header_fields, row)
            if record is None:
                continue
            if state == "qualification":
                qualifications.append(record)
            elif state == "companies":
                companies.append(record)
            elif state == "work":
                work_history.append(record)
            elif state == "positions":
                positions_held.append(record)
            continue

    for key, marker in _SECTION_MARKERS:
        if not saw_section[key]:
            warnings.append(
                f"Section '{marker}' was not found — this file may not be in "
                "the expected CV format, or that section was genuinely empty."
            )

    if not basic.get("name"):
        warnings.append("Could not find a 'Name' field — check this file's format.")

    if ocr_pages:
        pages_str = ", ".join(str(p) for p in ocr_pages)
        warnings.append(
            f"Page(s) {pages_str} had no text layer and looked like a scan, "
            "so they were read using OCR. OCR is less reliable than a native "
            "PDF/Word file — please double-check names, dates, and numbers "
            "on those pages."
        )

    result = {
        **{f: basic.get(f, "") for f in _BASIC_LABELS.values()},
        "qualifications": qualifications,
        "companies": companies,
        "work_history": work_history,
        "positions_held": positions_held,
        "warnings": warnings,
    }

    result["certifications"] = _extract_certifications(qualifications)
    cert_records = _certification_records(qualifications)
    result["certification_records"] = cert_records
    result["has_iahe_crri_training"] = _has_keyword_certification(cert_records, _IAHE_CRRI_KEYWORDS)
    result["has_software_certification"] = _has_keyword_certification(cert_records, _SOFTWARE_CERT_KEYWORDS)
    result["highest_qualification"] = _highest_qualification(qualifications)
    result["all_designations"] = _all_designations(work_history)
    result["latest_designation"] = _latest_designation(work_history)
    result["experience_years"] = _total_experience_years(work_history, companies)

    return result


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------

_QUALIFICATION_PRECEDENCE = [
    "post graduate", "graduate/degree", "diploma", "12th", "10th", "matric",
]


def _highest_qualification(qualifications: list[dict]) -> str:
    best_rank = len(_QUALIFICATION_PRECEDENCE)
    best = None
    for q in qualifications:
        level = (q.get("level") or "").strip().lower()
        if "certificate" in level:
            continue
        for rank, key in enumerate(_QUALIFICATION_PRECEDENCE):
            if key in level:
                if rank < best_rank:
                    best_rank = rank
                    best = q
                break
    if not best:
        return ""
    topic = best.get("topic") or best.get("qualification_level") or ""
    level = best.get("level", "")
    return f"{level} — {topic}".strip(" —") if topic else level


def _extract_certifications(qualifications: list[dict]) -> str:
    """Flat, display-friendly string of certification topics (kept for
    backward compatibility with the existing UI display field)."""
    certs = [
        (q.get("topic") or q.get("qualification_level") or "").strip()
        for q in qualifications
        if "certificate" in (q.get("level") or "").lower()
    ]
    return "; ".join(c for c in certs if c)


def _certification_records(qualifications: list[dict]) -> list[dict]:
    """Structured certification/training entries (rows in QUALIFICATION
    DETAILS whose Level is a certificate/training type, e.g. "Certificate
    Course"), for use by scoring logic that needs more than a flat
    string — e.g. checking whether a specific training body or software
    is mentioned, not just whether *some* certification exists."""
    records = []
    for q in qualifications:
        if "certificate" not in (q.get("level") or "").lower():
            continue
        records.append({
            "qualification_level": q.get("qualification_level", ""),
            "topic": q.get("topic", ""),
            "institute": q.get("college") or q.get("university") or "",
            "year": q.get("year_of_passing", ""),
        })
    return records


# RFP-style keyword sets for the two certification-based scoring criteria
# that recur across NHAI highway-personnel RFPs (see e.g. COASTAL_Package-1
# IE RFP, "General Qualification" — training course & software experience).
# Note: several RFPs specify that only a certificate from a Govt training
# institute or educational institute counts for these two items (not a
# private/vendor certificate) — `_certification_records()` returns the
# `institute` field so that check can be applied by the caller if the RFP
# in question requires it; it isn't hard-coded here since the exact
# wording/threshold varies by RFP.
_IAHE_CRRI_KEYWORDS = ["iahe", "crri"]
_SOFTWARE_CERT_KEYWORDS = [
    "ms project", "ms roads", "msroads", "primavera", "auto cad", "autocad",
    "staad", "civil 3d", "mx road", "mxroad",
]


def _has_keyword_certification(records: list[dict], keywords: list[str]) -> bool:
    for rec in records:
        blob = " ".join([
            rec.get("qualification_level", ""), rec.get("topic", ""),
            rec.get("institute", ""),
        ]).lower()
        if any(kw in blob for kw in keywords):
            return True
    return False


def _all_designations(work_history: list[dict]) -> str:
    seen = []
    for w in work_history:
        d = (w.get("designation") or "").strip()
        if d and d not in seen:
            seen.append(d)
    return "; ".join(seen)


def _parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _latest_designation(work_history: list[dict]) -> str:
    if not work_history:
        return ""
    dated = [(w, _parse_date(w.get("start_date", ""))) for w in work_history]
    dated_valid = [(w, d) for w, d in dated if d]
    if dated_valid:
        latest = max(dated_valid, key=lambda pair: pair[1])[0]
    else:
        latest = work_history[-1]
    return (latest.get("designation") or "").strip()


def _total_experience_years(work_history: list[dict], companies: list[dict]) -> float:
    """Merge overlapping start/completion date ranges from the work-history
    table (falling back to the companies table if work history is absent)
    and sum the covered days — so overlapping assignments aren't double
    counted."""
    rows = work_history if work_history else companies
    intervals = []
    today = date.today()
    for row in rows:
        start = _parse_date(row.get("start_date") or row.get("from_date", ""))
        end = _parse_date(row.get("completion_date") or row.get("to_date", ""))
        if not start:
            continue
        if not end or end < start:
            end = today
        intervals.append((start, end))

    if not intervals:
        return 0.0

    intervals.sort()
    merged = [intervals[0]]
    for start, end in intervals[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    total_days = sum((end - start).days for start, end in merged)
    return round(total_days / 365.25, 1)
