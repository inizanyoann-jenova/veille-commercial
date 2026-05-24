# Audit Fixes — Collecte & Analyse LLM

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corriger les 5 problèmes identifiés à l'audit : perte silencieuse de tenders sans date, incohérence de la fenêtre temporelle entre BOAMP et l'insertion, absence de retry sur BOAMP, limite LLM non configurable, et incohérence entre les deux prompts système.

**Architecture:** Chaque fix est indépendant et ciblé sur un seul module. On suit TDD : test écrit avant l'implémentation. Un commit par fichier modifié (règle repo). Les tests s'exécutent avec `pytest -x` depuis la racine.

**Tech Stack:** Python 3.11, SQLAlchemy (SQLite in-memory pour les tests), pytest, Mistral AI SDK, FastAPI.

---

## Fichiers modifiés / créés

| Fichier | Action | Responsabilité |
|---|---|---|
| `scraper_utils.py` | Modifier | Log + param `headers` dans `retry_get()` + `_INSERT_MAX_AGE_DAYS` env-driven |
| `scraper_boamp.py` | Modifier | Utiliser `retry_get()`, aligner fenêtre sur env var |
| `backend/main.py` | Modifier | Compteur `nb_rejected_no_date` dans la boucle collect, exposé en réponse API |
| `llm_analyzer.py` | Modifier | `LLM_BATCH_SIZE` env-driven + `_STRUCTURED_SYSTEM` aligné |
| `tests/test_insert_if_new.py` | Créer | Tests TDD pour les rejets d'insertion |
| `tests/test_collect_window.py` | Créer | Tests TDD pour l'alignement de fenêtre |
| `tests/test_boamp_retry.py` | Créer | Tests TDD pour le retry BOAMP |

---

## Task 1 — `insert_if_new` : log les rejets sur date manquante

**Problème :** Un tender sans `publication_date` est silencieusement écarté. Aucune trace, aucun compteur.

**Fix :** Ajouter un `_log.warning()` dans `insert_if_new` quand la date est absente.

**Files:**
- Modify: `scraper_utils.py`
- Create: `tests/test_insert_if_new.py`

---

- [ ] **Étape 1.1 : Écrire le test qui vérifie le warning sur date absente**

Créer `tests/test_insert_if_new.py` :

```python
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender
from scraper_utils import insert_if_new


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_tender(**kwargs) -> Tender:
    defaults = dict(
        id="T-001",
        title="Marché test",
        source="https://example.com",
        publication_date=None,
        status="À qualifier",
        relevance_score=0,
        is_maintenance=False,
        is_blacklisted=False,
        secteur="Public",
        tags=[],
    )
    defaults.update(kwargs)
    return Tender(**defaults)


def test_insert_if_new_logs_warning_when_no_date(db, caplog):
    t = _make_tender(id="T-001", publication_date=None)
    known: set = set()
    with caplog.at_level(logging.WARNING, logger="scraper_utils"):
        result = insert_if_new(db, t, known)
    assert result is False
    assert any("date" in r.message.lower() or "T-001" in r.message for r in caplog.records)


def test_insert_if_new_no_log_when_too_old(db, caplog):
    """Tender trop ancien : pas de log date manquante (date présente mais périmée)."""
    old = datetime(2000, 1, 1)
    t = _make_tender(id="T-002", publication_date=old)
    known: set = set()
    with caplog.at_level(logging.WARNING, logger="scraper_utils"):
        result = insert_if_new(db, t, known)
    assert result is False
    assert not any("date" in r.message.lower() and "T-002" in r.message for r in caplog.records)


def test_insert_if_new_inserts_valid_tender(db):
    pub = datetime.now() - timedelta(days=5)
    t = _make_tender(id="T-003", publication_date=pub)
    known: set = set()
    result = insert_if_new(db, t, known)
    assert result is True
    assert "T-003" in known


def test_insert_if_new_rejects_duplicate(db):
    pub = datetime.now() - timedelta(days=5)
    t = _make_tender(id="T-004", publication_date=pub)
    known: set = {"T-004"}
    result = insert_if_new(db, t, known)
    assert result is False
```

- [ ] **Étape 1.2 : Vérifier que le test échoue (warning attendu absent)**

```
pytest tests/test_insert_if_new.py::test_insert_if_new_logs_warning_when_no_date -v
```

Résultat attendu : **FAILED** — le log n'existe pas encore.

- [ ] **Étape 1.3 : Ajouter le log dans `scraper_utils.py`**

Dans `scraper_utils.py`, ajouter l'import du logger en haut de fichier (s'il n'existe pas) :

```python
import logging
_log = logging.getLogger(__name__)
```

Puis modifier `insert_if_new` — remplacer :

```python
    if tender.publication_date is None:
        return False
```

par :

```python
    if tender.publication_date is None:
        _log.warning(
            "insert_if_new: rejeté (date manquante) — id=%s titre=%s",
            tender.id,
            (tender.title or "")[:60],
        )
        return False
```

- [ ] **Étape 1.4 : Vérifier que tous les tests passent**

```
pytest tests/test_insert_if_new.py -v
```

Résultat attendu : **4 PASSED**.

- [ ] **Étape 1.5 : Commit**

```
git add scraper_utils.py
git commit -m "fix(insert_if_new): log warning quand publication_date manquante"
```

```
git add tests/test_insert_if_new.py
git commit -m "test(insert_if_new): ajouter tests TDD rejets d'insertion"
```

---

## Task 2 — Compteur `nb_rejected_no_date` dans la réponse `/api/collect`

**Problème :** La réponse de `/api/collect` n'indique pas combien de tenders ont été écartés faute de date. L'opérateur ne peut pas savoir si un scraper retourne des résultats sans date.

**Fix :** Dans la boucle de `collect()`, compter séparément les tenders sans date et les exposer dans la réponse JSON.

**Files:**
- Modify: `backend/main.py` (la boucle d'insertion, lignes ~1100–1115)

---

- [ ] **Étape 2.1 : Ajouter le compteur dans la boucle collect**

Dans `backend/main.py`, localiser la boucle (autour de la ligne 1100) :

```python
            nb_new = 0
            insert_db = SessionLocal()
            try:
                for item in items:
                    t = _dict_to_tender(item, source_category=source.category)
                    if insert_if_new(insert_db, t, known_ids):
                        nb_new += 1
```

Remplacer par :

```python
            nb_new = 0
            nb_rejected_no_date = 0
            insert_db = SessionLocal()
            try:
                for item in items:
                    t = _dict_to_tender(item, source_category=source.category)
                    if t.publication_date is None:
                        nb_rejected_no_date += 1
                    elif insert_if_new(insert_db, t, known_ids):
                        nb_new += 1
```

- [ ] **Étape 2.2 : Exposer le compteur dans la réponse et dans ScraperRun**

Juste après la boucle, la ligne existante :

```python
            results.append({"source": source.name, "status": "ok", "nb_new": nb_new})
```

Remplacer par :

```python
            results.append({
                "source": source.name,
                "status": "ok",
                "nb_found": nb_found,
                "nb_new": nb_new,
                "nb_rejected_no_date": nb_rejected_no_date,
            })
```

- [ ] **Étape 2.3 : Vérifier que les tests existants du backend passent toujours**

```
pytest tests/test_backend_new_routes.py -v
```

Résultat attendu : tous PASSED (la réponse a plus de champs mais aucun test ne vérifie l'absence de champs supplémentaires).

- [ ] **Étape 2.4 : Commit**

```
git add backend/main.py
git commit -m "feat(collect): compteur nb_rejected_no_date dans la réponse /api/collect"
```

---

## Task 3 — Aligner la fenêtre temporelle (une seule source de vérité)

**Problème :** BOAMP cherche par défaut 90 jours en arrière via `SCRAPER_WINDOW_DAYS`, mais `insert_if_new` rejette tout tender de plus de 30 jours (`_INSERT_MAX_AGE_DAYS = 30`). Résultat : 60 jours de résultats BOAMP récupérés et immédiatement jetés.

**Fix :** `_INSERT_MAX_AGE_DAYS` lit la même variable d'environnement `SCRAPER_WINDOW_DAYS` (défaut 30). Le défaut de BOAMP passe de 90 à 30. Les deux modules utilisent la même valeur.

**Files:**
- Modify: `scraper_utils.py`
- Modify: `scraper_boamp.py`
- Create: `tests/test_collect_window.py`

---

- [ ] **Étape 3.1 : Écrire le test de cohérence de fenêtre**

Créer `tests/test_collect_window.py` :

```python
import sys, os, importlib
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender
import scraper_utils


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_tender(id: str, days_old: int) -> Tender:
    pub = datetime.now() - timedelta(days=days_old)
    return Tender(
        id=id,
        title=f"Marché {id}",
        source="https://example.com",
        publication_date=pub,
        status="À qualifier",
        relevance_score=0,
        is_maintenance=False,
        is_blacklisted=False,
        secteur="Public",
        tags=[],
    )


def test_default_window_is_30_days(monkeypatch):
    """Sans variable d'env, la fenêtre par défaut est 30 jours."""
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    assert scraper_utils._INSERT_MAX_AGE_DAYS == 30


def test_window_reads_env(monkeypatch):
    """Avec SCRAPER_WINDOW_DAYS=60, la fenêtre passe à 60 jours."""
    monkeypatch.setenv("SCRAPER_WINDOW_DAYS", "60")
    importlib.reload(scraper_utils)
    assert scraper_utils._INSERT_MAX_AGE_DAYS == 60


def test_tender_at_29_days_is_inserted(db, monkeypatch):
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    t = _make_tender("A-029", days_old=29)
    known: set = set()
    assert scraper_utils.insert_if_new(db, t, known) is True


def test_tender_at_31_days_is_rejected(db, monkeypatch):
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    t = _make_tender("A-031", days_old=31)
    known: set = set()
    assert scraper_utils.insert_if_new(db, t, known) is False


def test_boamp_default_window_matches_insert_window(monkeypatch):
    """Le défaut de BOAMP (SCRAPER_WINDOW_DAYS) doit correspondre à _INSERT_MAX_AGE_DAYS."""
    monkeypatch.delenv("SCRAPER_WINDOW_DAYS", raising=False)
    importlib.reload(scraper_utils)
    # Défaut BOAMP = 30 (env non défini)
    boamp_default = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
    assert boamp_default == scraper_utils._INSERT_MAX_AGE_DAYS
```

- [ ] **Étape 3.2 : Vérifier que les tests échouent**

```
pytest tests/test_collect_window.py -v
```

Résultat attendu : `test_window_reads_env` et `test_default_window_is_30_days` **FAILED** — `_INSERT_MAX_AGE_DAYS` est une constante, pas lue depuis l'env.

- [ ] **Étape 3.3 : Rendre `_INSERT_MAX_AGE_DAYS` env-driven dans `scraper_utils.py`**

Remplacer :

```python
_INSERT_MAX_AGE_DAYS = 30
```

par :

```python
import os as _os
_INSERT_MAX_AGE_DAYS = int(_os.getenv("SCRAPER_WINDOW_DAYS", "30"))
```

- [ ] **Étape 3.4 : Aligner le défaut BOAMP dans `scraper_boamp.py`**

Dans `scraper_boamp.py`, remplacer :

```python
    days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
```

par :

```python
    days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
```

- [ ] **Étape 3.5 : Vérifier que tous les tests passent**

```
pytest tests/test_collect_window.py -v
```

Résultat attendu : **5 PASSED**.

Vérifier aussi qu'aucun test existant ne régresse :

```
pytest tests/test_insert_if_new.py tests/test_database_helpers.py -v
```

Résultat attendu : tous **PASSED**.

- [ ] **Étape 3.6 : Commit**

```
git add scraper_utils.py
git commit -m "fix(scraper_utils): _INSERT_MAX_AGE_DAYS lit SCRAPER_WINDOW_DAYS (défaut 30j)"
```

```
git add scraper_boamp.py
git commit -m "fix(scraper_boamp): aligner fenêtre par défaut sur 30j (cohérent avec insert)"
```

```
git add tests/test_collect_window.py
git commit -m "test(collect_window): vérifier cohérence fenêtre BOAMP / insert"
```

---

## Task 4 — BOAMP utilise `retry_get()` avec support des headers

**Problème :** `scraper_boamp.py` appelle `requests.get()` directement sans retry. Un timeout réseau interrompt la collecte BOAMP sans re-tentative.

**Fix :** Ajouter un paramètre `headers` à `retry_get()` dans `scraper_utils.py`, puis migrer BOAMP pour l'utiliser.

**Files:**
- Modify: `scraper_utils.py` (ajouter `headers` à `retry_get`)
- Modify: `scraper_boamp.py` (utiliser `retry_get`)
- Create: `tests/test_boamp_retry.py`

---

- [ ] **Étape 4.1 : Écrire le test pour le paramètre `headers` de `retry_get`**

Créer `tests/test_boamp_retry.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
import requests
from scraper_utils import retry_get


def _make_ok_response(json_data: dict) -> MagicMock:
    mock_resp = MagicMock(spec=requests.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_retry_get_passes_headers(monkeypatch):
    """retry_get doit transmettre les headers à requests.get."""
    calls = []

    def fake_get(url, params=None, headers=None, timeout=30):
        calls.append({"url": url, "headers": headers})
        return _make_ok_response({})

    monkeypatch.setattr(requests, "get", fake_get)
    retry_get("https://example.com", headers={"User-Agent": "test-bot/1.0"})
    assert calls[0]["headers"] == {"User-Agent": "test-bot/1.0"}


def test_retry_get_works_without_headers(monkeypatch):
    """retry_get sans headers ne lève pas d'erreur."""
    def fake_get(url, params=None, headers=None, timeout=30):
        return _make_ok_response({})

    monkeypatch.setattr(requests, "get", fake_get)
    resp = retry_get("https://example.com")
    assert resp is not None


def test_retry_get_retries_on_timeout(monkeypatch):
    """retry_get doit réessayer en cas de timeout."""
    attempt = [0]

    def fake_get(url, params=None, headers=None, timeout=30):
        attempt[0] += 1
        if attempt[0] < 2:
            raise requests.exceptions.Timeout()
        return _make_ok_response({})

    monkeypatch.setattr("time.sleep", lambda _: None)
    monkeypatch.setattr(requests, "get", fake_get)
    resp = retry_get("https://example.com", retries=3)
    assert attempt[0] == 2
```

- [ ] **Étape 4.2 : Vérifier que `test_retry_get_passes_headers` échoue**

```
pytest tests/test_boamp_retry.py::test_retry_get_passes_headers -v
```

Résultat attendu : **FAILED** — `retry_get` ne prend pas encore `headers`.

- [ ] **Étape 4.3 : Ajouter le paramètre `headers` à `retry_get` dans `scraper_utils.py`**

Remplacer la signature :

```python
def retry_get(
    url: str,
    *,
    params: dict | None = None,
    timeout: int = 30,
    rate_delay: float = _DEFAULT_RATE_DELAY,
    retries: int = _MAX_RETRIES,
) -> requests.Response:
```

par :

```python
def retry_get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
    rate_delay: float = _DEFAULT_RATE_DELAY,
    retries: int = _MAX_RETRIES,
) -> requests.Response:
```

Et dans le corps, remplacer :

```python
            resp = requests.get(url, params=params, timeout=timeout)
```

par :

```python
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
```

- [ ] **Étape 4.4 : Vérifier que les tests `retry_get` passent**

```
pytest tests/test_boamp_retry.py -v
```

Résultat attendu : **3 PASSED**.

- [ ] **Étape 4.5 : Migrer BOAMP pour utiliser `retry_get`**

Dans `scraper_boamp.py`, en haut du fichier remplacer :

```python
import requests
```

par :

```python
from scraper_utils import retry_get
```

(Retirer l'import `requests` s'il n'est plus utilisé ailleurs dans le fichier.)

Dans `fetch()`, remplacer :

```python
            try:
                resp = requests.get(
                    BOAMP_API_URL, headers=HEADERS, params=params, timeout=15
                )
            except requests.RequestException:
                break
```

par :

```python
            try:
                resp = retry_get(
                    BOAMP_API_URL, headers=HEADERS, params=params, timeout=15
                )
            except Exception:
                break
```

- [ ] **Étape 4.6 : Vérifier les tests existants BOAMP**

```
pytest tests/ -k "boamp" -v
```

Résultat attendu : tous **PASSED**.

- [ ] **Étape 4.7 : Commit**

```
git add scraper_utils.py
git commit -m "feat(scraper_utils): ajouter paramètre headers à retry_get"
```

```
git add scraper_boamp.py
git commit -m "fix(scraper_boamp): utiliser retry_get au lieu de requests.get direct"
```

```
git add tests/test_boamp_retry.py
git commit -m "test(boamp_retry): vérifier headers et retry dans retry_get"
```

---

## Task 5 — `auto_analyze_claude` configurable via `LLM_BATCH_SIZE`

**Problème :** `auto_analyze_claude(max_per_run=10)` est codé en dur. Après une grosse collecte, les analyses Mistral s'étalent sur de nombreux runs.

**Fix :** Lire `LLM_BATCH_SIZE` depuis l'environnement. La valeur par défaut reste 10 pour ne pas surprendre.

**Files:**
- Modify: `llm_analyzer.py`

---

- [ ] **Étape 5.1 : Modifier la valeur par défaut de `max_per_run` dans `llm_analyzer.py`**

Localiser la définition de `auto_analyze_claude` (~ligne 1371) :

```python
def auto_analyze_claude(
    db,
    max_per_run: int = 10,
    delay: float = 1.0,
    progress_cb=None,
) -> tuple[int, int]:
```

Remplacer par :

```python
_LLM_BATCH_SIZE = int(os.getenv("LLM_BATCH_SIZE", "10"))


def auto_analyze_claude(
    db,
    max_per_run: int = _LLM_BATCH_SIZE,
    delay: float = 1.0,
    progress_cb=None,
) -> tuple[int, int]:
```

(`os` est déjà importé en haut du fichier.)

- [ ] **Étape 5.2 : Vérifier que les tests LLM existants passent**

```
pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : tous **PASSED** (la valeur par défaut est identique = 10 si `LLM_BATCH_SIZE` n'est pas défini).

- [ ] **Étape 5.3 : Commit**

```
git add llm_analyzer.py
git commit -m "feat(llm_analyzer): auto_analyze_claude lit LLM_BATCH_SIZE depuis l'env"
```

---

## Task 6 — Aligner `_STRUCTURED_SYSTEM` avec le `SYSTEM_PROMPT` principal

**Problème :** `_STRUCTURED_SYSTEM` (utilisé par `analyze_tender_structured` avec `mistral-small-latest`) ignore les critères géographiques et les exclusions formelles du `SYSTEM_PROMPT` principal. Les deux analyses peuvent donner des verdicts contradictoires.

**Fix :** Enrichir `_STRUCTURED_SYSTEM` avec les zones prioritaires DEF OI et les exclusions. Le champ `recommandation` passe de `"GO" | "NON"` à `"OUI" | "NON"` pour s'aligner.

**Files:**
- Modify: `llm_analyzer.py` (constantes `_STRUCTURED_SYSTEM` et `_STRUCTURED_USER_TPL`)

---

- [ ] **Étape 6.1 : Remplacer `_STRUCTURED_SYSTEM` dans `llm_analyzer.py`**

Localiser (~ligne 1537) :

```python
_STRUCTURED_SYSTEM = (
    "Tu es un expert en marchés publics SSI, CMSI, désenfumage, vidéosurveillance "
    "et courants faibles pour les DOM (La Réunion 974, Mayotte 976). "
    "Tu retournes UNIQUEMENT un objet JSON valide, sans texte avant ni après."
)
```

Remplacer par :

```python
_STRUCTURED_SYSTEM = (
    "Tu es un expert en marchés publics pour DEF Océan Indien, spécialisé en SSI, CMSI, "
    "désenfumage, vidéosurveillance et courants faibles. "
    "ZONE PRIORITAIRE : La Réunion (974) et Mayotte (976). "
    "ZONE SECONDAIRE : Madagascar, Maurice, Comores. "
    "EXCLURE (recommandation=NON) si et seulement si : gardiennage, agents de sécurité, "
    "génie civil pur, VRD, électricité HT/BT seule, plomberie, extincteurs seuls sans SSI. "
    "En cas de doute sur le périmètre technique, préférer OUI. "
    "Tu retournes UNIQUEMENT un objet JSON valide, sans texte avant ni après."
)
```

- [ ] **Étape 6.2 : Aligner le champ `recommandation` dans `_STRUCTURED_USER_TPL`**

Localiser (~ligne 1543) :

```python
_STRUCTURED_USER_TPL = """Analyse ce marché et retourne ce JSON strict :

{{
  ...
  "recommandation": "GO" | "NON",
  ...
}}
```

Remplacer la ligne `"recommandation"` par :

```python
  "recommandation": "OUI" | "NON",
```

- [ ] **Étape 6.3 : Vérifier que les tests LLM existants passent**

```
pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : tous **PASSED**.

- [ ] **Étape 6.4 : Commit**

```
git add llm_analyzer.py
git commit -m "fix(llm_analyzer): aligner _STRUCTURED_SYSTEM avec SYSTEM_PROMPT (zones, exclusions, OUI/NON)"
```

---

## Vérification finale

- [ ] **Lancer la suite complète**

```
pytest -x
```

Résultat attendu : tous **PASSED**, aucune régression.

- [ ] **Vérifier les logs de collecte**

Démarrer le backend et déclencher une collecte via `/api/collect`. Vérifier dans les logs :
- Les tenders sans date apparaissent avec `WARNING insert_if_new: rejeté (date manquante) — id=...`
- La réponse JSON contient `nb_rejected_no_date` par source.
- BOAMP ne cherche plus sur 90 jours (vérifier en lisant les `params` loggués).

---

## Récapitulatif des corrections

| Ticket | Sévérité | Fix | Fichier(s) |
|---|---|---|---|
| Perte silencieuse sur date manquante | 🔴 CRITIQUE | Log WARNING + compteur API | `scraper_utils.py`, `backend/main.py` |
| Fenêtre 90j vs 30j incohérente | 🟡 | Variable env unique `SCRAPER_WINDOW_DAYS` (défaut 30) | `scraper_utils.py`, `scraper_boamp.py` |
| BOAMP sans retry réseau | 🟡 | Migrer vers `retry_get()` | `scraper_utils.py`, `scraper_boamp.py` |
| Limite LLM fixe à 10 | 🟡 | `LLM_BATCH_SIZE` env-driven | `llm_analyzer.py` |
| Deux prompts incohérents | 🟡 | Aligner `_STRUCTURED_SYSTEM` | `llm_analyzer.py` |
