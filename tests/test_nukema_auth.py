import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock


def _make_pw_mock(page_url: str):
    """Return a sync_playwright mock whose page always reports page_url."""
    mock_page = MagicMock()
    mock_page.url = page_url
    mock_page.query_selector_all.return_value = []
    mock_page.query_selector.return_value = None

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw


def test_nukema_returns_empty_when_cross_subdomain_auth_fails():
    """Quand page.url contient 'connexion' après navigation (cookies cross-subdomain perdus),
    le scraper doit ignorer l'URL et retourner une liste vide."""
    os.environ["NUKEMA_EMAIL"] = "test@test.com"
    os.environ["NUKEMA_PASSWORD"] = "pass"
    try:
        mock_pw = _make_pw_mock("https://marches-publics.nukema.com/connexion")
        with patch("scraper_nukema.sync_playwright", return_value=mock_pw):
            import scraper_nukema

            result = scraper_nukema.fetch()
        assert result == [], f"Attendu [], obtenu {result}"
    finally:
        os.environ.pop("NUKEMA_EMAIL", None)
        os.environ.pop("NUKEMA_PASSWORD", None)
