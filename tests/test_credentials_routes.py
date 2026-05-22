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


def test_save_credential_known_site():
    with patch.object(_m, '_CredMgr') as mock_cm:
        resp = _client.post('/api/credentials/nukema',
                            json={'email': 'u@u.com', 'password': 'secret'})
    assert resp.status_code == 200
    assert resp.json()['ok'] is True
    mock_cm.save.assert_called_once_with('nukema', 'u@u.com', 'secret')


def test_save_credential_unknown_site():
    resp = _client.post('/api/credentials/nonexistent_xyz',
                        json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 404


def test_delete_credential_known_site():
    with patch.object(_m, '_CredMgr') as mock_cm:
        resp = _client.delete('/api/credentials/instao')
    assert resp.status_code == 200
    assert resp.json()['ok'] is True
    mock_cm.delete.assert_called_once_with('instao')


def test_delete_credential_unknown_site():
    resp = _client.delete('/api/credentials/nonexistent_xyz')
    assert resp.status_code == 404


def test_test_credential_public_site_skips_playwright():
    """Sites without login URL return ok=True immediately."""
    resp = _client.post('/api/credentials/vaao/test',
                        json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert 'message' in body


def test_test_credential_playwright_success():
    import json as _json_mod
    mock_proc = MagicMock()
    mock_proc.stdout = _json_mod.dumps({'ok': True, 'url_finale': 'https://nukema.com/dashboard'})
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.return_value = mock_proc
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'correct'})
    assert resp.status_code == 200
    assert resp.json()['ok'] is True


def test_test_credential_playwright_wrong_password():
    import json as _json_mod
    mock_proc = MagicMock()
    mock_proc.stdout = _json_mod.dumps({'ok': False, 'erreur_page': 'Mot de passe erroné'})
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.return_value = mock_proc
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'wrong'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is False
    assert body['message'] == 'Identifiants incorrects : Mot de passe erroné'


def test_test_credential_playwright_timeout():
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.side_effect = TimeoutError()
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is False
    assert 'expiré' in body['message']


def test_test_credential_playwright_missing_selector():
    import json as _json_mod
    mock_proc = MagicMock()
    mock_proc.stdout = _json_mod.dumps({'ok': False, 'champ_manquant': '#login'})
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.return_value = mock_proc
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is False
    assert body['message'] == 'Champ introuvable — sélecteur CSS à mettre à jour'


def test_test_credential_playwright_no_redirect():
    import json as _json_mod
    mock_proc = MagicMock()
    mock_proc.stdout = _json_mod.dumps({'ok': False, 'no_redirect': True})
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.return_value = mock_proc
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is False
    assert body['message'] == 'Connexion refusée sans message d\'erreur'


def test_test_credential_unknown_site_returns_404():
    resp = _client.post('/api/credentials/nonexistent_xyz/test',
                        json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 404
