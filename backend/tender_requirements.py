"""
tender_requirements.py
=======================
The tender scoring system: requirements are typed in manually (position
name, required qualification/designation keywords, minimum experience,
and point weights) rather than auto-guessed from an uploaded tender PDF.
Candidates already in the database are then scored against whatever was
typed in.

A "requirement set" = one tender, made up of one PositionRequirement per
key position. Requirement sets can be saved to the DB and reloaded later.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import text

from database import engine


@dataclass
class PositionRequirement:
    position_name: str
    min_experience_years: float = 0
    qualification_keywords: list[str] = field(default_factory=list)
    designation_keywords: list[str] = field(default_factory=list)
    weight_qualification: float = 30
    weight_experience: float = 40
    weight_designation: float = 30
    id: int | None = None

    @property
    def total_weight(self) -> float:
        return self.weight_qualification + self.weight_experience + self.weight_designation


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def save_requirement_set(tender_name: str, positions: list[PositionRequirement]) -> None:
    """Replace any previously saved positions for this tender name with the
    given list."""
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM tender_requirements WHERE tender_name = :name"),
            {"name": tender_name}
        )
        for p in positions:
            conn.execute(
                text("""
                    INSERT INTO tender_requirements
                        (tender_name, position_name, min_experience_years,
                         qualification_keywords, designation_keywords,
                         weight_qualification, weight_experience, weight_designation)
                    VALUES
                        (:tender_name, :position_name, :min_experience_years,
                         :qualification_keywords, :designation_keywords,
                         :weight_qualification, :weight_experience, :weight_designation)
                """),
                {
                    "tender_name": tender_name,
                    "position_name": p.position_name,
                    "min_experience_years": p.min_experience_years,
                    "qualification_keywords": ", ".join(p.qualification_keywords),
                    "designation_keywords": ", ".join(p.designation_keywords),
                    "weight_qualification": p.weight_qualification,
                    "weight_experience": p.weight_experience,
                    "weight_designation": p.weight_designation,
                }
            )


def list_saved_tender_names() -> list[str]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT tender_name FROM tender_requirements ORDER BY tender_name")
        )
        return [r[0] for r in rows]


def load_requirement_set(tender_name: str) -> list[PositionRequirement]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, position_name, min_experience_years,
                       qualification_keywords, designation_keywords,
                       weight_qualification, weight_experience, weight_designation
                FROM tender_requirements
                WHERE tender_name = :name
                ORDER BY id
            """),
            {"name": tender_name}
        )
        positions = []
        for r in rows:
            m = r._mapping
            positions.append(PositionRequirement(
                id=m["id"],
                position_name=m["position_name"],
                min_experience_years=m["min_experience_years"] or 0,
                qualification_keywords=_split(m["qualification_keywords"]),
                designation_keywords=_split(m["designation_keywords"]),
                weight_qualification=m["weight_qualification"] or 0,
                weight_experience=m["weight_experience"] or 0,
                weight_designation=m["weight_designation"] or 0,
            ))
        return positions


def delete_requirement_set(tender_name: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM tender_requirements WHERE tender_name = :name"),
            {"name": tender_name}
        )


def _split(value: str) -> list[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _keyword_match_score(text_blob: str, keywords: list[str], max_points: float) -> tuple[float, bool]:
    if not keywords or max_points <= 0:
        return 0.0, False
    text_blob = (text_blob or "").lower()
    matched = sum(1 for kw in keywords if kw.lower() in text_blob)
    if matched == 0:
        return 0.0, False
    per_kw = max_points / len(keywords)
    return round(min(max_points, matched * per_kw), 2), True


def score_candidate(candidate: dict, requirement: PositionRequirement) -> dict:
    """Score one candidate (as returned by get_candidates()) against one
    PositionRequirement. Returns a breakdown so the UI can show *why* a
    score was awarded.

    Eligibility gate: a candidate must show at least some qualification or
    designation relevance before any points are awarded — otherwise someone
    with decades of unrelated experience could still score purely on
    years worked.
    """
    qualification_text = " ".join(filter(None, [
        candidate.get("highest_qualification", ""),
        candidate.get("certifications", ""),
    ]))
    designation_text = " ".join(filter(None, [
        candidate.get("all_designations", ""),
        candidate.get("latest_designation", ""),
    ]))
    experience_years = float(candidate.get("experience_years") or 0)

    breakdown = {
        "qualification_score": 0.0,
        "experience_score": 0.0,
        "designation_score": 0.0,
        "eligible": False,
        "total": 0.0,
    }

    qual_score, qual_relevant = _keyword_match_score(
        qualification_text, requirement.qualification_keywords, requirement.weight_qualification
    )
    desig_score, desig_relevant = _keyword_match_score(
        designation_text, requirement.designation_keywords, requirement.weight_designation
    )

    if requirement.qualification_keywords or requirement.designation_keywords:
        if not qual_relevant and not desig_relevant:
            return breakdown

    breakdown["eligible"] = True
    breakdown["qualification_score"] = qual_score
    breakdown["designation_score"] = desig_score

    if requirement.min_experience_years > 0:
        if experience_years >= requirement.min_experience_years:
            exp_score = requirement.weight_experience
        elif experience_years > 0:
            exp_score = round(
                (experience_years / requirement.min_experience_years)
                * requirement.weight_experience * 0.5, 2
            )
        else:
            exp_score = 0.0
    else:
        exp_score = 0.0
    breakdown["experience_score"] = exp_score

    breakdown["total"] = round(qual_score + desig_score + exp_score, 2)
    return breakdown
