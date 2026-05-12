import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender
import pytest


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _mock_pw_context(cards_html=None):
    """Retourne (mock_sync_playwright, mock_page) prêts à injecter."""
    mock_page = MagicMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.query_selector.return_value = None  # pas de bouton "suivant"
    if cards_html:
        mock_cards = []
        for data in cards_html:
            card = MagicMock()
            def make_qs(d):
                def qs(sel):
                    child = MagicMock()
                    child.inner_text.return_value = d.get("text", "")
                    child.get_attribute.return_value = d.get("href", "")
                    return child
                return qs
            card.query_selector.side_effect = make_qs(data)
            mock_cards.append(card)
        mock_page.query_selector_all.return_value = mock_cards
    else:
        mock_page.query_selector_all.return_value = []

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw, mock_page


# ── VAAO ─────────────────────────────────────────────────────────────────────

def test_fetch_vaao_empty_page():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_vaao.SessionLocal", Session):
            with patch("scraper_vaao.init_db"):
                from scraper_vaao import fetch_vaao_tenders
                result = fetch_vaao_tenders()
    assert result == 0


def test_fetch_vaao_inserts_relevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_vaao.extract_cards", return_value=[{
            "title": "Installation SSI alarme incendie Réunion",
            "description": "",
            "url": "https://www.vaao.fr/ao/1",
            "date": "15/04/2026",
        }]):
            with patch("scraper_vaao.paginate", return_value=False):
                with patch("scraper_vaao.SessionLocal", Session):
                    with patch("scraper_vaao.init_db"):
                        from scraper_vaao import fetch_vaao_tenders
                        result = fetch_vaao_tenders()
    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert len(tenders) == 1


# ── Marché Online ─────────────────────────────────────────────────────────────

def test_fetch_marcheonline_empty():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_marcheonline.extract_cards", return_value=[]):
            with patch("scraper_marcheonline.paginate", return_value=False):
                with patch("scraper_marcheonline.SessionLocal", Session):
                    with patch("scraper_marcheonline.init_db"):
                        from scraper_marcheonline import fetch_marcheonline_tenders
                        result = fetch_marcheonline_tenders()
    assert result == 0


# ── Nukema ────────────────────────────────────────────────────────────────────

def test_fetch_nukema_inserts_relevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_nukema.extract_cards", return_value=[{
            "title": "Maintenance CCTV vidéosurveillance campus universitaire",
            "description": "Mayotte 976",
            "url": "https://marches-publics.nukema.com/consultation/12345",
            "date": "10/05/2026",
        }]):
            with patch("scraper_nukema.paginate", return_value=False):
                with patch("scraper_nukema.SessionLocal", Session):
                    with patch("scraper_nukema.init_db"):
                        with patch("scraper_nukema.CredentialManager.get", return_value=None):
                            from scraper_nukema import fetch_nukema_tenders
                            result = fetch_nukema_tenders()
    assert result == 1


# ── Marchés Sécurisés ─────────────────────────────────────────────────────────

def test_fetch_marchessecurises_skips_without_creds():
    Session = _db_session()
    with patch("credential_manager.CredentialManager.get", return_value=None):
        with patch("scraper_marchessecurises.SessionLocal", Session):
            with patch("scraper_marchessecurises.init_db"):
                from scraper_marchessecurises import fetch_marchessecurises_tenders
                result = fetch_marchessecurises_tenders()
    assert result == 0


def test_fetch_marchessecurises_with_creds_inserts():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("credential_manager.CredentialManager.get", return_value=("u@u.com", "pass")):
        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            with patch("scraper_marchessecurises.login", return_value=True):
                with patch("scraper_marchessecurises.extract_cards", return_value=[{
                    "title": "Maintenance SSI incendie établissement public",
                    "description": "La Réunion 974",
                    "url": "https://www.marches-securises.fr/ao/99",
                    "date": "01/05/2026",
                }]):
                    with patch("scraper_marchessecurises.paginate", return_value=False):
                        with patch("scraper_marchessecurises.SessionLocal", Session):
                            with patch("scraper_marchessecurises.init_db"):
                                from scraper_marchessecurises import fetch_marchessecurises_tenders
                                result = fetch_marchessecurises_tenders()
    assert result == 1


# ── Instao ────────────────────────────────────────────────────────────────────

def test_fetch_instao_skips_without_creds():
    Session = _db_session()
    with patch("credential_manager.CredentialManager.get", return_value=None):
        with patch("scraper_instao.SessionLocal", Session):
            with patch("scraper_instao.init_db"):
                from scraper_instao import fetch_instao_tenders
                result = fetch_instao_tenders()
    assert result == 0


# ── Tenders Go ────────────────────────────────────────────────────────────────

def test_fetch_tendersgo_skips_without_creds():
    Session = _db_session()
    with patch("credential_manager.CredentialManager.get", return_value=None):
        with patch("scraper_tendersgo.SessionLocal", Session):
            with patch("scraper_tendersgo.init_db"):
                from scraper_tendersgo import fetch_tendersgo_tenders
                result = fetch_tendersgo_tenders()
    assert result == 0
