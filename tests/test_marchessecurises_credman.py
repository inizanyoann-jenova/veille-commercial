import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock


def test_marchessecurises_uses_credential_manager(monkeypatch):
    """scraper_marchessecurises.fetch() doit appeler CredentialManager.get('marches_securises'),
    pas os.getenv('MARCHESSECURISES_LOGIN') direct."""
    import scraper_marchessecurises

    mock_cm = MagicMock()
    mock_cm.get.return_value = None  # pas de credentials → retour []
    monkeypatch.setattr(scraper_marchessecurises, "CredentialManager", mock_cm)

    result = scraper_marchessecurises.fetch()

    mock_cm.get.assert_called_once_with("marches_securises")
    assert result == []


def test_marchessecurises_returns_empty_without_credentials(monkeypatch):
    """Sans credentials dans CredentialManager, fetch() retourne []."""
    import scraper_marchessecurises

    mock_cm = MagicMock()
    mock_cm.get.return_value = None
    monkeypatch.setattr(scraper_marchessecurises, "CredentialManager", mock_cm)

    result = scraper_marchessecurises.fetch()
    assert result == []
