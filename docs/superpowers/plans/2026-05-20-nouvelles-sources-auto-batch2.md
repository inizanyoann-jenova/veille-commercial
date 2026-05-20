# Nouvelles sources automatiques — Batch 2 — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter 5 nouvelles sources automatiques : UNDP + ADB (RSS dans scraper_devbanks), IsDB + SEMADER + CHM Mayotte (nouveaux scrapers Playwright).

**Architecture:** Les 2 sources RSS s'ajoutent en une ligne chacune dans `FLUX_DEVBANKS` — le filtrage géo+secteur existant s'applique sans modification. Les 3 scrapers HTML suivent exactement le pattern Playwright de `scraper_vaao.py` / `scraper_nukema.py` : `extract_cards()` + `paginate()` + `insert_if_new()`. Les 5 entrées `_DEFAULT_SOURCES` dans `source_registry.py` déclenchent leur création automatique au démarrage de l'app.

**Tech Stack:** Python, feedparser (RSS), Playwright (HTML scraping), SQLAlchemy, pytest/unittest.mock

---

## Fichiers touchés

| Fichier | Action |
|---------|--------|
| `scraper_devbanks.py` | Modifier — ajouter 2 tuples dans `FLUX_DEVBANKS` |
| `source_registry.py` | Modifier — ajouter 5 entrées dans `_DEFAULT_SOURCES` |
| `scraper_isdb.py` | Créer |
| `scraper_semader.py` | Créer |
| `scraper_chm.py` | Créer |
| `tests/test_scrapers_new.py` | Modifier — ajouter tests UNDP/ADB |
| `tests/test_scrapers_playwright.py` | Modifier — ajouter tests IsDB, SEMADER, CHM |
| `tests/test_source_registry.py` | Modifier — ajouter test des 5 nouveaux noms |

---

## Task 1 — UNDP + ADB dans FLUX_DEVBANKS (RSS)

**Files:**
- Modify: `scraper_devbanks.py:19-28`
- Modify: `source_registry.py` (section `_DEFAULT_SOURCES`)
- Modify: `tests/test_scrapers_new.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_scrapers_new.py` :

```python
# ── Tests scraper_devbanks — UNDP / ADB ───────────────────────────────────────

def test_fetch_devbanks_undp_inserted():
    """Un flux UNDP avec une entrée OI/construction doit être inséré."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda k, default="": {
        "title": "UNDP Procurement — Construction hospital Madagascar",
        "summary": "Construction of new hospital infrastructure in madagascar health",
        "link": "https://procurement-notices.undp.org/view_notice.cfm?notice_id=99999",
    }.get(k, default)
    mock_entry.published = None
    mock_entry.updated = None

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    import feedparser
    with patch("feedparser.parse", return_value=mock_feed):
        with patch("scraper_devbanks.SessionLocal", Session):
            with patch("scraper_devbanks.init_db"):
                from scraper_devbanks import fetch_devbanks
                result = fetch_devbanks()

    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result >= 1
    assert any("UNDP" in t.title or "madagascar" in t.title.lower() for t in tenders)


def test_fetch_devbanks_irrelevant_skipped():
    """Une entrée sans lien OI/secteur ne doit pas être insérée."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda k, default="": {
        "title": "Project in Germany — Software Development",
        "summary": "IT consulting project in Berlin",
        "link": "https://www.adb.org/projects/12345",
    }.get(k, default)
    mock_entry.published = None
    mock_entry.updated = None

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    with patch("feedparser.parse", return_value=mock_feed):
        with patch("scraper_devbanks.SessionLocal", Session):
            with patch("scraper_devbanks.init_db"):
                from scraper_devbanks import fetch_devbanks
                result = fetch_devbanks()

    assert result == 0
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_scrapers_new.py::test_fetch_devbanks_undp_inserted tests/test_scrapers_new.py::test_fetch_devbanks_irrelevant_skipped -v
```

Le premier test doit échouer (UNDP pas encore dans FLUX_DEVBANKS, le feed est mocké sur toutes les entrées donc ça va en fait tourner). Relire le résultat — si déjà vert, continuer quand même.

- [ ] **Step 3 : Ajouter UNDP et ADB dans FLUX_DEVBANKS**

Dans `scraper_devbanks.py`, modifier la liste `FLUX_DEVBANKS` (ligne 19) :

```python
FLUX_DEVBANKS = [
    ("Zone IO", "BAD - Actualités",   "https://www.afdb.org/en/rss/news-and-events.xml"),
    ("Zone IO", "BAD - Projets",      "https://www.afdb.org/en/rss/projects.xml"),
    ("Zone IO", "BEI - Actualités",   "https://www.eib.org/en/rss/all-news.htm"),
    ("Zone IO", "BEI - Projets",      "https://www.eib.org/en/rss/projects.htm"),
    ("Zone IO", "COI - Actualités",   "https://www.commissionoceanindien.org/feed/"),
    ("Madagascar", "JICA Madagascar", "https://www.jica.go.jp/madagascar/en/activities/rss.xml"),
    ("Maurice",    "JICA Maurice",    "https://www.jica.go.jp/mauritius/en/activities/rss.xml"),
    ("Zone IO", "KfW Dev Bank",       "https://www.kfw-entwicklungsbank.de/rss/news.xml"),
    ("Zone IO", "UNDP Procurement",   "https://procurement-notices.undp.org/rss_notices.cfm"),
    ("Zone IO", "ADB — Projets",      "https://www.adb.org/rss/projects.xml"),
]
```

- [ ] **Step 4 : Ajouter les 2 entrées dans _DEFAULT_SOURCES**

Dans `source_registry.py`, après la ligne `{"name": "Tenders Go", ...}` et avant le commentaire `# ── Manuels`, ajouter :

```python
    {"name": "UNDP Procurement",
     "url": "https://procurement-notices.undp.org",
     "category": "International", "scraper_module": "scraper_devbanks",
     "scraper_func": "fetch_devbanks", "is_manual": False, "display_order": 25},
    {"name": "ADB — Banque Asiatique de Développement",
     "url": "https://www.adb.org",
     "category": "International", "scraper_module": "scraper_devbanks",
     "scraper_func": "fetch_devbanks", "is_manual": False, "display_order": 26},
```

- [ ] **Step 5 : Lancer les tests**

```
pytest tests/test_scrapers_new.py::test_fetch_devbanks_undp_inserted tests/test_scrapers_new.py::test_fetch_devbanks_irrelevant_skipped -v
```

Résultat attendu : PASSED, PASSED

- [ ] **Step 6 : Commit**

```bash
git add scraper_devbanks.py source_registry.py tests/test_scrapers_new.py
git commit -m "feat: ajouter UNDP Procurement et ADB dans FLUX_DEVBANKS (sources auto RSS)"
```

---

## Task 2 — scraper_isdb.py (Playwright)

**Files:**
- Create: `scraper_isdb.py`
- Modify: `source_registry.py`
- Modify: `tests/test_scrapers_playwright.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_scrapers_playwright.py` :

```python
# ── IsDB ──────────────────────────────────────────────────────────────────────

def test_fetch_isdb_empty_page():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_isdb.extract_cards", return_value=[]):
            with patch("scraper_isdb.paginate", return_value=False):
                with patch("scraper_isdb.SessionLocal", Session):
                    with patch("scraper_isdb.init_db"):
                        from scraper_isdb import fetch_isdb_tenders
                        result = fetch_isdb_tenders()
    assert result == 0


def test_fetch_isdb_inserts_relevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_isdb.extract_cards", return_value=[{
            "title": "Construction hôpital SSI alarme incendie Comores",
            "description": "Projet infrastructure sanitaire Comores",
            "url": "https://www.isdb.org/project-procurement/12345",
            "date": "15/05/2026",
        }]):
            with patch("scraper_isdb.paginate", return_value=False):
                with patch("scraper_isdb.SessionLocal", Session):
                    with patch("scraper_isdb.init_db"):
                        from scraper_isdb import fetch_isdb_tenders
                        result = fetch_isdb_tenders()
    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert len(tenders) == 1
    assert "SSI" in tenders[0].title or "incendie" in tenders[0].title.lower()


def test_fetch_isdb_skips_irrelevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_isdb.extract_cards", return_value=[{
            "title": "Fournitures de bureau papeterie",
            "description": "Achat fournitures",
            "url": "https://www.isdb.org/project-procurement/99999",
            "date": "",
        }]):
            with patch("scraper_isdb.paginate", return_value=False):
                with patch("scraper_isdb.SessionLocal", Session):
                    with patch("scraper_isdb.init_db"):
                        from scraper_isdb import fetch_isdb_tenders
                        result = fetch_isdb_tenders()
    assert result == 0
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_scrapers_playwright.py::test_fetch_isdb_empty_page tests/test_scrapers_playwright.py::test_fetch_isdb_inserts_relevant tests/test_scrapers_playwright.py::test_fetch_isdb_skips_irrelevant -v
```

Résultat attendu : ModuleNotFoundError (scraper_isdb inexistant)

- [ ] **Step 3 : Créer scraper_isdb.py**

Créer le fichier `scraper_isdb.py` à la racine du projet :

```python
import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import extract_cards, paginate
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_URL = "https://www.isdb.org/project-procurement"
_CARD = "tr.views-row, .views-row, article.tender, li.tender, .procurement-item, table tbody tr"
_FIELDS = {
    "title": "td.views-field-title, .views-field-title, h3, h2, td:first-child",
    "description": "td.views-field-body, .views-field-body, .description, td:nth-child(2)",
    "url": "a@href",
    "date": "td.views-field-field-date, .date, time",
}
_NEXT = "a[title='Go to next page'], li.pager__item--next a, .pager-next a"


def fetch_isdb_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "IsDB — Banque Islamique de Développement")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    try:
                        page.goto(_URL, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception as exc:
                        _log.warning("IsDB inaccessible : %s", type(exc).__name__)
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
                        return 0
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            relevant, extra_tags = classify_relevance(f"{title} {desc}")
                            if not relevant:
                                continue
                            url = card.get("url", "") or _URL
                            if url and not url.startswith("http"):
                                url = f"https://www.isdb.org{url}"
                            tid = f"ISDB-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Banque Dev.",
                                tags=extra_tags,
                            )
                            if insert_if_new(db, t, existing_ids):
                                inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                finally:
                    page.close()
            finally:
                browser.close()

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("IsDB : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("IsDB : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("IsDB : %d AO insérés", fetch_isdb_tenders())
```

- [ ] **Step 4 : Ajouter l'entrée IsDB dans _DEFAULT_SOURCES**

Dans `source_registry.py`, dans la section `# ── Banques de développement — OI`, ajouter avant la ligne `{"name": "IFC..."}` :

```python
    {"name": "IsDB — Banque Islamique de Développement",
     "url": "https://www.isdb.org/project-procurement",
     "category": "International", "scraper_module": "scraper_isdb",
     "scraper_func": "fetch_isdb_tenders", "is_manual": False, "display_order": 55},
```

- [ ] **Step 5 : Lancer les tests**

```
pytest tests/test_scrapers_playwright.py::test_fetch_isdb_empty_page tests/test_scrapers_playwright.py::test_fetch_isdb_inserts_relevant tests/test_scrapers_playwright.py::test_fetch_isdb_skips_irrelevant -v
```

Résultat attendu : PASSED, PASSED, PASSED

- [ ] **Step 6 : Commit**

```bash
git add scraper_isdb.py source_registry.py tests/test_scrapers_playwright.py
git commit -m "feat: ajouter scraper IsDB Banque Islamique (Playwright)"
```

---

## Task 3 — scraper_semader.py (Playwright)

**Files:**
- Create: `scraper_semader.py`
- Modify: `source_registry.py`
- Modify: `tests/test_scrapers_playwright.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_scrapers_playwright.py` :

```python
# ── SEMADER Réunion ───────────────────────────────────────────────────────────

def test_fetch_semader_empty_page():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_semader.extract_cards", return_value=[]):
            with patch("scraper_semader.paginate", return_value=False):
                with patch("scraper_semader.SessionLocal", Session):
                    with patch("scraper_semader.init_db"):
                        from scraper_semader import fetch_semader_tenders
                        result = fetch_semader_tenders()
    assert result == 0


def test_fetch_semader_inserts_relevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_semader.extract_cards", return_value=[{
            "title": "Réhabilitation immeuble résidentiel — vidéosurveillance CCTV",
            "description": "Programme logement social SEMADER Réunion",
            "url": "https://www.semader.re/appels-d-offres/42",
            "date": "20/05/2026",
        }]):
            with patch("scraper_semader.paginate", return_value=False):
                with patch("scraper_semader.SessionLocal", Session):
                    with patch("scraper_semader.init_db"):
                        from scraper_semader import fetch_semader_tenders
                        result = fetch_semader_tenders()
    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert len(tenders) == 1


def test_fetch_semader_skips_irrelevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_semader.extract_cards", return_value=[{
            "title": "Entretien espaces verts jardinage",
            "description": "Taille de haies et tonte",
            "url": "https://www.semader.re/appels-d-offres/10",
            "date": "",
        }]):
            with patch("scraper_semader.paginate", return_value=False):
                with patch("scraper_semader.SessionLocal", Session):
                    with patch("scraper_semader.init_db"):
                        from scraper_semader import fetch_semader_tenders
                        result = fetch_semader_tenders()
    assert result == 0
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_scrapers_playwright.py::test_fetch_semader_empty_page tests/test_scrapers_playwright.py::test_fetch_semader_inserts_relevant tests/test_scrapers_playwright.py::test_fetch_semader_skips_irrelevant -v
```

Résultat attendu : ModuleNotFoundError (scraper_semader inexistant)

- [ ] **Step 3 : Créer scraper_semader.py**

Créer le fichier `scraper_semader.py` à la racine du projet :

```python
import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import extract_cards, paginate
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_URL = "https://www.semader.re/appels-d-offres"
_CARD = "article, .views-row, .node--type-appel-offre, li.ao-item, .field-content"
_FIELDS = {
    "title": "h2, h3, .node__title, .field--name-title",
    "description": ".field--name-body, .teaser, .description, p",
    "url": "a@href",
    "date": ".date, time, .field--name-field-date",
}
_NEXT = "a[title='Page suivante'], li.pager__item--next a, .pager-next a"


def fetch_semader_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "SEMADER Réunion")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    try:
                        page.goto(_URL, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception as exc:
                        _log.warning("SEMADER inaccessible : %s", type(exc).__name__)
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
                        return 0
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            relevant, extra_tags = classify_relevance(f"{title} {desc}")
                            if not relevant:
                                continue
                            url = card.get("url", "") or _URL
                            if url and not url.startswith("http"):
                                url = f"https://www.semader.re{url}"
                            tid = f"SEMADER-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
                                tags=extra_tags,
                            )
                            if insert_if_new(db, t, existing_ids):
                                inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                finally:
                    page.close()
            finally:
                browser.close()

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("SEMADER : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("SEMADER : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("SEMADER : %d AO insérés", fetch_semader_tenders())
```

- [ ] **Step 4 : Ajouter l'entrée SEMADER dans _DEFAULT_SOURCES**

Dans `source_registry.py`, après la ligne `{"name": "Marchés Publics — Dép. 974", ...}` (display_order 6), ajouter :

```python
    {"name": "SEMADER — Appels d'offres Réunion",
     "url": "https://www.semader.re/appels-d-offres",
     "category": "Public", "scraper_module": "scraper_semader",
     "scraper_func": "fetch_semader_tenders", "is_manual": False, "display_order": 9},
```

- [ ] **Step 5 : Lancer les tests**

```
pytest tests/test_scrapers_playwright.py::test_fetch_semader_empty_page tests/test_scrapers_playwright.py::test_fetch_semader_inserts_relevant tests/test_scrapers_playwright.py::test_fetch_semader_skips_irrelevant -v
```

Résultat attendu : PASSED, PASSED, PASSED

- [ ] **Step 6 : Commit**

```bash
git add scraper_semader.py source_registry.py tests/test_scrapers_playwright.py
git commit -m "feat: ajouter scraper SEMADER Réunion (Playwright)"
```

---

## Task 4 — scraper_chm.py (Playwright)

**Files:**
- Create: `scraper_chm.py`
- Modify: `source_registry.py`
- Modify: `tests/test_scrapers_playwright.py`

- [ ] **Step 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_scrapers_playwright.py` :

```python
# ── Centre Hospitalier Mayotte ────────────────────────────────────────────────

def test_fetch_chm_empty_page():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_chm.extract_cards", return_value=[]):
            with patch("scraper_chm.paginate", return_value=False):
                with patch("scraper_chm.SessionLocal", Session):
                    with patch("scraper_chm.init_db"):
                        from scraper_chm import fetch_chm_tenders
                        result = fetch_chm_tenders()
    assert result == 0


def test_fetch_chm_inserts_relevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_chm.extract_cards", return_value=[{
            "title": "Maintenance SSI détection incendie CHM Mayotte",
            "description": "Entretien système sécurité incendie bâtiments hospitaliers",
            "url": "https://www.chm-mayotte.fr/appels-d-offres/77",
            "date": "18/05/2026",
        }]):
            with patch("scraper_chm.paginate", return_value=False):
                with patch("scraper_chm.SessionLocal", Session):
                    with patch("scraper_chm.init_db"):
                        from scraper_chm import fetch_chm_tenders
                        result = fetch_chm_tenders()
    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert "SSI" in tenders[0].title or "incendie" in tenders[0].title.lower()


def test_fetch_chm_skips_irrelevant():
    Session = _db_session()
    mock_pw, _ = _mock_pw_context()
    with patch("playwright.sync_api.sync_playwright", return_value=mock_pw):
        with patch("scraper_chm.extract_cards", return_value=[{
            "title": "Achat médicaments pharmacie",
            "description": "Fourniture produits pharmaceutiques",
            "url": "https://www.chm-mayotte.fr/appels-d-offres/55",
            "date": "",
        }]):
            with patch("scraper_chm.paginate", return_value=False):
                with patch("scraper_chm.SessionLocal", Session):
                    with patch("scraper_chm.init_db"):
                        from scraper_chm import fetch_chm_tenders
                        result = fetch_chm_tenders()
    assert result == 0
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_scrapers_playwright.py::test_fetch_chm_empty_page tests/test_scrapers_playwright.py::test_fetch_chm_inserts_relevant tests/test_scrapers_playwright.py::test_fetch_chm_skips_irrelevant -v
```

Résultat attendu : ModuleNotFoundError (scraper_chm inexistant)

- [ ] **Step 3 : Créer scraper_chm.py**

Créer le fichier `scraper_chm.py` à la racine du projet :

```python
import hashlib
import logging

from playwright.sync_api import sync_playwright

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from playwright_base import extract_cards, paginate
from scraper_utils import parse_date, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

_URL = "https://www.chm-mayotte.fr/appels-d-offres"
_CARD = "article, .views-row, .node--type-appel-offre, .field-content, li.ao-item"
_FIELDS = {
    "title": "h2, h3, .node__title, .field--name-title",
    "description": ".field--name-body, .teaser, .description, p",
    "url": "a@href",
    "date": ".date, time, .field--name-field-date",
}
_NEXT = "a[title='Page suivante'], li.pager__item--next a, .pager-next a"


def fetch_chm_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "Centre Hospitalier Mayotte")
    try:
        existing_ids = load_existing_ids(db)

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    try:
                        page.goto(_URL, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=30000)
                    except Exception as exc:
                        _log.warning("CHM inaccessible : %s", type(exc).__name__)
                        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
                        return 0
                    page_count = 0
                    while page_count < 5:
                        for card in extract_cards(page, _CARD, _FIELDS):
                            title = card.get("title", "").strip()
                            desc = card.get("description", "").strip()
                            relevant, extra_tags = classify_relevance(f"{title} {desc}")
                            if not relevant:
                                continue
                            url = card.get("url", "") or _URL
                            if url and not url.startswith("http"):
                                url = f"https://www.chm-mayotte.fr{url}"
                            tid = f"CHM-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                            t = Tender(
                                id=tid, title=title, description=desc, source=url,
                                publication_date=parse_date(card.get("date")),
                                deadline=None, status="À qualifier",
                                relevance_score=0, is_maintenance=False,
                                llm_analysis=None, secteur="Public",
                                type_opportunite="Marché Public",
                                tags=extra_tags,
                            )
                            if insert_if_new(db, t, existing_ids):
                                inserted += 1
                        if not paginate(page, _NEXT):
                            break
                        page_count += 1
                finally:
                    page.close()
            finally:
                browser.close()

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("CHM Mayotte : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("CHM Mayotte : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _log.info("CHM Mayotte : %d AO insérés", fetch_chm_tenders())
```

- [ ] **Step 4 : Ajouter l'entrée CHM dans _DEFAULT_SOURCES**

Dans `source_registry.py`, après la ligne `{"name": "CADEMA — Marchés publics", ...}` (display_order 36), ajouter :

```python
    {"name": "Centre Hospitalier de Mayotte",
     "url": "https://www.chm-mayotte.fr/appels-d-offres",
     "category": "Public", "scraper_module": "scraper_chm",
     "scraper_func": "fetch_chm_tenders", "is_manual": False, "display_order": 38},
```

- [ ] **Step 5 : Lancer les tests**

```
pytest tests/test_scrapers_playwright.py::test_fetch_chm_empty_page tests/test_scrapers_playwright.py::test_fetch_chm_inserts_relevant tests/test_scrapers_playwright.py::test_fetch_chm_skips_irrelevant -v
```

Résultat attendu : PASSED, PASSED, PASSED

- [ ] **Step 6 : Commit**

```bash
git add scraper_chm.py source_registry.py tests/test_scrapers_playwright.py
git commit -m "feat: ajouter scraper Centre Hospitalier Mayotte (Playwright)"
```

---

## Task 5 — Validation du registre des sources

**Files:**
- Modify: `tests/test_source_registry.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Ajouter à la fin de `tests/test_source_registry.py` :

```python
def test_sources_batch2_presentes():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    from source_registry import init_sources, list_sources
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    init_sources(db)
    names = {s.name for s in list_sources(db)}
    expected = [
        "UNDP Procurement",
        "ADB — Banque Asiatique de Développement",
        "IsDB — Banque Islamique de Développement",
        "SEMADER — Appels d'offres Réunion",
        "Centre Hospitalier de Mayotte",
    ]
    for name in expected:
        assert name in names, f"Source manquante : {name}"
    db.close()
```

- [ ] **Step 2 : Vérifier que le test échoue**

```
pytest tests/test_source_registry.py::test_sources_batch2_presentes -v
```

Résultat attendu : FAILED (les sources ne sont pas encore dans `_DEFAULT_SOURCES` si les tasks précédentes n'ont pas été faites — ou PASSED si elles ont déjà été faites en ordre)

- [ ] **Step 3 : Lancer la suite complète des tests**

```
pytest tests/test_source_registry.py tests/test_scrapers_new.py tests/test_scrapers_playwright.py -v
```

Résultat attendu : toutes les nouvelles tests PASSED, aucun test existant cassé.

- [ ] **Step 4 : Commit final**

```bash
git add tests/test_source_registry.py
git commit -m "test: vérifier présence des 5 sources batch2 dans le registre"
```
