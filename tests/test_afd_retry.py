import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock
import requests


def _mock_empty_response():
    m = MagicMock(spec=requests.Response)
    m.status_code = 200
    m.json.return_value = {"results": []}
    m.raise_for_status.return_value = None
    return m


def test_afd_fetch_uses_retry_get(monkeypatch):
    """scraper_afd.fetch() doit appeler retry_get, pas requests.get directement."""
    import scraper_afd

    calls = []

    def fake_retry_get(url, **kwargs):
        calls.append(url)
        return _mock_empty_response()

    monkeypatch.setattr(scraper_afd, "retry_get", fake_retry_get)
    result = scraper_afd.fetch()

    assert len(calls) > 0, "retry_get n'a pas été appelé"
    assert result == []


def test_afd_fetch_breaks_on_retry_exception(monkeypatch):
    """Si retry_get lève RequestException, fetch() doit s'arrêter sans lever."""
    import scraper_afd

    def fake_retry_get(url, **kwargs):
        raise requests.exceptions.ConnectionError("réseau KO")

    monkeypatch.setattr(scraper_afd, "retry_get", fake_retry_get)
    result = scraper_afd.fetch()

    assert result == []
