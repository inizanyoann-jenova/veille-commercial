import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock
import requests


def _mock_empty_response():
    m = MagicMock(spec=requests.Response)
    m.status_code = 200
    m.json.return_value = []
    m.raise_for_status.return_value = None
    return m


def test_ungm_fetch_uses_retry_post(monkeypatch):
    """scraper_ungm._search_ungm() doit appeler retry_post, pas requests.post directement."""
    import scraper_ungm

    calls = []

    def fake_retry_post(url, **kwargs):
        calls.append(url)
        return _mock_empty_response()

    monkeypatch.setattr(scraper_ungm, "retry_post", fake_retry_post)
    result = scraper_ungm.fetch()

    assert len(calls) > 0, "retry_post n'a pas été appelé"
    assert result == []


def test_ungm_fetch_breaks_on_retry_exception(monkeypatch):
    """Si retry_post lève RequestException, fetch() doit retourner [] sans lever."""
    import scraper_ungm

    def fake_retry_post(url, **kwargs):
        raise requests.exceptions.ConnectionError("réseau KO")

    monkeypatch.setattr(scraper_ungm, "retry_post", fake_retry_post)
    result = scraper_ungm.fetch()

    assert result == []
