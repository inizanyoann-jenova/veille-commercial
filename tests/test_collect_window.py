import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender
import scraper_utils


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_tender(id: str, days_old: int) -> Tender:
    pub = datetime.now() - timedelta(days=days_old)
    return Tender(
        id=id,
        title=f"Marché {id}",
        source="https://example.com",
        publication_date=pub,
        status="À qualifier",
        relevance_score=0,
        is_maintenance=False,
        is_blacklisted=False,
        secteur="Public",
        tags=[],
    )


def test_default_window_is_30_days(monkeypatch):
    """Sans variable d'env, la fenêtre par défaut est 30 jours."""
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    assert scraper_utils._INSERT_MAX_AGE_DAYS == 30


def test_window_reads_env(monkeypatch):
    """Avec SCRAPER_WINDOW_DAYS=60, la fenêtre passe à 60 jours."""
    monkeypatch.setenv("SCRAPER_WINDOW_DAYS", "60")
    importlib.reload(scraper_utils)
    assert scraper_utils._INSERT_MAX_AGE_DAYS == 60


def test_tender_at_29_days_is_inserted(db, monkeypatch):
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    t = _make_tender("A-029", days_old=29)
    known: set = set()
    assert scraper_utils.insert_if_new(db, t, known) is True


def test_tender_at_31_days_is_rejected(db, monkeypatch):
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    t = _make_tender("A-031", days_old=31)
    known: set = set()
    assert scraper_utils.insert_if_new(db, t, known) is False


def test_boamp_default_window_matches_insert_window(monkeypatch):
    """Le défaut de BOAMP (SCRAPER_WINDOW_DAYS non défini) doit correspondre à _INSERT_MAX_AGE_DAYS."""
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    boamp_default = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
    assert boamp_default == scraper_utils._INSERT_MAX_AGE_DAYS
