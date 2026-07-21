"""
rubric_assessments.py
======================
Persistence for exact-formula rubric scoring (scoring_engine.py /
coastal_rubrics.py): save and load the raw per-criterion inputs an
assessor enters for a given candidate + position, so a scoring session
survives a page reload instead of living only in Streamlit session
state. The score itself is always recomputed from these raw values
against the *current* rubric definition — never stored — so fixing a
transcription error in coastal_rubrics.py automatically re-scores every
saved assessment next time it's loaded.
"""

import json

from sqlalchemy import text

from database import engine


def save_assessment(rubric_source: str, position_name: str, candidate_id: int,
                     values: dict) -> None:
    """Upsert the raw criterion values for one candidate + position."""
    with engine.begin() as conn:
        conn.execute(
            text("""
                INSERT INTO rubric_assessments (rubric_source, position_name, candidate_id, values_json)
                VALUES (:rubric_source, :position_name, :candidate_id, :values_json)
                ON CONFLICT (rubric_source, position_name, candidate_id)
                DO UPDATE SET values_json = EXCLUDED.values_json, updated_at = now()
            """),
            {
                "rubric_source": rubric_source,
                "position_name": position_name,
                "candidate_id": candidate_id,
                "values_json": json.dumps(values),
            }
        )


def load_assessment(rubric_source: str, position_name: str, candidate_id: int) -> dict:
    """Return the saved {criterion_key: value} dict, or {} if none saved yet."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT values_json FROM rubric_assessments
                WHERE rubric_source = :rubric_source
                  AND position_name = :position_name
                  AND candidate_id = :candidate_id
            """),
            {"rubric_source": rubric_source, "position_name": position_name, "candidate_id": candidate_id}
        ).fetchone()
    if not row or not row[0]:
        return {}
    try:
        return json.loads(row[0])
    except (TypeError, ValueError):
        return {}


def load_all_assessments(rubric_source: str, position_name: str) -> dict[int, dict]:
    """Return {candidate_id: {criterion_key: value}} for every candidate
    assessed against this position — used to score/rank the whole
    candidate pool for a position in one go."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT candidate_id, values_json FROM rubric_assessments
                WHERE rubric_source = :rubric_source AND position_name = :position_name
            """),
            {"rubric_source": rubric_source, "position_name": position_name}
        )
        out = {}
        for candidate_id, values_json in rows:
            try:
                out[candidate_id] = json.loads(values_json) if values_json else {}
            except (TypeError, ValueError):
                out[candidate_id] = {}
        return out
