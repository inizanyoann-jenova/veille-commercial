import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
import pytest


# ── Tests scraper_decp ─────────────────────────────────────────────────────

def test_fetch_decp_returns_zero_on_empty_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [], "total_count": 0}
    mock_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_resp):
        from scraper_decp import fetch_decp_tenders
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Base
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                result = fetch_decp_tenders()
    assert result == 0


def test_fetch_decp_inserts_relevant_record():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "results": [{
            "uid": "DECP-TEST-001",
            "objet": "Maintenance SSI alarme incendie La Réunion",
            "acheteur": {"nom": "CHU Réunion"},
            "dateNotification": "2025-03-01",
            "montant": 50000,
            "urlpublication": "https://data.economie.gouv.fr/test",
            "codeDepartementAcheteur": "974",
        }],
        "total_count": 1,
    }

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.get", return_value=mock_resp):
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                from scraper_decp import fetch_decp_tenders
                result = fetch_decp_tenders()

    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert len(tenders) == 1
    assert "SSI" in tenders[0].title or "incendie" in tenders[0].title.lower()


# ── Tests scraper_ungm ─────────────────────────────────────────────────────

def test_fetch_ungm_returns_zero_on_empty_html():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.text = "<html><body>No results</body></html>"
    mock_resp.status_code = 200

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.post", return_value=mock_resp):
        with patch("requests.get", return_value=mock_resp):
            with patch("scraper_ungm.SessionLocal", Session):
                with patch("scraper_ungm.init_db"):
                    from scraper_ungm import fetch_ungm_tenders
                    result = fetch_ungm_tenders()
    assert result == 0


# ── Tests scraper_devbanks — UNDP / ADB ───────────────────────────────────────

def test_fetch_devbanks_undp_inserted():
    """Un flux UNDP avec une entrée OI/construction doit être inséré."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda k, default="": {
        "title": "UNDP Procurement — Construction hospital Madagascar",
        "summary": "Construction of new hospital infrastructure in madagascar health",
        "link": "https://procurement-notices.undp.org/view_notice.cfm?notice_id=99999",
    }.get(k, default)
    mock_entry.published = None
    mock_entry.updated = None

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    import feedparser
    with patch("feedparser.parse", return_value=mock_feed):
        with patch("scraper_devbanks.SessionLocal", Session):
            with patch("scraper_devbanks.init_db"):
                from scraper_devbanks import fetch_devbanks
                result = fetch_devbanks()

    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result >= 1
    assert any("UNDP" in t.title or "madagascar" in t.title.lower() for t in tenders)


def test_fetch_devbanks_irrelevant_skipped():
    """Une entrée sans lien OI/secteur ne doit pas être insérée."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda k, default="": {
        "title": "Project in Germany — Software Development",
        "summary": "IT consulting project in Berlin",
        "link": "https://www.adb.org/projects/12345",
    }.get(k, default)
    mock_entry.published = None
    mock_entry.updated = None

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    with patch("feedparser.parse", return_value=mock_feed):
        with patch("scraper_devbanks.SessionLocal", Session):
            with patch("scraper_devbanks.init_db"):
                from scraper_devbanks import fetch_devbanks
                result = fetch_devbanks()

    assert result == 0
