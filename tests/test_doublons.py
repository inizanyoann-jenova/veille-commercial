import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def engine():
    from source_registry import Source          # noqa: registers Source
    from models import ScraperRun, DuplicateCandidate  # noqa: registers models
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_duplicate_candidates_table_exists(engine):
    inspector = inspect(engine)
    assert "duplicate_candidates" in inspector.get_table_names()


def test_duplicate_candidates_columns(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("duplicate_candidates")}
    assert {"id", "tender_id_a", "tender_id_b", "similarity_score", "detected_at", "resolved"} <= cols


from datetime import datetime


def _make_tender(db, id, title, source, deadline=None, score=70):
    from models import Tender
    t = Tender(
        id=id, title=title, source=source,
        relevance_score=score, deadline=deadline,
        status="À qualifier", is_blacklisted=False,
    )
    db.add(t)
    db.commit()
    return t


def test_detect_finds_similar_titles_different_sources(db):
    from database import detect_duplicates
    from models import DuplicateCandidate
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a1", "Rénovation SSI CHU Mayotte", "BOAMP", deadline=dl)
    _make_tender(db, "b1", "Rénovation SSI CHU Mayotte", "TED", deadline=dl)

    count = detect_duplicates(db)

    assert count == 1
    pair = db.query(DuplicateCandidate).first()
    assert pair.similarity_score >= 0.80
    assert pair.resolved is False


def test_detect_skips_same_source(db):
    from database import detect_duplicates
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a2", "Maintenance CMSI Hôpital", "BOAMP", deadline=dl)
    _make_tender(db, "b2", "Maintenance CMSI Hôpital", "BOAMP", deadline=dl)

    count = detect_duplicates(db)

    assert count == 0


def test_detect_skips_different_deadline(db):
    from database import detect_duplicates
    _make_tender(db, "a3", "SSI Lycée Victor Hugo", "BOAMP", deadline=datetime(2026, 6, 1))
    _make_tender(db, "b3", "SSI Lycée Victor Hugo", "TED",   deadline=datetime(2026, 7, 15))

    count = detect_duplicates(db)

    assert count == 0


def test_detect_no_duplicate_when_titles_differ(db):
    from database import detect_duplicates
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a4", "SSI Lycée Bellepierre", "BOAMP", deadline=dl)
    _make_tender(db, "b4", "Vidéosurveillance Mairie", "TED", deadline=dl)

    count = detect_duplicates(db)

    assert count == 0


def test_detect_does_not_create_duplicate_pair_twice(db):
    from database import detect_duplicates
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a5", "Courants faibles Hôtel Lux", "BOAMP", deadline=dl)
    _make_tender(db, "b5", "Courants faibles Hôtel Lux", "TED",   deadline=dl)

    detect_duplicates(db)
    count_second = detect_duplicates(db)

    assert count_second == 0
