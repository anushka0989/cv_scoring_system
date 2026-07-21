import json

from sqlalchemy import text

from database import engine

_JSON_FIELDS = ["qualifications_json", "companies_json", "work_history_json", "positions_held_json"]
_JSON_OUT_NAMES = {
    "qualifications_json": "qualifications",
    "companies_json": "companies",
    "work_history_json": "work_history",
    "positions_held_json": "positions_held",
}


def _deserialize(row: dict) -> dict:
    out = dict(row)
    for json_field, out_name in _JSON_OUT_NAMES.items():
        raw = out.pop(json_field, None)
        try:
            out[out_name] = json.loads(raw) if raw else []
        except (TypeError, ValueError):
            out[out_name] = []
    return out


def get_candidates() -> list[dict]:
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM candidates ORDER BY name")
        )
        return [_deserialize(dict(row._mapping)) for row in rows]


def get_candidate_by_id(candidate_id: int) -> dict | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM candidates WHERE id = :id"),
            {"id": candidate_id}
        ).fetchone()
    return _deserialize(dict(row._mapping)) if row else None
