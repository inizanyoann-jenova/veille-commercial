import sys
import os
import secrets

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from models import Base, Credential


def _make_test_session():
    """In-memory engine with StaticPool so all Session() calls share the same DB."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_get_returns_none_when_nothing_configured():
    Session = _make_test_session()
    clean_env = {k: v for k, v in os.environ.items()
                 if not k.endswith(("_EMAIL", "_PASSWORD", "CREDENTIAL_KEY"))}
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, clean_env, clear=True):
            from credential_manager import CredentialManager
            result = CredentialManager.get("instao")
    assert result is None


def test_get_returns_env_vars_first():
    Session = _make_test_session()
    env = {"INSTAO_EMAIL": "test@test.com", "INSTAO_PASSWORD": secrets.token_urlsafe(12)}
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, env):
            from credential_manager import CredentialManager
            result = CredentialManager.get("instao")
    assert result == ("test@test.com", env["INSTAO_PASSWORD"])


def test_save_and_get_from_db():
    Session = _make_test_session()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    pwd = secrets.token_urlsafe(16)
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, {"CREDENTIAL_KEY": key}):
            from credential_manager import CredentialManager
            CredentialManager.save("instao", "user@mail.com", pwd)
            result = CredentialManager.get("instao")
    assert result == ("user@mail.com", pwd)


def test_delete_removes_credential():
    Session = _make_test_session()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, {"CREDENTIAL_KEY": key}):
            from credential_manager import CredentialManager
            CredentialManager.save("instao", "u@u.com", secrets.token_urlsafe(8))
            CredentialManager.delete("instao")
            result = CredentialManager.get("instao")
    assert result is None


def test_list_configured_shows_saved_sites():
    Session = _make_test_session()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, {"CREDENTIAL_KEY": key}):
            from credential_manager import CredentialManager
            CredentialManager.save("tendersgo", "a@a.com", secrets.token_urlsafe(8))
            sites = CredentialManager.list_configured()
    assert any(s["site"] == "tendersgo" for s in sites)
