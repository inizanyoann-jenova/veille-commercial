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
