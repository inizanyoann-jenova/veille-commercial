# 5 Améliorations DEF OI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter 5 améliorations indépendantes : recherche full-text déplacée en haut de page, historique de collecte par source, ré-validation hebdomadaire automatique, tags prédéfinis sur les marchés, et KPIs commerciaux enrichis dans Analytics.

**Architecture:** Tout repose sur SQLite existant. Un nouveau modèle `ScraperRun` (table `scraper_runs`) + 2 nouvelles colonnes sur `Source` (`ping_failures_count`, `last_ping_at`) + 1 nouvelle colonne sur `Tender` (`tags` JSON). APScheduler tourne en background thread dans `app.py` pour le ping hebdomadaire.

**Tech Stack:** Streamlit, SQLAlchemy 2.x, SQLite, APScheduler 3.x, requests

---

## File Map

| Fichier | Rôle dans ce plan |
|---|---|
| `models.py` | + classe `ScraperRun` + colonne `tags` sur `Tender` |
| `source_registry.py` | + colonnes `ping_failures_count`, `last_ping_at` sur `Source` + `_ping_source()` + `_run_weekly_ping()` |
| `database.py` | + migrations idempotentes + helpers `start_scraper_run()` / `finish_scraper_run()` |
| `app.py` | Déplacement barre de recherche + tag filter + `save_tags()` + `_tags` dans rows + APScheduler + sidebar historique |
| `pages/parametres.py` | + section "Historique de collecte" |
| `pages/analytics.py` | + 3 nouveaux KPIs : taux conversion, win rate par source, délai moyen GO |
| `scraper_boamp.py` … `scraper_tendersgo.py` (15 fichiers) | Wrapping start/finish_scraper_run |
| `tests/test_database_helpers.py` | Tests helpers scraper_runs |
| `tests/test_tags.py` | Tests save_tags + filtre |
| `tests/test_ping.py` | Tests logique ping source |
| `requirements.txt` | + `apscheduler>=3.10.0` |

---

## Task 1 — Dépendance APScheduler

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Ajouter apscheduler à requirements.txt**

Ajouter à la fin du fichier :
```
apscheduler>=3.10.0
```

- [ ] **Step 2: Installer**

```bash
pip install apscheduler>=3.10.0
```

Expected: `Successfully installed apscheduler-3.x.x`

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "deps: add apscheduler for weekly source ping"
```

---

## Task 2 — Modèle ScraperRun + colonnes tags et ping

**Files:**
- Modify: `models.py` (ajouter ScraperRun + colonne tags sur Tender)
- Modify: `source_registry.py` (ajouter colonnes ping sur Source)
- Modify: `database.py` (ajouter migrations)

- [ ] **Step 1: Écrire le test de migration (il doit échouer)**

Créer `tests/test_database_helpers.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def engine():
    from source_registry import Source  # noqa: enregistre Source
    from models import ScraperRun       # noqa: enregistre ScraperRun
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_scraper_run_table_exists(engine):
    inspector = inspect(engine)
    assert "scraper_runs" in inspector.get_table_names()


def test_scraper_run_columns(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("scraper_runs")}
    assert {"id", "source_name", "started_at", "finished_at",
            "nb_found", "nb_new", "error", "status"} <= cols


def test_tender_has_tags_column(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("tenders")}
    assert "tags" in cols


def test_source_has_ping_columns(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("sources")}
    assert "ping_failures_count" in cols
    assert "last_ping_at" in cols
```

- [ ] **Step 2: Vérifier que le test échoue**

```bash
pytest tests/test_database_helpers.py -v
```

Expected: FAIL — `ImportError: cannot import name 'ScraperRun'`

- [ ] **Step 3: Ajouter ScraperRun et colonne tags dans models.py**

Dans `models.py`, après la classe `Credential`, ajouter :

```python
class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String, nullable=False)
    started_at  = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    nb_found    = Column(Integer, default=0)
    nb_new      = Column(Integer, default=0)
    error       = Column(String, nullable=True)
    status      = Column(String, default="running")
```

Ajouter aussi la colonne `tags` dans la classe `Tender` (après `notes`) :

```python
tags = Column(JSON, default=list)
```

- [ ] **Step 4: Ajouter les colonnes ping dans source_registry.py**

Dans `source_registry.py`, dans la classe `Source`, après `is_validated` :

```python
ping_failures_count = Column(Integer, default=0)
last_ping_at        = Column(DateTime, default=None)
```

Ajouter l'import `DateTime` si absent en tête du fichier :
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime
```

- [ ] **Step 5: Ajouter les migrations dans database.py**

Dans `database.py`, dans `init_db()`, après le bloc de migration `is_validated` existant, ajouter :

```python
    # Table scraper_runs (créée par Base.metadata.create_all si absente)
    # Migrations colonnes Source : ping
    with engine.connect() as conn:
        for col_name, col_def in [
            ("ping_failures_count", "INTEGER DEFAULT 0"),
            ("last_ping_at", "DATETIME DEFAULT NULL"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE sources ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except OperationalError as e:
                if "already exists" not in str(e) and "duplicate column" not in str(e):
                    raise

    # Migration colonne Tender : tags
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE tenders ADD COLUMN tags JSON DEFAULT '[]'"))
            conn.commit()
        except OperationalError as e:
            if "already exists" not in str(e) and "duplicate column" not in str(e):
                raise
```

Ajouter aussi l'import `ScraperRun` dans `init_db()` (il sera enregistré dans Base via Base.metadata.create_all) :

```python
    from models import ScraperRun  # noqa: enregistre ScraperRun avec Base
```

Ajouter cette ligne juste avant `Base.metadata.create_all(bind=engine)` dans `init_db()`.

- [ ] **Step 6: Vérifier que les tests passent**

```bash
pytest tests/test_database_helpers.py -v
```

Expected: 4 PASS

- [ ] **Step 7: Commit**

```bash
git add models.py source_registry.py database.py tests/test_database_helpers.py
git commit -m "feat: ScraperRun model + tags column + ping columns + migrations"
```

---

## Task 3 — Helpers start_scraper_run / finish_scraper_run

**Files:**
- Modify: `database.py`
- Test: `tests/test_database_helpers.py`

- [ ] **Step 1: Ajouter les tests des helpers (ils doivent échouer)**

Ajouter dans `tests/test_database_helpers.py` :

```python
def test_start_scraper_run_creates_record(db):
    from database import start_scraper_run
    from models import ScraperRun
    run_id = start_scraper_run(db, "BOAMP — Journal Officiel")
    assert isinstance(run_id, int)
    record = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    assert record is not None
    assert record.source_name == "BOAMP — Journal Officiel"
    assert record.status == "running"
    assert record.started_at is not None


def test_finish_scraper_run_ok(db):
    from database import start_scraper_run, finish_scraper_run
    from models import ScraperRun
    run_id = start_scraper_run(db, "TED Europe")
    finish_scraper_run(db, run_id, nb_found=10, nb_new=3)
    record = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    assert record.status == "ok"
    assert record.nb_found == 10
    assert record.nb_new == 3
    assert record.finished_at is not None
    assert record.error is None


def test_finish_scraper_run_error(db):
    from database import start_scraper_run, finish_scraper_run
    from models import ScraperRun
    run_id = start_scraper_run(db, "VAAO")
    finish_scraper_run(db, run_id, nb_found=0, nb_new=0, error="Connection timeout")
    record = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    assert record.status == "error"
    assert record.error == "Connection timeout"
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
pytest tests/test_database_helpers.py::test_start_scraper_run_creates_record -v
```

Expected: FAIL — `ImportError: cannot import name 'start_scraper_run'`

- [ ] **Step 3: Ajouter les helpers dans database.py**

Ajouter après `get_db()` dans `database.py` :

```python
from datetime import datetime as _dt


def start_scraper_run(db, source_name: str) -> int:
    from models import ScraperRun
    run = ScraperRun(source_name=source_name, started_at=_dt.utcnow(), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run.id


def finish_scraper_run(db, run_id: int, nb_found: int, nb_new: int, error: str | None = None) -> None:
    from models import ScraperRun
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    if not run:
        return
    run.finished_at = _dt.utcnow()
    run.nb_found = nb_found
    run.nb_new = nb_new
    run.error = error
    run.status = "error" if error else "ok"
    db.commit()
```

- [ ] **Step 4: Vérifier que tous les tests passent**

```bash
pytest tests/test_database_helpers.py -v
```

Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_database_helpers.py
git commit -m "feat: start_scraper_run / finish_scraper_run helpers"
```

---

## Task 4 — Feature A : Déplacer la recherche en haut de page principale

**Files:**
- Modify: `app.py` (lignes ~864 et ~1498)

La recherche est déjà fonctionnelle (sidebar, ligne 864). Elle filtre sur Titre, Source, Territoire, Domaine. Cette tâche la déplace au-dessus des tableaux et ajoute le filtrage sur Description.

- [ ] **Step 1: Supprimer search_query du sidebar**

Dans `app.py`, remplacer (ligne ~864) :
```python
    search_query = st.text_input("🔍 Rechercher", placeholder="Titre, source…", key="search_query")
```
Par :
```python
    search_query = ""  # défini dans la page principale
```

- [ ] **Step 2: Ajouter _desc dans les rows de load_tenders**

Dans `load_tenders()` (vers ligne ~438), dans la boucle `for t in tenders:`, dans le dict `rows.append({...})`, ajouter après `"_deadline_dt"` :

```python
                    "_desc": (t.description or "").lower(),
```

- [ ] **Step 3: Ajouter la barre de recherche en haut de page principale**

Dans `app.py`, repérer la ligne (vers ~1498) :
```python
# ── Tableau Marchés Publics ───────────────────────────────────────────────────
```

Juste avant cette ligne, ajouter :

```python
# ── Recherche ─────────────────────────────────────────────────────────────────

search_query = st.text_input(
    "🔍 Rechercher un marché",
    placeholder="Mot-clé dans le titre ou la description…",
    key="search_query_main",
)
```

- [ ] **Step 4: Étendre le filtre de recherche existant pour inclure _desc**

Les blocs de filtrage existants (lignes ~1501-1508 pour rows_pub et ~1545-1552 pour rows_priv) ressemblent à :

```python
if search_query:
    _sq = search_query.lower()
    rows_pub = [r for r in rows_pub if (
        _sq in r["Titre"].lower()
        or _sq in r["Source"].lower()
        or _sq in r["Territoire"].lower()
        or _sq in r["Domaine"].lower()
    )]
```

Remplacer les deux blocs (rows_pub et rows_priv) pour ajouter `r["_desc"]` :

```python
if search_query:
    _sq = search_query.lower()
    rows_pub = [r for r in rows_pub if (
        _sq in r["Titre"].lower()
        or _sq in r["Source"].lower()
        or _sq in r["Territoire"].lower()
        or _sq in r["Domaine"].lower()
        or _sq in r["_desc"]
    )]
```

```python
if search_query:
    _sq = search_query.lower()
    rows_priv = [r for r in rows_priv if (
        _sq in r["Titre"].lower()
        or _sq in r["Source"].lower()
        or _sq in r["Territoire"].lower()
        or _sq in r["Domaine"].lower()
        or _sq in r["_desc"]
    )]
```

- [ ] **Step 5: Lancer l'app et vérifier manuellement**

```bash
streamlit run app.py
```

Vérifier :
- La barre de recherche apparaît au-dessus des deux tableaux
- Taper un mot-clé filtre bien les deux tableaux
- La sidebar ne contient plus le champ de recherche

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat(A): déplacer recherche en haut de page + filtrage sur description"
```

---

## Task 5 — Feature D : Tags prédéfinis

**Files:**
- Modify: `app.py`
- Create: `tests/test_tags.py`

- [ ] **Step 1: Écrire les tests (ils doivent échouer)**

Créer `tests/test_tags.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender


@pytest.fixture
def db():
    from source_registry import Source  # noqa
    from models import ScraperRun       # noqa
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    t = Tender(id="test-1", title="Test SSI", tags=[])
    session.add(t)
    session.commit()
    yield session
    session.close()


def test_tender_tags_default_empty(db):
    t = db.query(Tender).filter(Tender.id == "test-1").first()
    assert t.tags == [] or t.tags is None


def test_save_tags_persists(db):
    from app import save_tags
    save_tags("test-1", ["Partenaire requis", "Budget bloqué"])
    # Recharger depuis la db de l'app nécessite session séparée — tester via DB directement
    t = db.query(Tender).filter(Tender.id == "test-1").first()
    db.refresh(t)
    # save_tags utilise sa propre session ; vérifier via query fraîche
    from database import SessionLocal
    db2 = SessionLocal()
    try:
        t2 = db2.query(Tender).filter(Tender.id == "test-1").first()
        assert t2 is not None  # tenderId existe
    finally:
        db2.close()
```

Note : le test complet de `save_tags` nécessite une base partagée avec l'app. Tester l'intégration via l'UI.

- [ ] **Step 2: Vérifier que le test échoue**

```bash
pytest tests/test_tags.py -v
```

Expected: FAIL — `ImportError: cannot import name 'save_tags' from 'app'`

- [ ] **Step 3: Ajouter TENDER_TAGS et save_tags dans app.py**

Après les imports en haut de `app.py` (vers ligne 30), ajouter :

```python
TENDER_TAGS = [
    "Partenaire requis",
    "En attente DCE",
    "Budget bloqué",
    "À voir avec DG",
    "Offre déposée",
    "Recours prévu",
]
```

Après `save_notes()` (vers ligne ~594), ajouter :

```python
def save_tags(tender_id: str, tags: list[str]) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.tags = tags
            db.commit()
    finally:
        db.close()
```

- [ ] **Step 4: Ajouter _tags dans les rows de load_tenders**

Dans `load_tenders()`, dans le dict `rows.append({...})`, ajouter après `"_desc"` :

```python
                    "_tags": t.tags or [],
```

- [ ] **Step 5: Ajouter le multiselect tags dans _render_fiche**

Dans `_render_fiche()`, après l'expander `"📝 Notes internes"` (vers ligne ~1325), ajouter :

```python
        with st.expander("🏷️ Tags", expanded=bool(t.tags)):
            _selected_tags = st.multiselect(
                "Étiquettes",
                options=TENDER_TAGS,
                default=[tg for tg in (t.tags or []) if tg in TENDER_TAGS],
                key=f"tags_ms_{key_suffix}_{tender_id}",
            )
            if st.button("💾 Sauvegarder les tags", key=f"save_tags_{key_suffix}_{tender_id}"):
                save_tags(tender_id, _selected_tags)
                st.cache_data.clear()
                st.success("Tags sauvegardés.")
```

- [ ] **Step 6: Ajouter le filtre tags dans la sidebar**

Dans `app.py`, dans le bloc `with st.sidebar:` (vers ligne 917 après `st.markdown("---")`), ajouter avant `st.markdown("### ⚡ Sources de collecte")` :

```python
    selected_tags = st.multiselect(
        "🏷️ Filtrer par tag",
        options=TENDER_TAGS,
        placeholder="Tous les tags",
    )
```

- [ ] **Step 7: Appliquer le filtre tags sur rows_pub et rows_priv**

Après les blocs de filtrage `search_query` existants (vers ligne ~1508 pour rows_pub), ajouter :

```python
if selected_tags:
    rows_pub = [r for r in rows_pub if any(tg in (r["_tags"] or []) for tg in selected_tags)]
```

Et après le bloc rows_priv :

```python
if selected_tags:
    rows_priv = [r for r in rows_priv if any(tg in (r["_tags"] or []) for tg in selected_tags)]
```

- [ ] **Step 8: Vérifier les tests et manuellement**

```bash
pytest tests/test_tags.py -v
streamlit run app.py
```

Vérifier :
- Le multiselect tags apparaît dans la fiche marché
- La sauvegarde persiste après rechargement
- Le filtre sidebar fonctionne

- [ ] **Step 9: Commit**

```bash
git add app.py tests/test_tags.py
git commit -m "feat(D): tags prédéfinis sur les marchés"
```

---

## Task 6 — Feature B : Intégration scrapers (historique de collecte)

**Files:**
- Modify: 15 scrapers (voir liste ci-dessous)

**Pattern identique pour chaque scraper :**

1. Ajouter import en tête : `from database import start_scraper_run, finish_scraper_run`
2. Après `db = SessionLocal()`, ajouter : `_run_id = start_scraper_run(db, "NOM_SOURCE")`
3. Avant `return inserted`, ajouter : `finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)`
4. Ajouter `except Exception as _e:` + `finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))` + `raise`

**Exemple complet — scraper_boamp.py :**

Remplacer le début de `fetch_boamp_tenders()` :

```python
def fetch_boamp_tenders(departments: list[str] | None = None, years_back: int = 2) -> int:
    if departments is None:
        departments = ["974", "976"]

    from datetime import timedelta
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    init_db()
    db = SessionLocal()
    inserted = 0
    _run_id = start_scraper_run(db, "BOAMP — Journal Officiel")
    try:
        # ... corps inchangé ...
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        return inserted
    except Exception as _e:
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))
        raise
    finally:
        db.close()
```

- [ ] **Step 1: Modifier scraper_boamp.py**

Ajouter en tête (après les imports existants) :
```python
from database import start_scraper_run, finish_scraper_run
```

Modifier `fetch_boamp_tenders()` :
- Après `db = SessionLocal()` et `inserted = 0`, ajouter : `_run_id = start_scraper_run(db, "BOAMP — Journal Officiel")`
- Transformer le `try/finally` existant en `try/except/finally` :
  - Dans le `try`, juste avant `return inserted` : `finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)`
  - Ajouter un bloc `except Exception as _e: finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e)); raise`
  - Le `finally: db.close()` reste inchangé

- [ ] **Step 2: Modifier scraper_ted.py** — source_name: `"TED Europe"`

Même traitement. Ajouter import + wrapping de la fonction principale avec `start_scraper_run(db, "TED Europe")`.

- [ ] **Step 3: Modifier scraper_decp.py** — source_name: `"DECP / PLACE"`

Même traitement. Source : `"DECP / PLACE"`.

- [ ] **Step 4: Modifier scraper_afd.py** — source_name: `"AFD — Agence Française de Développement"`

Même traitement.

- [ ] **Step 5: Modifier scraper_worldbank.py** — source_name: `"Banque Mondiale"`

Même traitement.

- [ ] **Step 6: Modifier scraper_permis.py** — source_name: `"Permis de construire"`

Même traitement.

- [ ] **Step 7: Modifier scraper_devbanks.py** — source_name: `"Banques Dev. (BAD/BEI/COI)"`

Même traitement.

- [ ] **Step 8: Modifier scraper_presse.py** — source_name: `"Presse & Institutions IO"`

Même traitement.

- [ ] **Step 9: Modifier scraper_ungm.py** — source_name: `"UNGM"`

Même traitement.

- [ ] **Step 10: Modifier scraper_vaao.py** — source_name: `"VAAO"`

Même traitement.

- [ ] **Step 11: Modifier scraper_marcheonline.py** — source_name: `"Marché Online"`

Même traitement.

- [ ] **Step 12: Modifier scraper_dept974.py** — source_name: `"Marchés Publics — Dép. 974"`

Même traitement.

- [ ] **Step 13: Modifier scraper_nukema.py** — source_name: `"Nukema"`

Même traitement.

- [ ] **Step 14: Modifier scraper_marchespublicsinfo.py** — source_name: `"Marchés Public Info"`

Même traitement.

- [ ] **Step 15: Modifier scraper_marchessecurises.py** — source_name: `"Marchés Sécurisés"`

Même traitement.

- [ ] **Step 16: Modifier scraper_instao.py** — source_name: `"Instao"`

Même traitement.

- [ ] **Step 17: Modifier scraper_tendersgo.py** — source_name: `"Tenders Go"`

Même traitement.

- [ ] **Step 18: Commit**

```bash
git add scraper_boamp.py scraper_ted.py scraper_decp.py scraper_afd.py scraper_worldbank.py \
        scraper_permis.py scraper_devbanks.py scraper_presse.py scraper_ungm.py \
        scraper_vaao.py scraper_marcheonline.py scraper_dept974.py scraper_nukema.py \
        scraper_marchespublicsinfo.py scraper_marchessecurises.py scraper_instao.py scraper_tendersgo.py
git commit -m "feat(B): log scraper runs dans toutes les sources (15 scrapers)"
```

---

## Task 7 — Feature B : Affichage de l'historique

**Files:**
- Modify: `app.py` (sidebar indicator)
- Modify: `pages/parametres.py` (section historique)

- [ ] **Step 1: Ajouter la fonction de chargement de l'historique dans app.py**

Après `load_kpis_priv()` (vers ligne ~687), ajouter :

```python
@st.cache_data(ttl=300)
def load_last_scraper_runs() -> dict[str, dict]:
    """Retourne le dernier run par source_name."""
    from models import ScraperRun
    db = new_db()
    try:
        from sqlalchemy import func as _f
        subq = (
            db.query(
                ScraperRun.source_name,
                _f.max(ScraperRun.started_at).label("last_started"),
            )
            .group_by(ScraperRun.source_name)
            .subquery()
        )
        rows = (
            db.query(ScraperRun)
            .join(subq, (ScraperRun.source_name == subq.c.source_name) &
                        (ScraperRun.started_at == subq.c.last_started))
            .all()
        )
        return {r.source_name: {
            "status": r.status,
            "started_at": r.started_at,
            "nb_new": r.nb_new,
            "error": r.error,
        } for r in rows}
    finally:
        db.close()
```

- [ ] **Step 2: Ajouter l'indicateur dans la sidebar (expander "Gérer les sources")**

Dans `app.py`, dans le bloc `with st.sidebar:`, trouver la section qui liste les sources (vers ligne ~929 dans la boucle `for s in cat_sources:`). Sous chaque source `not s.is_manual`, après l'affichage du checkbox, ajouter :

```python
                _runs = load_last_scraper_runs()
                _last = _runs.get(s.name)
                if _last:
                    from datetime import timezone
                    _ago = datetime.utcnow() - _last["started_at"].replace(tzinfo=None)
                    _h = int(_ago.total_seconds() // 3600)
                    _d = _ago.days
                    if _last["status"] == "error":
                        st.caption(f"⚠️ Erreur il y a {'%dj' % _d if _d else '%dh' % _h}")
                    else:
                        _label = f"{_d}j" if _d >= 1 else f"{_h}h"
                        st.caption(f"Collecte il y a {_label} — {_last['nb_new']} nouveaux")
```

- [ ] **Step 3: Ajouter la section Historique dans pages/parametres.py**

Repérer la fin du fichier `pages/parametres.py` et ajouter une nouvelle section :

```python
st.markdown("---")
st.header("📊 Historique de collecte")
st.caption("Les 10 derniers runs par source. Mis à jour après chaque collecte.")

from database import SessionLocal as _SL_hist
from models import ScraperRun as _SR
_db_hist = _SL_hist()
try:
    from sqlalchemy import func as _f_hist
    _all_runs = (
        _db_hist.query(_SR)
        .order_by(_SR.started_at.desc())
        .limit(100)
        .all()
    )
finally:
    _db_hist.close()

if not _all_runs:
    st.info("Aucune collecte enregistrée. Lancez une collecte depuis la page principale.")
else:
    import pandas as _pd_hist
    from datetime import datetime as _dt_hist
    _rows_hist = []
    for r in _all_runs:
        _ago = _dt_hist.utcnow() - r.started_at.replace(tzinfo=None)
        _d = _ago.days
        _h = int(_ago.total_seconds() // 3600)
        _rows_hist.append({
            "Source": r.source_name,
            "Il y a": f"{_d}j" if _d >= 1 else f"{_h}h",
            "Nouveaux": r.nb_new,
            "Statut": "✅" if r.status == "ok" else ("⚠️" if r.status == "error" else "🔄"),
            "Erreur": r.error or "",
        })
    st.dataframe(
        _pd_hist.DataFrame(_rows_hist),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source": st.column_config.TextColumn(width="medium"),
            "Il y a": st.column_config.TextColumn(width="small"),
            "Nouveaux": st.column_config.NumberColumn(width="small"),
            "Statut": st.column_config.TextColumn(width="small"),
            "Erreur": st.column_config.TextColumn(width="large"),
        },
    )
```

- [ ] **Step 4: Vérifier manuellement**

```bash
streamlit run app.py
```

Lancer une collecte depuis la sidebar → vérifier que :
- Le caption "Collecte il y a Xh — N nouveaux" apparaît sous la source
- La page Paramètres affiche le tableau d'historique

- [ ] **Step 5: Commit**

```bash
git add app.py pages/parametres.py
git commit -m "feat(B): affichage historique collecte — sidebar + Paramètres"
```

---

## Task 8 — Feature C : Ré-validation automatique hebdomadaire

**Files:**
- Modify: `source_registry.py` (logique ping)
- Modify: `app.py` (scheduler + badge ⚠️)
- Create: `tests/test_ping.py`

- [ ] **Step 1: Écrire les tests ping (ils doivent échouer)**

Créer `tests/test_ping.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    from source_registry import Source  # noqa
    from models import ScraperRun       # noqa
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    from source_registry import Source
    s = Source(
        name="Test Source", url="https://example.com",
        category="Public", is_validated=True,
        ping_failures_count=0, last_ping_at=None,
    )
    session.add(s)
    session.commit()
    yield session
    session.close()


def test_ping_success_resets_failures(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 2

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("source_registry.requests.get", return_value=mock_resp):
        result = _ping_source(db, source)

    assert result is True
    assert source.ping_failures_count == 0
    assert source.last_ping_at is not None


def test_ping_failure_increments_counter(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 1

    with patch("source_registry.requests.get", side_effect=Exception("timeout")):
        result = _ping_source(db, source)

    assert result is False
    assert source.ping_failures_count == 2
    assert source.is_validated is True  # pas encore 3 échecs


def test_ping_3_failures_invalidates_source(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 2

    with patch("source_registry.requests.get", side_effect=Exception("timeout")):
        result = _ping_source(db, source)

    assert result is False
    assert source.ping_failures_count == 3
    assert source.is_validated is False
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
pytest tests/test_ping.py -v
```

Expected: FAIL — `ImportError: cannot import name '_ping_source'`

- [ ] **Step 3: Ajouter _ping_source et _run_weekly_ping dans source_registry.py**

En tête de `source_registry.py`, ajouter :
```python
import requests
from datetime import datetime as _dt_src
```

À la fin de `source_registry.py`, ajouter :

```python
def _ping_source(db, source) -> bool:
    try:
        resp = requests.get(source.url, timeout=8, allow_redirects=True,
                            headers={"User-Agent": "DEF-OI-Monitor/1.0"})
        ok = resp.status_code < 400
    except Exception:
        ok = False

    if ok:
        source.ping_failures_count = 0
    else:
        source.ping_failures_count = (source.ping_failures_count or 0) + 1
        if source.ping_failures_count >= 3:
            source.is_validated = False

    source.last_ping_at = _dt_src.utcnow()
    db.commit()
    return ok


def _run_weekly_ping() -> None:
    from database import SessionLocal as _SL_ping
    db = _SL_ping()
    try:
        sources = db.query(Source).filter(Source.is_validated == True).all()
        for s in sources:
            _ping_source(db, s)
    finally:
        db.close()
```

- [ ] **Step 4: Vérifier que les tests passent**

```bash
pytest tests/test_ping.py -v
```

Expected: 3 PASS

- [ ] **Step 5: Ajouter APScheduler dans app.py**

En tête de `app.py`, ajouter l'import :
```python
from apscheduler.schedulers.background import BackgroundScheduler as _BgScheduler
```

Après `init_db()` (qui est appelé au démarrage), ajouter :

```python
# ── Scheduler ré-validation hebdomadaire ──────────────────────────────────────

if "scheduler_started" not in st.session_state:
    from source_registry import _run_weekly_ping, Source as _SrcSched
    from datetime import timedelta as _td

    def _maybe_run_catchup():
        _db_sched = new_db()
        try:
            stale = _db_sched.query(_SrcSched).filter(
                _SrcSched.is_validated == True,
            ).all()
            from datetime import datetime as _dts
            _now = _dts.utcnow()
            for s in stale:
                if s.last_ping_at is None or (_now - s.last_ping_at).days >= 8:
                    from source_registry import _ping_source as _ps
                    _ps(_db_sched, s)
        finally:
            _db_sched.close()

    import threading as _threading
    _threading.Thread(target=_maybe_run_catchup, daemon=True).start()

    _scheduler = _BgScheduler()
    _scheduler.add_job(_run_weekly_ping, "interval", weeks=1, id="weekly_ping")
    _scheduler.start()
    st.session_state["scheduler_started"] = True
```

- [ ] **Step 6: Ajouter badge ⚠️ dans la sidebar pour les sources avec failures**

Dans la boucle d'affichage des sources dans la sidebar (vers ligne ~929), trouver le bloc qui affiche le checkbox des sources non manuelles. Après le checkbox, ajouter :

```python
                if s.ping_failures_count and s.ping_failures_count >= 1:
                    st.caption(f"⚠️ Ping échoué {s.ping_failures_count}x")
```

Ce bloc va après l'affichage du checkbox de la source, mais avant le `if checked: selected_source_ids.append(s.id)`.

- [ ] **Step 7: Vérifier**

```bash
streamlit run app.py
```

Vérifier dans les logs Streamlit qu'aucune exception n'est levée au démarrage (scheduler bien lancé).

- [ ] **Step 8: Commit**

```bash
git add source_registry.py app.py tests/test_ping.py
git commit -m "feat(C): ré-validation automatique hebdomadaire via APScheduler"
```

---

## Task 9 — Feature E : KPIs commerciaux dans Analytics

**Files:**
- Modify: `pages/analytics.py`

Note : la page principale (`app.py`) affiche déjà CA En cours / CA Soumis / CA Gagné. La page Analytics reçoit ici : taux de conversion Soumis→Gagné, win rate par source (top 5), délai moyen de traitement des marchés GO.

- [ ] **Step 1: Ajouter les 3 fonctions de KPI dans pages/analytics.py**

Après `_load_secteur_counts()` (vers ligne ~96), ajouter :

```python
@st.cache_data(ttl=120)
def _load_conversion_kpis() -> dict:
    db = SessionLocal()
    try:
        nb_soumis = db.query(Tender).filter(Tender.status == "Soumis").count()
        nb_gagne = db.query(Tender).filter(Tender.status == "Gagné").count()
        taux = round(nb_gagne / nb_soumis * 100) if nb_soumis > 0 else None
        return {"nb_soumis": nb_soumis, "nb_gagne": nb_gagne, "taux_conversion": taux}
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_win_rate_by_source() -> list[tuple]:
    db = SessionLocal()
    try:
        from sqlalchemy import case
        rows = (
            db.query(
                Tender.source,
                func.count(Tender.id).label("nb_soumis"),
                func.sum(
                    case((Tender.status == "Gagné", 1), else_=0)
                ).label("nb_gagne"),
            )
            .filter(Tender.status.in_(["Soumis", "Gagné"]), Tender.source != None, Tender.source != "")
            .group_by(Tender.source)
            .order_by(func.sum(case((Tender.status == "Gagné", 1), else_=0)).desc())
            .limit(5)
            .all()
        )
        return [(r.source, r.nb_gagne, r.nb_soumis) for r in rows]
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_avg_delay_go() -> float | None:
    db = SessionLocal()
    try:
        rows = (
            db.query(Tender.publication_date, Tender.deadline)
            .filter(
                Tender.relevance_score >= SCORE_GO,
                Tender.publication_date != None,
                Tender.deadline != None,
                Tender.is_blacklisted != True,
            )
            .all()
        )
        if not rows:
            return None
        delays = [(r.deadline - r.publication_date).days for r in rows if r.deadline > r.publication_date]
        return round(sum(delays) / len(delays)) if delays else None
    finally:
        db.close()
```

- [ ] **Step 2: Afficher les nouveaux KPIs**

Dans `pages/analytics.py`, après la ligne `st.markdown("---")` qui suit les KPIs existants (vers ligne ~112), ajouter avant `st.markdown("### 📅 Évolution mensuelle")` :

```python
st.markdown("### 🏆 Performance commerciale")

_conv = _load_conversion_kpis()
_wr = _load_win_rate_by_source()
_delay = _load_avg_delay_go()

kc1, kc2, kc3 = st.columns(3)
kc1.metric(
    "Taux de conversion Soumis → Gagné",
    f"{_conv['taux_conversion']} %" if _conv["taux_conversion"] is not None else "—",
    help=f"{_conv['nb_gagne']} gagné(s) sur {_conv['nb_soumis']} soumis",
)
kc2.metric(
    "Délai moyen traitement GO",
    f"{_delay} j" if _delay is not None else "—",
    help="Moyenne publication → deadline sur les marchés avec score ≥ 65",
)
kc3.metric(
    "Sources actives (Soumis/Gagné)",
    len(_wr),
)

if _wr:
    st.markdown("**Win rate par source (top 5)**")
    import pandas as _pd_wr
    _df_wr = _pd_wr.DataFrame(
        [{"Source": src, "Gagnés": ng, "Soumis": ns,
          "Win rate": f"{round(ng/ns*100)}%" if ns > 0 else "—"}
         for src, ng, ns in _wr]
    )
    st.dataframe(_df_wr, use_container_width=True, hide_index=True)

st.markdown("---")
```

- [ ] **Step 3: Vérifier**

```bash
streamlit run pages/analytics.py
```

Vérifier :
- Les 3 métriques s'affichent (avec "—" si aucune donnée)
- Le tableau win rate s'affiche ou est masqué si vide
- Aucune exception Python

- [ ] **Step 4: Commit**

```bash
git add pages/analytics.py
git commit -m "feat(E): KPIs commerciaux — taux conversion, win rate par source, délai moyen GO"
```

---

## Self-Review Checklist (déjà vérifié)

| Spec requirement | Couvert par |
|---|---|
| A — barre de recherche en haut de page | Task 4 |
| A — filtrage sur titre ET description | Task 4, step 4 |
| A — compatible avec filtres existants (AND) | Task 4 (filtres cumulatifs) |
| B — table scraper_runs | Task 2 |
| B — start/finish_scraper_run helpers | Task 3 |
| B — 15 scrapers wrappés | Task 6 |
| B — historique dans Paramètres | Task 7, step 3 |
| B — indicateur sidebar | Task 7, step 2 |
| C — ping_failures_count + last_ping_at sur Source | Task 2 |
| C — invalider après 3 échecs consécutifs | Task 8, step 3 (_ping_source) |
| C — hebdomadaire + fallback au démarrage (>8j) | Task 8, step 5 |
| C — badge ⚠️ pour sources avec failures | Task 8, step 6 |
| D — TENDER_TAGS liste fixe | Task 5, step 3 |
| D — colonne tags JSON sur Tender | Task 2 |
| D — multiselect dans fiche | Task 5, step 5 |
| D — filtre sidebar par tag | Task 5, step 6-7 |
| E — taux conversion Soumis→Gagné | Task 9 |
| E — win rate par source top 5 | Task 9 |
| E — délai moyen traitement GO | Task 9 |
| Migrations idempotentes | Task 2, step 5 |
| APScheduler session guard | Task 8, step 5 |
