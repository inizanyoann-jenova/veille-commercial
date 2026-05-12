import os
import sys
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
import database as _db
from models import Credential

load_dotenv()
log = logging.getLogger(__name__)

# Module-level alias — preserve existing value on reload so test patches survive
if "credential_manager" not in sys.modules or not hasattr(sys.modules.get("credential_manager", None), "SessionLocal"):
    SessionLocal = _db.SessionLocal


def _session_factory():
    """Indirection so patching credential_manager.SessionLocal is always honoured."""
    return sys.modules[__name__].SessionLocal()

_ENV_MAP: dict[str, tuple[str, str]] = {
    "vaao":               ("VAAO_EMAIL",             "VAAO_PASSWORD"),
    "marcheonline":       ("MARCHEONLINE_EMAIL",      "MARCHEONLINE_PASSWORD"),
    "nukema":             ("NUKEMA_EMAIL",             "NUKEMA_PASSWORD"),
    "dept974":            ("DEPT974_EMAIL",            "DEPT974_PASSWORD"),
    "marchespublicsinfo": ("MARCHESPUBLICSINFO_EMAIL", "MARCHESPUBLICSINFO_PASSWORD"),
    "marches_securises":  ("MARCHES_SEC_EMAIL",        "MARCHES_SEC_PASSWORD"),
    "instao":             ("INSTAO_EMAIL",             "INSTAO_PASSWORD"),
    "tendersgo":          ("TENDERSGO_EMAIL",          "TENDERSGO_PASSWORD"),
}


def _get_fernet() -> Fernet:
    key = os.getenv("CREDENTIAL_KEY")
    if not key:
        key = Fernet.generate_key().decode()
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        set_key(env_path, "CREDENTIAL_KEY", key)
        os.environ["CREDENTIAL_KEY"] = key
        log.info("CREDENTIAL_KEY generated and saved to .env")
    return Fernet(key.encode() if isinstance(key, str) else key)


class CredentialManager:
    @staticmethod
    def get(site: str) -> tuple[str, str] | None:
        email_var, pwd_var = _ENV_MAP.get(site, (f"{site.upper()}_EMAIL", f"{site.upper()}_PASSWORD"))
        email = os.getenv(email_var)
        pwd = os.getenv(pwd_var)
        if email and pwd:
            return (email, pwd)
        db = _session_factory()
        try:
            cred = db.query(Credential).filter(Credential.site == site).first()
            if cred:
                return (cred.email, _get_fernet().decrypt(cred.password.encode()).decode())
        finally:
            db.close()
        return None

    @staticmethod
    def save(site: str, email: str, password: str) -> None:
        encrypted = _get_fernet().encrypt(password.encode()).decode()
        db = _session_factory()
        try:
            cred = db.query(Credential).filter(Credential.site == site).first()
            if cred:
                cred.email = email
                cred.password = encrypted
            else:
                db.add(Credential(site=site, email=email, password=encrypted))
            db.commit()
        finally:
            db.close()

    @staticmethod
    def delete(site: str) -> None:
        db = _session_factory()
        try:
            cred = db.query(Credential).filter(Credential.site == site).first()
            if cred:
                db.delete(cred)
                db.commit()
        finally:
            db.close()

    @staticmethod
    def list_configured() -> list[dict]:
        result = []
        db = _session_factory()
        try:
            for cred in db.query(Credential).all():
                email_var, _ = _ENV_MAP.get(cred.site, (f"{cred.site.upper()}_EMAIL", ""))
                result.append({
                    "site": cred.site,
                    "email": cred.email,
                    "has_env_override": bool(os.getenv(email_var)),
                })
        finally:
            db.close()
        for site, (email_var, _) in _ENV_MAP.items():
            if os.getenv(email_var) and not any(r["site"] == site for r in result):
                result.append({
                    "site": site,
                    "email": os.getenv(email_var),
                    "has_env_override": True,
                })
        return result
