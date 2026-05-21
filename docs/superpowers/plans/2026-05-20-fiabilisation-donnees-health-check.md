# Fiabilisation des Données — Health Checks, Double Horodatage, Rétention

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Éliminer les "silences fatals" en garantissant la fraîcheur absolue des données, en alertant sur tout changement de structure des sources, et en archivant automatiquement les données périmées.

**Architecture:** Nouveau module `health_check.py` indépendant qui tourne sur chaque source déclarée dans `source_registry.py`. Le modèle `Tender` reçoit un champ `date_extraction`. La rétention est assurée par `clean_obsolete_data()` dans `database.py`, appelée au démarrage de l'app. Les scrapers Playwright gardent leur mode mais reçoivent des marqueurs structurels pour détecter tout changement de layout.

**Tech Stack:** Python 3.12, SQLAlchemy, Requests, Playwright, Streamlit, pytest

---

## AUDIT PRÉLIMINAIRE — Ce qui change et pourquoi

### Sources avec API existante (✅ — conserver, renforcer les marqueurs)
- `scraper_boamp.py` → API OpenDataSoft, marqueur JSON : présence de la clé `"results"`
- `scraper_ted.py` → API TED v3, marqueur JSON : présence de la clé `"notices"`
- `scraper_afd.py` → API OpenDataSoft, marqueur JSON : présence de la clé `"results"` **+ bug `publication_date=datetime.now()` à corriger**
- `scraper_worldbank.py` → API World Bank JSON, marqueur : présence de la clé `"projects"` **+ bug `publication_date=datetime.now()` à corriger**
- `scraper_permis.py` → API Sit@del2 JSON, marqueur : présence de la clé `"results"`

### Sources Playwright (⚠️ — pas d'API publique, maintien + marqueurs CSS)
- `scraper_marcheonline.py` → marqueur : présence du bloc `blockNotice` dans les commentaires HTML
- `scraper_instao.py` → marqueur : sélecteur `.bid-card, article.bid` ou `.tender-card`
- `scraper_marchessecurises.py` → marqueur : sélecteur `table.tableau` ou `.liste-dce`
- `scraper_tendersgo.py` → marqueur : sélecteur `.tender-card, .tender-item`

### Ce qui manque (à créer / corriger)
| Directive | Fichier(s) concerné(s) | Statut |
|---|---|---|
| `date_extraction` | `models.py`, `database.py`, tous scrapers | ABSENT |
| `publication_date` correcte | `scraper_afd.py`, `scraper_worldbank.py` | BUG |
| `health_check.py` | À créer | ABSENT |
| Alerte Streamlit | `app.py` | ABSENT |
| `clean_obsolete_data()` | `database.py` | ABSENT |

---

## Fichiers créés / modifiés

| Fichier | Action | Responsabilité |
|---|---|---|
| `models.py` | Modifier | Ajouter colonne `date_extraction` dans `Tender` |
| `database.py` | Modifier | Migration + fonction `clean_obsolete_data()` |
| `scraper_utils.py` | Modifier | Ajouter helper `now_utc()` partagé |
| `scraper_afd.py` | Modifier | Corriger `publication_date` + ajouter `date_extraction` |
| `scraper_worldbank.py` | Modifier | Corriger `publication_date` + ajouter `date_extraction` |
| `scraper_boamp.py` | Modifier | Ajouter `date_extraction` |
| `scraper_ted.py` | Modifier | Ajouter `date_extraction` |
| `scraper_permis.py` | Modifier | Ajouter `date_extraction` |
| `scraper_marcheonline.py` | Modifier | Ajouter `date_extraction` + marqueur structurel |
| `scraper_instao.py` | Modifier | Ajouter `date_extraction` + marqueur structurel |
| `scraper_marchessecurises.py` | Modifier | Ajouter `date_extraction` + marqueur structurel |
| `scraper_tendersgo.py` | Modifier | Ajouter `date_extraction` + marqueur structurel |
| `health_check.py` | Créer | Module autonome de health check par source |
| `app.py` | Modifier | Appel `clean_obsolete_data()` + bannière d'alerte health check |
| `tests/test_health_check.py` | Créer | Tests unitaires du health check |
| `tests/test_retention.py` | Créer | Tests unitaires de la rétention |

---

## Tâche 1 : Double horodatage — `date_extraction` dans le modèle

**Files:**
- Modify: `models.py`
- Modify: `database.py`
- Modify: `scraper_utils.py`

- [ ] **Step 1.1 : Écrire le test qui vérifie que `date_extraction` est bien présent**

Créer `tests/test_double_horodatage.py` :

```python
from datetime import datetime, timezone
from models import Tender


def test_tender_has_date_extraction_field():
    t = Tender(
        id="TEST-001",
        title="Test",
        source="http://example.com",
        publication_date=datetime(2026, 5, 1),
        date_extraction=datetime(2026, 5, 20, 10, 0, 0),
    )
    assert t.date_extraction is not None
    assert isinstance(t.date_extraction, datetime)


def test_tender_date_extraction_independent_from_publication():
    pub = datetime(2026, 4, 1)
    ext = datetime(2026, 5, 20)
    t = Tender(id="TEST-002", title="T", source="http://x.com",
               publication_date=pub, date_extraction=ext)
    assert t.publication_date != t.date_extraction
    assert (ext - pub).days == 49
```

- [ ] **Step 1.2 : Lancer le test — il doit échouer**

```bash
pytest tests/test_double_horodatage.py -v
```

Résultat attendu : `AttributeError: type object 'Tender' has no attribute 'date_extraction'`

- [ ] **Step 1.3 : Modifier `models.py` — ajouter `date_extraction`**

Dans `models.py`, ajouter la colonne après `publication_date` :

```python
# Avant (ligne 14) :
publication_date = Column(DateTime)
deadline         = Column(DateTime)

# Après :
publication_date = Column(DateTime)
date_extraction  = Column(DateTime)          # timestamp collecte par notre script
deadline         = Column(DateTime)
```

Et ajouter un index dans `__table_args__` :

```python
Index("idx_tender_extraction", "date_extraction"),
```

- [ ] **Step 1.4 : Ajouter la migration dans `database.py`**

Dans `_MIGRATIONS`, ajouter :

```python
("tenders", "date_extraction", "DATETIME DEFAULT NULL"),
```

Et ajouter `"date_extraction"` dans `_VALID_COLS` (qui est dérivé automatiquement de `_MIGRATIONS`, donc rien à changer).

- [ ] **Step 1.5 : Ajouter `now_utc()` dans `scraper_utils.py`**

En bas de `scraper_utils.py`, ajouter :

```python
from datetime import timezone as _tz_utc


def now_utc() -> datetime:
    """Retourne le datetime UTC actuel sans timezone (pour SQLite)."""
    return datetime.now(_tz_utc.utc).replace(tzinfo=None)
```

- [ ] **Step 1.6 : Lancer le test — il doit passer**

```bash
pytest tests/test_double_horodatage.py -v
```

Résultat attendu : `2 passed`

- [ ] **Step 1.7 : Commit**

```bash
git add models.py database.py scraper_utils.py tests/test_double_horodatage.py
git commit -m "feat: ajouter date_extraction dans Tender + helper now_utc()"
```

---

## Tâche 2 : Corriger `publication_date` dans AFD et WorldBank + alimenter `date_extraction`

**Files:**
- Modify: `scraper_afd.py:84-95`
- Modify: `scraper_worldbank.py:77-90`

Ces deux scrapers écrivent `publication_date=datetime.now()` alors qu'ils ont des champs de date source disponibles dans l'API. C'est un "silence fatal" silencieux : les données semblent fraîches mais leur date est inventée.

- [ ] **Step 2.1 : Écrire le test de non-régression**

Dans `tests/test_double_horodatage.py`, ajouter :

```python
def test_afd_ne_met_pas_datetime_now_comme_publication_date(monkeypatch):
    """Vérifie que scraper_afd utilise la vraie date source, pas datetime.now()."""
    import scraper_afd
    # La date de début de projet AFD doit être parsée depuis date_octroi ou date_debut
    rec = {
        "iati_identifier": "FR-6-1234",
        "title_narrative": "Projet test",
        "description": "infrastructure santé",
        "date_dachevement": "2027-06-30",
        "date_octroi": "2024-03-15",      # vraie date source
        "cntry_name": "madagascar",
    }
    # La fonction _build_tender doit utiliser date_octroi, pas datetime.now()
    t = scraper_afd._build_tender(rec, "Madagascar")
    assert t.publication_date is not None
    assert t.publication_date.year < 2026  # antérieure à aujourd'hui
    assert t.date_extraction is not None
    assert t.date_extraction.year == 2026  # collecte aujourd'hui
```

- [ ] **Step 2.2 : Lancer le test — il doit échouer**

```bash
pytest tests/test_double_horodatage.py::test_afd_ne_met_pas_datetime_now_comme_publication_date -v
```

Résultat attendu : `AttributeError: module 'scraper_afd' has no attribute '_build_tender'`

- [ ] **Step 2.3 : Refactoriser `scraper_afd.py` — extraire `_build_tender()` et corriger la date**

Remplacer le bloc de construction du `Tender` (lignes 78-96) par :

```python
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc


def _build_tender(rec: dict, pays_label: str) -> "Tender":
    raw_id = rec.get("iati_identifier") or rec.get("id_projet") or ""
    tender_id = f"AFD-{raw_id}"
    title = rec.get("title_narrative") or f"Projet AFD {raw_id}"
    secteur = rec.get("description") or "Non précisé"
    description = f"AFD — Pays : {pays_label} — Secteur : {secteur}"
    deadline = parse_date(rec.get("date_dachevement"))
    # Vraie date source : date d'octroi (approbation) ou date de début
    pub_date = (
        parse_date(rec.get("date_octroi"))
        or parse_date(rec.get("date_debut"))
        or parse_date(rec.get("date_demarrage"))
    )
    return Tender(
        id=tender_id,
        title=title,
        description=description,
        source=f"https://www.afd.fr/fr/carte-des-projets?query={raw_id}",
        publication_date=pub_date,          # vraie date source (ou None si absente)
        date_extraction=now_utc(),          # timestamp de collecte
        deadline=deadline,
        status="À qualifier",
        relevance_score=0,
        is_maintenance=False,
        llm_analysis=None,
    )
```

Et dans `fetch_afd_projects()`, remplacer `t = Tender(...)` par `t = _build_tender(rec, pays_label)`.

- [ ] **Step 2.4 : Refactoriser `scraper_worldbank.py` — corriger la date**

Remplacer le bloc `Tender(...)` dans `fetch_worldbank_projects()` :

```python
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc

# Dans la boucle, remplacer :
t = Tender(
    id=tender_id,
    title=proj.get("project_name") or f"Projet BM {proj_id}",
    description=f"Banque Mondiale — Pays : {country_name} — Secteur : {sector_label}",
    source=f"https://projects.worldbank.org/en/projects-operations/project-detail/{proj_id}",
    publication_date=parse_date(proj.get("approvaldate") or proj.get("boardapprovaldate")),  # vraie date
    date_extraction=now_utc(),              # timestamp de collecte
    deadline=closing,
    status="À qualifier",
    relevance_score=0,
    is_maintenance=False,
    llm_analysis=None,
)
```

- [ ] **Step 2.5 : Alimenter `date_extraction` dans les scrapers API restants**

Dans `scraper_boamp.py`, `scraper_ted.py`, `scraper_permis.py` — ajouter `date_extraction=now_utc()` dans le constructeur `Tender(...)` de chacun.

Pour `scraper_boamp.py` (ligne ~135) :
```python
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc
# ...
t = Tender(
    # ... champs existants ...
    publication_date=parse_date(record.get("dateparution")),
    date_extraction=now_utc(),   # ← ajouter
    deadline=parse_date(record.get("datelimitereponse")),
    # ...
)
```

Pour `scraper_ted.py` (ligne ~95) :
```python
from scraper_utils import parse_date, retry_post, load_existing_ids, insert_if_new, now_utc
# ...
t = Tender(
    # ...
    publication_date=None,
    date_extraction=now_utc(),   # ← ajouter
    # ...
)
```

Pour `scraper_permis.py` (ligne ~101) :
```python
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new, now_utc
# ...
t = Tender(
    # ...
    publication_date=parse_date(rec.get("date_depot_doc") or rec.get("dat_depdoc")),
    date_extraction=now_utc(),   # ← ajouter
    # ...
)
```

- [ ] **Step 2.6 : Alimenter `date_extraction` dans les scrapers Playwright**

Dans `scraper_marcheonline.py`, `scraper_instao.py`, `scraper_marchessecurises.py`, `scraper_tendersgo.py` — ajouter l'import de `now_utc` et `date_extraction=now_utc()` dans chaque constructeur `Tender(...)`.

Exemple pour `scraper_instao.py` (ligne ~78) :
```python
from scraper_utils import parse_date, load_existing_ids, insert_if_new, now_utc
# ...
t = Tender(
    id=tid, title=title, description=desc, source=url,
    publication_date=parse_date(card.get("date")),
    date_extraction=now_utc(),   # ← ajouter
    deadline=None, status="À qualifier",
    # ...
)
```

Répéter pour `scraper_marchessecurises.py`, `scraper_tendersgo.py`, `scraper_marcheonline.py`.

- [ ] **Step 2.7 : Lancer les tests**

```bash
pytest tests/test_double_horodatage.py -v
```

Résultat attendu : `3 passed`

- [ ] **Step 2.8 : Commit**

```bash
git add scraper_afd.py scraper_worldbank.py scraper_boamp.py scraper_ted.py scraper_permis.py scraper_marcheonline.py scraper_instao.py scraper_marchessecurises.py scraper_tendersgo.py tests/test_double_horodatage.py
git commit -m "fix: corriger publication_date AFD/WB + alimenter date_extraction dans tous les scrapers"
```

---

## Tâche 3 : Module `health_check.py` + alerte Streamlit

**Files:**
- Create: `health_check.py`
- Create: `tests/test_health_check.py`
- Modify: `app.py` (bannière d'alerte)

Ce module vérifie indépendamment que chaque source répond et que sa structure attendue est toujours présente. Il est conçu pour être appelé de l'UI Streamlit sans bloquer et pour persister ses résultats en base.

- [ ] **Step 3.1 : Écrire les tests du health check**

Créer `tests/test_health_check.py` :

```python
from unittest.mock import patch, MagicMock
from health_check import check_source, HealthResult


def test_check_source_ok_returns_healthy():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"results": [{"id": 1}]}'
    mock_resp.json.return_value = {"results": [{"id": 1}]}

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="BOAMP",
            url="https://boamp-datadila.opendatasoft.com",
            marker_type="json_key",
            marker_value="results",
        )
    assert result.ok is True
    assert result.error is None
    assert result.http_status == 200


def test_check_source_missing_marker_returns_unhealthy():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"error": "not found"}'
    mock_resp.json.return_value = {"error": "not found"}

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="BOAMP",
            url="https://boamp-datadila.opendatasoft.com",
            marker_type="json_key",
            marker_value="results",
        )
    assert result.ok is False
    assert "marqueur" in result.error.lower()


def test_check_source_http_error_returns_unhealthy():
    with patch("health_check.requests.get", side_effect=Exception("Connection refused")):
        result = check_source(
            name="BOAMP",
            url="https://boamp-datadila.opendatasoft.com",
            marker_type="json_key",
            marker_value="results",
        )
    assert result.ok is False
    assert result.http_status is None


def test_check_source_html_marker():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '<html><body class="blockNotice">content</body></html>'
    mock_resp.json.side_effect = ValueError("not JSON")

    with patch("health_check.requests.get", return_value=mock_resp):
        result = check_source(
            name="MarchéOnline",
            url="https://www.marchesonline.com",
            marker_type="html_text",
            marker_value="blockNotice",
        )
    assert result.ok is True


def test_run_all_health_checks_returns_dict():
    from health_check import run_all_health_checks
    from unittest.mock import patch

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = '{"results": []}'
    mock_resp.json.return_value = {"results": []}

    with patch("health_check.requests.get", return_value=mock_resp):
        results = run_all_health_checks()

    assert isinstance(results, dict)
    assert len(results) > 0
    for name, r in results.items():
        assert hasattr(r, "ok")
        assert hasattr(r, "checked_at")
```

- [ ] **Step 3.2 : Lancer les tests — ils doivent échouer**

```bash
pytest tests/test_health_check.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'health_check'`

- [ ] **Step 3.3 : Créer `health_check.py`**

```python
"""
Module de health check indépendant — DEF OI Veille Commerciale.

Vérifie pour chaque source :
  1. Code HTTP 200
  2. Présence d'un marqueur structurel (clé JSON ou texte HTML)

Retourne un dict {source_name: HealthResult} consultable par l'UI Streamlit.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

_log = logging.getLogger(__name__)

TIMEOUT = 10  # secondes


@dataclass
class HealthResult:
    name: str
    ok: bool
    http_status: Optional[int] = None
    error: Optional[str] = None
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


# Registre des sources avec leur marqueur structurel attendu.
# marker_type : "json_key" | "html_text" | "none"
# marker_value : la clé JSON ou le texte HTML à rechercher
_SOURCE_MARKERS: list[dict] = [
    {"name": "BOAMP — Journal Officiel",
     "url": "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records?limit=1",
     "marker_type": "json_key", "marker_value": "results"},

    {"name": "TED Europe",
     "url": "https://api.ted.europa.eu/v3/notices/search",
     "marker_type": "json_key", "marker_value": "notices",
     "method": "post", "body": {"query": "FT~SSI", "limit": 1}},

    {"name": "AFD — Agence Française de Développement",
     "url": "https://opendata.afd.fr/api/explore/v2.1/catalog/datasets/les-projets-de-l-afd/records?limit=1",
     "marker_type": "json_key", "marker_value": "results"},

    {"name": "Banque Mondiale",
     "url": "https://search.worldbank.org/api/v2/projects?format=json&countrycode=MG&rows=1",
     "marker_type": "json_key", "marker_value": "projects"},

    {"name": "Permis de construire",
     "url": "https://data.statistiques.developpement-durable.gouv.fr/api/explore/v2.1/catalog/datasets/sitadel/records?limit=1",
     "marker_type": "json_key", "marker_value": "results"},

    {"name": "Marché Online",
     "url": "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101",
     "marker_type": "html_text", "marker_value": "blockNotice"},

    {"name": "Instao",
     "url": "https://www.instao.fr/bids",
     "marker_type": "html_text", "marker_value": "bid"},

    {"name": "Marchés Sécurisés",
     "url": "https://www.marches-securises.fr/entreprise/?page=entreprise_dce_recherche",
     "marker_type": "html_text", "marker_value": "connexion"},

    {"name": "Tenders Go",
     "url": "https://app.tendersgo.com",
     "marker_type": "html_text", "marker_value": "tender"},
]

_HEADERS = {"User-Agent": "DEF-OI-HealthCheck/1.0"}


def check_source(
    name: str,
    url: str,
    marker_type: str = "none",
    marker_value: str = "",
    method: str = "get",
    body: dict | None = None,
) -> HealthResult:
    """Vérifie une source : HTTP 200 + marqueur structurel."""
    try:
        if method == "post":
            resp = requests.post(url, json=body or {}, timeout=TIMEOUT, headers=_HEADERS)
        else:
            resp = requests.get(url, timeout=TIMEOUT, headers=_HEADERS, allow_redirects=True)

        http_status = resp.status_code

        if resp.status_code >= 400:
            return HealthResult(name=name, ok=False, http_status=http_status,
                                error=f"HTTP {resp.status_code}")

        # Vérification du marqueur structurel
        if marker_type == "json_key":
            try:
                data = resp.json()
                if marker_value not in data:
                    return HealthResult(name=name, ok=False, http_status=http_status,
                                        error=f"Marqueur JSON '{marker_value}' absent — structure du site changée ?")
            except Exception:
                return HealthResult(name=name, ok=False, http_status=http_status,
                                    error="Réponse non JSON — structure du site changée ?")

        elif marker_type == "html_text":
            if marker_value not in resp.text:
                return HealthResult(name=name, ok=False, http_status=http_status,
                                    error=f"Marqueur HTML '{marker_value}' absent — structure du site changée ?")

        return HealthResult(name=name, ok=True, http_status=http_status)

    except Exception as exc:
        _log.warning("HealthCheck [%s] : %s", name, exc)
        return HealthResult(name=name, ok=False, error=str(exc))


def run_all_health_checks() -> dict[str, HealthResult]:
    """Lance le health check sur toutes les sources enregistrées."""
    results: dict[str, HealthResult] = {}
    for source in _SOURCE_MARKERS:
        name = source["name"]
        _log.info("HealthCheck : vérification de '%s'", name)
        results[name] = check_source(
            name=name,
            url=source["url"],
            marker_type=source.get("marker_type", "none"),
            marker_value=source.get("marker_value", ""),
            method=source.get("method", "get"),
            body=source.get("body"),
        )
    return results


def persist_health_results(db, results: dict[str, HealthResult]) -> None:
    """Persiste les résultats dans la table `sources` (champs ping existants)."""
    from source_registry import Source
    for name, result in results.items():
        source = db.query(Source).filter(Source.name == name).first()
        if not source:
            continue
        source.last_ping_at = result.checked_at
        if result.ok:
            source.ping_failures_count = 0
        else:
            source.ping_failures_count = (source.ping_failures_count or 0) + 1
            if source.ping_failures_count >= 3:
                source.is_validated = False
    db.commit()
```

- [ ] **Step 3.4 : Lancer les tests — ils doivent passer**

```bash
pytest tests/test_health_check.py -v
```

Résultat attendu : `5 passed`

- [ ] **Step 3.5 : Ajouter la bannière d'alerte dans `app.py`**

Dans `app.py`, dans la section d'initialisation (après `init_db()`), ajouter la logique d'alerte :

```python
# Juste après init_db() dans la section principale de app.py
import health_check as _hc

@st.cache_data(ttl=3600)   # rafraîchi toutes les heures
def _get_health_status() -> dict:
    """Retourne le résultat du health check mis en cache 1h."""
    results = _hc.run_all_health_checks()
    db = SessionLocal()
    try:
        _hc.persist_health_results(db, results)
    finally:
        db.close()
    return {name: {"ok": r.ok, "error": r.error} for name, r in results.items()}


def _show_health_alerts():
    """Affiche une bannière orange/rouge si des sources sont dégradées."""
    try:
        statuses = _get_health_status()
    except Exception:
        return   # ne pas bloquer l'UI si le health check échoue

    degraded = [(name, info["error"]) for name, info in statuses.items() if not info["ok"]]
    if not degraded:
        return

    with st.container():
        st.warning(
            f"⚠️ **{len(degraded)} source(s) dégradée(s)** — les données peuvent être incomplètes :\n"
            + "\n".join(f"- **{name}** : {err}" for name, err in degraded),
            icon="🔴",
        )
```

Appeler `_show_health_alerts()` en haut de chaque page (ou dans la sidebar), après `st.title(...)`.

- [ ] **Step 3.6 : Lancer les tests complets**

```bash
pytest tests/test_health_check.py -v
```

Résultat attendu : `5 passed`

- [ ] **Step 3.7 : Commit**

```bash
git add health_check.py tests/test_health_check.py app.py
git commit -m "feat: module health_check.py + bannière alerte Streamlit sources dégradées"
```

---

## Tâche 4 : Règle de péremption — `clean_obsolete_data()`

**Files:**
- Modify: `database.py`
- Create: `tests/test_retention.py`
- Modify: `app.py` (appel au démarrage)

La fonction archive les tenders "À qualifier" dont la `publication_date` date de plus de 30 jours en changeant leur statut en `"Archivé"`. Les tenders avec décision (Soumis/Gagné/Perdu) et les enregistrements sans date ne sont jamais touchés.

- [ ] **Step 4.1 : Écrire les tests de rétention**

Créer `tests/test_retention.py` :

```python
from datetime import datetime, timedelta
from database import clean_obsolete_data
from models import Tender


def _make_tender(db, tid, pub_date, status="À qualifier"):
    t = Tender(
        id=tid, title=f"Tender {tid}", source="http://x.com",
        publication_date=pub_date, status=status,
        relevance_score=0, is_maintenance=False,
    )
    db.add(t)
    db.commit()
    return t


def test_tender_older_than_30_days_is_archived(db_session):
    old_date = datetime.now() - timedelta(days=35)
    _make_tender(db_session, "OLD-001", old_date, "À qualifier")

    count = clean_obsolete_data(db_session, days=30)

    assert count == 1
    t = db_session.query(Tender).filter(Tender.id == "OLD-001").first()
    assert t.status == "Archivé"


def test_tender_within_30_days_is_preserved(db_session):
    recent_date = datetime.now() - timedelta(days=10)
    _make_tender(db_session, "RECENT-001", recent_date, "À qualifier")

    count = clean_obsolete_data(db_session, days=30)

    assert count == 0
    t = db_session.query(Tender).filter(Tender.id == "RECENT-001").first()
    assert t.status == "À qualifier"


def test_tender_with_decision_is_never_archived(db_session):
    old_date = datetime.now() - timedelta(days=60)
    _make_tender(db_session, "SOUMIS-001", old_date, "Soumis")
    _make_tender(db_session, "GAGNE-001", old_date, "Gagné")
    _make_tender(db_session, "PERDU-001", old_date, "Perdu")

    count = clean_obsolete_data(db_session, days=30)

    assert count == 0
    for tid in ("SOUMIS-001", "GAGNE-001", "PERDU-001"):
        t = db_session.query(Tender).filter(Tender.id == tid).first()
        assert t.status != "Archivé"


def test_tender_without_publication_date_is_preserved(db_session):
    _make_tender(db_session, "NODDATE-001", None, "À qualifier")

    count = clean_obsolete_data(db_session, days=30)

    assert count == 0
    t = db_session.query(Tender).filter(Tender.id == "NODDATE-001").first()
    assert t.status == "À qualifier"


def test_blacklisted_tender_is_preserved(db_session):
    old_date = datetime.now() - timedelta(days=45)
    t = Tender(
        id="BLACK-001", title="Blacklisted", source="http://x.com",
        publication_date=old_date, status="À qualifier",
        is_blacklisted=True, relevance_score=0, is_maintenance=False,
    )
    db_session.add(t)
    db_session.commit()

    count = clean_obsolete_data(db_session, days=30)

    assert count == 0
    t = db_session.query(Tender).filter(Tender.id == "BLACK-001").first()
    assert t.status == "À qualifier"
```

Le `db_session` fixture est déjà défini dans `tests/conftest.py`.

- [ ] **Step 4.2 : Lancer les tests — ils doivent échouer**

```bash
pytest tests/test_retention.py -v
```

Résultat attendu : `ImportError: cannot import name 'clean_obsolete_data' from 'database'`

- [ ] **Step 4.3 : Ajouter `clean_obsolete_data()` dans `database.py`**

En bas de `database.py`, ajouter :

```python
def clean_obsolete_data(db, days: int = 30) -> int:
    """Archive les tenders 'À qualifier' dont la publication_date dépasse `days` jours.

    Règles strictes :
    - Ne touche JAMAIS les tenders avec statut Soumis/Gagné/Perdu
    - Ne touche JAMAIS les tenders blacklistés
    - Ne touche JAMAIS les tenders sans publication_date
    - Retourne le nombre de tenders archivés
    """
    from models import Tender
    from datetime import datetime as _ddt, timedelta as _td

    cutoff = _ddt.now(_tz.utc).replace(tzinfo=None) - _td(days=days)
    _DECISIONS = ("Soumis", "Gagné", "Perdu", "Archivé")

    tenders = (
        db.query(Tender)
        .filter(
            Tender.status == "À qualifier",
            Tender.is_blacklisted == False,
            Tender.publication_date != None,
            Tender.publication_date < cutoff,
        )
        .all()
    )

    for t in tenders:
        t.status = "Archivé"

    count = len(tenders)
    if count:
        db.commit()
        _log.info("clean_obsolete_data : %d tenders archivés (> %d jours)", count, days)
    return count
```

- [ ] **Step 4.4 : Lancer les tests — ils doivent passer**

```bash
pytest tests/test_retention.py -v
```

Résultat attendu : `5 passed`

- [ ] **Step 4.5 : Appeler `clean_obsolete_data()` au démarrage dans `app.py`**

Dans `app.py`, dans la section `init_db()` (appelée au premier chargement via `st.cache_resource` ou directement) :

```python
from database import SessionLocal, init_db, clean_obsolete_data

# Après init_db() :
if "retention_done" not in st.session_state:
    _db = SessionLocal()
    try:
        n = clean_obsolete_data(_db, days=30)
        if n:
            st.toast(f"🗂️ {n} offre(s) archivée(s) automatiquement (> 30 jours)", icon="ℹ️")
    finally:
        _db.close()
    st.session_state["retention_done"] = True
```

- [ ] **Step 4.6 : Lancer la suite complète de tests**

```bash
pytest tests/test_retention.py tests/test_health_check.py tests/test_double_horodatage.py -v
```

Résultat attendu : `13 passed`

- [ ] **Step 4.7 : Commit**

```bash
git add database.py tests/test_retention.py app.py
git commit -m "feat: clean_obsolete_data() — archivage automatique des tenders > 30 jours"
```

---

## Tâche 5 : Vérification finale et tests globaux

**Files:**
- Read: tous les fichiers modifiés

- [ ] **Step 5.1 : Lancer la suite complète**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Résultat attendu : tous les tests passent, aucune régression.

- [ ] **Step 5.2 : Vérifier que la migration fonctionne sur une base existante**

```bash
python -c "from database import init_db; init_db(); print('Migration OK')"
```

Résultat attendu : `Migration OK` (pas d'erreur, la colonne `date_extraction` est créée idempotement).

- [ ] **Step 5.3 : Commit final**

```bash
git add -A
git commit -m "feat: fiabilisation complète — double horodatage + health checks + rétention 30 jours"
```

---

## Récapitulatif des changements par directive

| Directive | Fichiers touchés | Résultat |
|---|---|---|
| **1. API-first** | `scraper_afd.py`, `scraper_worldbank.py` | Bug `datetime.now()` corrigé ; Playwright maintenu pour sources sans API |
| **2. Health checks** | `health_check.py` (nouveau), `app.py` | Vérif HTTP 200 + marqueur structurel + alerte Streamlit |
| **3. Double horodatage** | `models.py`, `database.py`, 9 scrapers | `date_extraction` partout, `publication_date` correcte |
| **4. Péremption** | `database.py`, `app.py` | `clean_obsolete_data()` au démarrage, toast notification |

## Notes sur les sources sans API publique

Pour **Instao**, **MarchésOnline**, **MarchésSecurisés** et **TendersGo** : aucune API publique documentée n'existe. Le scraping Playwright est maintenu, mais renforcé avec des marqueurs structurels dans `health_check.py` qui détecteront tout changement de layout avant qu'il ne provoque un silence fatal.
