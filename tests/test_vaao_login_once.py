import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch


def _make_pw_mock():
    mock_page = MagicMock()
    mock_page.url = "https://www.vaao.fr/results"
    mock_page.query_selector_all.return_value = []
    mock_page.query_selector.return_value = None
    mock_page.content.return_value = "<html></html>"

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw, mock_page, mock_browser


def test_vaao_login_called_exactly_once(monkeypatch):
    """Même avec plusieurs URLs, _login ne doit être appelé qu'une seule fois."""
    import scraper_vaao

    assert len(scraper_vaao._URLS) > 1, "Ce test n'a de sens qu'avec plusieurs URLs"

    mock_pw, mock_page, mock_browser = _make_pw_mock()
    login_calls = []

    def fake_login(page, email, password):
        login_calls.append((email, password))
        return True

    monkeypatch.setattr(scraper_vaao, "_login", fake_login)

    with patch("credential_manager.CredentialManager") as mock_cm:
        mock_cm.get.return_value = ("user@test.com", "pass123")
        with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
            scraper_vaao.fetch()

    assert len(login_calls) == 1, (
        f"_login appelé {len(login_calls)} fois au lieu de 1 — "
        "le login doit être factorisé hors de la boucle sur _URLS"
    )


def test_vaao_new_page_called_once(monkeypatch):
    """Une seule page Playwright doit être créée (session partagée pour toutes les URLs)."""
    import scraper_vaao

    mock_pw, mock_page, mock_browser = _make_pw_mock()
    monkeypatch.setattr(scraper_vaao, "_login", lambda page, e, p: True)

    with patch("credential_manager.CredentialManager") as mock_cm:
        mock_cm.get.return_value = ("user@test.com", "pass123")
        with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
            scraper_vaao.fetch()

    assert mock_browser.new_page.call_count == 1, (
        f"browser.new_page() appelé {mock_browser.new_page.call_count} fois — "
        "doit être appelé une seule fois avant la boucle"
    )
