import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base
import pytest


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_nukema_reports_error_when_auth_fails_cross_subdomain(db):
    """Quand la navigation post-login redirige vers /connexion (cookies cross-subdomain perdus),
    le scraper doit retourner 0 ET appeler finish_scraper_run avec un message d'erreur explicite."""
    from scraper_nukema import fetch_nukema_tenders

    mock_finish = MagicMock()

    with patch("scraper_nukema.sync_playwright") as pw_mock, \
         patch("scraper_nukema.SessionLocal", return_value=db), \
         patch("scraper_nukema.init_db"), \
         patch("scraper_nukema.start_scraper_run", return_value=1), \
         patch("scraper_nukema.finish_scraper_run", mock_finish), \
         patch("scraper_nukema.CredentialManager.get", return_value=("user@test.com", "pass")), \
         patch("scraper_nukema.login", return_value=True):

        browser = pw_mock.return_value.__enter__.return_value.chromium.launch.return_value
        page = browser.new_page.return_value
        type(page).url = PropertyMock(return_value="https://marches-publics.nukema.com/connexion")

        result = fetch_nukema_tenders()

    assert result == 0, f"Attendu 0, obtenu {result}"

    error_calls = [
        c for c in mock_finish.call_args_list
        if c.kwargs.get("error") or (len(c.args) > 4 and c.args[4])
    ]
    assert error_calls, (
        "finish_scraper_run doit être appelé avec error= quand auth cross-subdomain échoue. "
        f"Appels reçus : {mock_finish.call_args_list}"
    )
