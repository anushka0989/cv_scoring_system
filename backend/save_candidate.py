import json

from sqlalchemy import text

from database import engine


def save_candidate(candidate: dict, cv_path: str = None, source_filename: str = None) -> bool:
    """Save a candidate dict (as returned by cv_parser.parse_cv) to the DB.

    Duplicate detection: prefer PAN number (most reliable unique ID in
    this CV format); if PAN is blank, fall back to name + mobile.
    Returns False (no insert) if a duplicate is found or the name is empty.
    """
    name = (candidate.get("name") or "").strip()
    if not name:
        print("⚠️  Skipped: candidate name is empty.")
        return False

    pan = (candidate.get("pan_number") or "").strip()
    mobile = (candidate.get("mobile") or "").strip()

    data = {
        "name":                 name,
        "dob":                  candidate.get("dob", ""),
        "mother_name":          candidate.get("mother_name", ""),
        "email":                candidate.get("email", ""),
        "mobile":               mobile,
        "alternate_mobile":     candidate.get("alternate_mobile", ""),
        "landline_number":      candidate.get("landline_number", ""),
        "pan_number":           pan,
        "passport_number":      candidate.get("passport_number", ""),
        "current_state":        candidate.get("current_state", ""),
        "current_district":     candidate.get("current_district", ""),
        "current_address":      candidate.get("current_address", ""),
        "current_pincode":      candidate.get("current_pincode", ""),
        "permanent_state":      candidate.get("permanent_state", ""),
        "permanent_district":   candidate.get("permanent_district", ""),
        "permanent_address":    candidate.get("permanent_address", ""),
        "permanent_pincode":    candidate.get("permanent_pincode", ""),
        "qualifications_json":  json.dumps(candidate.get("qualifications", [])),
        "companies_json":       json.dumps(candidate.get("companies", [])),
        "work_history_json":    json.dumps(candidate.get("work_history", [])),
        "positions_held_json":  json.dumps(candidate.get("positions_held", [])),
        "highest_qualification": candidate.get("highest_qualification", ""),
        "certifications":       candidate.get("certifications", ""),
        "all_designations":     candidate.get("all_designations", ""),
        "latest_designation":   candidate.get("latest_designation", ""),
        "experience_years":     candidate.get("experience_years", 0),
        "cv_path":              cv_path,
        "source_filename":      source_filename,
        "parse_warnings":       json.dumps(candidate.get("warnings", [])),
    }

    with engine.begin() as conn:

        if pan:
            existing = conn.execute(
                text("""
                    SELECT id FROM candidates
                    WHERE pan_number IS NOT NULL
                      AND TRIM(pan_number) != ''
                      AND UPPER(TRIM(pan_number)) = UPPER(TRIM(:pan))
                """),
                {"pan": pan}
            ).fetchone()
        else:
            existing = conn.execute(
                text("""
                    SELECT id FROM candidates
                    WHERE LOWER(TRIM(name)) = LOWER(TRIM(:name))
                      AND TRIM(mobile) = TRIM(:mobile)
                      AND TRIM(mobile) != ''
                """),
                {"name": name, "mobile": mobile}
            ).fetchone()

        if existing:
            print(f"⚠️  Duplicate skipped: {name} ({pan or mobile})")
            return False

        columns = ", ".join(data.keys())
        placeholders = ", ".join(f":{k}" for k in data.keys())
        conn.execute(
            text(f"INSERT INTO candidates ({columns}) VALUES ({placeholders})"),
            data
        )

    print(f"✅  Saved: {name}")
    return True
