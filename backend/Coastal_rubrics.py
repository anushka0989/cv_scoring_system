"""
coastal_rubrics.py
===================
Exact CV-scoring rubrics for the COASTAL Package-1 Independent Engineer
RFP (RFP No. ORDIV-22011/2/2026-Odisha Division), Section VI-A,
pp. 259-277 — transcribed criterion-by-criterion using scoring_engine.py,
so every position scores exactly the way the RFP specifies (base marks
at a threshold + capped per-unit bonus), not the earlier 3-bucket
weighted-keyword approximation in tender_presets.py.

Each position totals exactly 100 (25 General Qualification +
70 Adequacy for the Project + 5 Employment with the Firm) — this is
asserted at import time so a transcription slip is caught immediately
rather than silently under/over-scoring a candidate.

One caveat, flagged in the RFP extraction itself: Planning Engineer,
criterion "pe_adeq_large_project_var_eot" has the source PDF text
reading "2 nos. -50" where every other criterion in the RFP uses
single-digit-to-low-teens marks and the section must sum to 70. That
is almost certainly an OCR/typo artifact in the RFP for "5", so this
file uses 5 — recorded here explicitly so it's never mistaken for a
verified figure. Re-check RFP page 276 directly if this position is
decisive for a live bid.
"""

from __future__ import annotations

from Scoring_engine import Criterion, PositionRubric

_GQ = "General Qualification"
_ADEQ = "Adequacy for the Project"
_EMP = "Employment with the Firm"

# Every position shares the same "Employment with the Firm" scale.
def _employment_criterion(key: str) -> Criterion:
    return Criterion(
        key=key, category=_EMP,
        label="Employment with the Firm",
        max_points=5, kind="threshold", unit_label="years",
        base_value=1, base_marks=3, increment_per_unit=0.5,
        increment_unit_size=1, increment_cap=2,
    )


# ---------------------------------------------------------------------------
# 3.1 Team Leader cum Senior Highway Engineer
# ---------------------------------------------------------------------------
TEAM_LEADER = PositionRubric(
    position_name="Team Leader Cum Senior Highway Engineer",
    source_note="RFP Section 3.1, pp. 259-261",
    criteria=[
        Criterion("tl_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 17, "flat"),
        Criterion("tl_gq_pg", _GQ, "PG in Management/Construction/Transportation/Highway/"
                  "Structural Engineering or equivalent specialized stream", 3, "flat"),
        Criterion("tl_gq_training", _GQ, "Min. 15-day training from IAHE/CRRI/Govt institute "
                  "(highway development)", 3, "flat"),
        Criterion("tl_gq_software", _GQ, "Software experience (MS Roads/Projects, Primavera, etc.)", 2, "flat"),

        Criterion("tl_adeq_total_exp", _ADEQ, "Total professional experience, Highway projects",
                  15, "threshold", unit_label="years",
                  base_value=15, base_marks=8, increment_per_unit=1, increment_cap=7),
        Criterion("tl_adeq_team_leader_exp", _ADEQ, "Experience as Team Leader (or similar) in Highway "
                  "Development Projects (2/4/6-laning+)",
                  15, "threshold", unit_label="years",
                  base_value=5, base_marks=11, increment_per_unit=1, increment_cap=4),
        Criterion("tl_adeq_ppp", _ADEQ, "Team Leader (or similar), major project (>=40% length, "
                  "2/4/6-laning+) on PPP",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=3, increment_per_unit=1, increment_cap=2),
        Criterion("tl_adeq_prep_design", _ADEQ, "Team Leader (or similar), project preparation incl. "
                  "design of major Highway project (>=40% length)",
                  10, "threshold", unit_label="projects",
                  base_value=2, base_marks=8, increment_per_unit=1, increment_cap=2),
        Criterion("tl_adeq_cs_ic", _ADEQ, "Team Leader/PM (or similar), Construction Supervision/IC "
                  "(>=40% length)",
                  20, "threshold", unit_label="projects",
                  base_value=2, base_marks=16, increment_per_unit=2, increment_cap=4),
        Criterion("tl_adeq_om", _ADEQ, "Team Leader (or similar), O&M of Major Highway (>=40% length)",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),

        _employment_criterion("tl_employment"),
    ],
)

# ---------------------------------------------------------------------------
# 3.2 Resident cum Highway Engineer
# ---------------------------------------------------------------------------
RESIDENT_ENGINEER = PositionRubric(
    position_name="Resident cum Highway Engineer",
    source_note="RFP Section 3.2, pp. 262-264",
    criteria=[
        Criterion("re_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 17, "flat"),
        Criterion("re_gq_pg", _GQ, "PG in Construction Mgmt/Transportation/Highway/Structural/"
                  "Geotechnical Engineering or equivalent", 3, "flat"),
        Criterion("re_gq_training", _GQ, "Min. 15-day training certificate from IAHE/CRRI/Govt Institute",
                  3, "flat"),
        Criterion("re_gq_software", _GQ, "Software experience (MS Roads/Projects, Primavera, etc.)", 2, "flat"),

        Criterion("re_adeq_total_exp", _ADEQ, "Total professional experience, Highway projects",
                  15, "threshold", unit_label="years",
                  base_value=12, base_marks=12, increment_per_unit=1, increment_cap=3),
        Criterion("re_adeq_role_exp", _ADEQ, "Experience as RE/Highway Engineer/Project Director/PM/"
                  "Superintending Engg/Executive Engg/AE/IE (2/4/6-laning+)",
                  20, "threshold", unit_label="years",
                  base_value=5, base_marks=15, increment_per_unit=1, increment_cap=5),
        Criterion("re_adeq_major_projects", _ADEQ, "Similar-capacity experience, major 2/4/6-laning projects "
                  "(>=40% length)",
                  25, "threshold", unit_label="projects",
                  base_value=1, base_marks=19, increment_per_unit=3, increment_cap=6),
        Criterion("re_adeq_ppp", _ADEQ, "Construction/Construction Supervision/IC on PPP (>=40% length)",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),
        Criterion("re_adeq_om", _ADEQ, "RE (or similar), O&M of Major Highway (>=40% length)",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),

        _employment_criterion("re_employment"),
    ],
)

# ---------------------------------------------------------------------------
# 3.3 Bridge/Structural Engineer
# ---------------------------------------------------------------------------
BRIDGE_ENGINEER = PositionRubric(
    position_name="Bridge/Structural Engineer",
    source_note="RFP Section 3.3, pp. 265-267",
    criteria=[
        Criterion("be_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 18, "flat"),
        Criterion("be_gq_pg", _GQ, "PG in Structural Engineering", 4, "flat"),
        Criterion("be_gq_training", _GQ, "Residential training on Collapse/Failure of Bridges/Structures "
                  "from IAHE/CRRI/Govt Institute", 3, "flat"),

        Criterion("be_adeq_total_exp", _ADEQ, "Total professional experience, Highway/Bridge projects",
                  15, "threshold", unit_label="years",
                  base_value=10, base_marks=11, increment_per_unit=1, increment_unit_size=2, increment_cap=4),
        Criterion("be_adeq_design_cs", _ADEQ, "Design/Construction/Supervision of Bridges/ROB/Flyover/"
                  "Interchanges/similar structures (2/4/6-laning+)",
                  20, "threshold", unit_label="years",
                  base_value=5, base_marks=15, increment_per_unit=1, increment_cap=5),
        Criterion("be_adeq_major_bridges", _ADEQ, "Supervision of Major Highway Bridges/ROB/Flyover/"
                  "Interchanges/similar structures",
                  20, "threshold", unit_label="bridges",
                  base_value=2, base_marks=15, increment_per_unit=2.5, increment_cap=5),
        Criterion("be_adeq_rehab", _ADEQ, "Supervision of rehabilitation/repair of Major Bridges/ROB/"
                  "Flyover/Interchanges", 10, "threshold", unit_label="bridges",
                  base_value=2, base_marks=8, increment_per_unit=2, increment_cap=2),
        Criterion("be_adeq_modern_tech", _ADEQ, "Modern bridge construction tech (Precast Segmental, "
                  "Balanced Cantilever, Extradosed, Incremental/Full-span Launching)",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),

        _employment_criterion("be_employment"),
    ],
)

# ---------------------------------------------------------------------------
# 3.4 Senior Pavement Specialist
# ---------------------------------------------------------------------------
PAVEMENT_SPECIALIST = PositionRubric(
    position_name="Senior Pavement Specialist",
    source_note="RFP Section 3.4, pp. 268-270",
    criteria=[
        Criterion("ps_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 18, "flat"),
        Criterion("ps_gq_pg", _GQ, "PG in Transportation/Highway Engineering/Pavement Engineering "
                  "or equivalent", 4, "flat"),
        Criterion("ps_gq_training", _GQ, "Training certificate from IAHE/CRRI/Govt Institute "
                  "(pavement design/maintenance)", 3, "flat"),

        Criterion("ps_adeq_total_exp", _ADEQ, "Total professional experience, Pavement Design/"
                  "Construction/Maintenance (Highway/Road/Airfield Runway)",
                  20, "threshold", unit_label="years",
                  base_value=10, base_marks=15, increment_per_unit=1, increment_cap=5),
        Criterion("ps_adeq_construction", _ADEQ, "Construction/Construction Supervision, 2/4/6-laning "
                  "Major Highway projects",
                  20, "threshold", unit_label="years",
                  base_value=5, base_marks=15, increment_per_unit=1, increment_cap=5),
        Criterion("ps_adeq_role", _ADEQ, "Pavement/Geotechnical Engineer role, Major Highway "
                  "projects (>=40% length)",
                  25, "threshold", unit_label="projects",
                  base_value=2, base_marks=20, increment_per_unit=2.5, increment_cap=5),
        Criterion("ps_adeq_ppp", _ADEQ, "PPP projects (>=40% length)",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),

        _employment_criterion("ps_employment"),
    ],
)

# ---------------------------------------------------------------------------
# 3.5 Senior Quality/Material Expert
# ---------------------------------------------------------------------------
QUALITY_EXPERT = PositionRubric(
    position_name="Senior Quality cum Material Expert",
    source_note="RFP Section 3.5, pp. 271-272",
    criteria=[
        Criterion("qe_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 18, "flat"),
        Criterion("qe_gq_pg", _GQ, "PG in Geotechnical/Foundation Engineering/Soil Mechanics/"
                  "Rock Mechanics", 4, "flat"),
        Criterion("qe_gq_training", _GQ, "16-day material testing course (IAHE/CRRI/Govt Institute)",
                  3, "flat"),

        Criterion("qe_adeq_total_exp", _ADEQ, "Total professional experience, Highway/Bridge projects",
                  15, "threshold", unit_label="years",
                  base_value=10, base_marks=11, increment_per_unit=1, increment_cap=4),
        Criterion("qe_adeq_construction", _ADEQ, "Construction/Construction Supervision, major Highway "
                  "Projects (2/4/6-laning+)",
                  25, "threshold", unit_label="years",
                  base_value=5, base_marks=19, increment_per_unit=2, increment_cap=6),
        Criterion("qe_adeq_similar_projects", _ADEQ, "Similar Highway projects (>=40% length)",
                  30, "threshold", unit_label="projects",
                  base_value=2, base_marks=25, increment_per_unit=2.5, increment_cap=5),

        _employment_criterion("qe_employment"),
    ],
)

# ---------------------------------------------------------------------------
# 3.6 Road Safety Expert
# ---------------------------------------------------------------------------
ROAD_SAFETY_EXPERT = PositionRubric(
    position_name="Road Safety Expert",
    source_note="RFP Section 3.6, pp. 273-274",
    criteria=[
        Criterion("rs_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 18, "flat"),
        Criterion("rs_gq_pg", _GQ, "PG in Traffic/Transportation/Safety Engineering or equivalent",
                  4, "flat"),
        Criterion("rs_gq_training", _GQ, "15-day Certificate course on Road Safety Audit "
                  "(IAHE/CRRI/Govt Institute)", 3, "flat"),

        Criterion("rs_adeq_total_exp", _ADEQ, "Total professional experience, Highway/Bridge projects",
                  15, "threshold", unit_label="years",
                  base_value=10, base_marks=11, increment_per_unit=1, increment_cap=4),
        Criterion("rs_adeq_road_safety_exp", _ADEQ, "Similar-capacity experience, Road Safety works "
                  "on Major Highway (2/4/6-laning+)",
                  15, "threshold", unit_label="years",
                  base_value=5, base_marks=11, increment_per_unit=1, increment_cap=4),
        Criterion("rs_adeq_audits", _ADEQ, "Road Safety Audits, 2/4/6-laning Highway projects at "
                  "different stages (incl. >=1 at design stage)",
                  20, "threshold", unit_label="projects",
                  base_value=2, base_marks=15, increment_per_unit=2.5, increment_cap=5),
        Criterion("rs_adeq_blackspots", _ADEQ, "Identification/improvement of black spots, Major Highway",
                  10, "threshold", unit_label="improvements",
                  base_value=2, base_marks=8, increment_per_unit=2, increment_cap=2),
        Criterion("rs_adeq_mgmt_plans", _ADEQ, "Road Safety Management Plans, Inter-Urban Highway",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),
        Criterion("rs_adeq_field_exp", _ADEQ, "Field experience, Road Safety Management Plan",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),

        _employment_criterion("rs_employment"),
    ],
)

# ---------------------------------------------------------------------------
# 3.7 Planning Engineer
# ---------------------------------------------------------------------------
PLANNING_ENGINEER = PositionRubric(
    position_name="Planning Engineer",
    source_note="RFP Section 3.7, pp. 275-276. NOTE: criterion "
                 "'pe_adeq_large_project_var_eot' base_marks corrected from the RFP's apparent "
                 "OCR/typo '50' to 5, so the section totals 70 — verify against the original PDF "
                 "page 276 if this position is decisive.",
    criteria=[
        Criterion("pe_gq_civil_degree", _GQ, "Graduate in Civil Engineering", 17, "flat"),
        Criterion("pe_gq_pg", _GQ, "PG in Construction Mgmt/Project Mgmt/Infrastructure Development "
                  "& Management", 3, "flat"),
        Criterion("pe_gq_training", _GQ, "Training on Project Management/Planning "
                  "(IAHE/CRRI/Govt Institute)", 3, "flat"),
        Criterion("pe_gq_software", _GQ, "Software experience (MS Roads/Projects, Primavera, etc.)", 2, "flat"),

        Criterion("pe_adeq_total_exp", _ADEQ, "Total professional experience, PM/Planning Engineer",
                  20, "threshold", unit_label="years",
                  base_value=15, base_marks=15, increment_per_unit=1, increment_cap=5),
        Criterion("pe_adeq_highway_exp", _ADEQ, "PM/Planning Engineer, National/State Highway project",
                  20, "threshold", unit_label="years",
                  base_value=4, base_marks=15, increment_per_unit=1, increment_cap=5),
        Criterion("pe_adeq_large_project_claims", _ADEQ, "PM/Planning Engineer, large Highway contract "
                  ">Rs.150 Cr (incl. variation orders/claims handling)",
                  15, "threshold", unit_label="projects",
                  base_value=2, base_marks=10, increment_per_unit=2.5, increment_cap=5),
        Criterion("pe_adeq_large_project_var_eot", _ADEQ, "Planning Engineer, large Highway project "
                  ">Rs.150 Cr (incl. variation orders/EOT handling)",
                  10, "threshold", unit_label="projects",
                  base_value=2, base_marks=5, increment_per_unit=2.5, increment_cap=5),
        Criterion("pe_adeq_arbitration", _ADEQ, "Arbitration case handling, Highway project",
                  5, "threshold", unit_label="projects",
                  base_value=1, base_marks=4, increment_per_unit=1, increment_cap=1),

        _employment_criterion("pe_employment"),
    ],
)

COASTAL_PACKAGE_1_IE_RUBRICS: dict[str, PositionRubric] = {
    r.position_name: r for r in [
        TEAM_LEADER, RESIDENT_ENGINEER, BRIDGE_ENGINEER, PAVEMENT_SPECIALIST,
        QUALITY_EXPERT, ROAD_SAFETY_EXPERT, PLANNING_ENGINEER,
    ]
}

# Fail fast at import time if any position doesn't sum to exactly 100 —
# catches a transcription error immediately rather than silently mis-scoring.
for _rubric in COASTAL_PACKAGE_1_IE_RUBRICS.values():
    if abs(_rubric.max_total - 100) > 0.01:
        raise AssertionError(
            f"{_rubric.position_name}: rubric max_total is {_rubric.max_total}, expected 100 "
            "— check the criteria transcription in coastal_rubrics.py."
        )
