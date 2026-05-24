# Refactoring Mistral API Pure — Suppression Claude/Anthropic et Streamlit

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Éliminer toute dépendance à Anthropic/Claude et à Streamlit pour migrer vers une API Python pure propulsée exclusivement par Mistral.

**Architecture:** La logique métier est déjà correctement séparée dans `llm_analyzer.py`, `database.py`, `models.py`, `filters.py`, `fiche_logic.py` et les scrapers. Phase 1 nettoie le client Anthropic et les tests obsolètes. Phase 2 supprime la couche Streamlit et expose un serveur FastAPI.

**Tech Stack:** Python 3.11+, Mistral AI (`mistralai>=1.0.0`), FastAPI, SQLAlchemy, APScheduler

---

## Phase 1 — Suppression Claude/Anthropic (safe, immédiat)

### Task 1 : Nettoyer `llm_analyzer.py` — supprimer le client Anthropic et `_claude_analyze`

**Files:**
- Modify: `llm_analyzer.py:623-780` (suppression client + fonction Claude)
- Modify: `llm_analyzer.py:1000-1005` (branchement `analyze_tender`)
- Modify: `llm_analyzer.py:1086-1091` (branchement `auto_analyze_claude`)
- Modify: `llm_analyzer.py:1017` (message de log contenant "_claude_analyze")

- [ ] **Step 1 : Supprimer le bloc client Anthropic (lignes 623-637)**

Remplacer ce bloc :
```python
_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except Exception:
            return None
    return _anthropic_client
```
Par : *(rien — supprimer entièrement)*

- [ ] **Step 2 : Supprimer la fonction `_claude_analyze` (lignes 718-780)**

Supprimer entièrement la fonction `def _claude_analyze(text: str) -> dict | None:` et son corps (environ 62 lignes, jusqu'à la ligne avec `return None` après le bloc `except Exception`).

- [ ] **Step 3 : Simplifier le branchement dans `analyze_tender()` (ligne ~1086-1091)**

Remplacer :
```python
    provider = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
    try:
        if provider == "mistral":
            llm_result = _mistral_analyze(text)
        else:
            llm_result = _claude_analyze(text)
    except _LLMQuotaError:
        llm_result = None
```
Par :
```python
    try:
        llm_result = _mistral_analyze(text)
    except _LLMQuotaError:
        llm_result = None
```

- [ ] **Step 4 : Simplifier le branchement dans `auto_analyze_claude()` (ligne ~1000-1005)**

Remplacer :
```python
        provider = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
        try:
            if provider == "mistral":
                llm_result = _mistral_analyze(text)
            else:
                llm_result = _claude_analyze(text)
        except _LLMQuotaError as qe:
```
Par :
```python
        try:
            llm_result = _mistral_analyze(text)
        except _LLMQuotaError as qe:
```

- [ ] **Step 5 : Corriger le message de log obsolète (ligne ~1017)**

Remplacer :
```python
            "auto_analyze_claude: marché '%s' — %s a retourné None (clé absente, JSON invalide ou erreur réseau)",
                (t.title or t.id)[:60], provider,
```
Par :
```python
            "auto_analyze_claude: marché '%s' — Mistral a retourné None (clé absente, JSON invalide ou erreur réseau)",
                (t.title or t.id)[:60],
```

- [ ] **Step 6 : Vérifier qu'aucune autre référence à `_claude_analyze` ou `anthropic` ne subsiste**

Run: `grep -n "claude_analyze\|_get_anthropic\|_anthropic_client\|import anthropic\|ANTHROPIC" llm_analyzer.py`
Expected: aucune ligne retournée.

- [ ] **Step 7 : Commit**

```bash
git add llm_analyzer.py
git commit -m "refactor(llm): supprimer client Anthropic et _claude_analyze, Mistral uniquement"
```

---

### Task 2 : Mettre à jour `tests/test_llm_analyzer.py` — supprimer/réécrire les tests Claude

**Files:**
- Modify: `tests/test_llm_analyzer.py`

Tests à **supprimer** (devenus dead code après Task 1) :

| Fonction test | Raison |
|---|---|
| `test_analyze_tender_returns_combined_score` (ligne ~46) | Mockait `_claude_analyze` — réécrire pour Mistral |
| `test_authentication_error_does_not_log_key` (ligne ~78) | Teste `_claude_analyze` et `anthropic.AuthenticationError` — supprimer |
| `test_analyze_tender_structured_returns_none_without_api_key` (ligne ~115) | Referençait `ANTHROPIC_API_KEY` — corriger pour `MISTRAL_API_KEY` |
| `test_analyze_tender_structured_parses_valid_json` (ligne ~126) | Mockait `anthropic.Anthropic` — réécrire pour Mistral |
| `test_analyze_tender_structured_handles_invalid_json` (ligne ~153) | Mockait `anthropic.Anthropic` — réécrire pour Mistral |
| `test_analyze_tender_routes_to_claude_by_default` (ligne ~311) | Testait le fallback Claude — supprimer |

- [ ] **Step 1 : Supprimer `test_authentication_error_does_not_log_key`**

Supprimer les lignes 78-102 (test entier).

- [ ] **Step 2 : Réécrire `test_analyze_tender_returns_combined_score` pour Mistral**

Remplacer le corps du test (qui monkeypatche `_claude_analyze`) par :
```python
def test_analyze_tender_returns_combined_score(monkeypatch):
    """Vérifie que analyze_tender combine scores quand Mistral répond."""
    from llm_analyzer import _local_analyze
    import llm_analyzer

    fake_mistral = {
        "score_pertinence": 80,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "Marché SSI direct.",
        "_source": "mistral",
    }
    monkeypatch.setattr(llm_analyzer, "_mistral_analyze", lambda text: fake_mistral)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")
    local = _local_analyze("Maintenance SSI La Réunion 974")
    expected_score = round(80 * 0.70 + local["score_pertinence"] * 0.30)
    assert result["score_pertinence"] == expected_score
    assert result["_source"] == "mistral"
```

- [ ] **Step 3 : Corriger `test_analyze_tender_structured_returns_none_without_api_key`**

Remplacer `monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)` par :
```python
    monkeypatch.delenv('MISTRAL_API_KEY', raising=False)
    import llm_analyzer
    llm_analyzer._mistral_client = None
```

- [ ] **Step 4 : Réécrire `test_analyze_tender_structured_parses_valid_json` pour Mistral**

```python
def test_analyze_tender_structured_parses_valid_json(monkeypatch):
    """Réponse Mistral JSON valide -> dict avec les bons champs."""
    monkeypatch.setenv('MISTRAL_API_KEY', 'fake-mistral-key-1234')
    import llm_analyzer
    from unittest.mock import MagicMock

    fake_json = '{"budget_estime": "150 000 euro", "type_travaux": "Installation neuve", "lots": ["Lot 1 - Detection"], "keywords_techniques": ["SSI categorie A"], "acheteur_type": "Etablissement scolaire", "niveau_concurrence": "Eleve", "recommandation": "GO", "score_confiance": 82, "justification": "ERP type J, coeur de metier."}'
    mock_choice = MagicMock()
    mock_choice.message.content = fake_json
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = mock_response
    llm_analyzer._mistral_client = None
    monkeypatch.setattr(llm_analyzer, "_get_mistral_client", lambda: mock_client)

    from llm_analyzer import analyze_tender_structured
    result = analyze_tender_structured(
        'Installation SSI ERP type J',
        'Installation d un systeme de securite incendie dans un ERP de type J categorie 2, desenfumage CMSI inclus.',
        amount=150000,
    )

    assert result is not None
    assert result['recommandation'] == 'GO'
    assert result['score_confiance'] == 82
    assert 'budget_estime' in result
    assert isinstance(result['lots'], list)
```

- [ ] **Step 5 : Réécrire `test_analyze_tender_structured_handles_invalid_json` pour Mistral**

```python
def test_analyze_tender_structured_handles_invalid_json(monkeypatch):
    """Mistral retourne du texte invalide -> None sans exception."""
    monkeypatch.setenv('MISTRAL_API_KEY', 'fake-mistral-key-1234')
    import llm_analyzer
    from unittest.mock import MagicMock

    mock_choice = MagicMock()
    mock_choice.message.content = 'Desole, je ne peux pas repondre.'
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = mock_response
    monkeypatch.setattr(llm_analyzer, "_get_mistral_client", lambda: mock_client)

    from llm_analyzer import analyze_tender_structured
    result = analyze_tender_structured(
        'Installation SSI',
        'Installation d un systeme de securite incendie complet avec CMSI et desenfumage.',
    )
    assert result is None
```

- [ ] **Step 6 : Supprimer `test_analyze_tender_routes_to_claude_by_default`**

Supprimer les lignes 311-332 (test entier + sa docstring).

- [ ] **Step 7 : Nettoyer `test_analyze_tender_routes_to_mistral_when_provider_is_mistral`**

Ce test mockait aussi `_claude_analyze` en fallback. Supprimer les références à `fake_claude` et `calls["claude"]` dans ce test. Résultat final :
```python
def test_analyze_tender_routes_to_mistral(monkeypatch):
    """analyze_tender utilise toujours _mistral_analyze."""
    import llm_analyzer

    fake_mistral_result = {
        "score_pertinence": 70,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "SSI Réunion.",
        "_source": "mistral",
    }
    calls = {"mistral": 0}

    def fake_mistral(text):
        calls["mistral"] += 1
        return fake_mistral_result

    monkeypatch.setattr(llm_analyzer, "_mistral_analyze", fake_mistral)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")

    assert calls["mistral"] == 1
    assert result["_source"] == "mistral"
```

- [ ] **Step 8 : Lancer les tests pour vérifier**

Run: `pytest tests/test_llm_analyzer.py -v`
Expected: tous les tests passent, aucune erreur `ModuleNotFoundError: anthropic`.

- [ ] **Step 9 : Commit**

```bash
git add tests/test_llm_analyzer.py
git commit -m "test(llm): réécrire tests Claude pour Mistral, supprimer tests Anthropic obsolètes"
```

---

### Task 3 : Mettre à jour `requirements.txt` — supprimer `anthropic`

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1 : Supprimer la ligne `anthropic>=0.25.0`**

Retirer la ligne suivante de `requirements.txt` :
```
anthropic>=0.25.0
```

- [ ] **Step 2 : Vérifier l'absence de références résiduelles**

Run: `grep -rn "anthropic" --include="*.py" . --exclude-dir=.claude`
Expected: aucune ligne retournée dans les fichiers `.py` hors worktrees.

- [ ] **Step 3 : Commit**

```bash
git add requirements.txt
git commit -m "deps: supprimer anthropic — Mistral est le seul LLM provider"
```

---

## Phase 2 — Suppression Streamlit et création API FastAPI

> **Prérequis :** Phase 1 terminée et tests passants.

### Task 4 : Créer `api.py` — serveur FastAPI avec les endpoints métier

**Files:**
- Create: `api.py`

Les endpoints à exposer correspondent aux actions principales de `app.py` :

| Endpoint | Méthode | Description |
|---|---|---|
| `GET /health` | GET | Statut app + sources (issu de `health_check.py`) |
| `GET /tenders` | GET | Liste filtrée (params: score_min, status, domaine, territoire, q) |
| `POST /tenders/{id}/analyze` | POST | Déclenche `analyze_tender` pour un marché |
| `POST /scrape` | POST | Lance le pipeline de scraping (body: sources[]) |
| `POST /auto-analyze` | POST | Lance `auto_analyze_pending` (body: max_per_run) |
| `GET /sources` | GET | Liste les sources depuis `source_registry` |
| `POST /sources` | POST | Ajoute une source |
| `DELETE /sources/{name}` | DELETE | Supprime une source |
| `GET /export/excel` | GET | Génère et retourne le rapport Excel |

- [ ] **Step 1 : Installer FastAPI et uvicorn**

Ajouter à `requirements.txt` :
```
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
```

- [ ] **Step 2 : Créer `api.py`**

```python
import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database import SessionLocal, init_db, clean_obsolete_data
from health_check import run_all_health_checks
from llm_analyzer import analyze_tender, auto_analyze_pending
from models import Tender
from source_registry import list_sources, add_source, remove_source, toggle_enabled
from export_excel import generate_executive_report

_log = logging.getLogger(__name__)
init_db()

app = FastAPI(title="DEF OI Veille Commerciale", version="2.0.0")


@app.get("/health")
def health():
    results = run_all_health_checks()
    return {
        "status": "ok",
        "sources": {name: {"ok": r.ok, "error": r.error} for name, r in results.items()},
    }


class TenderFilter(BaseModel):
    score_min: int = 0
    status: Optional[str] = None
    domaine: Optional[str] = None
    territoire: Optional[str] = None
    q: Optional[str] = None
    limit: int = 50
    offset: int = 0


@app.get("/tenders")
def list_tenders(
    score_min: int = Query(0),
    status: Optional[str] = Query(None),
    domaine: Optional[str] = Query(None),
    territoire: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    db = SessionLocal()
    try:
        query = db.query(Tender).filter(
            Tender.is_blacklisted == False,
            Tender.relevance_score >= score_min,
        )
        if status:
            query = query.filter(Tender.status == status)
        if q:
            query = query.filter(
                Tender.title.ilike(f"%{q}%") | Tender.description.ilike(f"%{q}%")
            )
        total = query.count()
        tenders = query.order_by(Tender.relevance_score.desc()).offset(offset).limit(limit).all()
        return {
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "title": t.title,
                    "score": t.relevance_score,
                    "status": t.status,
                    "amount": t.amount,
                    "publication_date": str(t.publication_date) if t.publication_date else None,
                    "source_url": t.source_url,
                    "llm_analysis": t.llm_analysis,
                }
                for t in tenders
            ],
        }
    finally:
        db.close()


@app.post("/tenders/{tender_id}/analyze")
def analyze_one(tender_id: str):
    db = SessionLocal()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Marché introuvable")
        text = f"{t.title or ''} {t.description or ''}"
        result = analyze_tender(text, source_url=t.source_url)
        t.llm_analysis = result
        t.relevance_score = result.get("score_pertinence", t.relevance_score)
        db.commit()
        return result
    finally:
        db.close()


class ScrapeRequest(BaseModel):
    sources: list[str] = []
    max_tenders: int = 50


@app.post("/scrape")
def scrape(req: ScrapeRequest):
    from source_registry import list_sources as _ls
    from importlib import import_module
    enabled = [s for s in _ls() if s["enabled"] and (not req.sources or s["name"] in req.sources)]
    results = {}
    for src in enabled:
        try:
            mod = import_module(src["module"])
            count = mod.run(max_results=req.max_tenders)
            results[src["name"]] = {"ok": True, "count": count}
        except Exception as exc:
            results[src["name"]] = {"ok": False, "error": str(exc)[:200]}
    return results


class AutoAnalyzeRequest(BaseModel):
    max_per_run: int = 10


@app.post("/auto-analyze")
def auto_analyze(req: AutoAnalyzeRequest):
    db = SessionLocal()
    try:
        nb_done, retry_after = auto_analyze_pending(db, max_per_run=req.max_per_run)
        return {"nb_done": nb_done, "retry_after": retry_after}
    finally:
        db.close()


@app.get("/sources")
def get_sources():
    return list_sources()


class SourceCreate(BaseModel):
    name: str
    module: str
    enabled: bool = True


@app.post("/sources")
def create_source(src: SourceCreate):
    add_source(src.name, src.module, src.enabled)
    return {"ok": True}


@app.delete("/sources/{name}")
def delete_source(name: str):
    remove_source(name)
    return {"ok": True}


@app.get("/export/excel")
def export_excel():
    db = SessionLocal()
    try:
        path = generate_executive_report(db)
        return FileResponse(path, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", filename="rapport_def_oi.xlsx")
    finally:
        db.close()
```

- [ ] **Step 3 : Vérifier que FastAPI démarre sans erreur**

Run: `uvicorn api:app --host 0.0.0.0 --port 8000 --reload`
Expected: `INFO: Application startup complete.` — aucun `ImportError`.

- [ ] **Step 4 : Tester les endpoints principaux**

Run:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/tenders?score_min=50&limit=5
curl http://localhost:8000/sources
```
Expected: réponses JSON valides.

- [ ] **Step 5 : Commit**

```bash
git add api.py requirements.txt
git commit -m "feat(api): créer serveur FastAPI pur — endpoints tenders, scrape, analyse, sources, export"
```

---

### Task 5 : Supprimer `app.py` et les pages Streamlit

**Files:**
- Delete: `app.py`
- Delete: `pages/analytics.py`
- Delete: `pages/direction.py`
- Delete: `pages/guide.py`
- Delete: `pages/parametres.py`
- Delete: `pages/pipeline.py`

> **Vérification préalable obligatoire :** s'assurer qu'aucun autre fichier n'importe `app.py` directement.

- [ ] **Step 1 : Vérifier les imports de app.py**

Run: `grep -rn "from app import\|import app" --include="*.py" . --exclude-dir=.claude`
Expected: aucune ligne retournée.

- [ ] **Step 2 : Vérifier que toute logique métier utile a été extraite**

Fonctions dans `app.py` déjà couvertes par les modules séparés :
- Scraping → scrapers existants + endpoint `/scrape`
- Analyse LLM → `llm_analyzer.py` + endpoint `/auto-analyze`
- Health check → `health_check.py` + endpoint `/health`
- Export → `export_excel.py` + endpoint `/export/excel`
- Source management → `source_registry.py` + endpoints `/sources`

Si des fonctions utilitaires uniques subsistent dans `app.py` (ex: `_compute_fiche_data` importé de `fiche_logic`), vérifier qu'elles existent déjà dans leur module propre.

- [ ] **Step 3 : Supprimer les fichiers Streamlit**

```bash
git rm app.py pages/analytics.py pages/direction.py pages/guide.py pages/parametres.py pages/pipeline.py
```

- [ ] **Step 4 : Supprimer streamlit et plotly de requirements.txt**

Retirer de `requirements.txt` :
```
streamlit>=1.32.0
plotly>=5.0.0
kaleido==0.2.1
```
(plotly et kaleido ne servent qu'aux graphiques Streamlit)

- [ ] **Step 5 : Lancer les tests pour s'assurer qu'il n'y a plus d'import Streamlit**

Run: `pytest tests/ -v --ignore=tests/test_scrapers_playwright.py`
Expected: tous les tests passent. Aucun `ModuleNotFoundError: streamlit`.

- [ ] **Step 6 : Commit séparé par fichier (règle du repo)**

```bash
git add pages/analytics.py && git commit -m "remove: supprimer page Streamlit analytics"
git add pages/direction.py && git commit -m "remove: supprimer page Streamlit direction"
git add pages/guide.py && git commit -m "remove: supprimer page Streamlit guide"
git add pages/parametres.py && git commit -m "remove: supprimer page Streamlit parametres"
git add pages/pipeline.py && git commit -m "remove: supprimer page Streamlit pipeline"
git add app.py && git commit -m "remove: supprimer app Streamlit — remplacé par api.py FastAPI"
git add requirements.txt && git commit -m "deps: supprimer streamlit, plotly, kaleido — API pure"
```

---

## Récapitulatif des fichiers impactés

| Fichier | Action | Phase |
|---|---|---|
| `llm_analyzer.py` | Supprimer `_anthropic_client`, `_get_anthropic_client`, `_claude_analyze`, simplifier branchements | 1 |
| `tests/test_llm_analyzer.py` | Supprimer 2 tests, réécrire 4 tests pour Mistral | 1 |
| `requirements.txt` | Supprimer `anthropic` | 1 |
| `requirements.txt` | Supprimer `streamlit`, `plotly`, `kaleido`; ajouter `fastapi`, `uvicorn` | 2 |
| `api.py` | Créer serveur FastAPI | 2 |
| `app.py` | Supprimer | 2 |
| `pages/analytics.py` | Supprimer | 2 |
| `pages/direction.py` | Supprimer | 2 |
| `pages/guide.py` | Supprimer | 2 |
| `pages/parametres.py` | Supprimer | 2 |
| `pages/pipeline.py` | Supprimer | 2 |

## Risques identifiés

- `pages/direction.py` contient des fonctions data pures (`_load_direction_kpis_data`) qui ne sont pas encore exposées via l'API. Avant de supprimer ce fichier, vérifier si ces KPIs doivent être ajoutés à `api.py` comme endpoint `/dashboard/kpis`.
- `app.py` gère un scheduler APScheduler pour les tâches périodiques. Ce comportement doit être géré dans `api.py` via un événement `lifespan` FastAPI, ou externalisé dans un script cron séparé (`scheduler.py`).
- Les tests `test_direction.py` et `test_analytics.py` peuvent contenir des dépendances Streamlit indirectes — les vérifier avant de lancer la suite complète en Phase 2.
