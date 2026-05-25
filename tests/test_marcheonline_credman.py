import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock


def _make_pw_mock():
    mock_page = MagicMock()
    mock_page.url = "https://www.marchesonline.com/appels-offres"
    mock_page.content.return_value = "<html></html>"
    mock_page.query_selector_all.return_value = []
    mock_page.query_selector.return_value = None

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser
    return mock_pw


def test_marcheonline_uses_credential_manager(monkeypatch):
    """scraper_marcheonline.fetch() doit appeler CredentialManager.get('marcheonline'),
    pas os.getenv('MARCHEONLINE_EMAIL') direct."""
    import scraper_marcheonline

    mock_cm = MagicMock()
    mock_cm.get.return_value = None  # pas de credentials → pas de login
    monkeypatch.setattr(scraper_marcheonline, "CredentialManager", mock_cm)

    mock_pw = _make_pw_mock()
    with patch("scraper_marcheonline.sync_playwright", return_value=mock_pw):
        result = scraper_marcheonline.fetch()

    mock_cm.get.assert_called_once_with("marcheonline")
    assert result == []
