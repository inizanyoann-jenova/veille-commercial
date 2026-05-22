import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
import main as _m

_client = TestClient(_m.app)


def _mock_db(rows=None):
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = rows or []
    mock_db.close = MagicMock()
    return mock_db


def test_get_credentials_returns_8_sites():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    sites = {d['site'] for d in data}
    assert 'nukema' in sites
    assert 'vaao' in sites
    assert 'instao' in sites


def test_get_credentials_missing_status():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    assert resp.status_code == 200
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'missing'
    assert nukema['email'] is None
    assert nukema['has_login_url'] is True


def test_get_credentials_configured_status():
    from models import Credential
    mock_cred = MagicMock(spec=Credential)
    mock_cred.site = 'nukema'
    mock_cred.email = 'user@test.com'
    with patch.object(_m, 'SessionLocal', return_value=_mock_db([mock_cred])), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'configured'
    assert nukema['email'] == 'user@test.com'


def test_get_credentials_env_override():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {'NUKEMA_EMAIL': 'env@test.com'}, clear=False):
        resp = _client.get('/api/credentials')
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'env_override'
    assert nukema['email'] == 'env@test.com'


def test_get_credentials_public_site_has_no_login_url():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    vaao = next(d for d in resp.json() if d['site'] == 'vaao')
    assert vaao['has_login_url'] is False
