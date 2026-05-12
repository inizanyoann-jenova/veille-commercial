# Évolution Veille Commerciale DEF OI — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter 4 fonctionnalités à l'app de veille DEF OI : registre dynamique des sources (table SQLite `sources`), nouveaux scrapers DECP/UNGM, sidebar à la carte avec checkboxes par catégorie, et analyse IA enrichie (System Prompt QHSE + score combiné 70/30 Gemini/local).

**Architecture:** `source_registry.py` définit le modèle SQLAlchemy `Source` et tout le CRUD. `database.py` l'initialise via un import lazy dans `init_db()`. `llm_analyzer.py` reçoit un System Prompt enrichi, un calcul de score combiné, et les nouveaux champs JSON (`tag_pertinence`, `domaines_concernes`, `justification_score`, `territoire_ia`). Le sidebar de `app.py` est entièrement régénéré depuis la table `sources`. Tous les scrapers existants sont préservés sans modification.

**Tech Stack:** Python 3.11+, Streamlit, SQLAlchemy (SQLite), google-genai (Gemini), requests, BeautifulSoup4

---

## Carte des fichiers

| Fichier | Action | Responsabilité |
|---------|--------|----------------|
| `source_registry.py` | Créer | Modèle `Source`, CRUD, données initiales |
| `database.py` | Modifier | Import lazy + appel `init_sources()` dans `init_db()` |
| `llm_analyzer.py` | Modifier | System Prompt QHSE, score combiné, nouveaux champs |
| `scraper_decp.py` | Créer | Collecte DECP API (depts 974/976) |
| `scraper_ungm.py` | Créer | Collecte UNGM (HTTP + BeautifulSoup) |
| `app.py` | Modifier | Sidebar dynamique, CRUD sources UI, fiche enrichie |
| `tests/test_source_registry.py` | Créer | Tests CRUD du registre |
| `tests/test_llm_analyzer.py` | Créer | Tests score combiné + champs locaux |
| `tests/test_scrapers_new.py` | Créer | Tests scrapers DECP/UNGM (mocks) |

Fichiers **inchangés** : `models.py`, `filters.py`, `export_excel.py`, `scraper_boamp.py`, `scraper_ted.py`, `scraper_afd.py`, `scraper_worldbank.py`, `scraper_permis.py`, `scraper_presse.py`, `scraper_devbanks.py`

---

## Task 1 : source_registry.py — Modèle + CRUD

**Fichiers :**
- Créer : `source_registry.py`
- Créer : `tests/test_source_registry.py`

- [ ] **Étape 1.1 : Écrire les tests (failing)**

Créer `tests/test_source_registry.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    # Import Source après Base pour enregistrer le modèle
    from source_registry import Source
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_init_sources_populates_table(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    sources = list_sources(db)
    assert len(sources) >= 9  # au moins les sources existantes + nouvelles


def test_init_sources_is_idempotent(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    init_sources(db)  # deuxième appel ne doit pas dupliquer
    sources = list_sources(db)
    names = [s.name for s in sources]
    assert len(names) == len(set(names))


def test_list_sources_by_category(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    public = list_sources(db, category="Public")
    assert all(s.category == "Public" for s in public)
    assert len(public) >= 3


def test_add_source(db):
    from source_registry import init_sources, add_source, list_sources
    init_sources(db)
    before = len(list_sources(db))
    add_source(db, name="Test Source", url="https://example.com", category="Public")
    after = len(list_sources(db))
    assert after == before + 1


def test_remove_manual_source(db):
    from source_registry import init_sources, add_source, remove_source, list_sources
    init_sources(db)
    s = add_source(db, name="À supprimer", url="https://example.com", category="Privé")
    result = remove_source(db, s.id)
    assert result is True
    assert all(src.name != "À supprimer" for src in list_sources(db))


def test_remove_auto_source_is_blocked(db):
    from source_registry import init_sources, list_sources, remove_source
    init_sources(db)
    auto_sources = [s for s in list_sources(db) if s.scraper_module is not None]
    assert len(auto_sources) > 0
    result = remove_source(db, auto_sources[0].id)
    assert result is False  # protection


def test_toggle_enabled(db):
    from source_registry import init_sources, list_sources, toggle_enabled
    init_sources(db)
    source = list_sources(db)[0]
    original = source.enabled
    toggle_enabled(db, source.id)
    db.refresh(source)
    assert source.enabled != original
```

- [ ] **Étape 1.2 : Vérifier que les tests échouent**

```
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
python -m pytest tests/test_source_registry.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'source_registry'`

- [ ] **Étape 1.3 : Créer source_registry.py**

```python
from sqlalchemy import Column, Integer, String, Boolean
from models import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    category = Column(String, nullable=False)   # 'Public' | 'Privé' | 'International'
    scraper_module = Column(String, default=None)
    scraper_func = Column(String, default=None)
    is_manual = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    notes = Column(String, default=None)
    display_order = Column(Integer, default=99)


_DEFAULT_SOURCES = [
    # ── Automatiques existants ────────────────────────────────────────────────
    {"name": "BOAMP — Journal Officiel",
     "url": "https://boamp-datadila.opendatasoft.com",
     "category": "Public", "scraper_module": "scraper_boamp",
     "scraper_func": "fetch_boamp_tenders", "is_manual": False, "display_order": 1},
    {"name": "DECP / PLACE",
     "url": "https://data.economie.gouv.fr",
     "category": "Public", "scraper_module": "scraper_decp",
     "scraper_func": "fetch_decp_tenders", "is_manual": False, "display_order": 2},
    {"name": "TED Europe",
     "url": "https://ted.europa.eu",
     "category": "Public", "scraper_module": "scraper_ted",
     "scraper_func": "fetch_ted_tenders", "is_manual": False, "display_order": 3},
    {"name": "Permis de construire",
     "url": "https://www.geoportail-urbanisme.gouv.fr",
     "category": "Privé", "scraper_module": "scraper_permis",
     "scraper_func": "fetch_permis_construire", "is_manual": False, "display_order": 10},
    {"name": "Presse & Institutions IO",
     "url": "https://www.zinfos974.com",
     "category": "Privé", "scraper_module": "scraper_presse",
     "scraper_func": "fetch_presse_io", "is_manual": False, "display_order": 11},
    {"name": "Banques Dev. (BAD/BEI/COI)",
     "url": "https://www.afdb.org",
     "category": "International", "scraper_module": "scraper_devbanks",
     "scraper_func": "fetch_devbanks", "is_manual": False, "display_order": 20},
    {"name": "AFD — Agence Française de Développement",
     "url": "https://opendata.afd.fr",
     "category": "International", "scraper_module": "scraper_afd",
     "scraper_func": "fetch_afd_projects", "is_manual": False, "display_order": 21},
    {"name": "Banque Mondiale",
     "url": "https://api.worldbank.org",
     "category": "International", "scraper_module": "scraper_worldbank",
     "scraper_func": "fetch_worldbank_projects", "is_manual": False, "display_order": 22},
    {"name": "UNGM",
     "url": "https://www.ungm.org/Public/Notice/SearchNotices",
     "category": "International", "scraper_module": "scraper_ungm",
     "scraper_func": "fetch_ungm_tenders", "is_manual": False, "display_order": 23},
    # ── Manuels (accès guidé) ─────────────────────────────────────────────────
    {"name": "Marché Online", "url": "https://www.marcheonline.com",
     "category": "Public", "is_manual": True, "display_order": 30},
    {"name": "Marchés Publics Info", "url": "https://www.marches-publics.info",
     "category": "Public", "is_manual": True, "display_order": 31},
    {"name": "e-marchés publics", "url": "https://www.e-marches-publics.fr",
     "category": "Public", "is_manual": True, "display_order": 32},
    {"name": "France Marchés", "url": "https://www.france-marches.fr",
     "category": "Privé", "is_manual": True, "display_order": 40},
    {"name": "Marchés Sécurisés", "url": "https://www.marches-securises.fr",
     "category": "Privé", "is_manual": True, "display_order": 41},
    {"name": "Achatpublic.com", "url": "https://www.achatpublic.com",
     "category": "Privé", "is_manual": True, "display_order": 42},
    {"name": "Dematis", "url": "https://www.dematis.com",
     "category": "Privé", "is_manual": True, "display_order": 43},
    {"name": "Instao", "url": "https://www.instao.fr",
     "category": "Privé", "is_manual": True, "display_order": 44},
    {"name": "Vaao", "url": "https://www.vaao.fr",
     "category": "Privé", "is_manual": True, "display_order": 45},
    {"name": "Nukema", "url": "https://www.nukema.fr",
     "category": "Privé", "is_manual": True, "display_order": 46},
    {"name": "Deepbloo", "url": "https://www.deepbloo.com",
     "category": "International", "is_manual": True, "display_order": 50},
    {"name": "Tenders Go", "url": "https://www.tendersgo.com",
     "category": "International", "is_manual": True, "display_order": 51},
    {"name": "Marchés internationaux", "url": "https://www.marches-internationaux.com",
     "category": "International", "is_manual": True, "display_order": 52},
]


def init_sources(db) -> None:
    """Insère les sources par défaut si la table est vide. Idempotent."""
    if db.query(Source).count() == 0:
        for data in _DEFAULT_SOURCES:
            db.add(Source(**data))
        db.commit()


def list_sources(db, category: str | None = None) -> list:
    """Retourne toutes les sources, optionnellement filtrées par catégorie."""
    q = db.query(Source)
    if category:
        q = q.filter(Source.category == category)
    return q.order_by(Source.display_order, Source.name).all()


def add_source(db, name: str, url: str, category: str, notes: str = None):
    """Ajoute une source manuelle. Retourne l'objet Source créé."""
    s = Source(name=name, url=url, category=category,
               is_manual=True, enabled=True, notes=notes)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def remove_source(db, source_id: int) -> bool:
    """Supprime une source manuelle. Retourne False si la source a un scraper dédié."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s or s.scraper_module is not None:
        return False
    db.delete(s)
    db.commit()
    return True


def toggle_enabled(db, source_id: int) -> bool:
    """Bascule l'état enabled d'une source. Retourne le nouvel état."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s:
        return False
    s.enabled = not s.enabled
    db.commit()
    return s.enabled
```

- [ ] **Étape 1.4 : Vérifier que les tests passent**

```
python -m pytest tests/test_source_registry.py -v
```

Résultat attendu : `7 passed`

- [ ] **Étape 1.5 : Commit**

```
git add source_registry.py tests/test_source_registry.py
git commit -m "feat: add source_registry with SQLAlchemy Source model and CRUD"
```

---

## Task 2 : database.py — Initialisation de la table sources

**Fichiers :**
- Modifier : `database.py`

- [ ] **Étape 2.1 : Modifier init_db() dans database.py**

Remplacer le contenu de `database.py` par :

```python
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    # Import lazy pour éviter la dépendance circulaire au niveau module
    from source_registry import Source, init_sources  # noqa: enregistre Source avec Base

    Base.metadata.create_all(bind=engine)

    # Migrations de colonnes existantes (conservées)
    with engine.connect() as conn:
        for col_name, col_def in [
            ("secteur", "VARCHAR"),
            ("type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE tenders ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except OperationalError as e:
                if "already exists" not in str(e) and "duplicate column" not in str(e):
                    raise

    # Seeding des sources par défaut si la table est vide
    db = SessionLocal()
    try:
        init_sources(db)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Étape 2.2 : Vérifier que l'app démarre sans erreur**

```
python -c "from database import init_db; init_db(); print('OK')"
```

Résultat attendu : `OK` (sans traceback). Si erreur SQLAlchemy sur la table `sources`, vérifier que `source_registry.py` est dans le même répertoire.

- [ ] **Étape 2.3 : Vérifier que les sources sont seedées**

```python
python -c "
from database import init_db, SessionLocal
init_db()
from source_registry import list_sources
db = SessionLocal()
srcs = list_sources(db)
print(f'{len(srcs)} sources chargées')
for s in srcs[:5]:
    print(f'  {s.category} | {s.name} | manuel={s.is_manual}')
db.close()
"
```

Résultat attendu : `23 sources chargées` avec les 5 premières listées correctement.

- [ ] **Étape 2.4 : Commit**

```
git add database.py
git commit -m "feat: init_db seeds sources table from source_registry"
```

---

## Task 3 : llm_analyzer.py — Enrichissement IA

**Fichiers :**
- Modifier : `llm_analyzer.py`
- Créer : `tests/test_llm_analyzer.py`

- [ ] **Étape 3.1 : Écrire les tests (failing)**

Créer `tests/test_llm_analyzer.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_compute_combined_score_with_gemini():
    from llm_analyzer import compute_combined_score
    result = compute_combined_score(gemini_score=80, local_score=50, gemini_available=True)
    assert result == round(80 * 0.70 + 50 * 0.30)  # 71


def test_compute_combined_score_without_gemini():
    from llm_analyzer import compute_combined_score
    result = compute_combined_score(gemini_score=80, local_score=50, gemini_available=False)
    assert result == 50  # local uniquement


def test_local_analyze_returns_new_fields():
    from llm_analyzer import _local_analyze
    result = _local_analyze("Maintenance SSI système de sécurité incendie La Réunion 974")
    assert "tag_pertinence" in result
    assert result["tag_pertinence"] in ("Très pertinent", "À évaluer", "Hors périmètre")
    assert "domaines_concernes" in result
    assert isinstance(result["domaines_concernes"], list)
    assert "justification_score" in result
    assert isinstance(result["justification_score"], str)
    assert "territoire_ia" in result


def test_local_analyze_ssi_reunion_high_score():
    from llm_analyzer import _local_analyze
    result = _local_analyze(
        "Marché de maintenance SSI CMSI alarme incendie - Saint-Denis La Réunion 974"
    )
    assert result["score_pertinence"] >= 65
    assert result["tag_pertinence"] == "Très pertinent"
    assert "SSI" in result["domaines_concernes"]


def test_local_analyze_gardiennage_low_score():
    from llm_analyzer import _local_analyze
    result = _local_analyze("Prestations de gardiennage et agents de sécurité")
    assert result["score_pertinence"] < 35
    assert result["tag_pertinence"] in ("À évaluer", "Hors périmètre")


def test_analyze_tender_returns_combined_score(monkeypatch):
    """Vérifie que analyze_tender combine scores quand Gemini répond."""
    from llm_analyzer import _local_analyze
    import llm_analyzer

    fake_gemini = {
        "score_pertinence": 80,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "Marché SSI direct.",
        "_source": "gemini",
    }
    monkeypatch.setattr(llm_analyzer, "_gemini_analyze", lambda text: fake_gemini)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")
    local = _local_analyze("Maintenance SSI La Réunion 974")
    expected_score = round(80 * 0.70 + local["score_pertinence"] * 0.30)
    assert result["score_pertinence"] == expected_score
    assert result["_source"] == "gemini"
```

- [ ] **Étape 3.2 : Vérifier que les tests échouent**

```
python -m pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : plusieurs `FAILED` (fonctions `compute_combined_score` et champs manquants).

- [ ] **Étape 3.3 : Réécrire llm_analyzer.py**

Remplacer le contenu complet de `llm_analyzer.py` par :

```python
import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Listes de marques concurrentes
# ---------------------------------------------------------------------------

_MARQUES_SSI = [
    "notifier", "hochiki", "apollo", "cerberus", "esser", "edwards", "kidde",
    "aritech", "autronica", "fireclass", "finsecur", "morley", "advanced",
    "nittan", "mircom", "napco", "c-tec", "tyco", "siemens", "bosch",
    "honeywell", "johnson controls", "ge security", "est3",
    "cooper", "gewiss", "daitem", "legrand", "sorhea",
]
_MARQUES_VIDEO = [
    "axis", "hikvision", "dahua", "hanwha", "avigilon", "genetec", "milestone",
    "pelco", "vivotek", "mobotix", "verkada", "ubiquiti", "sony", "panasonic",
    "bosch", "flir", "i-pro", "uniview", "reolink",
]
_MARQUES_ACCES = [
    "hid", "lenel", "assa abloy", "dorma", "kaba", "paxton", "suprema",
    "zkteco", "came", "bft", "cdvi", "fermax", "urmet", "aiphone",
]
_MARQUES_TOUTES = _MARQUES_SSI + _MARQUES_VIDEO + _MARQUES_ACCES

# ---------------------------------------------------------------------------
# Mots-clés métier
# ---------------------------------------------------------------------------

_KW_MAINTENANCE = [
    "maintenance", "entretien", "vérification", "verification", "contrat de maintenance",
    "mco", "maintien en condition", "préventif", "correctif", "gmao",
    "télémaintenance", "telemaintenance", "dépannage", "depannage",
    "intervention sur site", "contrat de service",
]
_KW_TRAVAUX = [
    "installation", "fourniture et pose", "travaux", "mise en place",
    "réalisation", "construction", "extension", "rénovation", "renovation",
    "remplacement", "mise aux normes", "fourniture", "pose et raccordement",
    "déploiement", "deploiement",
]
_KW_PENALITES = [
    "pénalité", "penalite", "pénalités de retard", "retenue de garantie",
    "dommages et intérêts", "pfa", "p.f.a.", "délai contractuel",
    "garantie décennale", "décennale", "responsabilité civile",
    "clause résolutoire", "défaillance",
]
_KW_SSI = [
    r"\bssi\b", r"\bcmsi\b", "détection incendie", "detection incendie",
    "alarme incendie", "désenfumage", "desenfumage", "évacuation incendie",
    "centrale incendie", "détecteur incendie", r"\bsprinkler\b", "extinction automatique",
    "système de sécurité incendie", "systeme de securite incendie",
]
_KW_VIDEO = [
    "vidéosurveillance", "videosurveillance", r"\bcctv\b", "caméras de sécurité",
    "cameras de securite", "vidéo protection", "video protection", "télésurveillance vidéo",
]
_KW_COURANTS_FAIBLES = [
    "courants faibles", "contrôle d'accès", "controle d'acces",
    r"\binterphonie\b", r"\bgtb\b", "anti-intrusion",
]
_KW_QHSE = [
    "qhse", "qualité hygiène sécurité", "audit incendie", "formation sécurité incendie",
    "document unique", "erp", "commission de sécurité",
]
_KW_TERRITOIRE_REUNION = [
    "réunion", "reunion", "974", "saint-denis", "saint-pierre", "saint-paul",
    "le port", "sainte-marie", "le tampon",
]
_KW_TERRITOIRE_MAYOTTE = [
    "mayotte", "976", "mamoudzou", "dzaoudzi", "koungou",
]
_KW_TERRITOIRE_IO = [
    "madagascar", "maurice", "mauritius", "comores", "comoros", "moroni",
]


def _match(kw: str, text: str) -> bool:
    if kw.startswith(r"\b"):
        return bool(re.search(kw, text))
    return kw in text


def _score_to_tag(score: int) -> str:
    if score >= 65:
        return "Très pertinent"
    elif score >= 35:
        return "À évaluer"
    return "Hors périmètre"


# ---------------------------------------------------------------------------
# Analyse locale (règles métier — sans API, toujours disponible)
# ---------------------------------------------------------------------------

def _local_analyze(text: str) -> dict:
    t = f" {text.lower()} "

    # --- Type de marché ---
    score_maint = sum(1 for kw in _KW_MAINTENANCE if _match(kw, t))
    score_trav = sum(1 for kw in _KW_TRAVAUX if _match(kw, t))
    if score_maint > score_trav:
        type_marche = "Maintenance"
    elif score_trav > 0:
        type_marche = "Travaux"
    else:
        type_marche = "Inconnu"

    # --- Marques concurrentes ---
    marques = [m for m in _MARQUES_TOUTES if re.search(r'\b' + re.escape(m) + r'\b', t)]
    marques = list(dict.fromkeys(marques))

    # --- Risques / pénalités ---
    penalites_trouvees = [kw for kw in _KW_PENALITES if kw in t]
    if penalites_trouvees:
        match = re.search(
            r'(pénalité|penalite|retenue)[^.]{0,80}(\d[\d\s]*[€%])',
            text, re.IGNORECASE
        )
        risques = (f"Pénalités détectées : {match.group(0)[:120]}" if match
                   else f"Clauses de pénalités/garantie ({', '.join(penalites_trouvees[:3])})")
    else:
        risques = None

    # --- Score de pertinence DEF ---
    score = 0
    nb_ssi = sum(1 for kw in _KW_SSI if _match(kw, t))
    nb_vid = sum(1 for kw in _KW_VIDEO if _match(kw, t))
    nb_cf = sum(1 for kw in _KW_COURANTS_FAIBLES if _match(kw, t))
    nb_qhse = sum(1 for kw in _KW_QHSE if _match(kw, t))

    if nb_ssi >= 2:      score += 50
    elif nb_ssi == 1:    score += 40
    if nb_vid >= 1:      score += 35
    if nb_cf >= 1:       score += 25
    if nb_qhse >= 1:     score += 15
    score = min(score, 50)

    if any(kw in t for kw in _KW_TERRITOIRE_REUNION):  score += 30
    elif any(kw in t for kw in _KW_TERRITOIRE_MAYOTTE): score += 28
    elif any(kw in t for kw in _KW_TERRITOIRE_IO):      score += 15

    if type_marche == "Maintenance":    score += 10
    if marques:                          score += min(len(marques) * 3, 10)
    score = min(score, 100)

    # --- Domaines concernés ---
    domaines = []
    if nb_ssi > 0:  domaines.append("SSI")
    if any(_match(kw, t) for kw in [r"\bcmsi\b", "désenfumage", "desenfumage"]): domaines.append("CMSI")
    if nb_vid > 0:  domaines.append("Vidéosurveillance")
    if nb_cf > 0:   domaines.append("Courants faibles")
    if nb_qhse > 0: domaines.append("QHSE")
    if type_marche == "Maintenance": domaines.append("Maintenance")

    # --- Territoire local ---
    if any(kw in t for kw in _KW_TERRITOIRE_REUNION):
        territoire_ia = "La Réunion"
    elif any(kw in t for kw in _KW_TERRITOIRE_MAYOTTE):
        territoire_ia = "Mayotte"
    elif any(kw in t for kw in _KW_TERRITOIRE_IO):
        territoire_ia = "Océan Indien"
    else:
        territoire_ia = "Non précisé"

    # --- Justification ---
    dom_str = ", ".join(domaines) if domaines else "aucun domaine métier détecté"
    justification = f"Analyse locale : {dom_str}. Territoire : {territoire_ia}."

    return {
        "type_marche": type_marche,
        "marques_concurrentes_citees": marques,
        "risques_penalites": risques,
        "score_pertinence": score,
        "tag_pertinence": _score_to_tag(score),
        "domaines_concernes": domaines,
        "territoire_ia": territoire_ia,
        "justification_score": justification,
        "_source": "local",
    }


# ---------------------------------------------------------------------------
# Score combiné
# ---------------------------------------------------------------------------

def compute_combined_score(gemini_score: int, local_score: int,
                            gemini_available: bool) -> int:
    """Pondère : 70 % Gemini + 30 % local si Gemini disponible, sinon 100 % local."""
    if gemini_available:
        return round(gemini_score * 0.70 + local_score * 0.30)
    return local_score


# ---------------------------------------------------------------------------
# System Prompt Gemini (réécrit — contexte DEF OI complet + QHSE)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Tu es un analyste commercial expert pour DEF Océan Indien, entreprise \
spécialisée en systèmes de sécurité incendie (SSI/CMSI), vidéosurveillance, \
courants faibles, et problématiques QHSE (Qualité, Hygiène, Sécurité, \
Environnement).

Zone prioritaire : La Réunion (974) et Mayotte (976).
Zone secondaire : Madagascar, Maurice, Comores, France métropole, International.

Cœur de métier DEF OI :
1. SSI : centrales incendie, détecteurs, déclencheurs manuels, CMSI, équipements \
d'alarme de type 1 à 4, tableaux de signalisation
2. Désenfumage / CMSI : volets de désenfumage, extracteurs de fumée, commandes \
manuelles centralisées
3. Vidéosurveillance / CCTV : caméras IP, enregistreurs NVR/DVR, VMS, analytics
4. Courants faibles : contrôle d'accès, interphonie, GTC/GTB, anti-intrusion
5. Maintenance réglementaire : vérifications annuelles SSI, MCO, contrats de \
service, GMAO
6. QHSE : audits incendie, formations sécurité incendie, accompagnement \
réglementaire ERP

EXCLURE impérativement (ne pas scorer > 20) :
- Gardiennage, agents de sécurité, SSIAP, rondes de sécurité
- Sécurité civile, pompiers, secours
- Génie civil pur, VRD, extincteurs seuls (sans composante SSI)
- Électricité générale (HT/BT) sans courants faibles

Réponds UNIQUEMENT en JSON valide :
{
  "score_pertinence": <entier 0-100>,
  "tag_pertinence": "Très pertinent" | "À évaluer" | "Hors périmètre",
  "type_marche": "Travaux" | "Maintenance" | "Fourniture" | "Mixte" | "Inconnu",
  "domaines_concernes": ["SSI", "CMSI", "Vidéosurveillance", "Courants faibles", \
"QHSE", "Maintenance"],
  "territoire": "La Réunion" | "Mayotte" | "Océan Indien" | "France métropole" | \
"International" | "Non précisé",
  "marques_concurrentes_citees": [],
  "risques_penalites": "texte court ou null",
  "justification_score": "1-2 phrases expliquant le score"
}

Barème : 80-100 = SSI/CMSI/vidéo direct sur 974/976 ; 60-79 = domaine présent \
+ territoire secondaire OU courants faibles/QHSE sur 974/976 ; 40-59 = signal \
ERP potentiel SSI ; 20-39 = faiblement pertinent ; 0-19 = hors périmètre.\
"""

_client = None


def _get_client():
    global _client
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=api_key)
        except Exception:
            return None
    return _client


def _gemini_analyze(text: str) -> dict | None:
    """Tente une analyse via Gemini. Retourne None si indisponible ou quota dépassé."""
    client = _get_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=f"Analyse ce marché :\n\n{text[:3000]}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        result["_source"] = "gemini"
        return result
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("429", "RESOURCE_EXHAUSTED", "quota", "401", "403", "API_KEY")):
            return None
        return None


# ---------------------------------------------------------------------------
# Analyse automatique en masse (local uniquement — sans quota)
# ---------------------------------------------------------------------------

def auto_analyze_pending(db) -> int:
    """Analyse tous les marchés sans llm_analysis. Moteur local uniquement."""
    from models import Tender
    pending = db.query(Tender).filter(Tender.llm_analysis == None).all()  # noqa: E711
    for t in pending:
        result = _local_analyze(f"{t.title or ''} {t.description or ''}")
        t.llm_analysis = result
        t.relevance_score = result.get("score_pertinence", 0)
        t.is_maintenance = result.get("type_marche", "").lower() == "maintenance"
    if pending:
        db.commit()
    return len(pending)


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def analyze_tender(text: str) -> dict:
    """
    Analyse un appel d'offre. Essaie Gemini en premier, calcule un score combiné
    70 % Gemini + 30 % local. Fallback sur analyse locale si Gemini indisponible.
    """
    local_result = _local_analyze(text)
    gemini_result = _gemini_analyze(text)

    if gemini_result is not None:
        combined_score = compute_combined_score(
            gemini_score=gemini_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            gemini_available=True,
        )
        gemini_result["score_pertinence"] = combined_score
        gemini_result.setdefault("tag_pertinence", _score_to_tag(combined_score))
        gemini_result.setdefault("domaines_concernes", local_result.get("domaines_concernes", []))
        gemini_result.setdefault("justification_score", local_result.get("justification_score", ""))
        gemini_result.setdefault("territoire_ia", local_result.get("territoire_ia", "Non précisé"))
        return gemini_result

    return local_result
```

- [ ] **Étape 3.4 : Vérifier que les tests passent**

```
python -m pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : `6 passed`

- [ ] **Étape 3.5 : Vérifier que les tests existants passent toujours**

```
python -m pytest tests/ -v
```

Résultat attendu : tous les tests existants + les nouveaux passent.

- [ ] **Étape 3.6 : Commit**

```
git add llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat: enrich llm_analyzer with QHSE system prompt and 70/30 combined score"
```

---

## Task 4 : scraper_decp.py — DECP / PLACE

**Fichiers :**
- Créer : `scraper_decp.py`
- Créer : `tests/test_scrapers_new.py`

> **Note API :** Le dataset `decp_augmente` est disponible sur `data.economie.gouv.fr`. Si les résultats sont vides, vérifier les noms de champs exacts via : `https://data.economie.gouv.fr/explore/dataset/decp_augmente/information/`

- [ ] **Étape 4.1 : Écrire les tests (failing)**

Créer `tests/test_scrapers_new.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
import pytest


# ── Tests scraper_decp ─────────────────────────────────────────────────────

def test_fetch_decp_returns_zero_on_empty_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [], "total_count": 0}
    mock_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_resp):
        from scraper_decp import fetch_decp_tenders
        # Utiliser une DB en mémoire
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from models import Base
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)

        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                result = fetch_decp_tenders()
    assert result == 0


def test_fetch_decp_inserts_relevant_record():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "results": [{
            "uid": "DECP-TEST-001",
            "objet": "Maintenance SSI alarme incendie La Réunion",
            "acheteur": {"nom": "CHU Réunion"},
            "dateNotification": "2025-03-01",
            "montant": 50000,
            "urlpublication": "https://data.economie.gouv.fr/test",
            "codeDepartementAcheteur": "974",
        }],
        "total_count": 1,
    }

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base, Tender
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.get", return_value=mock_resp):
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                from scraper_decp import fetch_decp_tenders
                result = fetch_decp_tenders()

    db = Session()
    tenders = db.query(Tender).all()
    db.close()
    assert result == 1
    assert len(tenders) == 1
    assert "SSI" in tenders[0].title or "incendie" in tenders[0].title.lower()


# ── Tests scraper_ungm ─────────────────────────────────────────────────────

def test_fetch_ungm_returns_zero_on_empty_html():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.text = "<html><body>No results</body></html>"
    mock_resp.status_code = 200

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.post", return_value=mock_resp):
        with patch("requests.get", return_value=mock_resp):
            with patch("scraper_ungm.SessionLocal", Session):
                with patch("scraper_ungm.init_db"):
                    from scraper_ungm import fetch_ungm_tenders
                    result = fetch_ungm_tenders()
    assert result == 0
```

- [ ] **Étape 4.2 : Vérifier que les tests échouent**

```
python -m pytest tests/test_scrapers_new.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'scraper_decp'`

- [ ] **Étape 4.3 : Créer scraper_decp.py**

```python
import hashlib
from datetime import datetime, timedelta

import requests

from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp_augmente/records"
)

_DEPT_FILTER = 'codeDepartementAcheteur in ("974", "976")'

_KEYWORD_FILTER = (
    'objet like "%SSI%"'
    ' OR objet like "%CMSI%"'
    ' OR objet like "%incendie%"'
    ' OR objet like "%désenfumage%"'
    ' OR objet like "%desenfumage%"'
    ' OR objet like "%vidéosurveillance%"'
    ' OR objet like "%videosurveillance%"'
    ' OR objet like "%caméra%"'
    ' OR objet like "%camera%"'
    ' OR objet like "%CCTV%"'
    ' OR objet like "%courants faibles%"'
)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value)[:19], fmt[:len(str(value)[:19])])
        except ValueError:
            continue
    return None


def fetch_decp_tenders(years_back: int = 2) -> int:
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    date_filter = f'dateNotification >= "{date_min}"'
    where = f"({_DEPT_FILTER}) AND ({_KEYWORD_FILTER}) AND ({date_filter})"

    init_db()
    db = SessionLocal()
    inserted = 0

    try:
        offset = 0
        limit = 100

        while True:
            params = {
                "where": where,
                "limit": limit,
                "offset": offset,
                "order_by": "dateNotification DESC",
            }
            response = requests.get(DECP_API, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            records = data.get("results", [])
            if not records:
                break

            for record in records:
                # Supporte les champs imbriqués et plats selon la version API
                acheteur = record.get("acheteur") or {}
                if isinstance(acheteur, dict):
                    acheteur_nom = acheteur.get("nom", "")
                else:
                    acheteur_nom = str(acheteur)

                objet = record.get("objet") or ""
                full_text = f"{objet} {acheteur_nom}"

                if not is_relevant_def(full_text):
                    continue

                uid = record.get("uid") or hashlib.md5(full_text.encode()).hexdigest()
                tender_id = f"DECP-{uid}"

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                url = record.get("urlpublication") or "https://data.economie.gouv.fr"

                db.add(Tender(
                    id=tender_id,
                    title=objet,
                    description=f"Acheteur : {acheteur_nom}",
                    source=url,
                    publication_date=_parse_date(record.get("dateNotification")),
                    deadline=None,
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Public",
                    type_opportunite="Marché Public",
                ))
                inserted += 1

            if len(records) < limit:
                break
            offset += limit

        if inserted:
            db.commit()

    finally:
        db.close()

    return inserted
```

- [ ] **Étape 4.4 : Vérifier que les tests passent**

```
python -m pytest tests/test_scrapers_new.py::test_fetch_decp_returns_zero_on_empty_response tests/test_scrapers_new.py::test_fetch_decp_inserts_relevant_record -v
```

Résultat attendu : `2 passed`

- [ ] **Étape 4.5 : Commit**

```
git add scraper_decp.py tests/test_scrapers_new.py
git commit -m "feat: add DECP/PLACE scraper for departments 974 and 976"
```

---

## Task 5 : scraper_ungm.py — UNGM

**Fichiers :**
- Créer : `scraper_ungm.py`

> **Note technique :** UNGM charge ses résultats via une API AJAX POST. Le scraper tente un POST JSON sur l'endpoint de recherche. Si UNGM change son API, inspecter les requêtes XHR dans le navigateur (DevTools > Network > XHR) sur `https://www.ungm.org/Public/Notice` pour trouver l'endpoint actuel.

- [ ] **Étape 5.1 : Créer scraper_ungm.py**

```python
import hashlib
import json
from datetime import datetime

import requests

from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender

UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice/SearchNotices"

_UNGM_KEYWORDS = [
    "fire detection", "SSI", "fire alarm", "fire safety",
    "smoke detection", "CCTV", "surveillance", "access control",
]

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DEF-OI-Veille/1.0)",
    "Accept": "application/json, text/html, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value)[:10], fmt[:10])
        except ValueError:
            continue
    return None


def _search_ungm(keyword: str) -> list[dict]:
    """Tente un POST JSON sur l'API UNGM. Retourne [] si indisponible."""
    payload = {
        "Title": keyword,
        "Description": "",
        "GoodsServices": "",
        "Deadline": None,
        "PublishedFrom": None,
        "CountryCodes": [],
        "AgencyId": None,
        "Status": 0,  # 0 = Active
    }
    try:
        resp = requests.post(
            UNGM_SEARCH_URL,
            headers=_HEADERS,
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("Notices", data.get("notices", data.get("results", [])))
    except Exception:
        pass
    return []


def fetch_ungm_tenders() -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    seen_ids: set[str] = set()

    try:
        for keyword in _UNGM_KEYWORDS:
            notices = _search_ungm(keyword)

            for notice in notices:
                # UNGM peut retourner des dicts avec divers noms de champs
                title = (notice.get("Title") or notice.get("title")
                         or notice.get("NoticeTitle") or "")
                description = (notice.get("Description") or notice.get("description")
                               or notice.get("GoodsServices") or "")
                full_text = f"{title} {description}"

                if not full_text.strip() or not is_relevant_def(full_text):
                    continue

                uid = (notice.get("Id") or notice.get("id")
                       or notice.get("NoticeId")
                       or hashlib.md5(full_text.encode()).hexdigest())
                tender_id = f"UNGM-{uid}"

                if tender_id in seen_ids:
                    continue
                seen_ids.add(tender_id)

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                deadline_raw = (notice.get("Deadline") or notice.get("deadline")
                                or notice.get("SubmissionDeadline"))
                pub_raw = (notice.get("PublishedOn") or notice.get("publishedOn")
                           or notice.get("PublicationDate"))
                url = (notice.get("Url") or notice.get("url")
                       or f"https://www.ungm.org/Public/Notice/{uid}")

                db.add(Tender(
                    id=tender_id,
                    title=title,
                    description=description,
                    source=url,
                    publication_date=_parse_date(pub_raw),
                    deadline=_parse_date(deadline_raw),
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Public",
                    type_opportunite="Marché International",
                ))
                inserted += 1

        if inserted:
            db.commit()

    finally:
        db.close()

    return inserted
```

- [ ] **Étape 5.2 : Vérifier que le test passe**

```
python -m pytest tests/test_scrapers_new.py::test_fetch_ungm_returns_zero_on_empty_html -v
```

Résultat attendu : `1 passed`

- [ ] **Étape 5.3 : Tous les tests passent**

```
python -m pytest tests/ -v
```

Résultat attendu : `tous passed`

- [ ] **Étape 5.4 : Commit**

```
git add scraper_ungm.py
git commit -m "feat: add UNGM scraper (POST JSON API with keyword search)"
```

---

## Task 6 : app.py — Sidebar dynamique + collecte à la carte

**Fichiers :**
- Modifier : `app.py`

Cette tâche remplace le bloc sidebar "Sources de données" (lignes 303–377) par des checkboxes dynamiques générées depuis la table `sources`.

- [ ] **Étape 6.1 : Ajouter les imports en tête de app.py**

Après la ligne `from llm_analyzer import analyze_tender, auto_analyze_pending` (ligne 8), ajouter :

```python
from source_registry import list_sources, add_source, remove_source, toggle_enabled
```

- [ ] **Étape 6.2 : Ajouter la fonction _collect_selected_sources**

Juste avant la définition du sidebar (ligne `with st.sidebar:`), ajouter :

```python
def _collect_selected_sources(selected_source_ids: list[int]) -> None:
    """Lance les scrapers des sources sélectionnées et affiche les résultats."""
    import importlib
    db_s = new_db()
    try:
        sources = list_sources(db_s)
    finally:
        db_s.close()

    total = 0
    errors = []
    with st.spinner("Collecte en cours…"):
        for source in sources:
            if source.id not in selected_source_ids:
                continue
            if source.is_manual or not source.scraper_module:
                continue
            try:
                mod = importlib.import_module(source.scraper_module)
                func = getattr(mod, source.scraper_func)
                count = func()
                total += count
            except Exception as exc:
                errors.append(f"{source.name} : {exc}")

    _run_auto_analysis()
    st.cache_data.clear()
    if total:
        st.success(f"{total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée pour les sources sélectionnées.")
    for err in errors:
        st.warning(err)
```

- [ ] **Étape 6.3 : Remplacer le bloc sidebar "Sources de données"**

Localiser dans `app.py` la ligne `st.markdown("### Sources de données")` (environ ligne 304).  
**Supprimer** tout le bloc depuis `st.markdown("### Sources de données")` jusqu'à la fin du `with st.sidebar:` (inclus le bouton "⚡ Toutes les sources").

**Remplacer par :**

```python
    st.markdown("---")
    st.markdown("### ⚡ Sources de collecte")

    db_src = new_db()
    try:
        all_sources = list_sources(db_src)
    finally:
        db_src.close()

    CATEGORY_ICONS = {"Public": "📋 Public", "Privé": "🏗️ Privé", "International": "🌍 International"}
    selected_source_ids: list[int] = []

    for cat in ["Public", "Privé", "International"]:
        cat_sources = [s for s in all_sources if s.category == cat and s.enabled]
        if not cat_sources:
            continue
        st.markdown(f"**{CATEGORY_ICONS[cat]}**")
        for s in cat_sources:
            if s.is_manual:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"<span style='color:grey;font-size:0.9em'>☐ {s.name}</span>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.link_button("🔗", url=s.url, help=f"Ouvrir {s.url}")
            else:
                checked = st.checkbox(
                    s.name,
                    value=True,
                    key=f"src_chk_{s.id}",
                )
                if checked:
                    selected_source_ids.append(s.id)

    st.markdown("")
    if st.button("⚡ Collecter la sélection", use_container_width=True, type="primary",
                 disabled=len(selected_source_ids) == 0):
        _collect_selected_sources(selected_source_ids)
```

- [ ] **Étape 6.4 : Lancer l'application et vérifier visuellement**

```
streamlit run app.py
```

Vérifier dans le sidebar :
- Les sources s'affichent groupées par catégorie (Public / Privé / International)
- Les sources automatiques ont des checkboxes cochées par défaut
- Les sources manuelles affichent un bouton 🔗 à droite
- Le bouton "⚡ Collecter la sélection" est présent en bas

- [ ] **Étape 6.5 : Commit**

```
git add app.py
git commit -m "feat: replace fixed source buttons with dynamic checkboxes by category"
```

---

## Task 7 : app.py — CRUD UI sources (Gérer les sources)

**Fichiers :**
- Modifier : `app.py`

Ajouter une section "⚙️ Gérer les sources de veille" juste avant le bloc `st.markdown("---")` final de l'app (avant le footer `DEF Océan Indien © 2025`).

- [ ] **Étape 7.1 : Ajouter la section CRUD dans app.py**

Localiser la ligne `st.markdown("---")` qui précède le caption `DEF Océan Indien © 2025`.  
**Avant** cette ligne, insérer :

```python
# ── Gestion des sources ──────────────────────────────────────────────────────

with st.expander("⚙️ Gérer les sources de veille"):
    db_gs = new_db()
    try:
        all_gs = list_sources(db_gs)
    finally:
        db_gs.close()

    st.markdown("#### Sources configurées")

    for s in all_gs:
        col_name, col_cat, col_type, col_toggle, col_del = st.columns([3, 1, 1, 1, 1])
        with col_name:
            st.markdown(f"**{s.name}**")
        with col_cat:
            st.caption(s.category)
        with col_type:
            if s.scraper_module:
                st.markdown("🤖 Auto")
            else:
                st.markdown("👤 Manuel")
        with col_toggle:
            label_toggle = "✅" if s.enabled else "❌"
            if st.button(label_toggle, key=f"toggle_{s.id}", help="Activer/Désactiver"):
                db_t = new_db()
                try:
                    toggle_enabled(db_t, s.id)
                finally:
                    db_t.close()
                st.cache_data.clear()
                st.rerun()
        with col_del:
            if s.scraper_module is None:  # uniquement les sources manuelles
                if st.button("🗑️", key=f"del_{s.id}", help="Supprimer cette source"):
                    db_d = new_db()
                    try:
                        remove_source(db_d, s.id)
                    finally:
                        db_d.close()
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.markdown("—")  # sources auto protégées

    st.markdown("---")
    st.markdown("#### Ajouter une source de veille")

    with st.form("form_add_source", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            new_name = st.text_input("Nom de la source *", placeholder="Ex : SEAO Québec")
            new_url = st.text_input("URL *", placeholder="https://...")
        with col_b:
            new_cat = st.selectbox("Catégorie", ["Public", "Privé", "International"])
            new_notes = st.text_input("Notes (optionnel)", placeholder="Ex : Appels d'offres Québec")

        submitted_src = st.form_submit_button("➕ Ajouter la source", use_container_width=True)
        if submitted_src:
            if not new_name.strip() or not new_url.strip():
                st.error("Le nom et l'URL sont obligatoires.")
            else:
                db_a = new_db()
                try:
                    add_source(db_a, name=new_name.strip(), url=new_url.strip(),
                               category=new_cat, notes=new_notes.strip() or None)
                finally:
                    db_a.close()
                st.success(f"✅ « {new_name} » ajoutée comme source {new_cat}.")
                st.cache_data.clear()
                st.rerun()
```

- [ ] **Étape 7.2 : Vérifier dans le navigateur**

```
streamlit run app.py
```

Faire défiler jusqu'en bas de la page. Vérifier :
- L'expander "⚙️ Gérer les sources de veille" est visible
- En l'ouvrant, toutes les sources s'affichent avec colonnes Nom / Catégorie / Type / Toggle / Supprimer
- Les sources avec `🤖 Auto` n'ont pas de bouton 🗑️ (colonne affiche `—`)
- Le formulaire d'ajout fonctionne : remplir un nom + URL + catégorie et soumettre → la source apparaît dans la liste

- [ ] **Étape 7.3 : Commit**

```
git add app.py
git commit -m "feat: add dynamic source management UI (CRUD expander)"
```

---

## Task 8 : app.py — Fiche commerciale enrichie

**Fichiers :**
- Modifier : `app.py`

Enrichir les deux fiches commerciales (publique et privée) avec les nouveaux champs LLM : `tag_pertinence`, `domaines_concernes`, `justification_score`.

- [ ] **Étape 8.1 : Mettre à jour la fiche commerciale marchés publics**

Localiser le bloc de la fiche commerciale publique (environ ligne 509). Après le bandeau Go/No-Go (`st.success/warning/error`), **ajouter** :

```python
                # Domaines concernés (chips)
                domaines = a.get("domaines_concernes", [])
                if domaines:
                    chips = " · ".join([f"`{d}`" for d in domaines])
                    st.markdown(f"**Domaines :** {chips}")

                # Justification du score
                if a.get("justification_score"):
                    st.caption(f"💡 {a['justification_score']}")
```

Et remplacer la ligne du bandeau pour inclure le `tag_pertinence` :

```python
                # Avant (remplacer) :
                # if score >= 65:
                #     st.success(f"**{decision}** — Score {score}/100 · {domaine} · {territoire}")

                # Après :
                tag = a.get("tag_pertinence") or decision
                if score >= 65:
                    st.success(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
                elif score >= 35:
                    st.warning(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
                else:
                    st.error(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
```

- [ ] **Étape 8.2 : Appliquer les mêmes changements à la fiche signal privé**

Localiser le bloc fiche commerciale privée (environ ligne 660). Appliquer les mêmes modifications :

```python
                tag = a.get("tag_pertinence") or decision
                if score >= 65:
                    st.success(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
                elif score >= 35:
                    st.warning(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
                else:
                    st.error(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")

                domaines = a.get("domaines_concernes", [])
                if domaines:
                    chips = " · ".join([f"`{d}`" for d in domaines])
                    st.markdown(f"**Domaines :** {chips}")

                if a.get("justification_score"):
                    st.caption(f"💡 {a['justification_score']}")
```

- [ ] **Étape 8.3 : Mettre à jour la caption source de l'analyse**

Localiser la ligne :
```python
source = a.get("_source", "local")
st.caption("🤖 Analyse Gemini" if source == "gemini" else "🔍 Analyse automatique (règles métier DEF)")
```

Remplacer par :
```python
source = a.get("_source", "local")
if source == "gemini":
    st.caption("🤖 Analyse Gemini (score combiné 70 % IA + 30 % règles métier)")
else:
    st.caption("🔍 Analyse locale (règles métier DEF — Gemini indisponible ou quota dépassé)")
```

- [ ] **Étape 8.4 : Vérifier dans le navigateur**

```
streamlit run app.py
```

Sélectionner un marché dans la fiche commerciale. Vérifier :
- Le bandeau Go/No-Go affiche le `tag_pertinence` (ex: "Très pertinent") à la place de "🟢 GO"
- Les domaines s'affichent en chips (ex: `` `SSI` · `Maintenance` ``)
- La justification du score apparaît en gris sous le bandeau
- La caption indique le mode d'analyse (Gemini ou local)

- [ ] **Étape 8.5 : Lancer tous les tests**

```
python -m pytest tests/ -v
```

Résultat attendu : tous les tests passent.

- [ ] **Étape 8.6 : Commit final**

```
git add app.py
git commit -m "feat: enrich commercial file with tag_pertinence, domaines_concernes, justification_score"
```

---

## Auto-révision du plan

### Couverture de la spec

| Exigence spec | Tâche couvrant |
|---|---|
| Nouvelles sources automatiques (DECP, UNGM) | Task 4, Task 5 |
| Sources manuelles pré-chargées (13 sites) | Task 1 — `_DEFAULT_SOURCES` |
| Table SQLite `sources` | Task 1, Task 2 |
| CRUD `source_registry.py` | Task 1 |
| Interface ajout/suppression sources | Task 7 |
| Toggle enabled/disabled | Task 7 |
| Protection sources auto contre suppression | Task 1 (`remove_source`) |
| Sidebar dynamique par catégorie | Task 6 |
| Sources manuelles = lien 🔗 (pas checkbox collecte) | Task 6 |
| Un seul bouton "Collecter la sélection" | Task 6 |
| System Prompt QHSE enrichi | Task 3 |
| Score combiné 70 % Gemini + 30 % local | Task 3 |
| Champs `tag_pertinence`, `domaines_concernes`, `justification_score`, `territoire_ia` | Task 3 |
| Fallback local si Gemini indisponible | Task 3 (`analyze_tender`) |
| Affichage enrichi fiche commerciale | Task 8 |
| Scrapers existants inchangés | ✅ Aucune modification dans les scrapers existants |
| Table `tenders` inchangée | ✅ Nouveaux champs restent dans colonne JSON `llm_analysis` |

### Cohérence des types

- `list_sources()` retourne `list[Source]` — utilisé tel quel dans Task 6 (itération) et Task 7 (CRUD UI) ✅
- `add_source()` → `Source` — retour utilisé uniquement pour confirmation dans Task 7 ✅
- `remove_source()` → `bool` — résultat ignoré dans Task 7 (rerun immédiat) ✅
- `compute_combined_score(gemini_score, local_score, gemini_available)` → `int` — signature identique en Task 3 test et implémentation ✅
- `_local_analyze()` retourne dict avec tous les nouveaux champs — utilisés dans `analyze_tender()` via `.setdefault()` ✅
- `fetch_decp_tenders()` → `int` — cohérent avec le pattern des scrapers existants ✅
- `fetch_ungm_tenders()` → `int` — idem ✅
