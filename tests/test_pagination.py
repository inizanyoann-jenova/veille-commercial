import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender


@pytest.fixture(scope="module")
def _engine():
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(_engine):
    Session = sessionmaker(bind=_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


def _make(db, tender_id, title="Marché test"):
    t = Tender(
        id=tender_id,
        title=title,
        description="desc",
        source="https://example.com",
        publication_date=datetime(2026, 1, 15),
        status="À qualifier",
        relevance_score=50,
        is_maintenance=False,
        is_blacklisted=False,
        secteur="Public",
        type_opportunite="Marché Public",
    )
    db.add(t)
    db.flush()
    return t


def test_get_tenders_returns_list(db):
    import main as bm

    for i in range(3):
        _make(db, f"LIST-{i:04d}", f"Marché {i}")

    result = bm.get_tenders(
        status="Tous", secteur="Public",
        maintenance_only=False, date_from=None,
        strict_date=False, only_recent=False,
        offset=0, limit=200, db=db,
    )
    assert isinstance(result, list)
    assert len(result) >= 3


def test_get_tenders_limit_applied(db):
    import main as bm

    for i in range(10):
        _make(db, f"LIM-{i:04d}", f"Marché limite {i}")

    result = bm.get_tenders(
        status="Tous", secteur="Public",
        maintenance_only=False, date_from=None,
        strict_date=False, only_recent=False,
        offset=0, limit=3, db=db,
    )
    assert len(result) <= 3


def test_get_tenders_offset_no_overlap(db):
    import main as bm

    for i in range(6):
        _make(db, f"OFF-{i:04d}", f"Marché offset {i}")

    page1 = bm.get_tenders(
        status="Tous", secteur="Public",
        maintenance_only=False, date_from=None,
        strict_date=False, only_recent=False,
        offset=0, limit=3, db=db,
    )
    page2 = bm.get_tenders(
        status="Tous", secteur="Public",
        maintenance_only=False, date_from=None,
        strict_date=False, only_recent=False,
        offset=3, limit=3, db=db,
    )
    ids1 = {t["id"] for t in page1}
    ids2 = {t["id"] for t in page2}
    assert ids1.isdisjoint(ids2), "Les pages 1 et 2 ne doivent pas se chevaucher"
