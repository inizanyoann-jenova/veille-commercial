import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
import main as _m
from database import get_db

_client = TestClient(_m.app)


def _override_db(rows=None):
    """FastAPI dependency override returning a mock DB session."""
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = rows or []
    def _get_fake_db():
        yield mock_db
    return _get_fake_db


def test_get_credentials_returns_8_sites():
    _m.app.dependency_overrides[get_db] = _override_db()
    try:
        with patch.dict('os.environ', {}, clear=True):
            resp = _client.get('/api/credentials')
    finally:
        _m.app.dependency_overrides.clear()
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    sites = {d['site'] for d in data}
    assert 'nukema' in sites
    assert 'vaao' in sites
    assert 'instao' in sites


def test_get_credentials_missing_status():
    _m.app.dependency_overrides[get_db] = _override_db()
    try:
        with patch.dict('os.environ', {}, clear=True):
            resp = _client.get('/api/credentials')
    finally:
        _m.app.dependency_overrides.clear()
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
    _m.app.dependency_overrides[get_db] = _override_db([mock_cred])
    try:
        with patch.dict('os.environ', {}, clear=True):
            resp = _client.get('/api/credentials')
    finally:
        _m.app.dependency_overrides.clear()
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'configured'
    assert nukema['email'] == 'user@test.com'


def test_get_credentials_env_override():
    _m.app.dependency_overrides[get_db] = _override_db()
    try:
        with patch.dict('os.environ', {'NUKEMA_EMAIL': 'env@test.com'}, clear=True):
            resp = _client.get('/api/credentials')
    finally:
        _m.app.dependency_overrides.clear()
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'env_override'
    assert nukema['email'] == 'env@test.com'


def test_get_credentials_public_site_has_no_login_url():
    _m.app.dependency_overrides[get_db] = _override_db()
    try:
        with patch.dict('os.environ', {}, clear=True):
            resp = _client.get('/api/credentials')
    finally:
        _m.app.dependency_overrides.clear()
    vaao = next(d for d in resp.json() if d['site'] == 'vaao')
    assert vaao['has_login_url'] is False


def test_get_credentials_env_overrides_db():
    """env_override wins even when DB also has a credential for the same site."""
    from models import Credential
    mock_cred = MagicMock(spec=Credential)
    mock_cred.site = 'nukema'
    mock_cred.email = 'db@test.com'
    _m.app.dependency_overrides[get_db] = _override_db([mock_cred])
    try:
        with patch.dict('os.environ', {'NUKEMA_EMAIL': 'env@test.com'}, clear=True):
            resp = _client.get('/api/credentials')
    finally:
        _m.app.dependency_overrides.clear()
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'env_override'
    assert nukema['email'] == 'env@test.com'
