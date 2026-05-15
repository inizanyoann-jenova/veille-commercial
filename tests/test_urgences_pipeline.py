import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def engine():
    from source_registry import Source                      # noqa
    from models import ScraperRun, DuplicateCandidate       # noqa
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _today_midnight():
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


def _add_tender(db, id, title, score, deadline_offset_days, status="À qualifier", blacklisted=False):
    from models import Tender
    midnight = _today_midnight()
    deadline = (midnight + timedelta(days=deadline_offset_days)) if deadline_offset_days is not None else None
    t = Tender(
        id=id, title=title, source="TEST",
        relevance_score=score, deadline=deadline,
        status=status, is_blacklisted=blacklisted,
    )
    db.add(t)
    db.commit()
    return t


def test_urgences_returns_go_with_deadline_in_range(db):
    from database import load_urgences
    _add_tender(db, "u1", "SSI CHU Mayotte", score=80, deadline_offset_days=5)

    result = load_urgences(db)

    assert len(result) == 1
    assert result[0]["id"] == "u1"
    assert result[0]["jours"] == 5


def test_urgences_excludes_low_score(db):
    from database import load_urgences
    _add_tender(db, "u2", "Travaux divers", score=40, deadline_offset_days=5)

    assert load_urgences(db) == []


def test_urgences_excludes_past_deadline(db):
    from database import load_urgences
    _add_tender(db, "u3", "SSI Lycée", score=80, deadline_offset_days=-1)

    assert load_urgences(db) == []


def test_urgences_excludes_deadline_beyond_30j(db):
    from database import load_urgences
    _add_tender(db, "u4", "CMSI Hôpital", score=80, deadline_offset_days=35)

    assert load_urgences(db) == []


def test_urgences_excludes_gagne_perdu(db):
    from database import load_urgences
    _add_tender(db, "u5", "SSI Mairie", score=80, deadline_offset_days=5, status="Gagné")
    _add_tender(db, "u6", "CMSI Centre", score=80, deadline_offset_days=5, status="Perdu")

    assert load_urgences(db) == []


def test_urgences_excludes_blacklisted(db):
    from database import load_urgences
    _add_tender(db, "u7", "SSI Stade", score=80, deadline_offset_days=5, blacklisted=True)

    assert load_urgences(db) == []


def test_urgences_sorted_by_deadline_asc(db):
    from database import load_urgences
    _add_tender(db, "u8", "SSI A", score=80, deadline_offset_days=20)
    _add_tender(db, "u9", "SSI B", score=80, deadline_offset_days=5)

    result = load_urgences(db)

    assert result[0]["id"] == "u9"
    assert result[1]["id"] == "u8"


def test_pipeline_go_contains_high_score_tenders(db):
    from database import load_pipeline_data
    _add_tender(db, "p1", "SSI Prioritaire", score=75, deadline_offset_days=10, status="À qualifier")

    data = load_pipeline_data(db)

    assert "p1" in [t.id for t in data["go"]]
    assert "p1" not in [t.id for t in data["soumis"]]
    assert "p1" not in [t.id for t in data["resultats"]]


def test_pipeline_excludes_low_score_from_go(db):
    from database import load_pipeline_data
    _add_tender(db, "p2", "Divers travaux", score=40, deadline_offset_days=10, status="À qualifier")

    data = load_pipeline_data(db)

    assert "p2" not in [t.id for t in data["go"]]


def test_pipeline_soumis_column(db):
    from database import load_pipeline_data
    _add_tender(db, "p3", "CMSI Hôpital", score=80, deadline_offset_days=10, status="Soumis")

    data = load_pipeline_data(db)

    assert "p3" in [t.id for t in data["soumis"]]
    assert "p3" not in [t.id for t in data["go"]]


def test_pipeline_resultats_column(db):
    from database import load_pipeline_data
    _add_tender(db, "p4", "SSI Gagné", score=80, deadline_offset_days=10, status="Gagné")
    _add_tender(db, "p5", "SSI Perdu", score=80, deadline_offset_days=10, status="Perdu")

    data = load_pipeline_data(db)

    ids = [t.id for t in data["resultats"]]
    assert "p4" in ids
    assert "p5" in ids


def test_pipeline_go_sorted_by_deadline_asc(db):
    from database import load_pipeline_data
    _add_tender(db, "p6", "SSI A", score=80, deadline_offset_days=20)
    _add_tender(db, "p7", "SSI B", score=80, deadline_offset_days=5)

    data = load_pipeline_data(db)

    ids = [t.id for t in data["go"]]
    assert ids.index("p7") < ids.index("p6")
