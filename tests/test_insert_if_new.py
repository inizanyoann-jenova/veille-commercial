import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender
from scraper_utils import insert_if_new


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_tender(**kwargs) -> Tender:
    defaults = dict(
        id="T-001",
        title="Marché test",
        source="https://example.com",
        publication_date=None,
        status="À qualifier",
        relevance_score=0,
        is_maintenance=False,
        is_blacklisted=False,
        secteur="Public",
        tags=[],
    )
    defaults.update(kwargs)
    return Tender(**defaults)


def test_insert_if_new_logs_warning_when_no_date(db, caplog):
    t = _make_tender(id="T-001", publication_date=None)
    known: set = set()
    with caplog.at_level(logging.WARNING, logger="scraper_utils"):
        result = insert_if_new(db, t, known)
    assert result is False
    assert any("date" in r.message.lower() or "T-001" in r.message for r in caplog.records)


def test_insert_if_new_no_log_when_too_old(db, caplog):
    """Tender trop ancien : pas de log date manquante (date présente mais périmée)."""
    old = datetime(2000, 1, 1)
    t = _make_tender(id="T-002", publication_date=old)
    known: set = set()
    with caplog.at_level(logging.WARNING, logger="scraper_utils"):
        result = insert_if_new(db, t, known)
    assert result is False
    assert len(caplog.records) == 0


def test_insert_if_new_inserts_valid_tender(db):
    pub = datetime.now() - timedelta(days=5)
    t = _make_tender(id="T-003", publication_date=pub)
    known: set = set()
    result = insert_if_new(db, t, known)
    assert result is True
    assert "T-003" in known


def test_insert_if_new_rejects_duplicate(db):
    pub = datetime.now() - timedelta(days=5)
    t = _make_tender(id="T-004", publication_date=pub)
    known: set = {"T-004"}
    result = insert_if_new(db, t, known)
    assert result is False


def test_insert_if_new_rejects_invalid_date_string(db):
    """Publication_date est une chaîne ISO invalide : tender rejeté sans exception."""
    t = _make_tender(id="T-005", publication_date="not-a-date")
    known: set = set()
    result = insert_if_new(db, t, known)
    assert result is False
    assert "T-005" not in known


def test_insert_if_new_accepts_aware_datetime(db):
    """Un datetime timezone-aware récent doit être inséré, pas rejeté silencieusement."""
    from datetime import timezone
    pub = datetime.now(timezone.utc) - timedelta(days=5)
    t = _make_tender(id="T-006", publication_date=pub)
    known: set = set()
    result = insert_if_new(db, t, known)
    assert result is True, "datetime aware rejeté alors qu'il est récent"
    assert "T-006" in known


def test_insert_if_new_rejects_old_aware_datetime(db):
    """Un datetime timezone-aware trop ancien doit être rejeté."""
    from datetime import timezone
    pub = datetime.now(timezone.utc) - timedelta(days=365)
    t = _make_tender(id="T-007", publication_date=pub)
    known: set = set()
    result = insert_if_new(db, t, known)
    assert result is False
