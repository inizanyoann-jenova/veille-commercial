# Nouveaux Scrapers + Paramètres + Guide — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Intégrer 8 nouvelles sources de collecte (VAAO, Marché Online, Dép. 974, Nukema, Marchés Public Info, Marchés Sécurisés, Instao, Tenders Go) via Playwright, avec gestion des identifiants chiffrés, une page Paramètres et une page Guide in-app.

**Architecture:** Module `playwright_base.py` partagé (lancement navigateur + helpers). `credential_manager.py` abstrait l'accès aux credentials (.env en priorité, SQLite chiffré Fernet sinon). 8 scrapers suivent exactement le pattern existant (`fetch_xxx() -> int`). Pages Streamlit multi-pages pour Paramètres et Guide.

**Tech Stack:** `playwright>=1.44.0`, `cryptography>=42.0.0`, SQLAlchemy, Streamlit 1.32+

---

## Fichiers créés / modifiés

| Fichier | Action |
|---------|--------|
| `requirements.txt` | Modifier — ajouter playwright, cryptography |
| `models.py` | Modifier — ajouter `Credential` |
| `database.py` | Modifier — créer table credentials |
| `source_registry.py` | Modifier — 8 nouvelles sources, nettoyer _DEFUNCT_URLS |
| `playwright_base.py` | Créer |
| `credential_manager.py` | Créer |
| `scraper_vaao.py` | Créer |
| `scraper_marcheonline.py` | Créer |
| `scraper_dept974.py` | Créer |
| `scraper_nukema.py` | Créer |
| `scraper_marchespublicsinfo.py` | Créer |
| `scraper_marchessecurises.py` | Créer |
| `scraper_instao.py` | Créer |
| `scraper_tendersgo.py` | Créer |
| `pages/parametres.py` | Créer |
| `pages/guide.py` | Créer |
| `app.py` | Modifier — liens sidebar Paramètres + Guide |
| `tests/test_playwright_base.py` | Créer |
| `tests/test_credential_manager.py` | Créer |
| `tests/test_scrapers_playwright.py` | Créer |

---

## Task 1 : Dépendances + `playwright_base.py`

**Files:**
- Modify: `requirements.txt`
- Create: `playwright_base.py`
- Create: `tests/test_playwright_base.py`

- [ ] **Step 1 : Ajouter les dépendances**

Contenu final de `requirements.txt` :
```
streamlit>=1.32.0
sqlalchemy>=2.0.0
requests>=2.31.0
google-genai>=1.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
openpyxl>=3.1.0
feedparser>=6.0.0
playwright>=1.44.0
cryptography>=42.0.0
```

- [ ] **Step 2 : Installer les dépendances**

```bash
pip install playwright>=1.44.0 cryptography>=42.0.0
playwright install chromium
```

Résultat attendu : `Chromium 12x.x.xxxx downloaded` sans erreur.

- [ ] **Step 3 : Écrire les tests de `playwright_base.py`**

Créer `tests/test_playwright_base.py` :
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch
import pytest


def _make_mock_page(cards=None):
    """Retourne un mock de page Playwright avec des cartes simulées."""
    mock_page = MagicMock()
    if cards is not None:
        mock_elements = []
        for card_data in cards:
            el = MagicMock()
            def make_qs(data):
                def qs(sel):
                    key = sel.lstrip(".").split(",")[0].strip()
                    child = MagicMock()
                    child.inner_text.return_value = data.get(key, "")
                    child.get_attribute.return_value = data.get("href", "")
                    return child
                return qs
            el.query_selector.side_effect = make_qs(card_data)
            mock_elements.append(el)
        mock_page.query_selector_all.return_value = mock_elements
    else:
        mock_page.query_selector_all.return_value = []
    return mock_page


def test_extract_cards_empty_page():
    from playwright_base import extract_cards
    page = _make_mock_page(cards=[])
    result = extract_cards(page, ".card", {"title": ".title"})
    assert result == []


def test_extract_cards_with_attribute():
    from playwright_base import extract_cards
    page = MagicMock()
    el = MagicMock()
    child = MagicMock()
    child.get_attribute.return_value = "https://example.com/ao/1"
    el.query_selector.return_value = child
    page.query_selector_all.return_value = [el]
    result = extract_cards(page, ".card", {"url": "a@href"})
    assert result[0]["url"] == "https://example.com/ao/1"


def test_paginate_no_next_button():
    from playwright_base import paginate
    page = MagicMock()
    page.query_selector.return_value = None
    result = paginate(page, ".next", max_pages=5)
    assert result is False


def test_paginate_clicks_next():
    from playwright_base import paginate
    page = MagicMock()
    btn = MagicMock()
    btn.is_enabled.return_value = True
    page.query_selector.side_effect = [btn, None]  # 1 page puis plus de bouton
    paginate(page, ".next", max_pages=3)
    btn.click.assert_called_once()


def test_login_returns_true_on_success():
    from playwright_base import login
    page = MagicMock()
    page.goto.return_value = None
    page.fill.return_value = None
    page.click.return_value = None
    page.wait_for_load_state.return_value = None
    selectors = {"email": "#email", "password": "#pwd", "submit": "button[type=submit]"}
    result = login(page, "https://example.com/login", "u@u.com", "pass", selectors)
    assert result is True


def test_login_returns_false_on_exception():
    from playwright_base import login
    page = MagicMock()
    page.goto.side_effect = Exception("Timeout")
    selectors = {"email": "#email", "password": "#pwd", "submit": "button"}
    result = login(page, "https://example.com/login", "u@u.com", "pass", selectors)
    assert result is False
```

- [ ] **Step 4 : Vérifier que les tests échouent**

```bash
pytest tests/test_playwright_base.py -v
```

Attendu : `ImportError: cannot import name 'extract_cards' from 'playwright_base'`

- [ ] **Step 5 : Créer `playwright_base.py`**

```python
import logging
from playwright.sync_api import Page

log = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


def login(page: Page, url: str, email: str, password: str, selectors: dict) -> bool:
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        page.fill(selectors["email"], email)
        page.fill(selectors["password"], password)
        page.click(selectors["submit"])
        page.wait_for_load_state("networkidle", timeout=15000)
        return True
    except Exception as exc:
        log.warning("Login failed on %s: %s", url, exc)
        return False


def extract_cards(page: Page, card_selector: str, field_map: dict) -> list[dict]:
    cards = page.query_selector_all(card_selector)
    results = []
    for card in cards:
        item = {}
        for field, selector in field_map.items():
            if "@" in selector:
                sel, attr = selector.rsplit("@", 1)
                el = card.query_selector(sel) if sel else card
                item[field] = el.get_attribute(attr).strip() if el else ""
            else:
                el = card.query_selector(selector)
                item[field] = el.inner_text().strip() if el else ""
        results.append(item)
    return results


def paginate(page: Page, next_selector: str, max_pages: int = 5) -> bool:
    for _ in range(max_pages - 1):
        btn = page.query_selector(next_selector)
        if not btn or not btn.is_enabled():
            return False
        btn.click()
        page.wait_for_load_state("networkidle", timeout=15000)
    return True
```

- [ ] **Step 6 : Vérifier que les tests passent**

```bash
pytest tests/test_playwright_base.py -v
```

Attendu : 6 tests PASS.

- [ ] **Step 7 : Commit**

```bash
git add requirements.txt playwright_base.py tests/test_playwright_base.py
git commit -m "feat: add playwright_base helpers and install playwright/cryptography"
```

---

## Task 2 : `credential_manager.py` + modèle `Credential`

**Files:**
- Modify: `models.py`
- Modify: `database.py`
- Create: `credential_manager.py`
- Create: `tests/test_credential_manager.py`

- [ ] **Step 1 : Écrire les tests**

Créer `tests/test_credential_manager.py` :
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Credential


def _make_test_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_get_returns_none_when_nothing_configured():
    Session = _make_test_session()
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, {}, clear=False):
            from credential_manager import CredentialManager
            result = CredentialManager.get("instao")
    assert result is None


def test_get_returns_env_vars_first():
    Session = _make_test_session()
    env = {"INSTAO_EMAIL": "test@test.com", "INSTAO_PASSWORD": "secret"}
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, env):
            from credential_manager import CredentialManager
            result = CredentialManager.get("instao")
    assert result == ("test@test.com", "secret")


def test_save_and_get_from_db():
    Session = _make_test_session()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, {"CREDENTIAL_KEY": key}):
            from credential_manager import CredentialManager
            CredentialManager.save("instao", "user@mail.com", "mypassword")
            result = CredentialManager.get("instao")
    assert result == ("user@mail.com", "mypassword")


def test_delete_removes_credential():
    Session = _make_test_session()
    from cryptography.fernet import Fernet
    key = Fernet.generate_key().decode()
    with patch("credential_manager.SessionLocal", Session):
        with patch.dict(os.environ, {"CREDENTIAL_KEY": key}):
            from credential_manager import CredentialManager
            CredentialManager.save("instao", "u@u.com", "p")
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
            CredentialManager.save("tendersgo", "a@a.com", "pass")
            sites = CredentialManager.list_configured()
    assert any(s["site"] == "tendersgo" for s in sites)
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_credential_manager.py -v
```

Attendu : `ImportError: No module named 'credential_manager'`

- [ ] **Step 3 : Ajouter le modèle `Credential` dans `models.py`**

Ajouter à la fin de `models.py` (après la classe `Tender`) :
```python

class Credential(Base):
    __tablename__ = "credentials"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    site     = Column(String, unique=True, nullable=False)
    email    = Column(String, nullable=False)
    password = Column(String, nullable=False)  # chiffré Fernet
```

- [ ] **Step 4 : Mettre à jour `database.py` pour créer la table**

La ligne `Base.metadata.create_all(bind=engine)` dans `init_db()` créera automatiquement la table `credentials` dès que `Credential` est importé. Ajouter l'import en haut de `database.py` :

Modifier la ligne existante :
```python
from models import Base
```
→
```python
from models import Base, Credential  # noqa: Credential enregistre la table credentials
```

- [ ] **Step 5 : Créer `credential_manager.py`**

```python
import os
import logging
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
from database import SessionLocal
from models import Credential

load_dotenv()
log = logging.getLogger(__name__)

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
        db = SessionLocal()
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
        db = SessionLocal()
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
        db = SessionLocal()
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
        db = SessionLocal()
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
```

- [ ] **Step 6 : Vérifier que les tests passent**

```bash
pytest tests/test_credential_manager.py -v
```

Attendu : 5 tests PASS.

- [ ] **Step 7 : Commit**

```bash
git add models.py database.py credential_manager.py tests/test_credential_manager.py
git commit -m "feat: add Credential model and CredentialManager with Fernet encryption"
```

---

## Task 3 : Mise à jour `source_registry.py`

**Files:**
- Modify: `source_registry.py`
- Test: `tests/test_source_registry.py`

- [ ] **Step 1 : Ajouter un test pour les nouvelles sources**

Ouvrir `tests/test_source_registry.py` et ajouter à la fin :
```python
def test_new_sources_present():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    from source_registry import Source, init_sources, list_sources
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    init_sources(db)
    names = [s.name for s in list_sources(db)]
    for expected in ["VAAO", "Marché Online", "Nukema", "Instao", "Tenders Go"]:
        assert expected in names, f"{expected} manquant dans les sources"
    db.close()


def test_defunct_urls_not_in_sources():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    from source_registry import Source, init_sources, list_sources
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    init_sources(db)
    urls = [s.url for s in list_sources(db)]
    assert "https://www.nukema.fr" not in urls
    assert "https://www.marcheonline.com" not in urls
    db.close()
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_source_registry.py::test_new_sources_present -v
```

Attendu : FAIL — VAAO manquant.

- [ ] **Step 3 : Mettre à jour `source_registry.py`**

Remplacer le bloc `_DEFUNCT_URLS` et `_DEFAULT_SOURCES` :

Dans `_DEFUNCT_URLS`, supprimer ces 6 lignes :
```python
    "https://www.vaao.fr",
    "https://www.instao.fr",
    "https://www.nukema.fr",
    "https://www.marcheonline.com",
    "https://www.marches-publics.info",
    "https://www.tendersgo.com",
```

Laisser uniquement :
```python
_DEFUNCT_URLS = {
    "https://www.e-marches-publics.fr",
    "https://www.marches-internationaux.com",
}
```

Ajouter les 8 nouvelles entrées dans `_DEFAULT_SOURCES` (après `"UNGM"`, avant les manuels) :
```python
    {"name": "VAAO",
     "url": "https://www.vaao.fr",
     "category": "Public", "scraper_module": "scraper_vaao",
     "scraper_func": "fetch_vaao_tenders", "is_manual": False, "display_order": 4},
    {"name": "Marché Online",
     "url": "https://www.marchesonline.com",
     "category": "Public", "scraper_module": "scraper_marcheonline",
     "scraper_func": "fetch_marcheonline_tenders", "is_manual": False, "display_order": 5},
    {"name": "Marchés Publics — Dép. 974",
     "url": "https://cg974.e-marchespublics.com",
     "category": "Public", "scraper_module": "scraper_dept974",
     "scraper_func": "fetch_dept974_tenders", "is_manual": False, "display_order": 6},
    {"name": "Nukema",
     "url": "https://marches-publics.nukema.com",
     "category": "Public", "scraper_module": "scraper_nukema",
     "scraper_func": "fetch_nukema_tenders", "is_manual": False, "display_order": 7},
    {"name": "Marchés Public Info",
     "url": "https://www.marches-publics.info",
     "category": "Public", "scraper_module": "scraper_marchespublicsinfo",
     "scraper_func": "fetch_marchespublicsinfo_tenders", "is_manual": False, "display_order": 8},
    {"name": "Marchés Sécurisés",
     "url": "https://www.marches-securises.fr",
     "category": "Privé", "scraper_module": "scraper_marchessecurises",
     "scraper_func": "fetch_marchessecurises_tenders", "is_manual": False, "display_order": 12},
    {"name": "Instao",
     "url": "https://www.instao.fr",
     "category": "Privé", "scraper_module": "scraper_instao",
     "scraper_func": "fetch_instao_tenders", "is_manual": False, "display_order": 13},
    {"name": "Tenders Go",
     "url": "https://www.tendersgo.com",
     "category": "International", "scraper_module": "scraper_tendersgo",
     "scraper_func": "fetch_tendersgo_tenders", "is_manual": False, "display_order": 24},
```

Supprimer aussi l'ancienne entrée `"Marchés Sécurisés (MPS)"` du bloc manuels (display_order 41) puisqu'elle est maintenant automatique.

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_source_registry.py -v
```

Attendu : tous PASS.

- [ ] **Step 5 : Commit**

```bash
git add source_registry.py tests/test_source_registry.py
git commit -m "feat: register 8 new sources, remove from defunct URLs"
```

---

## Task 4 : Scrapers publics (VAAO, Marché Online, Dép. 974, Nukema)

**Files:**
- Create: `scraper_vaao.py`, `scraper_marcheonline.py`, `scraper_dept974.py`, `scraper_nukema.py`
- Create: `tests/test_scrapers_playwright.py`

- [ ] **Step 1 : Écrire les tests (mocks Playwright)**

Créer `tests/test_scrapers_playwright.py` :
```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender
import pytest


def _db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def _mock_pw_context(cards_html=None):
    """Retourne (mock_sync_playwright, mock_page) prêts à injecter."""
    mock_page = MagicMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_load_state.return_value = None
    mock_page.query_selector.return_value = None  # pas de bouton "suivant"
    if cards_html:
        mock_cards = []
        for data in cards_html:
            card = MagicMock()
            def make_qs(d):
                def qs(sel):
                    child = MagicMock()
                    child.inner_text.return_value = d.get("text", "")
                    child.get_attribute.return_value = d.get("href", "")
                    return child
                return qs
            card.query_selector.side_effect = make_qs(data)
            mock_cards.append(card)
        mock_page.query_selector_all.return_value = mock_cards
    else:
        mock_page.query_selector_all.return_value = []

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw, mock_page


# ── VAAO ─────────────────────────────────────────────────────────────────────

def test_fetch_vaao_empty_page():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_vaao.SessionLocal", Session):
            with patch("scraper_vaao.init_db"):
                from scraper_vaao import fetch_vaao_tenders
                result = fetch_vaao_tenders()
    assert result == 0


def test_fetch_vaao_inserts_relevant():
    Session = _db_session()
    cards = [{"text": "Installation SSI alarme incendie bâtiment public Réunion", "href": "/ao/1"}]
    mock_pw, mock_page = _mock_pw_context(cards)
    mock_page.query_selector_all.return_value = [mock_page.query_selector_all.return_value[0]
                                                  ] if False else _make_relevant_card()

    # Approche directe : mocker extract_cards
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_vaao.extract_cards", return_value=[{
            "title": "Installation SSI alarme incendie Réunion",
            "description": "",
            "url": "https://www.vaao.fr/ao/1",
            "date": "15/04/2026",
        }]):
            with patch("scraper_vaao.paginate", return_value=False):
                with patch("scraper_vaao.SessionLocal", Session):
                    with patch("scraper_vaao.init_db"):
                        from scraper_vaao import fetch_vaao_tenders
                        result = fetch_vaao_tenders()
    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert len(tenders) == 1


def _make_relevant_card():
    return []  # helper non utilisé directement


# ── Marché Online ─────────────────────────────────────────────────────────────

def test_fetch_marcheonline_empty():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_marcheonline.extract_cards", return_value=[]):
            with patch("scraper_marcheonline.paginate", return_value=False):
                with patch("scraper_marcheonline.SessionLocal", Session):
                    with patch("scraper_marcheonline.init_db"):
                        from scraper_marcheonline import fetch_marcheonline_tenders
                        result = fetch_marcheonline_tenders()
    assert result == 0


# ── Nukema ────────────────────────────────────────────────────────────────────

def test_fetch_nukema_inserts_relevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_nukema.extract_cards", return_value=[{
            "title": "Maintenance CCTV vidéosurveillance campus universitaire",
            "description": "Mayotte 976",
            "url": "https://marches-publics.nukema.com/consultation/12345",
            "date": "10/05/2026",
        }]):
            with patch("scraper_nukema.paginate", return_value=False):
                with patch("scraper_nukema.SessionLocal", Session):
                    with patch("scraper_nukema.init_db"):
                        from scraper_nukema import fetch_nukema_tenders
                        result = fetch_nukema_tenders()
    assert result == 1
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_scrapers_playwright.py::test_fetch_vaao_empty_page -v
```

Attendu : `ModuleNotFoundError: No module named 'scraper_vaao'`

- [ ] **Step 3 : Créer le module utilitaire `_parse_date` partagé**

Chaque scraper a besoin d'un `_parse_date`. Ajouter ce helper directement dans chaque fichier (copié) :

```python
def _parse_date(value: str | None):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %B %Y"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None
```

- [ ] **Step 4 : Créer `scraper_vaao.py`**

```python
import hashlib
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate
from credential_manager import CredentialManager

_URLS = [
    "https://www.vaao.fr/departement/la-reunion",
    "https://www.vaao.fr/departement/mayotte",
]
_CARD = ".views-row, article.node--type-appel-offre, .appel-offre-item, article"
_FIELDS = {
    "title": "h3, h2, .node__title, .title",
    "description": ".field--name-body, .description, .body",
    "url": "a@href",
    "date": "time, .date, .field--name-field-date",
}
_NEXT = "a[rel='next'], li.pager__item--next > a, .pager-next a"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_vaao_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for base_url in _URLS:
                    page = browser.new_page()
                    page.goto(base_url, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or base_url
                            if url and not url.startswith("http"):
                                url = f"https://www.vaao.fr{url}"
                            tid = f"VAAO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            if db.query(Tender).filter(Tender.id == tid).first():
                                continue
                            db.add(Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=_parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
                            ))
                            inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                    page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"VAAO : {fetch_vaao_tenders()} AO insérés")
```

- [ ] **Step 5 : Créer `scraper_marcheonline.py`**

```python
import hashlib
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate

_URLS = [
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101",
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/mayotte-D976",
]
_CARD = ".annonce, .appel-offre, tr.ao-row, .liste-ao li, article"
_FIELDS = {
    "title": "h3, h2, .titre, .objet, td.objet",
    "description": ".description, .resume, td.organisme",
    "url": "a@href",
    "date": ".date, td.date, time",
}
_NEXT = "a.next, .pagination a[aria-label='Next'], li.page-item.active + li a"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_marcheonline_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                for base_url in _URLS:
                    page = browser.new_page()
                    page.goto(base_url, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or base_url
                            if url and not url.startswith("http"):
                                url = f"https://www.marchesonline.com{url}"
                            tid = f"MARCHEONLINE-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            if db.query(Tender).filter(Tender.id == tid).first():
                                continue
                            db.add(Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=_parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
                            ))
                            inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                    page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Marché Online : {fetch_marcheonline_tenders()} AO insérés")
```

- [ ] **Step 6 : Créer `scraper_dept974.py`**

```python
import hashlib
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate

_URL = "https://cg974.e-marchespublics.com/"
_CARD = "tr.ligneMarche, .liste-marche tr, .avis-marche, li.marche"
_FIELDS = {
    "title": "td.objet, .objet, h3, h2",
    "description": "td.organisme, .organisme, td.lieu",
    "url": "a@href",
    "date": "td.date, .date-publication, time",
}
_NEXT = "a.suivant, a[title='Page suivante'], .pagination-next a"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_dept974_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(_URL, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=15000)
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _URL
                        if url and not url.startswith("http"):
                            url = f"https://cg974.e-marchespublics.com{url}"
                        tid = f"DEPT974-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="Public",
                            type_opportunite="Marché Public",
                        ))
                        inserted += 1
                    if not paginate(page, _NEXT):
                        break
                    page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Dép. 974 : {fetch_dept974_tenders()} AO insérés")
```

- [ ] **Step 7 : Créer `scraper_nukema.py`**

```python
import hashlib
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager

_URLS = [
    "https://marches-publics.nukema.com/seo/consultation/departement?departement=974",
    "https://marches-publics.nukema.com/seo/consultation/departement?departement=976",
]
_LOGIN_URL = "https://www.actu.nukema.com/connexion"
_LOGIN_SELECTORS = {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}
_CARD = ".consultation-card, .card, article.consultation, li.consultation"
_FIELDS = {
    "title": "h3, h2, .card-title, .consultation-title",
    "description": ".card-text, .description, .organisme",
    "url": "a@href",
    "date": ".date, .card-date, time",
}
_NEXT = "a[aria-label='Next'], .pagination-next a, a.next"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_nukema_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    creds = CredentialManager.get("nukema")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if creds:
                    login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS)
                for base_url in _URLS:
                    page.goto(base_url, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            if not is_relevant_def(f"{title} {desc}"):
                                continue
                            url = card.get("url", "") or base_url
                            if url and not url.startswith("http"):
                                url = f"https://marches-publics.nukema.com{url}"
                            tid = f"NUKEMA-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            if db.query(Tender).filter(Tender.id == tid).first():
                                continue
                            db.add(Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=_parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
                            ))
                            inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Nukema : {fetch_nukema_tenders()} AO insérés")
```

- [ ] **Step 8 : Vérifier que les tests passent**

```bash
pytest tests/test_scrapers_playwright.py -v
```

Attendu : tous PASS.

- [ ] **Step 9 : Commit**

```bash
git add scraper_vaao.py scraper_marcheonline.py scraper_dept974.py scraper_nukema.py tests/test_scrapers_playwright.py
git commit -m "feat: add 4 public scrapers (VAAO, MarcheOnline, Dept974, Nukema) via Playwright"
```

---

## Task 5 : Scrapers avec authentification (Marchés Sécurisés, Instao, Tenders Go)

**Files:**
- Create: `scraper_marchessecurises.py`, `scraper_instao.py`, `scraper_tendersgo.py`

- [ ] **Step 1 : Ajouter les tests auth**

Ajouter à `tests/test_scrapers_playwright.py` :
```python
# ── Marchés Sécurisés ─────────────────────────────────────────────────────────

def test_fetch_marchessecurises_skips_without_creds():
    Session = _db_session()
    with patch("credential_manager.CredentialManager.get", return_value=None):
        with patch("scraper_marchessecurises.SessionLocal", Session):
            with patch("scraper_marchessecurises.init_db"):
                from scraper_marchessecurises import fetch_marchessecurises_tenders
                result = fetch_marchessecurises_tenders()
    assert result == 0


def test_fetch_marchessecurises_with_creds_inserts():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("credential_manager.CredentialManager.get", return_value=("u@u.com", "pass")):
        with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
            with patch("scraper_marchessecurises.login", return_value=True):
                with patch("scraper_marchessecurises.extract_cards", return_value=[{
                    "title": "Maintenance SSI incendie établissement public",
                    "description": "La Réunion 974",
                    "url": "https://www.marches-securises.fr/ao/99",
                    "date": "01/05/2026",
                }]):
                    with patch("scraper_marchessecurises.paginate", return_value=False):
                        with patch("scraper_marchessecurises.SessionLocal", Session):
                            with patch("scraper_marchessecurises.init_db"):
                                from scraper_marchessecurises import fetch_marchessecurises_tenders
                                result = fetch_marchessecurises_tenders()
    assert result == 1


# ── Instao ────────────────────────────────────────────────────────────────────

def test_fetch_instao_skips_without_creds():
    Session = _db_session()
    with patch("credential_manager.CredentialManager.get", return_value=None):
        with patch("scraper_instao.SessionLocal", Session):
            with patch("scraper_instao.init_db"):
                from scraper_instao import fetch_instao_tenders
                result = fetch_instao_tenders()
    assert result == 0


# ── Tenders Go ────────────────────────────────────────────────────────────────

def test_fetch_tendersgo_skips_without_creds():
    Session = _db_session()
    with patch("credential_manager.CredentialManager.get", return_value=None):
        with patch("scraper_tendersgo.SessionLocal", Session):
            with patch("scraper_tendersgo.init_db"):
                from scraper_tendersgo import fetch_tendersgo_tenders
                result = fetch_tendersgo_tenders()
    assert result == 0
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_scrapers_playwright.py::test_fetch_marchessecurises_skips_without_creds -v
```

Attendu : `ModuleNotFoundError: No module named 'scraper_marchessecurises'`

- [ ] **Step 3 : Créer `scraper_marchessecurises.py`**

```python
import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager

log = logging.getLogger(__name__)

_LOGIN_URL = "https://www.marches-securises.fr/entreprise/?page=connexion"
_SEARCH_URL = "https://www.marches-securises.fr/entreprise/?page=entreprise_dce_recherche"
_LOGIN_SELECTORS = {
    "email": "input[name='login'], input[type='email'], #login",
    "password": "input[name='pass'], input[type='password'], #password",
    "submit": "input[type='submit'], button[type='submit']",
}
_CARD = "table.tableau tr.ligneMarche, .liste-dce tr, tr[class*='ligne']"
_FIELDS = {
    "title": "td.objet, .objet, td:nth-child(2)",
    "description": "td.pa, .organisme-acheteur, td:nth-child(3)",
    "url": "a@href",
    "date": "td.date, .date-limite, td:last-child",
}
_NEXT = "a.suivant, a[title='Suivant'], .page-suivante"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_marchessecurises_tenders() -> int:
    creds = CredentialManager.get("marches_securises")
    if not creds:
        log.warning("Marchés Sécurisés : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                    log.warning("Marchés Sécurisés : login échoué — vérifiez vos identifiants dans Paramètres")
                    return 0
                page.goto(_SEARCH_URL, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=15000)
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _SEARCH_URL
                        if url and not url.startswith("http"):
                            url = f"https://www.marches-securises.fr{url}"
                        tid = f"MARCHESSEC-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="Privé",
                            type_opportunite="Marché Public",
                        ))
                        inserted += 1
                    if not paginate(page, _NEXT):
                        break
                    page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Marchés Sécurisés : {fetch_marchessecurises_tenders()} AO insérés")
```

- [ ] **Step 4 : Créer `scraper_instao.py`**

```python
import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager

log = logging.getLogger(__name__)

_LOGIN_URL = "https://www.instao.fr/connexion"
_SEARCH_URL = "https://www.instao.fr/bids?c=&l=974%2C976"
_LOGIN_SELECTORS = {
    "email": "input[type='email'], input[name='email'], #email",
    "password": "input[type='password'], input[name='password'], #password",
    "submit": "button[type='submit'], input[type='submit']",
}
_CARD = ".bid-card, article.bid, .tender-card, li.bid"
_FIELDS = {
    "title": "h3, h2, .bid-title, .card-title",
    "description": ".bid-description, .card-text, .organisme",
    "url": "a@href",
    "date": ".bid-date, .card-date, time, .date",
}
_NEXT = "a[aria-label='Page suivante'], .pagination-next a, button.next"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_instao_tenders() -> int:
    creds = CredentialManager.get("instao")
    if not creds:
        log.warning("Instao : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                    log.warning("Instao : login échoué — vérifiez vos identifiants dans Paramètres")
                    return 0
                page.goto(_SEARCH_URL, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=15000)
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _SEARCH_URL
                        if url and not url.startswith("http"):
                            url = f"https://www.instao.fr{url}"
                        tid = f"INSTAO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="Privé",
                            type_opportunite="Marché Public",
                        ))
                        inserted += 1
                    if not paginate(page, _NEXT):
                        break
                    page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Instao : {fetch_instao_tenders()} AO insérés")
```

- [ ] **Step 5 : Créer `scraper_tendersgo.py`**

```python
import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, login, paginate
from credential_manager import CredentialManager

log = logging.getLogger(__name__)

_LOGIN_URL = "https://app.tendersgo.com/login"
_SEARCH_URL = "https://app.tendersgo.com/tenders?country=FR&keywords=SSI+incendie+videosurveillance+CCTV+CMSI"
_LOGIN_SELECTORS = {
    "email": "input[type='email'], input[name='email'], #email",
    "password": "input[type='password'], input[name='password'], #password",
    "submit": "button[type='submit'], input[type='submit']",
}
_CARD = ".tender-card, .tender-item, article.tender, li.tender, tr.tender-row"
_FIELDS = {
    "title": "h3, h2, .tender-title, .title",
    "description": ".tender-description, .description, .country",
    "url": "a@href",
    "date": ".tender-date, .date, time",
}
_NEXT = "a[aria-label='Next page'], .pagination-next a, button.next-page"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_tendersgo_tenders() -> int:
    creds = CredentialManager.get("tendersgo")
    if not creds:
        log.warning("Tenders Go : aucun identifiant configuré — scraper ignoré")
        return 0
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                if not login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS):
                    log.warning("Tenders Go : login échoué — vérifiez vos identifiants dans Paramètres")
                    return 0
                page.goto(_SEARCH_URL, timeout=15000)
                page.wait_for_load_state("networkidle", timeout=15000)
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _SEARCH_URL
                        if url and not url.startswith("http"):
                            url = f"https://app.tendersgo.com{url}"
                        tid = f"TENDERSGO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="International",
                            type_opportunite="Marché International",
                        ))
                        inserted += 1
                    if not paginate(page, _NEXT):
                        break
                    page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Tenders Go : {fetch_tendersgo_tenders()} AO insérés")
```

- [ ] **Step 6 : Vérifier que les tests passent**

```bash
pytest tests/test_scrapers_playwright.py -v
```

Attendu : tous PASS (y compris les nouveaux tests auth).

- [ ] **Step 7 : Commit**

```bash
git add scraper_marchessecurises.py scraper_instao.py scraper_tendersgo.py tests/test_scrapers_playwright.py
git commit -m "feat: add 3 auth scrapers (MarchesSecurises, Instao, TendersGo) via Playwright"
```

---

## Task 6 : `scraper_marchespublicsinfo.py`

**Files:**
- Create: `scraper_marchespublicsinfo.py`

- [ ] **Step 1 : Créer `scraper_marchespublicsinfo.py`**

```python
import hashlib
import logging
from playwright.sync_api import sync_playwright
from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender
from playwright_base import extract_cards, paginate

log = logging.getLogger(__name__)

_URL = "https://www.marches-publics.info/index.php?page=entreprise.EntrepriseAdvancedSearch&searchAnnouncement[query]=SSI+incendie+CMSI+videosurveillance&searchAnnouncement[dptList][]=974&searchAnnouncement[dptList][]=976"
_CARD = "tr.annonce, .annonce-row, li.annonce, .search-result-item"
_FIELDS = {
    "title": "td.objet, .objet, h3, .titre",
    "description": "td.pa, .organisme, .acheteur",
    "url": "a@href",
    "date": "td.date, .date, time",
}
_NEXT = "a.next, a[title='Page suivante'], .pagination-next a"


def _parse_date(value):
    if not value:
        return None
    from datetime import datetime
    value = " ".join(str(value).split())
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[:10], fmt[:10])
        except ValueError:
            continue
    return None


def fetch_marchespublicsinfo_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    page.goto(_URL, timeout=15000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception as exc:
                    log.warning("Marchés Public Info inaccessible : %s", exc)
                    return 0
                page_count = 0
                while page_count < 5:
                    for card in extract_cards(page, _CARD, _FIELDS):
                        title = card.get("title", "").strip()
                        desc = card.get("description", "").strip()
                        if not is_relevant_def(f"{title} {desc}"):
                            continue
                        url = card.get("url", "") or _URL
                        if url and not url.startswith("http"):
                            url = f"https://www.marches-publics.info{url}"
                        tid = f"MARCHESPUBLICSINFO-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if db.query(Tender).filter(Tender.id == tid).first():
                            continue
                        db.add(Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=_parse_date(card.get("date")),
                            deadline=None, status="À qualifier",
                            relevance_score=0, is_maintenance=False,
                            llm_analysis=None, secteur="Public",
                            type_opportunite="Marché Public",
                        ))
                        inserted += 1
                    if not paginate(page, _NEXT):
                        break
                    page_count += 1
                page.close()
            finally:
                browser.close()
        if inserted:
            db.commit()
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    print(f"Marchés Public Info : {fetch_marchespublicsinfo_tenders()} AO insérés")
```

- [ ] **Step 2 : Commit**

```bash
git add scraper_marchespublicsinfo.py
git commit -m "feat: add scraper_marchespublicsinfo (public, department filter 974/976)"
```

---

## Task 7 : Page Paramètres (`pages/parametres.py`)

**Files:**
- Create: `pages/parametres.py`

- [ ] **Step 1 : Créer le dossier `pages/` si absent**

```bash
mkdir -p pages
```

- [ ] **Step 2 : Créer `pages/parametres.py`**

```python
import os
import streamlit as st
from dotenv import load_dotenv
from credential_manager import CredentialManager
from database import init_db

load_dotenv()
init_db()

st.set_page_config(page_title="Paramètres — DEF OI", page_icon="⚙️", layout="wide")
st.title("⚙️ Paramètres")

_SITE_LABELS = {
    "vaao":               ("VAAO",                      "Public"),
    "marcheonline":       ("Marché Online",              "Public"),
    "dept974":            ("Marchés Publics — Dép. 974", "Public"),
    "nukema":             ("Nukema",                     "Public"),
    "marchespublicsinfo": ("Marchés Public Info",        "Public"),
    "marches_securises":  ("Marchés Sécurisés",          "Privé"),
    "instao":             ("Instao",                     "Privé"),
    "tendersgo":          ("Tenders Go",                 "International"),
}

# ── Section identifiants ──────────────────────────────────────────────────────
st.header("🔐 Identifiants des sources")
st.caption("Les mots de passe sont chiffrés en base de données. Les variables `.env` ont la priorité.")

configured = {c["site"]: c for c in CredentialManager.list_configured()}

for site_key, (site_label, category) in _SITE_LABELS.items():
    cred = configured.get(site_key)
    icon = "✅" if cred else "⬜"
    with st.expander(f"{icon} {site_label} — {category}"):
        if cred and cred.get("has_env_override"):
            st.success(f"Configuré via `.env` — email : `{cred['email']}`")
            st.info("Pour modifier, éditez le fichier `.env` et relancez l'application.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                new_email = st.text_input(
                    "Email / Identifiant",
                    value=cred["email"] if cred else "",
                    key=f"email_{site_key}",
                )
            with col2:
                new_pwd = st.text_input(
                    "Mot de passe",
                    type="password",
                    placeholder="••••••••" if cred else "",
                    key=f"pwd_{site_key}",
                )
            btn1, btn2, btn3 = st.columns([2, 2, 4])
            with btn1:
                if st.button("💾 Enregistrer", key=f"save_{site_key}"):
                    if new_email and new_pwd:
                        CredentialManager.save(site_key, new_email, new_pwd)
                        st.success("Identifiants enregistrés ✓")
                        st.rerun()
                    else:
                        st.error("Email et mot de passe requis")
            with btn2:
                if cred and st.button("🗑️ Supprimer", key=f"del_{site_key}"):
                    CredentialManager.delete(site_key)
                    st.rerun()
            with btn3:
                if cred and st.button("🔌 Tester la connexion", key=f"test_{site_key}"):
                    with st.spinner("Test en cours…"):
                        try:
                            from playwright.sync_api import sync_playwright
                            from playwright_base import login
                            _TEST_URLS = {
                                "marches_securises": ("https://www.marches-securises.fr/entreprise/?page=connexion",
                                                      {"email": "input[name='login']", "password": "input[name='pass']", "submit": "input[type='submit']"}),
                                "instao":            ("https://www.instao.fr/connexion",
                                                      {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                                "tendersgo":         ("https://app.tendersgo.com/login",
                                                      {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                            }
                            if site_key in _TEST_URLS:
                                url, selectors = _TEST_URLS[site_key]
                                with sync_playwright() as pw:
                                    browser = pw.chromium.launch(headless=True)
                                    page = browser.new_page()
                                    ok = login(page, url, new_email or cred["email"], new_pwd or "", selectors)
                                    browser.close()
                                if ok:
                                    st.success("✅ Connexion réussie")
                                else:
                                    st.error("❌ Connexion échouée — vérifiez vos identifiants")
                            else:
                                st.info("Test de connexion non disponible pour cette source (accès public).")
                        except Exception as e:
                            st.error(f"Erreur : {e}")

# ── Section sécurité ──────────────────────────────────────────────────────────
st.markdown("---")
st.header("🔑 Sécurité")

key_present = bool(os.getenv("CREDENTIAL_KEY"))
if key_present:
    st.success("Clé de chiffrement active — présente dans `.env`")
else:
    st.warning("Clé de chiffrement absente — elle sera générée automatiquement au 1er enregistrement d'identifiant.")

if st.button("🔄 Régénérer la clé de chiffrement"):
    st.warning("⚠️ Attention : régénérer la clé rendra illisibles tous les mots de passe stockés en base. Vous devrez les ressaisir.")
    if st.checkbox("Je comprends, procéder quand même"):
        from cryptography.fernet import Fernet
        from dotenv import set_key
        new_key = Fernet.generate_key().decode()
        set_key(".env", "CREDENTIAL_KEY", new_key)
        os.environ["CREDENTIAL_KEY"] = new_key
        st.success("Nouvelle clé générée et sauvegardée dans `.env`. Relancez l'application.")

# ── Section maintenance ───────────────────────────────────────────────────────
st.markdown("---")
st.header("🧹 Maintenance")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("🗑️ Vider le cache Streamlit"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Cache vidé ✓")
with col_b:
    if st.button("🔄 Réinitialiser les sources par défaut"):
        st.warning("Cette action ne supprime pas les sources existantes — elle ajoute les sources manquantes.")
        from database import SessionLocal
        from source_registry import init_sources
        db = SessionLocal()
        try:
            init_sources(db)
            st.success("Sources vérifiées et initialisées ✓")
        finally:
            db.close()
```

- [ ] **Step 3 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat: add Paramètres page with credential management UI"
```

---

## Task 8 : Page Guide (`pages/guide.py`)

**Files:**
- Create: `pages/guide.py`

- [ ] **Step 1 : Créer `pages/guide.py`**

```python
import streamlit as st

st.set_page_config(page_title="Guide — DEF OI", page_icon="📖", layout="wide")
st.title("📖 Guide utilisateur — DEF Océan Indien")
st.caption("Version 2.0 — Mise à jour mai 2026")

# ── 1. Présentation ───────────────────────────────────────────────────────────
st.header("1. Qu'est-ce que cette application ?")
st.markdown("""
Cette application est un **outil de veille automatique des marchés publics** pour les
commerciaux de DEF Océan Indien.

Elle surveille en continu les appels d'offres publiés sur **La Réunion (974)** et
**Mayotte (976)** dans les domaines :

| Domaine | Exemples |
|---------|---------|
| SSI / CMSI | Systèmes de sécurité incendie, centrales |
| Détection incendie | Alarmes, détecteurs, désenfumage |
| Vidéosurveillance | CCTV, caméras, contrôle d'accès |
| Courants faibles | Câblage, réseaux, domotique |

L'IA analyse chaque opportunité et lui attribue un **score de pertinence** (0–100).
""")

# ── 2. Tableau de bord ────────────────────────────────────────────────────────
st.markdown("---")
st.header("2. Tableau de bord — lire les résultats")
st.markdown("""
### Les KPIs en haut de page
- **Total AO** : nombre total d'appels d'offres collectés
- **En cours** : AO avec statut "En cours" ou "Soumis"
- **Gagnés** : AO remportés
- **Score moyen** : pertinence moyenne des AO actifs

### Les statuts
Chaque AO suit ce cycle de vie :

```
À qualifier  →  En cours  →  Soumis  →  Gagné
                                    ↘  Perdu
```

- **À qualifier** : nouvel AO importé, à examiner
- **En cours** : vous travaillez sur ce dossier
- **Soumis** : offre déposée
- **Gagné / Perdu** : résultat connu

### Le score de pertinence (0–100)
Calculé par l'IA (Gemini) sur le titre et la description.
- **80–100** : très pertinent, à traiter en priorité
- **50–79** : pertinent, à examiner
- **0–49** : faible pertinence, probablement hors périmètre
""")

# ── 3. Sources ────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("3. Sources de collecte")
st.markdown("""
L'application collecte automatiquement sur ces sources :
""")

sources_data = [
    ("BOAMP — Journal Officiel", "Public", "✅ Automatique", "Non", "AO officiels France entière"),
    ("DECP / PLACE", "Public", "✅ Automatique", "Non", "Données essentielles commande publique"),
    ("TED Europe", "Public", "✅ Automatique", "Non", "AO européens (marchés > seuil)"),
    ("VAAO", "Public", "✅ Automatique", "Non", "Agrégateur AO Réunion/Mayotte"),
    ("Marché Online", "Public", "✅ Automatique", "Non", "Agrégateur AO par département"),
    ("Marchés Publics — Dép. 974", "Public", "✅ Automatique", "Non", "AO officiels Conseil Dép. Réunion"),
    ("Nukema", "Public", "✅ Automatique", "Optionnel", "Veille marchés publics France"),
    ("Marchés Public Info", "Public", "✅ Automatique", "Non", "Agrégateur marchés publics"),
    ("Permis de construire", "Privé", "✅ Automatique", "Non", "Signaux avant-vente construction"),
    ("Presse & Institutions IO", "Privé", "✅ Automatique", "Non", "Actualités locales Réunion"),
    ("Marchés Sécurisés", "Privé", "✅ Automatique", "Oui ⚠️", "Plateforme dématérialisée"),
    ("Instao", "Privé", "✅ Automatique", "Oui ⚠️", "IA marchés publics"),
    ("Banques Dev. (BAD/BEI/COI)", "International", "✅ Automatique", "Non", "Projets africains et insulaires"),
    ("AFD", "International", "✅ Automatique", "Non", "Projets Agence Française Développement"),
    ("Banque Mondiale", "International", "✅ Automatique", "Non", "Projets Banque Mondiale"),
    ("UNGM", "International", "✅ Automatique", "Non", "Marchés ONU"),
    ("Tenders Go", "International", "✅ Automatique", "Oui ⚠️", "Agrégateur mondial"),
]

import pandas as pd
df = pd.DataFrame(sources_data, columns=["Source", "Catégorie", "Collecte", "Compte requis", "Couverture"])
st.dataframe(df, use_container_width=True, hide_index=True)

st.info("⚠️ Les sources marquées 'Compte requis' nécessitent vos identifiants dans **⚙️ Paramètres**.")

# ── 4. Lancer une collecte ────────────────────────────────────────────────────
st.markdown("---")
st.header("4. Lancer une collecte — pas à pas")
st.markdown("""
**Étape 1 — Cocher les sources**
Dans la barre latérale gauche, cochez les sources que vous voulez interroger.
Les sources sans identifiant configuré seront ignorées automatiquement.

**Étape 2 — Choisir la période**
Sélectionnez la période d'analyse :
- *Depuis cette année* : AO publiés depuis janvier
- *Depuis 2 ans* (défaut) : recommandé pour un premier import
- *Tout afficher* : tous les AO disponibles (peut être lent)

**Étape 3 — Cliquer "⚡ Collecter la sélection"**
La collecte démarre. Pour les sources Playwright (navigateur), cela peut prendre 1–3 minutes.

**Étape 4 — Consulter les résultats**
Les nouveaux AO apparaissent en haut du tableau avec le statut **"À qualifier"**.
L'analyse IA se déclenche automatiquement après la collecte.

**Étape 5 — Traiter les AO**
Changez le statut, ajoutez des notes, lancez une analyse IA manuelle si besoin.
""")

# ── 5. Gérer les opportunités ─────────────────────────────────────────────────
st.markdown("---")
st.header("5. Gérer les opportunités")
st.markdown("""
### Changer le statut
Dans la colonne **Statut** de chaque ligne, utilisez le menu déroulant pour faire évoluer l'AO.

### Déclencher l'analyse IA
Cliquez sur **🤖 Analyser** sur un AO pour obtenir :
- Un résumé en quelques lignes
- Un score de pertinence (0–100)
- Les domaines concernés (SSI, CMSI, vidéo…)
- Une justification du score

### Exporter le rapport Excel
Le bouton **📊 Télécharger le Rapport Direction** génère un fichier Excel avec :
- Tous les AO actifs
- Les scores et analyses
- Les statuts et dates

Ce rapport est conçu pour être partagé en réunion commerciale.
""")

# ── 6. Configurer les identifiants ────────────────────────────────────────────
st.markdown("---")
st.header("6. Configurer les identifiants")
st.markdown("""
Deux méthodes pour configurer les identifiants des sources qui le nécessitent :

### Méthode 1 — Via l'interface (recommandée)
1. Allez dans **⚙️ Paramètres** (menu latéral)
2. Dépliez la source souhaitée
3. Entrez email et mot de passe
4. Cliquez **💾 Enregistrer**

### Méthode 2 — Via le fichier `.env`
Ouvrez le fichier `.env` à la racine du projet et ajoutez :
```
MARCHES_SEC_EMAIL=votre@email.com
MARCHES_SEC_PASSWORD=votre_mot_de_passe

INSTAO_EMAIL=votre@email.com
INSTAO_PASSWORD=votre_mot_de_passe

TENDERSGO_EMAIL=votre@email.com
TENDERSGO_PASSWORD=votre_mot_de_passe

NUKEMA_EMAIL=votre@email.com
NUKEMA_PASSWORD=votre_mot_de_passe
```
Puis **relancez l'application**. Les variables `.env` ont toujours la priorité sur la base de données.
""")

# ── 7. FAQ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("7. FAQ & Résolution de problèmes")

with st.expander("Un scraper retourne une erreur 400 ou 500"):
    st.markdown("""
    - Vérifiez votre connexion internet
    - L'API ou le site peut être temporairement indisponible — relancez dans 10 minutes
    - Si l'erreur persiste, le format du site a peut-être changé (contacter le support)
    """)

with st.expander("Aucun résultat après une collecte"):
    st.markdown("""
    - Élargissez la période (passez à "2 ans" ou "Tout afficher")
    - Vérifiez que les sources sont bien cochées
    - Certaines sources (Marchés Sécurisés, Instao, Tenders Go) nécessitent un compte configuré
    """)

with st.expander("Les sources Playwright sont lentes"):
    st.markdown("""
    Un scraper Playwright (navigateur headless) prend 30–90 secondes par source.
    C'est normal — il simule un vrai navigateur pour accéder aux sites.
    Lancez la collecte et attendez la fin du spinner.
    """)

with st.expander("Identifiants incorrects — login échoué"):
    st.markdown("""
    1. Allez dans **⚙️ Paramètres**
    2. Utilisez **🔌 Tester la connexion** pour vérifier
    3. Corrigez email/mot de passe et re-enregistrez
    4. Si le site a changé son formulaire de login, contactez le support
    """)

with st.expander("L'application ne démarre pas"):
    st.markdown("""
    Dans le terminal, dans le dossier de l'application :
    ```bash
    streamlit run app.py
    ```
    Si erreur `ModuleNotFoundError` :
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```
    """)

with st.expander("Comment sauvegarder mes données ?"):
    st.markdown("""
    Toutes les données sont dans le fichier `def_oi_veille.db` (SQLite).
    Faites une copie régulière de ce fichier pour sauvegarder vos AO et analyses.
    """)
```

- [ ] **Step 2 : Commit**

```bash
git add pages/guide.py
git commit -m "feat: add Guide utilisateur in-app (page Streamlit)"
```

---

## Task 9 : Mise à jour `app.py` — navigation

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Ajouter les liens de navigation dans la sidebar**

Dans `app.py`, trouver le bloc `with st.sidebar:` et localiser la ligne `st.markdown("---")` juste avant le bouton "⚡ Collecter". Ajouter après le bouton collecte, à la fin du bloc sidebar :

```python
    st.markdown("---")
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        st.page_link("pages/parametres.py", label="⚙️ Paramètres", use_container_width=True)
    with col_nav2:
        st.page_link("pages/guide.py", label="📖 Guide", use_container_width=True)
```

- [ ] **Step 2 : Vérifier que l'app démarre sans erreur**

```bash
streamlit run app.py
```

Vérifier :
- La sidebar affiche les liens ⚙️ Paramètres et 📖 Guide
- Cliquer sur Paramètres ouvre la page de gestion des identifiants
- Cliquer sur Guide ouvre le manuel utilisateur

- [ ] **Step 3 : Commit final**

```bash
git add app.py
git commit -m "feat: add sidebar navigation links to Paramètres and Guide pages"
```

---

## Task 10 : Tests d'intégration et vérification globale

- [ ] **Step 1 : Lancer tous les tests**

```bash
pytest tests/ -v --tb=short
```

Attendu : tous PASS, 0 erreurs.

- [ ] **Step 2 : Tester manuellement les scrapers publics**

```bash
python scraper_vaao.py
python scraper_marcheonline.py
python scraper_dept974.py
python scraper_nukema.py
python scraper_marchespublicsinfo.py
```

Pour chaque scraper : si 0 AO insérés mais pas d'erreur Python, le CSS selector ne correspond pas.
Dans ce cas, lancer en mode debug :

```python
# En haut du scraper, changer headless=True → headless=False
browser = pw.chromium.launch(headless=False)
# Puis inspecter l'élément dans le navigateur qui s'ouvre
```

Mettre à jour les constantes `_CARD` et `_FIELDS` selon la structure réelle observée.

- [ ] **Step 3 : Commit de correction des sélecteurs si nécessaire**

```bash
git add scraper_vaao.py scraper_marcheonline.py scraper_dept974.py scraper_nukema.py scraper_marchespublicsinfo.py
git commit -m "fix: adjust CSS selectors after manual verification of live sites"
```

- [ ] **Step 4 : Commit final**

```bash
git tag v2.0.0-scrapers
git log --oneline -15
```

---

## Rappel : ajustement des sélecteurs CSS

Les sélecteurs CSS fournis dans ce plan sont des valeurs initiales raisonnables basées sur les patterns communs de ces plateformes. Si un scraper retourne 0 résultats sans erreur :

1. Passer `headless=False` temporairement
2. Ouvrir les outils développeur (F12) sur la page
3. Inspecter les éléments des cartes AO
4. Mettre à jour `_CARD` et `_FIELDS` dans le scraper
5. Repasser `headless=True`

C'est une étape normale du développement de scrapers web — les sites changent leurs structures.
