import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock


def _mock_empty_response():
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"results": []}
    m.raise_for_status.return_value = None
    return m


def test_decp_fetch_uses_retry_get(monkeypatch):
    """scraper_decp.fetch() doit appeler retry_get, pas requests.get directement."""
    import scraper_decp

    calls = []

    def fake_retry_get(url, **kwargs):
        calls.append(url)
        return _mock_empty_response()

    monkeypatch.setattr(scraper_decp, "retry_get", fake_retry_get)
    result = scraper_decp.fetch()

    assert len(calls) > 0, "retry_get n'a pas été appelé"
    assert result == []


def test_decp_fetch_breaks_on_retry_exception(monkeypatch):
    """Si retry_get lève RequestException, fetch() doit s'arrêter sans lever."""
    import requests
    import scraper_decp

    def fake_retry_get(url, **kwargs):
        raise requests.exceptions.ConnectionError("réseau KO")

    monkeypatch.setattr(scraper_decp, "retry_get", fake_retry_get)
    result = scraper_decp.fetch()

    assert result == []
