import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock
import requests
from scraper_utils import retry_get


def _make_ok_response(json_data: dict) -> MagicMock:
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_retry_get_passes_headers(monkeypatch):
    """retry_get doit transmettre les headers à requests.get."""
    calls = []

    def fake_get(url, params=None, headers=None, timeout=30):
        calls.append({"url": url, "headers": headers})
        return _make_ok_response({})

    monkeypatch.setattr(requests, "get", fake_get)
    retry_get("https://example.com", headers={"User-Agent": "test-bot/1.0"})
    assert calls[0]["headers"] == {"User-Agent": "test-bot/1.0"}


def test_retry_get_works_without_headers(monkeypatch):
    """retry_get sans headers ne lève pas d'erreur."""
    def fake_get(url, params=None, headers=None, timeout=30):
        return _make_ok_response({})

    monkeypatch.setattr(requests, "get", fake_get)
    resp = retry_get("https://example.com")
    assert resp is not None


def test_retry_get_retries_on_timeout(monkeypatch):
    """retry_get doit réessayer en cas de timeout."""
    attempt = [0]

    def fake_get(url, params=None, headers=None, timeout=30):
        attempt[0] += 1
        if attempt[0] < 2:
            raise requests.exceptions.Timeout()
        return _make_ok_response({})

    monkeypatch.setattr("time.sleep", lambda _: None)
    monkeypatch.setattr(requests, "get", fake_get)
    resp = retry_get("https://example.com", retries=3)
    assert attempt[0] == 2
