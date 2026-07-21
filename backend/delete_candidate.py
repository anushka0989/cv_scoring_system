from sqlalchemy import text

from database import engine


def delete_candidate(candidate_id: int) -> bool:
    """Delete a candidate by id. Returns True if a row was deleted."""
    with engine.begin() as conn:
        result = conn.execute(
            text("DELETE FROM candidates WHERE id = :id"),
            {"id": candidate_id}
        )
    if result.rowcount > 0:
        print(f"🗑️  Deleted candidate id={candidate_id}")
        return True
    print(f"⚠️  Not found: id={candidate_id}")
    return False
