"""
tender_presets.py
==================
Hardcoded requirement sets, so common tenders don't need to be re-typed
(or loaded via a separate script) every time — they're just built into
the Tender Evaluator page as a one-click preset.

Add more tenders here as you need them: each entry is a tender name
mapping to a list of PositionRequirement.
"""

from tender_requirements import PositionRequirement

# ---------------------------------------------------------------------------
# COASTAL Package-1 — Independent Engineer RFP
# (RFP No. ORDIV-22011/2/2026-Odisha Division)
# Source: RFP Section VI-A "List of Key Experts and Required Qualifications"
#   - Man-Month table: p.239
#   - Qualification narratives: p.241-244
#   - CV scoring rubrics: p.259-277
#
# NOTE ON FIDELITY: the RFP's real CV-scoring formula awards incremental
# marks per extra year of experience and per extra project handled (e.g.
# Resident Engineer: "5 years similar-capacity experience = 15 marks, +1
# mark per extra year up to 5 more"). This engine only does a simpler
# 3-bucket check — cleared minimum experience? qualification keyword
# present? designation keyword present? That's a reasonable approximation
# for shortlisting, but will NOT reproduce the RFP's exact point totals.
# For exact-formula fidelity (e.g. for an actual bid submission), a
# separate, more involved scoring engine would be needed.
# ---------------------------------------------------------------------------

COASTAL_PACKAGE_1_IE = [
    PositionRequirement(
        position_name="Team Leader Cum Senior Highway Engineer",
        min_experience_years=12,  # RFP essential-qualification floor (scoring curve itself starts marks at 15 yrs)
        qualification_keywords=["civil engineering", "highway", "transportation",
                                 "structural engineering", "construction management"],
        designation_keywords=["team leader", "resident engineer", "project manager",
                               "superintending engineer"],
        weight_qualification=25, weight_experience=15, weight_designation=60,
    ),
    PositionRequirement(
        position_name="Resident cum Highway Engineer",
        min_experience_years=12,
        qualification_keywords=["civil engineering", "construction management", "transportation",
                                 "highway engineering", "structural engineering", "geotechnical engineering"],
        designation_keywords=["resident engineer", "highway engineer", "project director",
                               "project manager", "superintending engineer", "executive engineer",
                               "authority engineer", "independent engineer"],
        weight_qualification=25, weight_experience=15, weight_designation=60,
    ),
    PositionRequirement(
        position_name="Bridge/Structural Engineer",
        min_experience_years=10,
        qualification_keywords=["civil engineering", "structural engineering"],
        designation_keywords=["bridge engineer", "project manager", "resident engineer",
                               "executive engineer"],
        weight_qualification=25, weight_experience=15, weight_designation=60,
    ),
    PositionRequirement(
        position_name="Senior Pavement Specialist",
        min_experience_years=10,
        qualification_keywords=["civil engineering", "transportation", "highway engineering",
                                 "pavement engineering"],
        designation_keywords=["pavement specialist", "pavement engineer", "pavement expert",
                               "highway engineer", "executive engineer"],
        weight_qualification=25, weight_experience=20, weight_designation=55,
    ),
    PositionRequirement(
        position_name="Senior Quality cum Material Expert",
        min_experience_years=10,
        qualification_keywords=["civil engineering", "geotechnical engineering", "foundation engineering",
                                 "soil mechanics", "rock mechanics"],
        designation_keywords=["quality expert", "material engineer", "material expert",
                               "quality engineer", "geo-technical expert", "executive engineer",
                               "quality control"],
        weight_qualification=25, weight_experience=15, weight_designation=60,
    ),
    PositionRequirement(
        position_name="Road Safety Expert",
        min_experience_years=10,
        qualification_keywords=["civil engineering", "traffic", "transportation",
                                 "safety engineering", "road safety"],
        designation_keywords=["road safety expert", "road safety auditor", "safety engineer",
                               "highway engineer"],
        weight_qualification=25, weight_experience=15, weight_designation=60,
    ),
    PositionRequirement(
        position_name="Planning Engineer",
        min_experience_years=15,
        qualification_keywords=["civil engineering", "construction management", "project management",
                                 "infrastructure development"],
        designation_keywords=["project manager", "planning engineer", "construction manager",
                               "executive engineer"],
        weight_qualification=25, weight_experience=20, weight_designation=55,
    ),
]


# Registry — add future hardcoded tenders here.
PRESETS = {
    "COASTAL Package-1 IE": COASTAL_PACKAGE_1_IE,
}


def get_preset(name: str) -> list[PositionRequirement]:
    """Return a *fresh copy* of a preset's positions (so editing them in the
    UI doesn't mutate the hardcoded constant)."""
    import copy
    return copy.deepcopy(PRESETS[name])
