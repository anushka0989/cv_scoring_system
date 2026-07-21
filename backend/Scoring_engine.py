"""
scoring_engine.py
==================
A generic engine for RFP-style CV scoring rubrics of the shape used by
NHAI/highway-personnel tenders (see e.g. COASTAL Package-1 IE RFP,
Section VI-A, "Evaluation Criteria for assessment of score of Key
Staff"): each position is scored out of 100, broken into named
criteria, each with its own maximum points and its own scoring rule.

This replaces the old 3-bucket weighted-keyword approximation in
tender_requirements.py for any tender where the *exact* published
formula is known. Two criterion shapes cover every case seen in the
COASTAL RFP:

  - "flat"      — a fixed-points item that is either met or not
                   (e.g. "Graduate in Civil Engineering — 17 marks").
                   Also supports partial credit (0..1) if a rubric ever
                   needs it, but every case seen so far is binary.

  - "threshold" — the recurring RFP pattern:
                     "< X <unit> - 0
                      X <unit> - Y marks
                      Add Z marks for each additional <unit>
                      (or each additional N <unit>s), subject to a
                      maximum of W marks"
                   i.e. base_marks awarded once `value` reaches
                   base_value, plus increment_per_unit for every
                   increment_unit_size of value beyond that, capped at
                   increment_cap additional marks (so the criterion's
                   ceiling is base_marks + increment_cap, which should
                   equal max_points).

Each PositionRubric is an ordered list of Criterion, grouped by
`category` (e.g. "General Qualification", "Adequacy for the Project",
"Employment with the Firm") purely for display — scoring doesn't care
about the grouping, only about summing every criterion's score.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class Criterion:
    key: str                     # unique within a position, e.g. "gq_civil_degree"
    category: str                # display grouping, e.g. "General Qualification"
    label: str                   # description text, taken from the RFP
    max_points: float

    kind: Literal["flat", "threshold"] = "flat"

    # --- threshold-only fields ---------------------------------------
    unit_label: str = ""             # "years", "projects", "bridges", ...
    base_value: float = 0            # X in "< X <unit> - 0"
    base_marks: float = 0            # Y in "X <unit> - Y marks"
    increment_per_unit: float = 0    # Z
    increment_unit_size: float = 1   # e.g. "per additional 2 years" -> 2
    increment_cap: float = 0         # W — additional marks are capped here
                                      # (so ceiling = base_marks + increment_cap)

    note: str = ""                   # free-text caveat from the RFP, shown as a tooltip

    def score(self, value: Optional[float]) -> float:
        """Score this single criterion given a raw input value.

        For "flat" criteria, `value` is treated as 0/1 (or any fraction
        in between, for partial credit) and multiplied by max_points.
        For "threshold" criteria, `value` is the raw count (years,
        projects, etc.) claimed for this criterion.
        """
        if value is None:
            return 0.0

        if self.kind == "flat":
            fraction = max(0.0, min(1.0, float(value)))
            return round(fraction * self.max_points, 2)

        # threshold
        value = float(value)
        if value < self.base_value:
            return 0.0
        extra_units = (value - self.base_value) / self.increment_unit_size
        bonus = extra_units * self.increment_per_unit
        bonus = max(0.0, min(bonus, self.increment_cap))
        return round(min(self.base_marks + bonus, self.max_points), 2)

    def scale_description(self) -> str:
        """Human-readable one-liner of the scoring scale, for display in the UI."""
        if self.kind == "flat":
            return f"{self.max_points:g} marks if met, 0 if not"
        unit = self.unit_label or "unit(s)"
        step = f" per {self.increment_unit_size:g} {unit}" if self.increment_unit_size != 1 else f" per {unit}"
        return (
            f"< {self.base_value:g} {unit} = 0; "
            f"{self.base_value:g} {unit} = {self.base_marks:g} marks; "
            f"+{self.increment_per_unit:g}{step}, up to +{self.increment_cap:g} "
            f"(max {self.max_points:g})"
        )


@dataclass
class PositionRubric:
    position_name: str
    criteria: list[Criterion] = field(default_factory=list)
    source_note: str = ""   # e.g. citation to the RFP section/page

    @property
    def max_total(self) -> float:
        return round(sum(c.max_points for c in self.criteria), 2)

    @property
    def categories(self) -> list[str]:
        seen = []
        for c in self.criteria:
            if c.category not in seen:
                seen.append(c.category)
        return seen

    def score(self, values: dict[str, float]) -> dict:
        """Score every criterion given a dict of {criterion_key: raw_value}.

        Returns a breakdown: per-criterion scores (in rubric order) plus
        the total, so the caller/UI can show exactly how each of the
        100 marks was earned rather than a single collapsed number.
        """
        per_criterion = []
        total = 0.0
        for c in self.criteria:
            raw = values.get(c.key)
            earned = c.score(raw)
            total += earned
            per_criterion.append({
                "key": c.key,
                "category": c.category,
                "label": c.label,
                "max_points": c.max_points,
                "raw_value": raw,
                "earned": earned,
            })
        return {
            "position_name": self.position_name,
            "per_criterion": per_criterion,
            "total": round(total, 2),
            "max_total": self.max_total,
        }
