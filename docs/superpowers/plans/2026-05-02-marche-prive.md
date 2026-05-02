# Extension Marché Privé — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter la veille marché privé à l'app DEF OI : permis de construire (974/976), presse locale IO (~20 flux), flux institutionnels (~15), et banques de développement régionales (BAD, BEI, COI, JICA, KfW).

**Architecture:** 3 nouveaux scrapers (`scraper_permis.py`, `scraper_presse.py`, `scraper_devbanks.py`) + 2 nouvelles colonnes sur le modèle `Tender` existant (`secteur`, `type_opportunite`) + nouvelle section dans `app.py`. Tout transite par la même BDD SQLite.

**Tech Stack:** Python 3.12+, SQLAlchemy 2.x, SQLite, Streamlit, `requests`, `feedparser` (nouveau), API OpenDataSoft (Sit@del2), RSS feeds.

---

## Fichiers impactés

| Fichier | Action | Rôle |
|---|---|---|
| `requirements.txt` | Modifier | Ajouter `feedparser` |
| `models.py` | Modifier | Ajouter colonnes `secteur`, `type_opportunite` |
| `database.py` | Modifier | Migration SQLite ALTER TABLE |
| `filters.py` | Modifier | Ajouter `KEYWORDS_CONSTRUCTION` |
| `scraper_permis.py` | Créer | Permis de construire Sit@del2 (974/976) |
| `scraper_presse.py` | Créer | RSS presse locale + institutions IO |
| `scraper_devbanks.py` | Créer | BAD, BEI, COI, JICA, KfW via RSS |
| `app.py` | Modifier | 3 boutons sidebar + section Marché Privé |
| `tests/test_filters.py` | Créer | Tests unitaires filtres construction |

---

## Task 1 — Dépendance feedparser

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1 : Ajouter feedparser**

Contenu final de `requirements.txt` :

```
streamlit>=1.32.0
sqlalchemy>=2.0.0
requests>=2.31.0
openai>=1.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
openpyxl>=3.1.0
feedparser>=6.0.0
```

- [ ] **Step 2 : Installer**

```bash
pip install feedparser>=6.0.0
```

Résultat attendu : `Successfully installed feedparser-6.0.x`

- [ ] **Step 3 : Commit**

```bash
git add requirements.txt
git commit -m "chore: add feedparser dependency"
```

---

## Task 2 — Migration modèle de données

**Files:**
- Modify: `models.py`
- Modify: `database.py`
- Create: `tests/test_filters.py` (infrastructure pytest)

- [ ] **Step 1 : Créer l'infrastructure de test**

Créer `tests/__init__.py` (fichier vide) et `tests/test_filters.py` :

```python
# tests/test_filters.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from filters import KEYWORDS_CONSTRUCTION, is_construction_relevant


def test_keywords_construction_not_empty():
    assert len(KEYWORDS_CONSTRUCTION) > 0


def test_is_construction_relevant_hotel():
    assert is_construction_relevant("Construction d'un hôtel 4 étoiles à Saint-Denis") is True


def test_is_construction_relevant_irrelevant():
    assert is_construction_relevant("Résultats du championnat de pétanque") is False


def test_is_construction_relevant_chantier():
    assert is_construction_relevant("Nouveau chantier immobilier dans le Nord") is True
```

- [ ] **Step 2 : Lancer les tests pour voir qu'ils échouent**

```bash
pytest tests/test_filters.py -v
```

Résultat attendu : `ImportError` ou `AttributeError` — `is_construction_relevant` n'existe pas encore.

- [ ] **Step 3 : Mettre à jour `models.py`**

Remplacer le contenu de `models.py` par :

```python
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String)
    source = Column(String)
    publication_date = Column(DateTime)
    deadline = Column(DateTime)
    status = Column(String, default="À qualifier")
    relevance_score = Column(Integer, default=0)
    is_maintenance = Column(Boolean, default=False)
    llm_analysis = Column(JSON)
    secteur = Column(String, default=None)
    type_opportunite = Column(String, default="Marché Public")
```

- [ ] **Step 4 : Mettre à jour `database.py`**

Remplacer le contenu de `database.py` par :

```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Migration : ajoute les colonnes si elles n'existent pas (SQLite ne les crée pas via create_all)
    with engine.connect() as conn:
        for col_name, col_def in [
            ("secteur", "VARCHAR"),
            ("type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE tenders ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass  # Colonne déjà présente


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 5 : Vérifier que la migration tourne sans erreur**

```bash
python -c "from database import init_db; init_db(); print('Migration OK')"
```

Résultat attendu : `Migration OK`

- [ ] **Step 6 : Commit**

```bash
git add models.py database.py tests/__init__.py tests/test_filters.py
git commit -m "feat: add secteur and type_opportunite columns to Tender model"
```

---

## Task 3 — Mots-clés construction dans filters.py

**Files:**
- Modify: `filters.py`

- [ ] **Step 1 : Mettre à jour `filters.py`**

Remplacer le contenu par :

```python
INCLUSION_KEYWORDS = [
    "ssi",
    "cmsi",
    "détection incendie",
    "désenfumage",
    "vidéosurveillance",
    "cctv",
    "caméras",
    "courants faibles",
]

EXCLUSION_KEYWORDS = [
    "gardiennage",
    "agents de sécurité",
    "télésurveillance",
    "maître-chien",
    "ssiap",
    "sécurité civile",
]

KEYWORDS_CONSTRUCTION = [
    "construction", "chantier", "permis de construire", "projet immobilier",
    "immeuble", "résidence", "hôtel", "hôpital", "clinique", "ehpad",
    "école", "lycée", "université", "centre commercial", "mall",
    "entrepôt", "usine", "réhabilitation", "rénovation", "extension",
    "bâtiment", "programme immobilier", "logements", "infrastructure",
    "complexe", "siège social", "campus", "promotion immobilière",
    "lotissement", "résidence étudiante", "résidence sénior",
]


def is_relevant_def(text: str) -> bool:
    text_lower = text.lower()
    for keyword in EXCLUSION_KEYWORDS:
        if keyword in text_lower:
            return False
    for keyword in INCLUSION_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


def is_construction_relevant(text: str) -> bool:
    """Retourne True si le texte mentionne un projet de construction susceptible de nécessiter du SSI/CMSI."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
```

- [ ] **Step 2 : Lancer les tests**

```bash
pytest tests/test_filters.py -v
```

Résultat attendu : `4 passed`

- [ ] **Step 3 : Commit**

```bash
git add filters.py tests/test_filters.py
git commit -m "feat: add KEYWORDS_CONSTRUCTION and is_construction_relevant to filters"
```

---

## Task 4 — scraper_permis.py (Permis de construire Sit@del2)

**Files:**
- Create: `scraper_permis.py`

> Sit@del2 est publié par le SDES (Ministère de la Transition Écologique) via OpenDataSoft. L'endpoint ci-dessous utilise le même pattern que BOAMP. Si l'API retourne une erreur 404, vérifier l'ID exact du dataset sur https://data.statistiques.developpement-durable.gouv.fr en cherchant "sitadel".

- [ ] **Step 1 : Créer `scraper_permis.py`**

```python
"""
Scraper Permis de Construire — Sit@del2 (SDES / data.gouv.fr).
Récupère les permis déposés sur les départements 974 (La Réunion) et 976 (Mayotte).
Filtre sur les types de bâtiments nécessitant du SSI : ERP, habitations collectives, industrie.
"""
import hashlib
from datetime import datetime, timedelta

import requests

from database import SessionLocal, init_db
from models import Tender

SITADEL_API = (
    "https://data.statistiques.developpement-durable.gouv.fr"
    "/api/explore/v2.1/catalog/datasets/sitadel/records"
)

# Types de bâtiments cibles (champ lib_type_batiment ou lib_nature_projet)
TYPES_CIBLES = [
    "erp", "établissement recevant du public",
    "habitation collective", "logement collectif", "immeuble",
    "industriel", "entrepôt", "bureau", "commerce",
    "hôpital", "clinique", "hôtel", "école", "université",
    "équipement", "salle", "centre",
]


def _type_batiment_ok(record: dict) -> bool:
    text = " ".join([
        str(record.get("lib_type_batiment") or ""),
        str(record.get("lib_nature_proj") or ""),
        str(record.get("lib_usage_principal") or ""),
    ]).lower()
    return any(t in text for t in TYPES_CIBLES) or text.strip() == ""


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value)[:10], fmt[:8])
        except ValueError:
            continue
    return None


def fetch_permis_construire(years_back: int = 1) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    try:
        for dept in ["974", "976"]:
            offset = 0
            limit = 100

            while True:
                params = {
                    "where": (
                        f"code_dep='{dept}'"
                        f" AND date_depot_doc >= '{date_min}'"
                    ),
                    "limit": limit,
                    "offset": offset,
                    "order_by": "date_depot_doc DESC",
                }

                try:
                    r = requests.get(SITADEL_API, params=params, timeout=30)
                    r.raise_for_status()
                except requests.RequestException as exc:
                    raise RuntimeError(f"Sit@del2 API ({dept}) : {exc}") from exc

                records = r.json().get("results", [])
                if not records:
                    break

                for rec in records:
                    if not _type_batiment_ok(rec):
                        continue

                    commune = rec.get("lib_nom_commune") or rec.get("lib_commune") or dept
                    nature = (
                        rec.get("lib_type_batiment")
                        or rec.get("lib_nature_proj")
                        or "Bâtiment"
                    )
                    surface = rec.get("surf_tot") or rec.get("surface_totale") or ""
                    surface_txt = f" — {surface} m²" if surface else ""

                    raw_id = (
                        rec.get("num_permis")
                        or rec.get("id_permis")
                        or hashlib.md5(str(rec).encode()).hexdigest()[:12]
                    )
                    tender_id = f"PC-{dept}-{raw_id}"

                    if db.query(Tender).filter(Tender.id == tender_id).first():
                        continue

                    title = f"[PC] {nature}{surface_txt} — {commune} ({dept})"
                    description = (
                        f"Permis de construire — Département {dept} — {commune}\n"
                        f"Nature : {nature}{surface_txt}\n"
                        f"Adresse : {rec.get('adresse') or rec.get('lib_adresse') or 'Non renseignée'}"
                    )

                    db.add(Tender(
                        id=tender_id,
                        title=title,
                        description=description,
                        source=(
                            rec.get("url") or
                            f"https://data.statistiques.developpement-durable.gouv.fr/explore/dataset/sitadel/table/?q={raw_id}"
                        ),
                        publication_date=_parse_date(rec.get("date_depot_doc") or rec.get("dat_depdoc")),
                        deadline=None,
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                        secteur="Privé",
                        type_opportunite="Permis Construire",
                    ))
                    inserted += 1

                db.commit()
                if len(records) < limit:
                    break
                offset += limit

    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    print("Collecte Permis de Construire (974 & 976)…")
    count = fetch_permis_construire()
    print(f"Terminé — {count} permis inséré(s).")
```

- [ ] **Step 2 : Tester en direct**

```bash
python scraper_permis.py
```

Si l'API retourne `404` ou `{"results": []}` : aller sur https://data.statistiques.developpement-durable.gouv.fr, chercher "sitadel", copier l'ID exact du dataset et remplacer dans `SITADEL_API`. Les noms de champs disponibles sont listés dans l'onglet "API" du dataset.

Résultat attendu si l'API fonctionne : `Terminé — N permis inséré(s).`

- [ ] **Step 3 : Commit**

```bash
git add scraper_permis.py
git commit -m "feat: add scraper_permis for Sit@del2 building permits (974/976)"
```

---

## Task 5 — scraper_presse.py (Presse locale + Institutions)

**Files:**
- Create: `scraper_presse.py`

- [ ] **Step 1 : Créer `scraper_presse.py`**

```python
"""
Scraper RSS — Presse locale et institutions de l'Océan Indien.
Filtre les articles mentionnant des projets de construction/bâtiment
susceptibles de nécessiter du SSI/CMSI/Vidéosurveillance.
"""
import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import requests

from database import SessionLocal, init_db
from filters import is_construction_relevant
from models import Tender

# ── Flux RSS presse locale ────────────────────────────────────────────────────

FLUX_PRESSE = [
    # La Réunion
    ("La Réunion", "Le JIR",             "https://www.lejir.com/feed/"),
    ("La Réunion", "Le Quotidien",        "https://www.lequotidiendelarunion.fr/feed/"),
    ("La Réunion", "Zinfos974",           "https://www.zinfos974.com/feed/"),
    ("La Réunion", "Imaz Press",          "https://www.imazpresss.re/feed/"),
    ("La Réunion", "Réunion la 1ère",     "https://la1ere.francetvinfo.fr/reunion/rss.xml"),
    ("La Réunion", "Clicanoo",            "https://www.clicanoo.re/rss"),
    ("La Réunion", "Batiactu DOM",        "https://www.batiactu.com/rss/rss_actualites.xml"),
    # Mayotte
    ("Mayotte",    "Mayotte Hebdo",       "https://www.mayottehebdo.com/feed/"),
    ("Mayotte",    "Journal de Mayotte",  "https://lejournaldemayotte.yt/feed/"),
    ("Mayotte",    "Kwezi",               "https://kwezi.fr/feed/"),
    ("Mayotte",    "Mayotte la 1ère",     "https://la1ere.francetvinfo.fr/mayotte/rss.xml"),
    # Maurice
    ("Maurice",    "L'Express Maurice",   "https://lexpress.mu/rss"),
    ("Maurice",    "Le Défi",             "https://www.defimedia.info/feed/"),
    ("Maurice",    "Business Magazine",   "https://businessmag.mu/feed/"),
    # Madagascar
    ("Madagascar", "La Tribune Mada",     "https://www.latribune.mg/feed/"),
    ("Madagascar", "L'Express Mada",      "https://lexpress.mg/feed/"),
    ("Madagascar", "Midi Madagasikara",   "https://www.midi-madagasikara.mg/feed/"),
    # Comores
    ("Comores",    "Alwatwan",            "https://alwatwan.net/feed/"),
    ("Comores",    "HZK-Presse",          "https://www.hzk-presse.com/feed/"),
    ("Comores",    "La Gazette Comores",  "https://www.lagazettedescomores.com/feed/"),
]

# ── Flux RSS institutionnels ──────────────────────────────────────────────────

FLUX_INSTITUTIONS = [
    # La Réunion — collectivités
    ("La Réunion", "Région Réunion",      "https://regionreunion.com/feed/"),
    ("La Réunion", "CD 974",              "https://www.cg974.re/feed/"),
    ("La Réunion", "CCI Réunion",         "https://www.reunion.cci.fr/feed/"),
    ("La Réunion", "CINOR",               "https://www.cinor.re/feed/"),
    ("La Réunion", "CIVIS",               "https://www.civis.re/feed/"),
    ("La Réunion", "CIREST",              "https://www.cirest.fr/feed/"),
    ("La Réunion", "CASUD",               "https://www.casud.re/feed/"),
    ("La Réunion", "TCO",                 "https://www.tco.re/feed/"),
    ("La Réunion", "SPL Horizon",         "https://www.spl-horizon.re/feed/"),
    # La Réunion — bailleurs sociaux
    ("La Réunion", "SHLMR",               "https://www.shlmr.re/feed/"),
    ("La Réunion", "Erilia Réunion",      "https://www.erilia.fr/feed/"),
    ("La Réunion", "SODIAC",              "https://www.sodiac.re/feed/"),
    # Mayotte
    ("Mayotte",    "CD 976",              "https://www.cg976.re/feed/"),
    ("Mayotte",    "CCI Mayotte",         "https://www.mayotte.cci.fr/feed/"),
    ("Mayotte",    "SIM Mayotte",         "https://www.sim976.re/feed/"),
]


def _parse_date(entry) -> datetime | None:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                try:
                    return datetime(*entry.get(f"{attr}_parsed", [])[:6])
                except Exception:
                    pass
    return datetime.now()


def _dedup_id(url: str) -> str:
    return "RSS-" + hashlib.md5(url.encode()).hexdigest()[:14]


def _fetch_feed(territoire: str, nom: str, url: str, db, type_opp: str, filter_fn) -> int:
    inserted = 0
    try:
        feed = feedparser.parse(url)
    except Exception:
        return 0

    for entry in feed.entries:
        title = entry.get("title") or ""
        summary = entry.get("summary") or entry.get("description") or ""

        if not filter_fn(f"{title} {summary}"):
            continue

        link = entry.get("link") or url
        tender_id = _dedup_id(link)

        if db.query(Tender).filter(Tender.id == tender_id).first():
            continue

        db.add(Tender(
            id=tender_id,
            title=f"[{nom}] {title[:200]}",
            description=f"{territoire} — {nom}\n{summary[:500]}",
            source=link,
            publication_date=_parse_date(entry),
            deadline=None,
            status="À qualifier",
            relevance_score=0,
            is_maintenance=False,
            llm_analysis=None,
            secteur="Privé",
            type_opportunite=type_opp,
        ))
        inserted += 1

    db.commit()
    return inserted


def fetch_presse_io() -> int:
    init_db()
    db = SessionLocal()
    total = 0
    try:
        for territoire, nom, url in FLUX_PRESSE:
            total += _fetch_feed(territoire, nom, url, db, "Presse", is_construction_relevant)
        for territoire, nom, url in FLUX_INSTITUTIONS:
            # Institutions : on insère tous les articles (pas de filtre construction strict)
            # car les flux institutionnels publient déjà des projets ciblés
            total += _fetch_feed(territoire, nom, url, db, "Institution", lambda t: True)
    finally:
        db.close()
    return total


if __name__ == "__main__":
    print("Collecte flux RSS presse & institutions IO…")
    count = fetch_presse_io()
    print(f"Terminé — {count} article(s)/projet(s) inséré(s).")
```

- [ ] **Step 2 : Tester**

```bash
python scraper_presse.py
```

Résultat attendu : `Terminé — N article(s)/projet(s) inséré(s).` (même si N=0 pour des flux qui n'ont pas de RSS actif, le script ne doit pas planter).

Si une URL de flux retourne une erreur, `feedparser` retourne un feed vide — le script continue sur les suivants. Les URLs incorrectes seront ignorées silencieusement.

- [ ] **Step 3 : Commit**

```bash
git add scraper_presse.py
git commit -m "feat: add scraper_presse for press and institutional RSS feeds (IO)"
```

---

## Task 6 — scraper_devbanks.py (BAD, BEI, COI, JICA, KfW)

**Files:**
- Create: `scraper_devbanks.py`

- [ ] **Step 1 : Créer `scraper_devbanks.py`**

```python
"""
Scraper Banques de Développement Régionales — Océan Indien.
Sources : BAD (Afrique), BEI (Europe), COI (Océan Indien), JICA (Japon), KfW (Allemagne).
Ces institutions financent des infrastructures dans la zone IO qui nécessitent du SSI/CCTV.
Complément aux scrapers AFD et Banque Mondiale déjà existants.
"""
import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser
import requests

from database import SessionLocal, init_db
from filters import is_construction_relevant, INCLUSION_KEYWORDS
from models import Tender

# ── Flux RSS / APIs des banques de développement ─────────────────────────────

FLUX_DEVBANKS = [
    # BAD — Banque Africaine de Développement
    ("Zone IO", "BAD - Actualités",   "https://www.afdb.org/en/rss/news-and-events.xml"),
    ("Zone IO", "BAD - Projets",      "https://www.afdb.org/en/rss/projects.xml"),
    # BEI — Banque Européenne d'Investissement
    ("Zone IO", "BEI - Actualités",   "https://www.eib.org/en/rss/all-news.htm"),
    ("Zone IO", "BEI - Projets",      "https://www.eib.org/en/rss/projects.htm"),
    # COI — Commission de l'Océan Indien
    ("Zone IO", "COI - Actualités",   "https://www.commissionoceanindien.org/feed/"),
    # JICA — Agence Japonaise de Coopération Internationale
    ("Madagascar", "JICA Madagascar", "https://www.jica.go.jp/madagascar/en/activities/rss.xml"),
    ("Maurice",    "JICA Maurice",    "https://www.jica.go.jp/mauritius/en/activities/rss.xml"),
    # KfW — Banque de développement allemande
    ("Zone IO", "KfW Dev Bank",       "https://www.kfw-entwicklungsbank.de/rss/news.xml"),
]

# Pays et territoires Océan Indien pour filtrage géographique
PAYS_IO = [
    "madagascar", "mauritius", "île maurice", "ile maurice", "comores", "comoros",
    "réunion", "reunion", "mayotte", "indian ocean", "océan indien",
    "east africa", "afrique de l'est", "seychelles", "maldives",
]

# Secteurs pertinents pour SSI/CCTV dans les projets de banques de dev
SECTEURS_BANQUES = [
    "santé", "sante", "health", "hospital", "clinic",
    "education", "school", "university",
    "urban", "housing", "logement", "infrastructure",
    "transport", "energy", "énergie", "water", "eau",
    "tourism", "tourisme", "public administration",
    "construction", "bâtiment", "building",
]


def _is_relevant_devbank(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    geo_ok = any(p in text for p in PAYS_IO)
    secteur_ok = any(s in text for s in SECTEURS_BANQUES) or any(k in text for k in INCLUSION_KEYWORDS)
    return geo_ok and secteur_ok


def _parse_date(entry) -> datetime | None:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                try:
                    return datetime(*entry.get(f"{attr}_parsed", [])[:6])
                except Exception:
                    pass
    return datetime.now()


def _dedup_id(url: str, prefix: str) -> str:
    return f"{prefix}-" + hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_devbanks() -> int:
    init_db()
    db = SessionLocal()
    total = 0

    try:
        for territoire, nom, url in FLUX_DEVBANKS:
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue

            for entry in feed.entries:
                title = entry.get("title") or ""
                summary = entry.get("summary") or entry.get("description") or ""

                if not _is_relevant_devbank(title, summary):
                    continue

                link = entry.get("link") or url
                tender_id = _dedup_id(link, "DB")

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                db.add(Tender(
                    id=tender_id,
                    title=f"[{nom}] {title[:200]}",
                    description=f"{territoire} — {nom}\n{summary[:500]}",
                    source=link,
                    publication_date=_parse_date(entry),
                    deadline=None,
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Public",
                    type_opportunite="Banque Dev.",
                ))
                total += 1

            db.commit()

    finally:
        db.close()

    return total


if __name__ == "__main__":
    print("Collecte Banques de Développement (BAD, BEI, COI, JICA, KfW)…")
    count = fetch_devbanks()
    print(f"Terminé — {count} projet(s)/article(s) inséré(s).")
```

- [ ] **Step 2 : Tester**

```bash
python scraper_devbanks.py
```

Résultat attendu : `Terminé — N projet(s)/article(s) inséré(s).` sans plantage.

- [ ] **Step 3 : Commit**

```bash
git add scraper_devbanks.py
git commit -m "feat: add scraper_devbanks for BAD, BEI, COI, JICA, KfW RSS feeds"
```

---

## Task 7 — Mise à jour app.py

**Files:**
- Modify: `app.py`

Trois changements dans `app.py` :
1. `load_tenders` : ajouter filtre `secteur` pour séparer public et privé
2. Sidebar : 3 nouveaux boutons de collecte
3. Corps de page : nouvelle section "Marché Privé" après le tableau existant

- [ ] **Step 1 : Mettre à jour `load_tenders` pour supporter le filtre secteur**

Remplacer la fonction `load_tenders` (lignes 140–189) par :

```python
@st.cache_data(ttl=60)
def load_tenders(status_filter: str, maintenance_only: bool, annee_min: int, secteur: str = "Public") -> list[dict]:
    db = new_db()
    try:
        from sqlalchemy import or_, extract
        q = db.query(Tender)

        # Filtre secteur
        if secteur == "Public":
            q = q.filter(or_(Tender.secteur == "Public", Tender.secteur == None))
        elif secteur == "Privé":
            q = q.filter(Tender.secteur == "Privé")

        if status_filter != "Tous":
            q = q.filter(Tender.status == status_filter)
        if maintenance_only:
            q = q.filter(Tender.is_maintenance == True)
        if annee_min > 0:
            q = q.filter(or_(
                extract("year", Tender.publication_date) >= annee_min,
                extract("year", Tender.deadline) >= annee_min,
                Tender.publication_date == None,
            ))
        tenders = q.order_by(Tender.deadline).all()

        rows = []
        for t in tenders:
            a = t.llm_analysis or {}
            domaine = detect_domaine(t.title or "")
            territoire = detect_territoire(t.title or "", t.description or "")
            score = (
                t.relevance_score
                or a.get("score_pertinence", 0)
                or calc_score(t.title or "", domaine, territoire)
            )
            row = {
                "ID": t.id,
                "Titre": t.title or "Sans titre",
                "Source": t.source or "",
                "Territoire": territoire,
                "Domaine": domaine,
                "Score": score,
                "Date Limite": t.deadline.strftime("%d/%m/%Y") if t.deadline else "—",
                "Publication": (
                    t.publication_date.strftime("%d/%m/%Y") if t.publication_date else "—"
                ),
                "Statut": t.status or "À qualifier",
                "Type": t.type_opportunite or a.get("type_marche", "—"),
                "Maint.": "✓" if t.is_maintenance else "",
                "Concurrents": ", ".join(a.get("marques_concurrentes_citees", [])),
            }
            rows.append(row)
        return rows
    finally:
        db.close()
```

- [ ] **Step 2 : Ajouter les 3 boutons dans la sidebar**

Dans la sidebar, après le bloc Banque Mondiale et avant `st.markdown("**Tout collecter**")`, ajouter :

```python
    st.markdown("**Permis de construire** — Signaux en amont")
    if st.button("🏗️ Collecter Permis (974 & 976)", use_container_width=True):
        with st.spinner("Interrogation Sit@del2…"):
            try:
                from scraper_permis import fetch_permis_construire
                count = fetch_permis_construire()
                st.cache_data.clear()
                st.success(f"Permis : {count} nouveau(x) inséré(s).")
            except Exception as exc:
                st.error(f"Erreur Permis : {exc}")

    st.markdown("**Presse & Institutions** — Océan Indien")
    if st.button("📰 Collecter Presse & Institutions (IO)", use_container_width=True):
        with st.spinner("Lecture flux RSS…"):
            try:
                from scraper_presse import fetch_presse_io
                count = fetch_presse_io()
                st.cache_data.clear()
                st.success(f"Presse/Institutions : {count} nouveau(x) inséré(s).")
            except Exception as exc:
                st.error(f"Erreur Presse : {exc}")

    st.markdown("**Banques de Développement** — BAD / BEI / COI / JICA / KfW")
    if st.button("🌍 Collecter Banques Dev. (IO)", use_container_width=True):
        with st.spinner("Collecte BAD / BEI / COI…"):
            try:
                from scraper_devbanks import fetch_devbanks
                count = fetch_devbanks()
                st.cache_data.clear()
                st.success(f"Banques Dev. : {count} nouveau(x) inséré(s).")
            except Exception as exc:
                st.error(f"Erreur Banques Dev. : {exc}")
```

- [ ] **Step 3 : Mettre à jour le bouton "Toutes les sources"**

Dans le bouton `⚡ Toutes les sources`, ajouter les 3 nouveaux scrapers à la liste `func_path` :

```python
    if st.button("⚡ Toutes les sources", use_container_width=True, type="primary"):
        with st.spinner("Collecte toutes sources…"):
            total = 0
            errors = []
            for name, func_path in [
                ("BOAMP", "scraper_boamp.fetch_boamp_tenders"),
                ("TED", "scraper_ted.fetch_ted_tenders"),
                ("AFD", "scraper_afd.fetch_afd_projects"),
                ("Banque Mondiale", "scraper_worldbank.fetch_worldbank_projects"),
                ("Permis", "scraper_permis.fetch_permis_construire"),
                ("Presse IO", "scraper_presse.fetch_presse_io"),
                ("Banques Dev.", "scraper_devbanks.fetch_devbanks"),
            ]:
                try:
                    module_name, func_name = func_path.rsplit(".", 1)
                    import importlib
                    mod = importlib.import_module(module_name)
                    total += getattr(mod, func_name)()
                except Exception as exc:
                    errors.append(f"{name} : {exc}")
            st.cache_data.clear()
            if total:
                st.success(f"{total} nouveau(x) inséré(s) au total.")
            for err in errors:
                st.warning(err)
```

- [ ] **Step 4 : Mettre à jour l'appel `load_tenders` du tableau public**

Dans le corps de la page, la ligne `rows = load_tenders(...)` devient :

```python
rows = load_tenders(selected_status, maintenance_only, annee_min, secteur="Public")
```

- [ ] **Step 5 : Ajouter la section Marché Privé**

Après le bloc `st.markdown("---")` qui suit le tableau interactif principal (et avant l'expander "Saisie manuelle"), ajouter :

```python
# ── section marché privé ──────────────────────────────────────────────────────

st.subheader("🏗️ Signaux & Opportunités Marché Privé")
st.caption("Sources : Permis de construire · Presse locale IO · Institutions · Banques de développement")

rows_priv = load_tenders(selected_status, maintenance_only, annee_min, secteur="Privé")

# Filtres territoire/domaine côté affichage (réutilise les variables sidebar)
if terr_actifs:
    rows_priv = [r for r in rows_priv if any(t in r["Territoire"] for t in terr_actifs)]
if selected_domaines:
    rows_priv = [r for r in rows_priv if any(d in r["Domaine"] for d in selected_domaines)]

# KPIs
db_priv = new_db()
try:
    nb_permis = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.type_opportunite == "Permis Construire"
    ).count()
    nb_presse = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.type_opportunite == "Presse"
    ).count()
    nb_instit = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.type_opportunite == "Institution"
    ).count()
    nb_qualif = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.status == "À qualifier"
    ).count()
finally:
    db_priv.close()

kp1, kp2, kp3, kp4 = st.columns(4)
kp1.metric("Permis construire", nb_permis)
kp2.metric("Articles presse", nb_presse)
kp3.metric("Institutions", nb_instit)
kp4.metric("À qualifier", nb_qualif)

if not rows_priv:
    st.info("Aucun signal privé. Lancez la collecte Permis / Presse / Banques Dev. depuis le menu latéral.")
else:
    st.caption(f"{len(rows_priv)} signal(s) affiché(s)")
    df_priv = pd.DataFrame(rows_priv)
    edited_priv = st.data_editor(
        df_priv,
        column_config={
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Titre": st.column_config.TextColumn("Titre", width="large"),
            "Source": st.column_config.LinkColumn("Source", width="small"),
            "Territoire": st.column_config.TextColumn("Territoire", width="medium", disabled=True),
            "Domaine": st.column_config.TextColumn("Domaine", width="medium", disabled=True),
            "Score": st.column_config.NumberColumn("Score", min_value=0, max_value=100, width="small"),
            "Date Limite": st.column_config.TextColumn("Date Limite", width="small"),
            "Publication": st.column_config.TextColumn("Publication", width="small"),
            "Statut": st.column_config.SelectboxColumn(
                "Statut", options=["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"], width="medium"
            ),
            "Type": st.column_config.TextColumn("Type", width="small", disabled=True),
            "Maint.": st.column_config.TextColumn("Maint.", width="small", disabled=True),
            "Concurrents": st.column_config.TextColumn("Concurrents", width="medium"),
        },
        column_order=["Titre", "Source", "Territoire", "Type", "Score", "Publication", "Statut", "Maint.", "ID"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="priv_editor",
    )

    editor_state_priv = st.session_state.get("priv_editor", {})
    for row_idx, changes in editor_state_priv.get("edited_rows", {}).items():
        if "Statut" in changes:
            save_status(df_priv.iloc[row_idx]["ID"], changes["Statut"])
            st.cache_data.clear()
            st.rerun()

st.markdown("---")
```

- [ ] **Step 6 : Lancer l'app et vérifier**

```bash
streamlit run app.py
```

Vérifier :
- La sidebar affiche les 3 nouveaux boutons et le bouton "Toutes les sources" les inclut
- La section "Signaux & Opportunités Marché Privé" apparaît entre le tableau principal et l'expander "Saisie manuelle"
- Les 4 KPIs s'affichent (à 0 si la collecte n'a pas encore été lancée)
- Cliquer sur "🏗️ Collecter Permis (974 & 976)" insère des données sans erreur
- Cliquer sur "📰 Collecter Presse & Institutions (IO)" insère des données sans erreur

- [ ] **Step 7 : Commit final**

```bash
git add app.py
git commit -m "feat: add private market section to app (permis, presse, banques dev)"
```

---

## Self-Review

**Couverture spec :**
- ✅ Permis de construire Sit@del2 (974/976) → Task 4
- ✅ ~20 flux presse locale → Task 5
- ✅ ~15 flux institutionnels → Task 5
- ✅ BAD, BEI, COI, JICA, KfW → Task 6
- ✅ Migration modèle (`secteur`, `type_opportunite`) → Task 2
- ✅ `KEYWORDS_CONSTRUCTION` + `is_construction_relevant` → Task 3
- ✅ 3 boutons sidebar + "Toutes les sources" → Task 7
- ✅ Section Marché Privé avec KPIs + tableau éditable → Task 7
- ✅ Mêmes filtres sidebar appliqués au tableau privé → Task 7

**Cohérence types :** `fetch_permis_construire`, `fetch_presse_io`, `fetch_devbanks` — noms cohérents entre les scrapers et les imports dans `app.py`.

**Migration SQLite :** notée explicitement avec `ALTER TABLE` dans `database.py`.
