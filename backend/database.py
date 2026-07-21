import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

from models import metadata

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:012345@127.0.0.1:5432/cv_dashboard"
)

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,   # auto-reconnect on stale connections
    pool_size=5,
    max_overflow=10
)

# Fresh-start schema: creates `candidates` and `tender_requirements` if they
# don't exist yet. Does NOT alter/drop existing tables — if you're upgrading
# from the old schema, drop the old `candidates` table first (its columns
# don't match the new fixed-format schema).
metadata.create_all(engine)
