from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import JSON, TIMESTAMP, Boolean, Column, Integer, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

load_dotenv()

# A clone should boot without requiring a locally provisioned PostgreSQL server.
# DATABASE_URL can still point to PostgreSQL in production.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_PATH = BACKEND_ROOT / "data" / "nexus_config.db"
_raw_database_url = os.getenv("DATABASE_URL", "").strip()
DATABASE_URL = _raw_database_url or f"sqlite:///{DEFAULT_SQLITE_PATH}"

_engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False, "timeout": 10}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)
    category = Column(Text, index=True)
    info = Column(JSON)
    created_at = Column(TIMESTAMP, server_default=func.now())


class AIProviderConfig(Base):
    __tablename__ = "ai_provider_config"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(Text, nullable=False, default="omniroute")
    base_url = Column(
        Text,
        nullable=False,
        default="http://127.0.0.1:20128/v1/chat/completions",
    )
    api_key = Column(Text, nullable=False, default="")
    model = Column(Text, nullable=False, default="auto")
    fallback_models = Column(JSON, nullable=False, default=list)
    referer = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    extra_headers = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


def init_db() -> None:
    if DATABASE_URL.startswith("sqlite"):
        DEFAULT_SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
