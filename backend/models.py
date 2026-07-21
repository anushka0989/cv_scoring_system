from sqlalchemy import (
    Table, Column, MetaData,
    Integer, String, Text, Float, DateTime, UniqueConstraint
)
from sqlalchemy.sql import func

metadata = MetaData()

# ---------------------------------------------------------------------------
# candidates — one row per parsed CV, in the fixed INFRACON format.
# Variable-length sections (qualifications, companies, work history,
# positions held) are stored as JSON text — simplest reliable option for
# a Streamlit app; query them in Python after loading, not in SQL.
# ---------------------------------------------------------------------------

candidates = Table(
    "candidates",
    metadata,

    Column("id",                   Integer,  primary_key=True, autoincrement=True),

    # Basic details
    Column("name",                 String(255)),
    Column("dob",                  String(20)),
    Column("mother_name",          String(255)),
    Column("email",                String(255)),
    Column("mobile",               String(20)),
    Column("alternate_mobile",     String(20)),
    Column("landline_number",      String(20)),
    Column("pan_number",           String(20)),
    Column("passport_number",      String(20)),
    Column("current_state",        String(100)),
    Column("current_district",     String(100)),
    Column("current_address",      Text),
    Column("current_pincode",      String(20)),
    Column("permanent_state",      String(100)),
    Column("permanent_district",   String(100)),
    Column("permanent_address",    Text),
    Column("permanent_pincode",    String(20)),

    # Variable-length sections, stored as JSON text
    Column("qualifications_json",  Text),   # list of {level, qualification_level, topic, college, university, year_of_passing, percentage, enrollment_number, certificate_details}
    Column("companies_json",       Text),   # list of {sno, company_name, from_date, to_date}
    Column("work_history_json",    Text),   # list of {sno, work_name, client, designation, project_cost_cr, start_date, completion_date, country}
    Column("positions_held_json",  Text),   # list of {sno, position, from_date, to_date, details}

    # Derived fields (computed once at parse time, used for search/scoring)
    Column("highest_qualification", Text),
    Column("certifications",        Text),
    Column("all_designations",      Text),
    Column("latest_designation",    Text),
    Column("experience_years",      Float, default=0),

    Column("cv_path",              Text),
    Column("source_filename",      Text),
    Column("parse_warnings",       Text),
    Column("created_at",           DateTime, server_default=func.now()),

    # A candidate is identified by PAN when available (most reliable
    # unique ID in this format); duplicate-detection falls back to
    # name + mobile when PAN is blank. Enforced in save_candidate.py
    # rather than as a DB constraint, since PAN can legitimately be empty.
)


# ---------------------------------------------------------------------------
# tender_requirements — manually entered scoring rubrics ("feed the
# requirements into the system"). One row per position within a saved
# tender/requirement set.
# ---------------------------------------------------------------------------

tender_requirements = Table(
    "tender_requirements",
    metadata,

    Column("id",                       Integer, primary_key=True, autoincrement=True),
    Column("tender_name",              String(255)),
    Column("position_name",            String(255)),
    Column("min_experience_years",     Float, default=0),
    Column("qualification_keywords",   Text),   # comma-separated
    Column("designation_keywords",     Text),   # comma-separated
    Column("weight_qualification",     Float, default=30),
    Column("weight_experience",        Float, default=40),
    Column("weight_designation",       Float, default=30),
    Column("created_at",               DateTime, server_default=func.now()),
)


# ---------------------------------------------------------------------------
# rubric_assessments — raw per-criterion inputs for exact-formula scoring
# (scoring_engine.py / coastal_rubrics.py). One row per (rubric source,
# position, candidate): `values_json` holds {criterion_key: raw_value},
# e.g. {"tl_gq_civil_degree": 1, "tl_adeq_total_exp": 20, ...}. The score
# itself is always recomputed from values_json + the current rubric
# definition rather than stored, so a rubric correction retroactively
# re-scores every saved assessment instead of leaving stale numbers.
# ---------------------------------------------------------------------------

rubric_assessments = Table(
    "rubric_assessments",
    metadata,

    Column("id",             Integer, primary_key=True, autoincrement=True),
    Column("rubric_source",  String(100)),   # e.g. "coastal_package_1_ie"
    Column("position_name",  String(255)),
    Column("candidate_id",   Integer),
    Column("values_json",    Text),
    Column("created_at",     DateTime, server_default=func.now()),
    Column("updated_at",     DateTime, server_default=func.now(), onupdate=func.now()),

    UniqueConstraint("rubric_source", "position_name", "candidate_id",
                      name="uq_rubric_assessment_candidate_position"),
)
