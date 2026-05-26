# Sprint 1 — Corrections Audit (4 fixes) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger les 4 blocages prioritaires identifiés lors de l'audit : bug `parse_date`, deadlines manquantes dans scrapers, persistance health check, et pagination `/api/tenders`.

**Architecture:** Chaque tâche est indépendante et non-régressive. Les scrapers VAAO/Nukema restent retro-compatibles (deadline = "" si sélecteur non trouvé). La pagination backend utilise des valeurs par défaut qui n'impactent pas le frontend actuel.

**Tech Stack:** Python/FastAPI (backend), pytest, React/Axios (frontend, tâche 4 seulement)

**Règle commits:** Un commit par fichier modifié (CLAUDE.md).

---

## Task 1 : Ajouter `parse_date()` dans `scraper_utils.py`

**Problème :** `llm_analyzer.py:1463` fait `from scraper_utils import parse_date` mais cette fonction n'existe pas → l'extraction de date par le LLM échoue silencieusement pour tous les marchés sans `publication_date`.

**Files:**
- Modify: `scraper_utils.py`
- Test: `tests/test_scraper_utils.py` (nouveau fichier)

- [ ] **Étape 1 : Écrire le test**

Créer `tests/test_scraper_utils.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_utils import parse_date
from datetime import datetime


def test_parse_date_iso():
    result = parse_date("2026-04-15")
    assert result == datetime(2026, 4, 15)


def test_parse_date_iso_with_time():
    result = parse_date("2026-04-15T10:30:00")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_numeric():
    result = parse_date("15/04/2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_numeric_dashes():
    result = parse_date("15-04-2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_textual():
    result = parse_date("15 avril 2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_abbreviated():
    result = parse_date("15 avr. 2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_null_string():
    assert parse_date("null") is None


def test_parse_date_empty():
    assert parse_date("") is None


def test_parse_date_none():
    assert parse_date(None) is None


def test_parse_date_garbage():
    assert parse_date("pas une date") is None
```

- [ ] **Étape 2 : Vérifier que le test échoue**

```
pytest tests/test_scraper_utils.py -v
```
Résultat attendu : `ImportError: cannot import name 'parse_date' from 'scraper_utils'`

- [ ] **Étape 3 : Implémenter `parse_date` dans `scraper_utils.py`**

Ajouter à la fin de `scraper_utils.py`, après la ligne `existing_ids.add(tender.id)` :

```python
# ── Utilitaire parsing dates ──────────────────────────────────────────────────

import re as _re
from datetime import datetime as _datetime

_FR_MONTHS = {
    "janvier": 1, "jan": 1,
    "février": 2, "fevrier": 2, "fév": 2, "fev": 2,
    "mars": 3, "mar": 3,
    "avril": 4, "avr": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7, "juil": 7,
    "août": 8, "aout": 8, "aou": 8,
    "septembre": 9, "sep": 9, "sept": 9,
    "octobre": 10, "oct": 10,
    "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}


def parse_date(s: str | None) -> "_datetime | None":
    """Parse une chaîne date vers datetime. Supporte ISO, numérique français et textuel français."""
    if not s or s in ("null", "None", "N/A", ""):
        return None
    s = s.strip()
    # ISO: 2026-04-15 ou 2026-04-15T10:30:00
    try:
        return _datetime.fromisoformat(s[:10])
    except (ValueError, TypeError):
        pass
    # Numérique français: 15/04/2026 ou 15-04-2026
    m = _re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", s)
    if m:
        try:
            return _datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    # Textuel français: "15 avril 2026" ou "15 avr. 2026"
    m = _re.match(r"^(\d{1,2})\s+([a-zéûôàèê\.]+)\s+(\d{4})$", s.lower())
    if m:
        month_key = m.group(2).rstrip(".")
        month = _FR_MONTHS.get(month_key)
        if month:
            try:
                return _datetime(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                pass
    return None
```

- [ ] **Étape 4 : Vérifier que les tests passent**

```
pytest tests/test_scraper_utils.py -v
```
Résultat attendu : tous les tests `PASSED`.

- [ ] **Étape 5 : Commit**

```
git add scraper_utils.py
git commit -m "feat(scraper_utils): ajouter parse_date() pour extraction dates LLM"
git add tests/test_scraper_utils.py
git commit -m "test(scraper_utils): tests parse_date formats ISO/français"
```

---

## Task 2 : Extraction deadline dans `scraper_vaao.py`

**Problème :** `_normalise` retourne `"deadline": ""` hardcodé. Les urgences générées par le LLM existent mais `deadline` = None → les marchés VAAO n'apparaissent jamais dans l'onglet Urgences.

**Files:**
- Modify: `scraper_vaao.py`
- Test: `tests/test_scrapers_playwright.py` (ajouter cas)

- [ ] **Étape 1 : Écrire le test**

Ajouter dans `tests/test_scrapers_playwright.py` après le test `test_fetch_vaao_inserts_relevant` :

```python
def test_fetch_vaao_extracts_deadline():
    import scraper_vaao

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_vaao._extract_card",
            return_value={
                "name": "Installation SSI Réunion",
                "description": "",
                "url": "https://www.vaao.fr/ao/1",
                "raw_date": "2026-04-15",
                "raw_deadline": "2026-05-30",
            },
        ):
            result = scraper_vaao.fetch()

    assert len(result) >= 1
    assert result[0]["deadline"] == "2026-05-30"


def test_fetch_vaao_empty_deadline_stays_empty():
    import scraper_vaao

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_vaao._extract_card",
            return_value={
                "name": "Installation SSI Réunion",
                "description": "",
                "url": "https://www.vaao.fr/ao/1",
                "raw_date": "2026-04-15",
                "raw_deadline": "",
            },
        ):
            result = scraper_vaao.fetch()

    assert len(result) >= 1
    assert result[0]["deadline"] == ""
```

- [ ] **Étape 2 : Vérifier que les tests échouent**

```
pytest tests/test_scrapers_playwright.py::test_fetch_vaao_extracts_deadline -v
```
Résultat attendu : `FAILED` — `raw_deadline` non transmis par `_extract_card`.

- [ ] **Étape 3 : Modifier `scraper_vaao.py`**

Dans `_extract_card`, remplacer :
```python
    return {
        "name": title,
        "description": description,
        "url": url or base_url,
        "raw_date": date,
    }
```
par :
```python
    deadline = text(
        ".field--name-field-date-limite, .date-limite, .deadline, "
        ".echeance, .field--name-field-echeance, time[datetime]"
    )
    return {
        "name": title,
        "description": description,
        "url": url or base_url,
        "raw_date": date,
        "raw_deadline": deadline,
    }
```

Dans `_normalise`, remplacer :
```python
    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _BASE),
        "source": "VAAO",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "description": raw.get("description", ""),
    }
```
par :
```python
    raw_deadline = raw.get("raw_deadline") or ""
    try:
        deadline = (
            datetime.fromisoformat(raw_deadline[:10]).date().isoformat()
            if raw_deadline
            else ""
        )
    except ValueError:
        deadline = raw_deadline

    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _BASE),
        "source": "VAAO",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "description": raw.get("description", ""),
    }
```

- [ ] **Étape 4 : Vérifier que les tests passent**

```
pytest tests/test_scrapers_playwright.py -k "vaao" -v
```
Résultat attendu : tous les tests VAAO `PASSED`.

- [ ] **Étape 5 : Commit**

```
git add scraper_vaao.py
git commit -m "feat(scraper_vaao): extraction deadline depuis les cartes AO"
```

---

## Task 3 : Extraction deadline dans `scraper_nukema.py`

**Problème :** Même problème que VAAO — `"deadline": ""` hardcodé.

**Files:**
- Modify: `scraper_nukema.py`
- Test: `tests/test_scrapers_playwright.py` (ajouter cas)

- [ ] **Étape 1 : Écrire le test**

Ajouter dans `tests/test_scrapers_playwright.py` après `test_fetch_nukema_inserts_relevant` :

```python
def test_fetch_nukema_extracts_deadline():
    import scraper_nukema

    mock_pw, mock_page = _make_pw_mock(
        page_url="https://marches-publics.nukema.com/consultation"
    )
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_nukema.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_nukema._extract_card",
            return_value={
                "name": "Maintenance CCTV campus 976",
                "description": "",
                "url": "https://marches-publics.nukema.com/consultation/42",
                "raw_date": "2026-05-10",
                "raw_deadline": "2026-06-15",
            },
        ):
            result = scraper_nukema.fetch()

    assert len(result) >= 1
    assert result[0]["deadline"] == "2026-06-15"
```

- [ ] **Étape 2 : Vérifier que le test échoue**

```
pytest tests/test_scrapers_playwright.py::test_fetch_nukema_extracts_deadline -v
```
Résultat attendu : `FAILED`.

- [ ] **Étape 3 : Modifier `scraper_nukema.py`**

Dans `_extract_card`, remplacer :
```python
    return {
        "name": title,
        "description": description,
        "url": url or base_url,
        "raw_date": date,
    }
```
par :
```python
    deadline = text(
        ".date-limite, .date-echeance, .deadline, .remise-offres, "
        ".card-deadline, .consultation-deadline, time[datetime]"
    )
    return {
        "name": title,
        "description": description,
        "url": url or base_url,
        "raw_date": date,
        "raw_deadline": deadline,
    }
```

Dans `_normalise`, remplacer :
```python
    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _BASE),
        "source": "Nukema",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "description": raw.get("description", ""),
    }
```
par :
```python
    raw_deadline = raw.get("raw_deadline") or ""
    try:
        deadline = (
            datetime.fromisoformat(raw_deadline[:10]).date().isoformat()
            if raw_deadline
            else ""
        )
    except ValueError:
        deadline = raw_deadline

    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _BASE),
        "source": "Nukema",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "description": raw.get("description", ""),
    }
```

- [ ] **Étape 4 : Vérifier que les tests passent**

```
pytest tests/test_scrapers_playwright.py -k "nukema" -v
```
Résultat attendu : tous `PASSED`.

- [ ] **Étape 5 : Commit**

```
git add scraper_nukema.py
git commit -m "feat(scraper_nukema): extraction deadline depuis les cartes AO"
```

---

## Task 4 : Deadline approximative dans `scraper_decp.py`

**Problème :** L'API DECP n'expose pas de deadline explicite, mais retourne `dureemois` (durée du marché en mois). On calcule une deadline approximative : `datenotification + dureemois mois`.

**Files:**
- Modify: `scraper_decp.py`
- Test: `tests/test_scrapers_new.py` (ajouter cas) ou nouveau fichier

- [ ] **Étape 1 : Écrire le test**

Ajouter dans `tests/test_scrapers_new.py` (vérifier qu'il existe, sinon créer `tests/test_decp_deadline.py`) :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_decp import _normalise


def test_normalise_calculates_deadline_from_dureemois():
    raw = {
        "id": "2026-DECP-001",
        "objet": "SSI alarme incendie lycée",
        "datenotification": "2026-01-15",
        "dureemois": 6,
        "lieuexecution_code": "97400",
        "codecpv": "45312100",
        "montant": 50000,
        "acheteur_id": "CHU-974",
    }
    result = _normalise(raw)
    assert result["deadline"] == "2026-07-15"


def test_normalise_deadline_crosses_year():
    raw = {
        "id": "2026-DECP-002",
        "objet": "Maintenance CCTV",
        "datenotification": "2026-10-01",
        "dureemois": 6,
        "lieuexecution_code": "97600",
        "codecpv": "35111300",
        "montant": None,
        "acheteur_id": "",
    }
    result = _normalise(raw)
    assert result["deadline"] == "2027-04-01"


def test_normalise_no_dureemois_leaves_deadline_empty():
    raw = {
        "id": "2026-DECP-003",
        "objet": "Travaux construction",
        "datenotification": "2026-04-01",
        "dureemois": None,
        "lieuexecution_code": "97400",
        "codecpv": "",
        "montant": None,
        "acheteur_id": "",
    }
    result = _normalise(raw)
    assert result["deadline"] == ""
```

- [ ] **Étape 2 : Vérifier que les tests échouent**

```
pytest tests/test_decp_deadline.py -v
```
Résultat attendu : `FAILED` — `deadline` est toujours `""`.

- [ ] **Étape 3 : Modifier `scraper_decp.py`**

Ajouter un helper de calcul de date en haut du fichier, après les imports :

```python
def _add_months(dt: "datetime", months: int) -> "datetime":
    """Ajoute N mois à une datetime sans dépendance dateutil."""
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    day = min(dt.day, last_day)
    return dt.replace(year=year, month=month, day=day)
```

Dans `_normalise`, remplacer :
```python
    return {
        ...
        "deadline": "",
        ...
    }
```
par (après le bloc `publication_date`) :

```python
    deadline = ""
    dureemois = raw.get("dureemois")
    if raw_date and dureemois:
        try:
            pub_dt = datetime.fromisoformat(str(raw_date)[:10])
            dl_dt = _add_months(pub_dt, int(dureemois))
            deadline = dl_dt.date().isoformat()
        except (ValueError, TypeError):
            pass
```

Et dans le dict de retour, remplacer `"deadline": "",` par `"deadline": deadline,`.

- [ ] **Étape 4 : Vérifier que les tests passent**

```
pytest tests/test_decp_deadline.py -v
```
Résultat attendu : tous `PASSED`.

- [ ] **Étape 5 : Vérifier que les tests existants ne régressent pas**

```
pytest tests/ -x -q
```
Résultat attendu : aucune régression.

- [ ] **Étape 6 : Commit**

```
git add scraper_decp.py
git commit -m "feat(scraper_decp): calcul deadline approximative via dureemois"
git add tests/test_decp_deadline.py
git commit -m "test(scraper_decp): vérifier calcul deadline dureemois"
```

---

## Task 5 : Persister les résultats `/api/health` en base

**Problème :** `health_check.py` contient `persist_health_results()` mais elle n'est jamais appelée. `ping_failures_count` reste 0 → aucune source n'est jamais désactivée automatiquement malgré les pannes.

**Files:**
- Modify: `backend/main.py` (endpoint `/api/health` + import)
- Test: `tests/test_health_check.py` (ajouter test de persistance)

- [ ] **Étape 1 : Écrire le test de persistance**

Ajouter dans `tests/test_health_check.py` :

```python
def test_persist_health_results_increments_failures(db):
    from health_check import HealthResult, persist_health_results
    from source_registry import Source
    from datetime import datetime, timezone

    # Créer une source en base
    src = Source(
        name="BOAMP — Journal Officiel",
        url="https://boamp.fr",
        category="Officiel",
        enabled=True,
        is_validated=True,
        ping_failures_count=0,
    )
    db.add(src)
    db.flush()

    results = {
        "BOAMP — Journal Officiel": HealthResult(
            name="BOAMP — Journal Officiel",
            ok=False,
            http_status=503,
            error="Service unavailable",
            checked_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    }
    persist_health_results(db, results)

    db.refresh(src)
    assert src.ping_failures_count == 1


def test_persist_health_results_resets_on_success(db):
    from health_check import HealthResult, persist_health_results
    from source_registry import Source
    from datetime import datetime, timezone

    src = Source(
        name="BOAMP — Journal Officiel",
        url="https://boamp.fr",
        category="Officiel",
        enabled=True,
        is_validated=False,
        ping_failures_count=3,
    )
    db.add(src)
    db.flush()

    results = {
        "BOAMP — Journal Officiel": HealthResult(
            name="BOAMP — Journal Officiel",
            ok=True,
            http_status=200,
            checked_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
    }
    persist_health_results(db, results)

    db.refresh(src)
    assert src.ping_failures_count == 0
```

- [ ] **Étape 2 : Vérifier que les tests passent déjà (la logique existe dans health_check.py)**

```
pytest tests/test_health_check.py::test_persist_health_results_increments_failures -v
```
Résultat attendu : `PASSED` si `Source` possède la colonne `ping_failures_count`. Si `AttributeError` → vérifier `source_registry.py` que le modèle `Source` a bien ce champ.

- [ ] **Étape 3 : Modifier `backend/main.py` — importer `persist_health_results`**

Trouver la ligne :
```python
from health_check import run_all_health_checks  # noqa: E402
```
La remplacer par :
```python
from health_check import run_all_health_checks, persist_health_results  # noqa: E402
```

- [ ] **Étape 4 : Modifier l'endpoint `/api/health` pour persister**

Trouver dans `backend/main.py` :
```python
@app.get("/api/health", summary="État des sources externes")
def health():
    results = run_all_health_checks()
    return {
        "status": "ok",
        "sources": {
            name: {"ok": r.ok, "http_status": r.http_status, "error": r.error}
            for name, r in results.items()
        },
    }
```
Remplacer par :
```python
@app.get("/api/health", summary="État des sources externes")
def health(db: Session = Depends(get_db)):
    results = run_all_health_checks()
    try:
        persist_health_results(db, results)
    except Exception:
        pass  # Ne pas bloquer la réponse si la persistance échoue
    return {
        "status": "ok",
        "sources": {
            name: {"ok": r.ok, "http_status": r.http_status, "error": r.error}
            for name, r in results.items()
        },
    }
```

- [ ] **Étape 5 : Vérifier que les tests passent**

```
pytest tests/test_health_check.py -v
```
Résultat attendu : tous `PASSED`.

- [ ] **Étape 6 : Commit**

```
git add backend/main.py
git commit -m "fix(health): persister ping_failures_count après chaque /api/health"
git add tests/test_health_check.py
git commit -m "test(health): vérifier persistance ping_failures et reset"
```

---

## Task 6 : Pagination `offset/limit` sur `GET /api/tenders`

**Problème :** L'endpoint retourne tous les marchés sans limite. À 2000+ marchés, le payload dépasse 10 MB et le frontend freeze. Solution : ajouter `limit=200` (défaut) et `offset=0` sans casser le frontend actuel qui ne passe pas ces params.

**Files:**
- Modify: `backend/main.py` (endpoint `GET /api/tenders`)
- Test: `tests/test_backend_new_routes.py` (ajouter cas de pagination)

- [ ] **Étape 1 : Écrire les tests**

Ajouter dans `tests/test_backend_new_routes.py` (ou créer `tests/test_pagination.py`) :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

from backend.main import app
from tests.conftest import *  # noqa: F401,F403


@pytest.fixture
def client(db):
    from database import get_db
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_tenders_default_limit(client, make_tender):
    for i in range(5):
        make_tender(
            id=f"PAG-{i:04d}",
            title=f"Marché test {i}",
            publication_date="2026-01-15",
        )
    resp = client.get("/api/tenders")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_tenders_limit_applied(client, make_tender):
    for i in range(10):
        make_tender(
            id=f"LIM-{i:04d}",
            title=f"Marché test {i}",
            publication_date="2026-01-15",
        )
    resp = client.get("/api/tenders?limit=3&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) <= 3


def test_get_tenders_offset_pagination(client, make_tender):
    for i in range(6):
        make_tender(
            id=f"OFF-{i:04d}",
            title=f"Marché test {i}",
            publication_date="2026-01-15",
        )
    page1 = client.get("/api/tenders?limit=3&offset=0").json()
    page2 = client.get("/api/tenders?limit=3&offset=3").json()
    ids1 = {t["id"] for t in page1}
    ids2 = {t["id"] for t in page2}
    assert ids1.isdisjoint(ids2), "Pages 1 et 2 ne doivent pas se chevaucher"
```

- [ ] **Étape 2 : Vérifier que les tests passent (le test basique) ou échouent (limit/offset)**

```
pytest tests/test_pagination.py -v
```
Résultat attendu : `test_get_tenders_limit_applied` et `test_get_tenders_offset_pagination` échouent car `limit`/`offset` ignorés.

- [ ] **Étape 3 : Modifier `backend/main.py` — ajouter params pagination**

Trouver la signature de `get_tenders` :
```python
@app.get("/api/tenders", summary="Liste des marchés avec filtres")
def get_tenders(
    status: str = Query("Tous", description="Filtre statut"),
    secteur: str = Query("Public", description="Public | Privé | International"),
    maintenance_only: bool = Query(False),
    date_from: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
    strict_date: bool = Query(False),
    only_recent: bool = Query(False, description="Publiés dans les dernières 24h"),
    db: Session = Depends(get_db),
):
```
Remplacer par :
```python
@app.get("/api/tenders", summary="Liste des marchés avec filtres")
def get_tenders(
    status: str = Query("Tous", description="Filtre statut"),
    secteur: str = Query("Public", description="Public | Privé | International"),
    maintenance_only: bool = Query(False),
    date_from: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
    strict_date: bool = Query(False),
    only_recent: bool = Query(False, description="Publiés dans les dernières 24h"),
    offset: int = Query(0, ge=0, description="Décalage pagination"),
    limit: int = Query(200, ge=1, le=2000, description="Nombre max de résultats"),
    db: Session = Depends(get_db),
):
```

Trouver la ligne de retour finale :
```python
    tenders = q.order_by(
        Tender.deadline.asc().nullslast(),
        Tender.relevance_score.desc(),
    ).all()
    return [_tender_to_dict(t) for t in tenders]
```
Remplacer par :
```python
    tenders = q.order_by(
        Tender.deadline.asc().nullslast(),
        Tender.relevance_score.desc(),
    ).offset(offset).limit(limit).all()
    return [_tender_to_dict(t) for t in tenders]
```

- [ ] **Étape 4 : Vérifier que les tests passent**

```
pytest tests/test_pagination.py -v
```
Résultat attendu : tous `PASSED`.

- [ ] **Étape 5 : Vérifier que les tests existants ne régressent pas**

```
pytest tests/ -x -q
```
Résultat attendu : aucune régression.

- [ ] **Étape 6 : Commit**

```
git add backend/main.py
git commit -m "feat(api): pagination offset/limit sur GET /api/tenders (défaut 200)"
git add tests/test_pagination.py
git commit -m "test(api): vérifier pagination offset/limit sur /api/tenders"
```

---

## Auto-review

### Couverture du spec
- [x] Bug `parse_date` → Task 1
- [x] Deadlines VAAO → Task 2
- [x] Deadlines Nukema → Task 3
- [x] Deadline DECP approximative → Task 4
- [x] Health check persistance → Task 5
- [x] Pagination `/api/tenders` → Task 6

### Scan placeholders
Aucun TBD ou TODO dans le plan.

### Cohérence des types
- `parse_date` retourne `datetime | None` — conforme à l'usage dans `llm_analyzer.py:1466` (`if _parsed:`)
- `deadline` retourne toujours un `str` ISO ou `""` — conforme aux conventions des autres scrapers
- `persist_health_results(db, results)` — signature inchangée depuis `health_check.py:194`
- `offset/limit` sont des `int` — `SQLAlchemy .offset()/.limit()` attend des `int`
