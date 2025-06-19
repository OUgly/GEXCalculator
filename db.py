from __future__ import annotations

"""Database models and session setup for the GEX application."""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite database located at ./gex.db
engine = create_engine("sqlite:///./gex.db", future=True)

# Session factory bound to this engine
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Base class for declarative models
Base = declarative_base()


class OptionChain(Base):
    """Stored option chain JSON fetched from an external provider."""

    __tablename__ = "option_chains"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, index=True, nullable=False)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_json = Column(Text, nullable=False)


class Note(Base):
    """User notes associated with a particular symbol."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, nullable=False)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

