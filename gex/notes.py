"""Helper functions for managing note entries in the database."""

from datetime import datetime
from sqlalchemy.orm import Session

from db import Note


def get_or_create_note(session: Session, symbol: str) -> Note:
    """Return the existing note for a symbol or create a blank one."""
    note = session.query(Note).filter_by(symbol=symbol).first()
    if note is None:
        note = Note(symbol=symbol, content="", updated_at=datetime.utcnow())
        session.add(note)
        session.commit()
        session.refresh(note)
    return note


def update_note(session: Session, symbol: str, content: str) -> None:
    """Create or update a note for the given symbol."""
    note = session.query(Note).filter_by(symbol=symbol).first()
    if note is None:
        note = Note(symbol=symbol, content=content, updated_at=datetime.utcnow())
        session.add(note)
    else:
        note.content = content
        note.updated_at = datetime.utcnow()
    session.commit()

