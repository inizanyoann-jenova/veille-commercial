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
            "id": "DECP-TEST-001",
            "objetmarche": "Maintenance SSI alarme incendie La Réunion",
            "nomacheteur": "CHU Réunion",
            "datenotification": "2025-03-01",
            "montant": 50000,
            "urlpublication": "https://data.economie.gouv.fr/test",
            "codedepartementexecution": "974",
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


def test_fetch_decp_inserts_public_erp_implicit_record():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "results": [{
            "id": "DECP-ERP-001",
            "objetmarche": "Construction d'un nouveau collège à La Réunion",
            "nomacheteur": "Département de La Réunion",
            "datenotification": "2026-05-01",
            "codedepartementexecution": "974",
        }],
        "total_count": 1,
    }

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                from scraper_decp import fetch_decp_tenders
                result = fetch_decp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    db = Session()
    tenders = db.query(Tender).all()
    db.close()

    assert "construction" in where_clause
    assert "collège" in where_clause
    assert result == 1
    assert len(tenders) == 1
    assert "Potentiel SSI implicite" in tenders[0].tags


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


# ── Tests scraper_ted ─────────────────────────────────────────────────────────

def test_ted_api_url_is_v3():
    import importlib
    import scraper_ted
    importlib.reload(scraper_ted)
    assert scraper_ted.TED_API_URL == "https://ted.europa.eu/api/v3.0/notices/search"


def test_ted_mayotte_query_includes_city_variants():
    import importlib
    import scraper_ted
    importlib.reload(scraper_ted)
    q = scraper_ted.QUERIES["Mayotte"]
    assert "Mamoudzou" in q
    assert "Dzaoudzi" in q
    assert "Mahorais" in q


def test_ted_public_search_includes_cpv():
    import importlib
    import scraper_ted
    importlib.reload(scraper_ted)
    assert "PC~45312100" in scraper_ted._PUBLIC_SEARCH
    assert "PC~50610000" in scraper_ted._PUBLIC_SEARCH


def test_ted_fetch_sends_date_filter():
    """Le payload envoyé à l'API doit contenir un filtre de date PD>=."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"notices": []}

    captured_payloads = []

    def fake_retry_post(url, json=None, **kwargs):
        captured_payloads.append(json or {})
        return mock_resp

    import importlib, scraper_ted
    importlib.reload(scraper_ted)

    with patch("scraper_ted.retry_post", side_effect=fake_retry_post):
        with patch("scraper_ted.SessionLocal", Session):
            with patch("scraper_ted.init_db"):
                scraper_ted.fetch_ted_tenders(zones=["La Réunion"])

    assert len(captured_payloads) > 0
    assert "PD>=" in captured_payloads[0].get("query", "")


# ── Tests DECP CPV + fenêtre temporelle ──────────────────────────────────────

def test_decp_cpv_filter_in_where_clause():
    """Le where DECP doit inclure les codes CPV SSI."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                import importlib, scraper_decp
                importlib.reload(scraper_decp)
                scraper_decp.fetch_decp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    assert "45312100" in where_clause
    assert "50610000" in where_clause


def test_decp_window_defaults_to_90_days():
    """La fenêtre par défaut doit être 90 jours (pas 3 ans)."""
    import os
    from datetime import datetime, timedelta
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    os.environ.pop("SCRAPER_WINDOW_DAYS", None)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                import importlib, scraper_decp
                importlib.reload(scraper_decp)
                scraper_decp.fetch_decp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    expected_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert expected_date in where_clause


# ── Tests BOAMP fenêtre temporelle ───────────────────────────────────────────

def test_boamp_window_defaults_to_90_days():
    """La fenêtre par défaut doit être 90 jours (pas 2 ans)."""
    import os
    from datetime import datetime, timedelta
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    os.environ.pop("SCRAPER_WINDOW_DAYS", None)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_boamp.SessionLocal", Session):
            with patch("scraper_boamp.init_db"):
                import importlib, scraper_boamp
                importlib.reload(scraper_boamp)
                scraper_boamp.fetch_boamp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    expected_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert expected_date in where_clause
