# SSI Scrapers Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Améliorer précision et efficacité de la collecte marchés SSI : corriger l'endpoint TED v3.0, enrichir les mots-clés, ajouter le filtrage CPV, étendre les variantes géographiques Mayotte, limiter la fenêtre temporelle à 90 jours glissants.

**Architecture:** Option A — modifications atomiques fichier par fichier, sans nouveau module. `SCRAPER_WINDOW_DAYS` est lu via `os.getenv(...)` inline dans chaque scraper concerné.

**Tech Stack:** Python 3.11+, pytest, SQLAlchemy (sqlite://:memory: pour les tests), requests, python-dotenv

---

## File Map

| Fichier | Changement |
|---------|-----------|
| `.env.example` | +1 variable `SCRAPER_WINDOW_DAYS=90` |
| `filters.py` | +15 mots-clés dans `INCLUSION_KEYWORDS`, +4 acronymes dans `_WORD_BOUNDARY_KW` |
| `scraper_ted.py` | URL v3.0, filtre date PD>=, variantes Mayotte, codes CPV (PC~) |
| `scraper_decp.py` | `_CPV_FILTER` + `years_back` → `days_back` via env |
| `scraper_boamp.py` | `years_back` → `days_back` via env + `import os` |
| `tests/test_filters.py` | +19 tests pour les nouveaux mots-clés |
| `tests/test_scrapers_new.py` | +4 tests TED + 2 tests DECP + 1 test BOAMP |

---

## Task 1 : `.env.example` — SCRAPER_WINDOW_DAYS

**Files:**
- Modify: `.env.example`

- [ ] **Step 1 : Ajouter la variable**

Ouvrir `.env.example`, ajouter en fin de fichier :

```
# Fenêtre glissante de collecte active (jours). Défaut : 90.
# Augmenter pour un premier import historique, réduire pour les runs quotidiens.
SCRAPER_WINDOW_DAYS=90
```

- [ ] **Step 2 : Vérifier**

```bash
python -c "import os; os.environ['SCRAPER_WINDOW_DAYS']='90'; print(int(os.getenv('SCRAPER_WINDOW_DAYS', '90')))"
```
Attendu : `90`

- [ ] **Step 3 : Commit**

```bash
git add .env.example
git commit -m "config: add SCRAPER_WINDOW_DAYS env var (default 90 days)"
```

---

## Task 2 : `filters.py` — nouveaux mots-clés SSI

**Files:**
- Modify: `filters.py`
- Test: `tests/test_filters.py`

- [ ] **Step 1 : Écrire les tests en échec**

Ajouter à la **fin** de `tests/test_filters.py` :

```python
# ── Nouveaux mots-clés SSI directs ───────────────────────────────────────────

def test_classify_ria_direct():
    ok, tags = classify_relevance("Installation d'un RIA dans le couloir technique")
    assert ok is True
    assert tags == []


def test_classify_ria_word_boundary():
    # "matériaux" contient "ria" comme sous-chaîne (maté-r-i-a-ux) — ne doit PAS matcher
    ok, _ = classify_relevance("Fourniture de matériaux de construction")
    assert ok is False


def test_classify_baas_direct():
    ok, tags = classify_relevance("Fourniture et pose de BAAS homologué NF")
    assert ok is True


def test_classify_robinet_incendie_arme():
    ok, tags = classify_relevance("Remplacement des robinets incendie armés du bâtiment A")
    assert ok is True


def test_classify_bloc_autonome_alarme():
    ok, tags = classify_relevance("Fourniture de blocs autonomes alarme sonores et lumineux")
    assert ok is True


# ── Déclencheurs travaux SSI ─────────────────────────────────────────────────

def test_classify_dta():
    ok, tags = classify_relevance("Réalisation DTA avant démarrage des travaux")
    assert ok is True


def test_classify_dossier_technique_amiante():
    ok, tags = classify_relevance("Dossier technique amiante — bâtiment R+3 Mamoudzou")
    assert ok is True


def test_classify_mise_en_conformite():
    ok, tags = classify_relevance("Mise en conformité des installations de sécurité ERP")
    assert ok is True


def test_classify_verification_reglementaire():
    ok, tags = classify_relevance("Vérification réglementaire des équipements de sécurité")
    assert ok is True


def test_classify_verification_periodique():
    ok, tags = classify_relevance("Contrat de vérification périodique des extincteurs et RIA")
    assert ok is True


# ── Courants faibles / GTB ───────────────────────────────────────────────────

def test_classify_gtb_direct():
    ok, tags = classify_relevance("Mise en service GTB du nouveau bâtiment administratif")
    assert ok is True


def test_classify_gtb_word_boundary():
    # "EGTBA" contient "gtb" comme sous-chaîne — ne doit PAS matcher
    ok, _ = classify_relevance("Résultats sportifs championnat EGTBA")
    assert ok is False


def test_classify_gtc_direct():
    ok, tags = classify_relevance("Déploiement système GTC hôtel 4 étoiles Réunion")
    assert ok is True


def test_classify_bms_direct():
    ok, tags = classify_relevance("Installation BMS pour la gestion technique centralisée")
    assert ok is True


def test_classify_gestion_technique_batiment():
    ok, tags = classify_relevance("Marché de gestion technique bâtiment — lycée Saint-Paul")
    assert ok is True


def test_classify_building_management():
    ok, tags = classify_relevance("Building management system — hôpital neuf 974")
    assert ok is True


# ── Maintenance SSI ──────────────────────────────────────────────────────────

def test_classify_mco_ssi():
    ok, tags = classify_relevance("MCO SSI — contrat annuel préventif et curatif")
    assert ok is True


def test_classify_contrat_maintenance_ssi():
    ok, tags = classify_relevance("Contrat de maintenance SSI EHPAD Saint-Pierre La Réunion")
    assert ok is True


def test_classify_verification_annuelle():
    ok, tags = classify_relevance("Vérification annuelle des installations de sécurité incendie")
    assert ok is True
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
python -m pytest tests/test_filters.py -k "ria or baas or robinet or bloc_autonome or dta or dossier_technique or mise_en_conformite or verification_reglementaire or verification_periodique or gtb or gtc or bms or gestion_technique or building_management or mco or contrat_maintenance or verification_annuelle" -v
```
Attendu : plusieurs FAILED (`classify_relevance` ne connaît pas encore ces mots)

- [ ] **Step 3 : Implémenter dans `filters.py`**

Remplacer `INCLUSION_KEYWORDS` (lignes 4-15) par :

```python
INCLUSION_KEYWORDS = [
    "ssi",
    "cmsi",
    "détection incendie",
    "désenfumage",
    "vidéosurveillance",
    "cctv",
    "caméras de sécurité",
    "courants faibles",
    "alarme incendie",
    "système incendie",
    # SSI direct — équipements complémentaires
    "ria",
    "robinet incendie armé",
    "baas",
    "bloc autonome alarme",
    # Déclencheurs travaux SSI (conformité réglementaire)
    "dta",
    "dossier technique amiante",
    "mise en conformité",
    "vérification réglementaire",
    "vérification périodique",
    # Courants faibles / GTB
    "gtb",
    "gtc",
    "bms",
    "gestion technique bâtiment",
    "building management",
    # Maintenance SSI
    "mco ssi",
    "contrat de maintenance ssi",
    "vérification annuelle",
]
```

Remplacer `_WORD_BOUNDARY_KW` (ligne 69) par :

```python
_WORD_BOUNDARY_KW = {"ssi", "cmsi", "cctv", "ria", "gtb", "gtc", "bms"}
```

La recompilation de `_COMPILED_BOUNDARY` est automatique (elle itère sur `_WORD_BOUNDARY_KW`).

- [ ] **Step 4 : Vérifier que tous les tests filters passent**

```bash
python -m pytest tests/test_filters.py -v
```
Attendu : PASSED pour les 30+ tests (anciens + 19 nouveaux)

- [ ] **Step 5 : Commit**

```bash
git add filters.py tests/test_filters.py
git commit -m "feat(filters): add SSI keywords — RIA, BAAS, GTB/GTC/BMS, DTA, MCO, maintenance"
```

---

## Task 3 : `scraper_ted.py` — URL v3.0, fenêtre date, Mayotte, CPV

**Files:**
- Modify: `scraper_ted.py`
- Test: `tests/test_scrapers_new.py`

- [ ] **Step 1 : Écrire les tests en échec**

Ajouter à la fin de `tests/test_scrapers_new.py` :

```python
# ── Tests scraper_ted ─────────────────────────────────────────────────────────

def test_ted_api_url_is_v3():
    import importlib
    import scraper_ted
    importlib.reload(scraper_ted)
    assert scraper_ted.TED_API_URL == "https://ted.europa.eu/api/v3.0/notices/search"


def test_ted_mayotte_query_includes_city_variants():
    import importlib
    import scraper_ted
    importlib.reload(scraper_ted)
    q = scraper_ted.QUERIES["Mayotte"]
    assert "Mamoudzou" in q
    assert "Dzaoudzi" in q
    assert "Mahorais" in q


def test_ted_public_search_includes_cpv():
    import importlib
    import scraper_ted
    importlib.reload(scraper_ted)
    assert "PC~45312100" in scraper_ted._PUBLIC_SEARCH
    assert "PC~50610000" in scraper_ted._PUBLIC_SEARCH


def test_ted_fetch_sends_date_filter():
    """Le payload envoyé à l'API doit contenir un filtre de date PD>=."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    mock_resp = MagicMock()
    mock_resp.json.return_value = {"notices": []}

    captured_payloads = []

    def fake_retry_post(url, json=None, **kwargs):
        captured_payloads.append(json or {})
        return mock_resp

    with patch("scraper_ted.retry_post", side_effect=fake_retry_post):
        with patch("scraper_ted.SessionLocal", Session):
            with patch("scraper_ted.init_db"):
                import importlib, scraper_ted
                importlib.reload(scraper_ted)
                scraper_ted.fetch_ted_tenders(zones=["La Réunion"])

    assert len(captured_payloads) > 0
    assert "PD>=" in captured_payloads[0].get("query", "")
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
python -m pytest tests/test_scrapers_new.py -k "ted" -v
```
Attendu : FAILED sur `test_ted_api_url_is_v3`, `test_ted_mayotte_query_includes_city_variants`, `test_ted_public_search_includes_cpv`

- [ ] **Step 3 : Implémenter les modifications dans `scraper_ted.py`**

Remplacer le contenu complet de `scraper_ted.py` par :

```python
import hashlib
import logging
import os
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from scraper_utils import parse_date, retry_post, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

TED_API_URL = "https://ted.europa.eu/api/v3.0/notices/search"

_METIERS = (
    "FT~SSI OR FT~CMSI OR FT~incendie OR FT~desenfumage"
    " OR FT~videosurveillance OR FT~camera OR FT~CCTV"
)
_CONSTRUCTION = (
    "FT~construction OR FT~chantier OR FT~travaux OR FT~rehabilitation"
    " OR FT~renovation OR FT~extension OR FT~restructuration OR FT~amenagement"
)
_ERP = (
    "FT~hopital OR FT~clinique OR FT~ehpad OR FT~hotel OR FT~ecole"
    " OR FT~lycee OR FT~college OR FT~universite OR FT~gymnase"
    " OR FT~stade OR FT~mairie OR FT~tribunal OR FT~aeroport OR FT~gare"
)
# Codes CPV SSI : alarme incendie, matériel incendie, maintenance sécu,
# anti-intrusion, contrôle d'accès, prévention incendie
_CPV = (
    "PC~45312100 OR PC~35111300 OR PC~50610000"
    " OR PC~45312200 OR PC~42961000 OR PC~35111000"
)
_IMPLICITE_ERP = f"(({_CONSTRUCTION}) AND ({_ERP}))"
_PUBLIC_SEARCH = f"({_METIERS}) OR ({_IMPLICITE_ERP}) OR ({_CPV})"

# Variantes géographiques Mayotte — villes et gentilé pour meilleure couverture TED
_MAYOTTE_GEO = (
    "FT~Mayotte OR FT~Mahorais OR FT~Mamoudzou"
    " OR FT~Kaweni OR FT~Dzaoudzi OR FT~Koungou OR FT~Bandraboua"
)

QUERIES = {
    "La Réunion": f"FT~974 AND ({_PUBLIC_SEARCH})",
    "Mayotte":    f"({_MAYOTTE_GEO}) AND ({_PUBLIC_SEARCH})",
    "Madagascar": f"FT~Madagascar AND ({_PUBLIC_SEARCH})",
    "Maurice":    f"FT~Mauritius AND ({_PUBLIC_SEARCH})",
    "Comores":    f"FT~Comoros AND ({_PUBLIC_SEARCH})",
}

_FIELDS = ["notice-title", "publication-number", "deadline-receipt-tender-date-lot", "description-glo"]


def _extract_fr(field_value) -> str:
    if not field_value:
        return ""
    if isinstance(field_value, list):
        return " ".join(_extract_fr(item) for item in field_value if item).strip()
    if isinstance(field_value, dict):
        return (field_value.get("fra") or field_value.get("eng")
                or next(iter(field_value.values()), "")) or ""
    return str(field_value)


def _fetch_query(db, query: str, existing_ids: set, date_from: str) -> int:
    inserted = 0
    page     = 1
    limit    = 100

    while True:
        # Filtre date glissante — évite de re-scraper l'historique à chaque run
        full_query = f"({query}) AND PD>={date_from}"
        payload    = {"query": full_query, "fields": _FIELDS, "page": page, "limit": limit}
        r          = retry_post(TED_API_URL, json=payload, rate_delay=1.5)
        notices    = r.json().get("notices", [])
        if not notices:
            break

        for notice in notices:
            pub_num     = notice.get("publication-number") or ""
            title       = _extract_fr(notice.get("notice-title"))
            description = _extract_fr(notice.get("description-glo"))

            relevant, extra_tags = classify_relevance(f"{title} {description}")
            if not relevant:
                continue

            tender_id = (f"TED-{pub_num}" if pub_num
                         else f"TED-{hashlib.md5(title.encode()).hexdigest()[:12]}")

            links  = notice.get("links", {})
            url_fr = ((links.get("html") or {}).get("FRA")
                      or f"https://ted.europa.eu/fr/notice/{pub_num}/html")

            t = Tender(
                id=tender_id,
                title=title or f"Avis TED {pub_num}",
                description=description,
                source=url_fr,
                publication_date=None,
                deadline=parse_date(notice.get("deadline-receipt-tender-date-lot")),
                status="À qualifier",
                relevance_score=0,
                is_maintenance=False,
                llm_analysis=None,
                tags=extra_tags,
            )
            if insert_if_new(db, t, existing_ids):
                inserted += 1

        if len(notices) < limit:
            break
        page += 1

    return inserted


def fetch_ted_tenders(zones: list[str] | None = None) -> int:
    init_db()
    db    = SessionLocal()
    total = 0
    _run_id = start_scraper_run(db, "TED Europe")

    window_days = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
    date_from   = (datetime.now() - timedelta(days=window_days)).strftime("%Y%m%d")

    selected = {k: v for k, v in QUERIES.items() if zones is None or k in zones}

    try:
        existing_ids = load_existing_ids(db)
        for zone, query in selected.items():
            _log.info("TED : collecte zone '%s'", zone)
            total += _fetch_query(db, query, existing_ids, date_from)
        if total:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=total, nb_new=total)
        _log.info("TED : %d marché(s) inséré(s)", total)
    except Exception as exc:
        _log.exception("TED : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_ted_tenders()
    _log.info("TED terminé — %d marché(s)", count)
```

- [ ] **Step 4 : Vérifier que les 4 tests TED passent**

```bash
python -m pytest tests/test_scrapers_new.py -k "ted" -v
```
Attendu : PASSED (`test_ted_api_url_is_v3`, `test_ted_mayotte_query_includes_city_variants`, `test_ted_public_search_includes_cpv`, `test_ted_fetch_sends_date_filter`)

- [ ] **Step 5 : Commit**

```bash
git add scraper_ted.py tests/test_scrapers_new.py
git commit -m "feat(ted): v3.0 endpoint, 90-day window, Mayotte city variants, CPV codes"
```

---

## Task 4 : `scraper_decp.py` — filtre CPV + fenêtre temporelle

**Files:**
- Modify: `scraper_decp.py`
- Test: `tests/test_scrapers_new.py`

- [ ] **Step 1 : Écrire les tests en échec**

Ajouter à la fin de `tests/test_scrapers_new.py` :

```python
# ── Tests DECP CPV + fenêtre temporelle ──────────────────────────────────────

def test_decp_cpv_filter_in_where_clause():
    """Le where DECP doit inclure les codes CPV SSI."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                import importlib, scraper_decp
                importlib.reload(scraper_decp)
                scraper_decp.fetch_decp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    assert "45312100" in where_clause
    assert "50610000" in where_clause


def test_decp_window_defaults_to_90_days():
    """La fenêtre par défaut doit être 90 jours (pas 3 ans)."""
    import os
    from datetime import datetime, timedelta
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    os.environ.pop("SCRAPER_WINDOW_DAYS", None)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_decp.SessionLocal", Session):
            with patch("scraper_decp.init_db"):
                import importlib, scraper_decp
                importlib.reload(scraper_decp)
                scraper_decp.fetch_decp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    expected_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert expected_date in where_clause
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
python -m pytest tests/test_scrapers_new.py -k "decp_cpv or decp_window" -v
```
Attendu : FAILED (CPV absent, date encore à 3 ans)

- [ ] **Step 3 : Implémenter les modifications dans `scraper_decp.py`**

Remplacer le contenu complet de `scraper_decp.py` par :

```python
import hashlib
import logging
import os
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import classify_relevance
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp_augmente/records"
)

_DEPT_FILTER    = 'codedepartementexecution in ("974", "976")'
_KEYWORD_FILTER = (
    'search(objetmarche, "SSI")'
    ' OR search(objetmarche, "CMSI")'
    ' OR search(objetmarche, "incendie")'
    ' OR search(objetmarche, "desenfumage")'
    ' OR search(objetmarche, "videosurveillance")'
    ' OR search(objetmarche, "camera")'
    ' OR search(objetmarche, "CCTV")'
    ' OR search(objetmarche, "courants faibles")'
)
# Codes CPV SSI dans le dataset DECP Augmenté (champ "codecpv")
# Si l'API retourne un 400, vérifier le nom exact du champ via :
# GET .../records?limit=1&select=codecpv
_CPV_FILTER = (
    'search(codecpv, "45312100")'
    ' OR search(codecpv, "35111300")'
    ' OR search(codecpv, "50610000")'
    ' OR search(codecpv, "45312200")'
    ' OR search(codecpv, "42961000")'
    ' OR search(codecpv, "35111000")'
)
_CONSTRUCTION_FILTER = (
    'search(objetmarche, "construction")'
    ' OR search(objetmarche, "chantier")'
    ' OR search(objetmarche, "travaux")'
    ' OR search(objetmarche, "réhabilitation")'
    ' OR search(objetmarche, "rehabilitation")'
    ' OR search(objetmarche, "rénovation")'
    ' OR search(objetmarche, "renovation")'
    ' OR search(objetmarche, "extension")'
    ' OR search(objetmarche, "restructuration")'
    ' OR search(objetmarche, "aménagement")'
    ' OR search(objetmarche, "amenagement")'
)
_ERP_FILTER = (
    'search(objetmarche, "hôpital")'
    ' OR search(objetmarche, "hopital")'
    ' OR search(objetmarche, "clinique")'
    ' OR search(objetmarche, "ehpad")'
    ' OR search(objetmarche, "hôtel")'
    ' OR search(objetmarche, "hotel")'
    ' OR search(objetmarche, "école")'
    ' OR search(objetmarche, "ecole")'
    ' OR search(objetmarche, "lycée")'
    ' OR search(objetmarche, "lycee")'
    ' OR search(objetmarche, "collège")'
    ' OR search(objetmarche, "college")'
    ' OR search(objetmarche, "université")'
    ' OR search(objetmarche, "universite")'
    ' OR search(objetmarche, "centre commercial")'
    ' OR search(objetmarche, "gymnase")'
    ' OR search(objetmarche, "stade")'
    ' OR search(objetmarche, "mairie")'
    ' OR search(objetmarche, "tribunal")'
    ' OR search(objetmarche, "aéroport")'
    ' OR search(objetmarche, "aeroport")'
    ' OR search(objetmarche, "gare")'
)
_PUBLIC_SEARCH_FILTER = (
    f"({_KEYWORD_FILTER}) OR ({_CPV_FILTER})"
    f" OR (({_CONSTRUCTION_FILTER}) AND ({_ERP_FILTER}))"
)


def fetch_decp_tenders(days_back: int | None = None) -> int:
    if days_back is None:
        days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
    date_min = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    where    = f"({_DEPT_FILTER}) AND ({_PUBLIC_SEARCH_FILTER}) AND (datenotification >= \"{date_min}\")"

    init_db()
    db       = SessionLocal()
    inserted = 0
    _run_id  = start_scraper_run(db, "DECP / PLACE")

    try:
        existing_ids = load_existing_ids(db)
        offset = 0
        limit  = 100

        while True:
            params   = {"where": where, "limit": limit, "offset": offset, "order_by": "datenotification DESC"}
            response = retry_get(DECP_API, params=params, rate_delay=1.0)
            records  = response.json().get("results", [])
            if not records:
                break

            for record in records:
                acheteur_nom = record.get("nomacheteur") or ""
                objet        = record.get("objetmarche") or ""
                full_text    = f"{objet} {acheteur_nom}"

                relevant, extra_tags = classify_relevance(full_text)
                if not relevant:
                    continue

                uid       = record.get("id") or hashlib.md5(full_text.encode()).hexdigest()
                tender_id = f"DECP-{uid}"

                t = Tender(
                    id=tender_id, title=objet,
                    description=f"Acheteur : {acheteur_nom}",
                    source="https://data.economie.gouv.fr",
                    publication_date=parse_date(record.get("datenotification")),
                    deadline=None, status="À qualifier",
                    relevance_score=0, is_maintenance=False, llm_analysis=None,
                    secteur="Public", type_opportunite="Marché Public",
                    tags=extra_tags,
                )
                if insert_if_new(db, t, existing_ids):
                    inserted += 1

            if len(records) < limit:
                break
            offset += limit

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("DECP : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("DECP : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_decp_tenders()
    _log.info("DECP terminé — %d marché(s)", count)
```

- [ ] **Step 4 : Vérifier que tous les tests DECP passent**

```bash
python -m pytest tests/test_scrapers_new.py -k "decp" -v
```
Attendu : PASSED pour les 5 tests DECP (3 anciens + 2 nouveaux)

- [ ] **Step 5 : Commit**

```bash
git add scraper_decp.py tests/test_scrapers_new.py
git commit -m "feat(decp): add CPV filter + 90-day sliding window via SCRAPER_WINDOW_DAYS"
```

---

## Task 5 : `scraper_boamp.py` — fenêtre temporelle 90 jours

**Files:**
- Modify: `scraper_boamp.py` (lignes 1-3 et 70-74)
- Test: `tests/test_scrapers_new.py`

- [ ] **Step 1 : Écrire le test en échec**

Ajouter à la fin de `tests/test_scrapers_new.py` :

```python
# ── Tests BOAMP fenêtre temporelle ───────────────────────────────────────────

def test_boamp_window_defaults_to_90_days():
    """La fenêtre par défaut doit être 90 jours (pas 2 ans)."""
    import os
    from datetime import datetime, timedelta
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    os.environ.pop("SCRAPER_WINDOW_DAYS", None)

    with patch("requests.get", return_value=mock_resp) as req:
        with patch("scraper_boamp.SessionLocal", Session):
            with patch("scraper_boamp.init_db"):
                import importlib, scraper_boamp
                importlib.reload(scraper_boamp)
                scraper_boamp.fetch_boamp_tenders()

    where_clause = req.call_args.kwargs["params"]["where"]
    expected_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
    assert expected_date in where_clause
```

- [ ] **Step 2 : Vérifier que le test échoue**

```bash
python -m pytest tests/test_scrapers_new.py -k "boamp_window" -v
```
Attendu : FAILED (date encore à 2 ans)

- [ ] **Step 3 : Modifier `scraper_boamp.py`**

Ajouter `import os` en ligne 3 (après `from datetime import datetime, timedelta`) :

```python
import hashlib
import logging
import os
from datetime import datetime, timedelta
```

Remplacer la signature et le calcul de date (lignes 70-74) :

```python
def fetch_boamp_tenders(departments: list[str] | None = None, years_back: int | None = None) -> int:
    if departments is None:
        departments = ["974", "976"]

    # years_back conservé pour compatibilité ; sinon fenêtre glissante via env
    if years_back is not None:
        days_back = years_back * 365
    else:
        days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))

    date_min = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
```

- [ ] **Step 4 : Vérifier que le test passe**

```bash
python -m pytest tests/test_scrapers_new.py -k "boamp" -v
```
Attendu : PASSED

- [ ] **Step 5 : Vérifier la suite complète**

```bash
python -m pytest tests/ -v --tb=short
```
Attendu : PASSED pour l'ensemble des tests (aucune régression)

- [ ] **Step 6 : Commit final**

```bash
git add scraper_boamp.py tests/test_scrapers_new.py
git commit -m "feat(boamp): 90-day sliding window via SCRAPER_WINDOW_DAYS"
```

---

## Note runtime — `codecpv` DECP

Si l'API DECP retourne HTTP 400 lors de la première exécution réelle, le champ CPV ne s'appelle peut-être pas `codecpv`. Vérifier avec :

```bash
curl "https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/decp_augmente/records?limit=1&select=*" | python -m json.tool | grep -i cpv
```

Si le champ s'appelle autrement (ex: `cpv`, `codecpv_objet`), mettre à jour `_CPV_FILTER` en conséquence dans `scraper_decp.py`.
