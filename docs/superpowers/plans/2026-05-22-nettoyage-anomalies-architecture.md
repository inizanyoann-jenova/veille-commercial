# Nettoyage anomalies architecture (A→E) — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger 5 anomalies architecturales — déplacer `Source` dans `models.py`, supprimer une whitelist tautologique, restreindre CORS, migrer 5 routes manquantes vers `backend/main.py`, supprimer `api.py`.

**Architecture:** Corrections localisées et indépendantes. Ordre : A (models) → B (database) → D (CORS) → E (routes + suppression api.py). Re-export transparent pour A — aucun import existant ne casse, aucun test ne change.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy (SQLite), pytest

---

## Fichiers touchés

| Fichier | Action |
|---|---|
| `models.py` | Modifier — ajouter classe `Source` |
| `source_registry.py` | Modifier — remplacer définition par import |
| `database.py` | Modifier — supprimer `_VALID_COLS` et check redondant |
| `backend/main.py` | Modifier — restreindre CORS + ajouter 5 routes + imports |
| `api.py` | Supprimer |
| `tests/test_source_in_models.py` | Créer — test re-export A |
| `tests/test_backend_new_routes.py` | Créer — tests routes E |

---

### Task 1 : A — Déplacer Source dans models.py (re-export transparent)

**Files:**
- Modify: `models.py`
- Modify: `source_registry.py`
- Create: `tests/test_source_in_models.py`

- [ ] **Step 1.1 : Écrire le test (TDD — doit échouer)**

Créer `tests/test_source_in_models.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_source_class_defined_in_models():
    from models import Source
    assert Source.__tablename__ == "sources"
    assert hasattr(Source, "name")
    assert hasattr(Source, "url")
    assert hasattr(Source, "category")
    assert hasattr(Source, "is_validated")
    assert hasattr(Source, "ping_failures_count")


def test_source_still_importable_from_source_registry():
    from source_registry import Source
    assert Source.__tablename__ == "sources"
```

- [ ] **Step 1.2 : Vérifier que le test échoue**

```
pytest tests/test_source_in_models.py -v
```

Résultat attendu : `FAILED test_source_class_defined_in_models` — `ImportError: cannot import name 'Source' from 'models'`

- [ ] **Step 1.3 : Ajouter Source dans models.py**

Dans `models.py`, ajouter à la fin du fichier (après `ScoreWeight`) :

```python
class Source(Base):
    __tablename__ = "sources"

    id                  = Column(Integer, primary_key=True, autoincrement=True)
    name                = Column(String, nullable=False)
    url                 = Column(String, nullable=False)
    category            = Column(String, nullable=False)
    scraper_module      = Column(String, default=None)
    scraper_func        = Column(String, default=None)
    is_manual           = Column(Boolean, default=False)
    enabled             = Column(Boolean, default=True)
    notes               = Column(String, default=None)
    display_order       = Column(Integer, default=99)
    is_validated        = Column(Boolean, default=False)
    ping_failures_count = Column(Integer, default=0)
    last_ping_at        = Column(DateTime, default=None)
```

- [ ] **Step 1.4 : Mettre à jour source_registry.py**

Remplacer les lignes 1-23 de `source_registry.py` (import `Base` + définition entière de la classe `Source`) par :

```python
from models import Source  # noqa: re-export — `from source_registry import Source` fonctionne toujours
import requests
from datetime import datetime as _dt_src, timezone as _tz_src
```

- [ ] **Step 1.5 : Vérifier que tous les tests passent**

```
pytest tests/test_source_in_models.py tests/test_source_registry.py -v
```

Résultat attendu : tous PASSED

- [ ] **Step 1.6 : Commit models.py**

```bash
git add models.py
git commit -m "refactor(models): ajouter Source — cohérence avec les autres modèles SQLAlchemy"
```

- [ ] **Step 1.7 : Commit source_registry.py**

```bash
git add source_registry.py
git commit -m "refactor(source_registry): remplacer définition Source par import depuis models"
```

- [ ] **Step 1.8 : Commit test**

```bash
git add tests/test_source_in_models.py
git commit -m "test: vérifier Source importable depuis models et source_registry"
```

---

### Task 2 : B — Supprimer la whitelist tautologique dans database.py

**Files:**
- Modify: `database.py:35-52`

- [ ] **Step 2.1 : Baseline — vérifier que les tests existants passent**

```
pytest tests/test_database_helpers.py -v
```

Résultat attendu : tous PASSED

- [ ] **Step 2.2 : Supprimer `_VALID_COLS` et le check redondant**

Dans `database.py`, remplacer depuis `_VALID_TABLES` jusqu'à la première ligne du `try` dans `_run_migrations` :

```python
_VALID_TABLES = {"tenders", "sources"}
_VALID_COLS   = {col for _, col, _ in _MIGRATIONS}


def _run_migrations(engine) -> None:
    """Exécute les migrations de colonnes avec validation stricte des noms.

    Sécurité :
    - Les noms de tables et colonnes sont validés contre des whitelists (_VALID_TABLES, _VALID_COLS)
    - Seules les migrations définies dans _MIGRATIONS (liste statique) sont exécutées
    - Approche sécurisée pour une application locale avec validation stricte en amont
    """
    with engine.connect() as conn:
        for table, col_name, col_def in _MIGRATIONS:
            if table not in _VALID_TABLES:
                raise ValueError(f"Migration refusée — table inconnue : {table}")
            if col_name not in _VALID_COLS:
                raise ValueError(f"Migration refusée — colonne inconnue : {col_name}")
            try:
```

Par :

```python
_VALID_TABLES = {"tenders", "sources"}


def _run_migrations(engine) -> None:
    """Exécute les migrations de colonnes avec validation stricte des noms.

    Sécurité :
    - Les noms de tables sont validés contre _VALID_TABLES
    - Seules les migrations définies dans _MIGRATIONS (liste statique) sont exécutées
    - Approche sécurisée pour une application locale avec validation stricte en amont
    """
    with engine.connect() as conn:
        for table, col_name, col_def in _MIGRATIONS:
            if table not in _VALID_TABLES:
                raise ValueError(f"Migration refusée — table inconnue : {table}")
            try:
```

- [ ] **Step 2.3 : Vérifier que les tests passent toujours**

```
pytest tests/test_database_helpers.py -v
```

Résultat attendu : tous PASSED

- [ ] **Step 2.4 : Commit**

```bash
git add database.py
git commit -m "refactor(database): supprimer _VALID_COLS tautologique dans _run_migrations"
```

---

### Task 3 : D — Restreindre CORS dans backend/main.py

**Files:**
- Modify: `backend/main.py` (bloc `add_middleware` ~ligne 279)

- [ ] **Step 3.1 : Modifier le bloc CORSMiddleware**

Dans `backend/main.py`, remplacer :

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Par :

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
```

- [ ] **Step 3.2 : Commit**

```bash
git add backend/main.py
git commit -m "fix(cors): restreindre allow_methods et allow_headers — supprimer wildcards"
```

---

### Task 4 : E (TDD) — Écrire les tests pour les 5 nouvelles routes

**Files:**
- Create: `tests/test_backend_new_routes.py`

- [ ] **Step 4.1 : Créer le fichier de tests (doivent échouer)**

Créer `tests/test_backend_new_routes.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture(scope="module")
def _engine():
    import source_registry  # noqa: enregistre Source avec Base
    from models import ScraperRun, DuplicateCandidate  # noqa
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(_engine):
    Session = sessionmaker(bind=_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ── GET /api/health ────────────────────────────────────────────────────────────

def test_health_returns_ok_structure():
    import main as bm
    mock_r = MagicMock(ok=True, http_status=200, error=None)
    with patch("main.run_all_health_checks", return_value={"BOAMP": mock_r}):
        result = bm.health()
    assert result["status"] == "ok"
    assert "BOAMP" in result["sources"]
    assert result["sources"]["BOAMP"]["ok"] is True
    assert result["sources"]["BOAMP"]["http_status"] == 200


# ── POST /api/sources ──────────────────────────────────────────────────────────

def test_create_source_returns_id_and_name(db):
    import main as bm
    body = bm.SourceCreate(name="Test Source", url="https://example.com", category="Public")
    result = bm.create_source(src=body, db=db)
    assert result["name"] == "Test Source"
    assert "id" in result


# ── DELETE /api/sources/{id} ──────────────────────────────────────────────────

def test_delete_manual_source_returns_ok(db):
    import main as bm
    from source_registry import add_source
    s = add_source(db, name="À supprimer", url="https://del.com", category="Privé")
    result = bm.delete_source(source_id=s.id, db=db)
    assert result == {"ok": True}


def test_delete_source_with_scraper_raises_400(db):
    import main as bm
    from fastapi import HTTPException
    from models import Source
    s = Source(
        name="Scraper Source", url="https://scraper.com",
        category="Public", scraper_module="scraper_boamp",
        scraper_func="fetch_boamp_tenders",
    )
    db.add(s)
    db.flush()
    with pytest.raises(HTTPException) as exc_info:
        bm.delete_source(source_id=s.id, db=db)
    assert exc_info.value.status_code == 400


# ── PATCH /api/sources/{id}/toggle ────────────────────────────────────────────

def test_toggle_source_flips_enabled_state(db):
    import main as bm
    from source_registry import add_source
    s = add_source(db, name="Toggle Test", url="https://toggle.com", category="Privé")
    initial = s.enabled
    result = bm.toggle_source(source_id=s.id, db=db)
    assert result["enabled"] == (not initial)


def test_toggle_nonexistent_source_raises_404(db):
    import main as bm
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        bm.toggle_source(source_id=99999, db=db)
    assert exc_info.value.status_code == 404


# ── GET /api/export/excel ──────────────────────────────────────────────────────

def test_export_excel_returns_xlsx_response(db):
    import main as bm
    fake_xlsx = b"PK\x03\x04fake_xlsx_content"
    with patch("main.generate_executive_report", return_value=fake_xlsx):
        response = bm.export_excel(db=db)
    assert response.body == fake_xlsx
    assert "xlsx" in response.media_type
```

- [ ] **Step 4.2 : Vérifier que les tests échouent**

```
pytest tests/test_backend_new_routes.py -v
```

Résultat attendu : tous FAILED (`AttributeError: module 'main' has no attribute 'health'`, etc.)

---

### Task 5 : E (implémentation) — Ajouter 5 routes dans backend/main.py

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 5.1 : Mettre à jour les imports**

Dans `backend/main.py`, remplacer la ligne :

```python
from source_registry import list_sources  # noqa: E402
```

Par :

```python
from source_registry import list_sources, add_source, remove_source, toggle_enabled  # noqa: E402
from health_check import run_all_health_checks  # noqa: E402
from export_excel import generate_executive_report  # noqa: E402
```

Et dans le bloc d'imports FastAPI (tout en haut), ajouter `Response` :

```python
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
```

- [ ] **Step 5.2 : Ajouter le schéma Pydantic SourceCreate**

Dans la section `# ── Schémas Pydantic ──` de `backend/main.py`, après `class SavedUpdate`, ajouter :

```python
class SourceCreate(BaseModel):
    name: str
    url: str
    category: str
    notes: Optional[str] = None
```

- [ ] **Step 5.3 : Ajouter les 5 routes à la fin de backend/main.py**

Après le dernier endpoint (`POST /api/admin/archive-old`), ajouter :

```python
# ── GET /api/health ───────────────────────────────────────────────────────────

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


# ── POST /api/sources ─────────────────────────────────────────────────────────

@app.post("/api/sources", status_code=201, summary="Ajouter une source manuelle")
def create_source(src: SourceCreate, db: Session = Depends(get_db)):
    s = add_source(db, name=src.name, url=src.url, category=src.category, notes=src.notes)
    return {"id": s.id, "name": s.name}


# ── DELETE /api/sources/{id} ──────────────────────────────────────────────────

@app.delete("/api/sources/{source_id}", summary="Supprimer une source manuelle")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    ok = remove_source(db, source_id)
    if not ok:
        raise HTTPException(400, "Source introuvable ou non supprimable (scraper dédié)")
    return {"ok": True}


# ── PATCH /api/sources/{id}/toggle ───────────────────────────────────────────

@app.patch("/api/sources/{source_id}/toggle", summary="Activer / désactiver une source")
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    new_state = toggle_enabled(db, source_id)
    if new_state is None:
        raise HTTPException(404, "Source introuvable")
    return {"enabled": new_state}


# ── GET /api/export/excel ─────────────────────────────────────────────────────

@app.get("/api/export/excel", summary="Télécharger le rapport Excel")
def export_excel(db: Session = Depends(get_db)):
    data = generate_executive_report(db)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rapport_def_oi.xlsx"},
    )
```

- [ ] **Step 5.4 : Vérifier que les tests passent**

```
pytest tests/test_backend_new_routes.py -v
```

Résultat attendu : tous PASSED

- [ ] **Step 5.5 : Commit backend/main.py**

```bash
git add backend/main.py
git commit -m "feat(api): migrer 5 routes manquantes depuis api.py — health, sources CRUD, export excel"
```

- [ ] **Step 5.6 : Commit tests**

```bash
git add tests/test_backend_new_routes.py
git commit -m "test(api): couvrir routes health, sources CRUD, export excel"
```

---

### Task 6 : E (cleanup) — Supprimer api.py

**Files:**
- Delete: `api.py`

- [ ] **Step 6.1 : Vérifier la suite complète avant suppression**

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py
```

Résultat attendu : tous PASSED

- [ ] **Step 6.2 : Supprimer api.py et committer**

```bash
git rm api.py
git commit -m "remove(api): supprimer api.py legacy — toutes les routes migrées vers backend/main.py"
```

- [ ] **Step 6.3 : Vérifier la suite complète après suppression**

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py
```

Résultat attendu : tous PASSED, aucune régression
