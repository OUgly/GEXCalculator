import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, Note
from gex.notes import get_or_create_note, update_note


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", future=True)
    TestingSession = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    with TestingSession() as s:
        yield s


def test_get_or_create_returns_same_note(session):
    note1 = get_or_create_note(session, "SPY")
    assert note1.symbol == "SPY"
    assert note1.content == ""
    note2 = get_or_create_note(session, "SPY")
    assert note2.id == note1.id


def test_update_note_upserts(session):
    update_note(session, "AAPL", "first")
    notes = session.query(Note).all()
    assert len(notes) == 1
    assert notes[0].content == "first"

    update_note(session, "AAPL", "second")
    notes = session.query(Note).all()
    assert len(notes) == 1
    assert notes[0].content == "second"
