# Sprint 2 — Qualité & Robustesse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Améliorer les filtres (exclusion contextuelle), la robustesse réseau (retry DECP), les logs de supervision (source_registry), la précision du scoring adaptatif (decay temporel), et l'extraction CPV (BOAMP).

**Architecture:** 6 tâches indépendantes touchant chacune un module isolé. TDD strict : test rouge → implémentation minimale → test vert → commit. Un commit par fichier modifié.

**Tech Stack:** Python 3.11, pytest, `unittest.mock` / `monkeypatch`, `caplog` (fixture pytest), SQLAlchemy in-memory SQLite, `collections.Counter`

---

## File Map

| Fichier | Tâches | Ce qui change |
|---|---|---|
| `filters.py:310-345` | T1 | Inverser l'ordre inclusion/exclusion dans `classify_relevance()` |
| `tests/test_filters.py` | T1 | 3 nouveaux tests, 2 tests mis à jour |
| `scraper_decp.py:9,112` | T2 | Remplacer `requests.get` par `retry_get` |
| `tests/test_decp_retry.py` (nouveau) | T2 | Test d'appel à `retry_get` |
| `source_registry.py:424-445` | T3+T4 | Logger + logs error/info dans `_ping_source()` |
| `tests/test_ping.py` | T3+T4 | 2 nouveaux tests caplog |
| `score_adaptive.py:54-100` | T5 | Nouvelle fonction `_age_weight()` + counters pondérés |
| `tests/test_score_adaptive.py` | T5 | 3 nouveaux tests unitaires + 1 intégration |
| `scraper_boamp.py:130-173` | T6 | Ajouter champ `cpv` dans `_normalise()` |
| `tests/test_boamp_cpv.py` (nouveau) | T6 | 3 tests sur `_normalise()` |

---

## Task 1: Exclusion contextuelle dans filters.py

**Files:**
- Modify: `filters.py:310-345`
- Modify: `tests/test_filters.py`

**Contexte:** Actuellement `classify_relevance()` vérifie les exclusions EN PREMIER. Un marché "gardiennage + SSI" est donc bloqué. La nouvelle règle : si un mot d'inclusion SSI/CMSI/vidéo est présent dans le texte, les exclusions ne s'appliquent pas.

### Étape 1.1 — Écrire les tests qui échouent

Ouvrir `tests/test_filters.py`. Ajouter à la fin du fichier (après le dernier test) :

```python
# ── Sprint 2 : exclusion contextuelle ────────────────────────────────────────


def test_classify_inclusion_overrides_exclusion():
    """Un mot SSI direct dans le texte doit primer sur un mot d'exclusion."""
    ok, tags = classify_relevance("Marché de gardiennage et SSI pour la mairie")
    assert ok is True
    assert tags == []


def test_classify_pure_exclusion_without_inclusion_still_blocked():
    """Sans mot d'inclusion direct, le mot d'exclusion doit toujours bloquer."""
    ok, tags = classify_relevance("Marché de gardiennage pour la mairie")
    assert ok is False
    assert tags == []


def test_classify_cctv_overrides_agents_securite():
    """CCTV présent → pertinent, même si 'agents de sécurité' dans le texte."""
    ok, tags = classify_relevance(
        "Fourniture et installation CCTV — lot agents de sécurité inclus"
    )
    assert ok is True
```

- [ ] **Step 1.1 : Ajouter les 3 nouveaux tests dans `tests/test_filters.py`**

- [ ] **Step 1.2 : Vérifier qu'ils échouent**

```
pytest tests/test_filters.py::test_classify_inclusion_overrides_exclusion tests/test_filters.py::test_classify_cctv_overrides_agents_securite -v
```

Expected : FAILED (le code actuel vérifie les exclusions avant les inclusions)

### Étape 1.3 — Mettre à jour les 2 tests qui reflètent l'ancien comportement

Dans `tests/test_filters.py`, localiser et modifier :

**Test ligne ~108** (`test_prive_exclusion_gardiennage`) :
```python
# AVANT
def test_prive_exclusion_gardiennage():
    """Exclusion absolue gardiennage → NON pertinent même avec SSI."""
    assert is_prive_relevant("Marché de gardiennage et SSI pour la mairie") is False

# APRÈS
def test_prive_exclusion_gardiennage():
    """SSI présent → pertinent, même si 'gardiennage' dans le texte."""
    assert is_prive_relevant("Marché de gardiennage et SSI pour la mairie") is True
```

**Test ligne ~246** (`test_classify_exclusion_gardiennage_retourne_false`) :
```python
# AVANT
def test_classify_exclusion_gardiennage_retourne_false():
    ok, tags = classify_relevance("Marché de gardiennage et SSI pour la mairie")
    assert ok is False
    assert tags == []

# APRÈS
def test_classify_exclusion_gardiennage_retourne_false():
    # SSI inclusion overrides gardiennage exclusion (nouvelle règle Sprint 2)
    ok, tags = classify_relevance("Marché de gardiennage et SSI pour la mairie")
    assert ok is True
```

- [ ] **Step 1.3 : Mettre à jour les 2 anciens tests dans `tests/test_filters.py`**

### Étape 1.4 — Implémenter la nouvelle logique dans `filters.py`

Dans `filters.py`, remplacer `classify_relevance()` (lignes 310-345) par :

```python
def classify_relevance(text: str) -> tuple[bool, list[str]]:
    """Retourne (pertinent, tags).

    tags contient ["Potentiel SSI implicite"] quand la capture est via
    la logique construction+ERP, sans mot-clé DEF OI direct.

    Règle d'exclusion contextuelle : un mot d'exclusion ne s'applique QUE si
    aucun mot d'inclusion direct (SSI/CMSI/vidéo/courants faibles) n'est présent.
    """
    text_lower = text.lower()

    # Vérifier les inclusions en premier — un match direct annule toute exclusion
    for kw in INCLUSION_KEYWORDS:
        if kw in _WORD_BOUNDARY_KW:
            if _COMPILED_BOUNDARY[kw].search(text_lower):
                return True, []
        elif kw in text_lower:
            return True, []

    # Exclusions : seulement si aucun mot d'inclusion direct trouvé
    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False, []

    has_chantier = any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
    has_erp = any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)

    # Logique assouplie : construction seule = potentiel SSI pour ERP publics
    if has_chantier:
        if has_erp:
            return True, ["Potentiel SSI implicite"]
        # Ajout : tout projet de construction dans 974/976 est potentiellement pertinent
        if (
            "974" in text_lower
            or "976" in text_lower
            or "réunion" in text_lower
            or "mayotte" in text_lower
        ):
            return True, ["Potentiel SSI implicite"]

    return False, []
```

- [ ] **Step 1.4 : Modifier `classify_relevance()` dans `filters.py`**

- [ ] **Step 1.5 : Vérifier que tous les tests passent**

```
pytest tests/test_filters.py -v
```

Expected : tous verts (0 failures)

- [ ] **Step 1.6 : Commit**

```
git add filters.py
git commit -m "feat(filters): exclusion contextuelle — inclusion SSI prime sur exclusion"

git add tests/test_filters.py
git commit -m "test(filters): exclusion contextuelle — 3 nouveaux tests + 2 mis à jour"
```

---

## Task 2: Retry réseau dans scraper_decp.py

**Files:**
- Modify: `scraper_decp.py:9,112`
- Create: `tests/test_decp_retry.py`

**Contexte:** `scraper_decp.py` appelle `requests.get()` directement (ligne 112) sans retry. La fonction `retry_get()` de `scraper_utils` offre déjà le backoff exponentiel et la gestion 429. VAAO et Nukema utilisent Playwright exclusivement — pas de `requests.get` — donc pas de changement nécessaire pour eux.

### Étape 2.1 — Écrire le test qui échoue

Créer `tests/test_decp_retry.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import MagicMock


def _mock_empty_response():
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = {"results": []}
    m.raise_for_status.return_value = None
    return m


def test_decp_fetch_uses_retry_get(monkeypatch):
    """scraper_decp.fetch() doit appeler retry_get, pas requests.get directement."""
    import scraper_decp

    calls = []

    def fake_retry_get(url, **kwargs):
        calls.append(url)
        return _mock_empty_response()

    monkeypatch.setattr(scraper_decp, "retry_get", fake_retry_get)
    result = scraper_decp.fetch()

    assert len(calls) > 0, "retry_get n'a pas été appelé"
    assert result == []


def test_decp_fetch_breaks_on_retry_exception(monkeypatch):
    """Si retry_get lève RequestException, fetch() doit s'arrêter sans lever."""
    import requests
    import scraper_decp

    def fake_retry_get(url, **kwargs):
        raise requests.exceptions.ConnectionError("réseau KO")

    monkeypatch.setattr(scraper_decp, "retry_get", fake_retry_get)
    result = scraper_decp.fetch()

    assert result == []
```

- [ ] **Step 2.1 : Créer `tests/test_decp_retry.py`**

- [ ] **Step 2.2 : Vérifier que les tests échouent**

```
pytest tests/test_decp_retry.py -v
```

Expected : FAILED — `module 'scraper_decp' has no attribute 'retry_get'`

### Étape 2.3 — Implémenter le changement dans `scraper_decp.py`

**Ligne 9** — remplacer :
```python
import requests
```
par :
```python
import requests
from scraper_utils import retry_get
```

**Lignes 111-113** — remplacer :
```python
        try:
            resp = requests.get(DECP_API, headers=HEADERS, params=params, timeout=15)
        except requests.RequestException:
            break
```
par :
```python
        try:
            resp = retry_get(DECP_API, headers=HEADERS, params=params, timeout=15)
        except requests.RequestException:
            break
```

- [ ] **Step 2.3 : Modifier `scraper_decp.py` (import + appel)**

- [ ] **Step 2.4 : Vérifier que les tests passent**

```
pytest tests/test_decp_retry.py -v
```

Expected : PASSED (2 tests)

- [ ] **Step 2.5 : Vérifier qu'aucun test existant n'est cassé**

```
pytest tests/test_decp_deadline.py -v
```

Expected : PASSED

- [ ] **Step 2.6 : Commit**

```
git add scraper_decp.py
git commit -m "feat(scraper): decp — remplacer requests.get par retry_get avec backoff"

git add tests/test_decp_retry.py
git commit -m "test(scraper): decp — vérifier l'utilisation de retry_get"
```

---

## Task 3 & 4: Logs alerte + réinitialisation dans source_registry.py

**Files:**
- Modify: `source_registry.py:1-5,424-445`
- Modify: `tests/test_ping.py`

**Contexte :**
- **T3** : quand `ping_failures_count >= 3` et `is_validated` passe à False, émettre `_log.error(...)`.
- **T4** : quand ping réussit et que la source était `is_validated=False`, remettre `is_validated=True` et émettre `_log.info(...)`.

### Étape 3.1 — Écrire les tests qui échouent

Ouvrir `tests/test_ping.py`. Ajouter en tête de fichier :
```python
import logging
```

Ajouter à la fin du fichier :

```python
def test_ping_logs_error_when_source_disabled(db, monkeypatch, caplog):
    """_ping_source doit logguer ERROR quand la source passe à is_validated=False."""
    from source_registry import _ping_source, Source

    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 2
    source.is_validated = True
    db.commit()

    with monkeypatch.context() as m:
        import source_registry
        m.setattr(
            source_registry.requests,
            "get",
            lambda *a, **kw: (_ for _ in ()).throw(Exception("timeout")),
        )
        with caplog.at_level(logging.ERROR, logger="source_registry"):
            _ping_source(db, source)

    assert source.ping_failures_count == 3
    assert source.is_validated is False
    assert "Test Source" in caplog.text


def test_ping_logs_info_and_restores_on_recovery(db, monkeypatch, caplog):
    """_ping_source doit logguer INFO et remettre is_validated=True si la source récupère."""
    from source_registry import _ping_source, Source

    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 3
    source.is_validated = False
    db.commit()

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with monkeypatch.context() as m:
        import source_registry
        m.setattr(source_registry.requests, "get", lambda *a, **kw: mock_resp)
        with caplog.at_level(logging.INFO, logger="source_registry"):
            result = _ping_source(db, source)

    assert result is True
    assert source.is_validated is True
    assert source.ping_failures_count == 0
    assert "Test Source" in caplog.text
```

Note : le test_ping.py utilise déjà `MagicMock` — l'import existe déjà en tête de fichier.

- [ ] **Step 3.1 : Ajouter `import logging` et les 2 nouveaux tests dans `tests/test_ping.py`**

- [ ] **Step 3.2 : Vérifier que les tests échouent**

```
pytest tests/test_ping.py::test_ping_logs_error_when_source_disabled tests/test_ping.py::test_ping_logs_info_and_restores_on_recovery -v
```

Expected : FAILED (pas de logging dans `_ping_source`, pas de restauration `is_validated`)

### Étape 3.3 — Implémenter les logs dans `source_registry.py`

**En tête du fichier** (après les imports existants, ligne 4) — ajouter :
```python
import logging
_log = logging.getLogger(__name__)
```

**Fonction `_ping_source()`** — remplacer le corps actuel (lignes 424-445) par :

```python
def _ping_source(db, source) -> bool:
    try:
        resp = requests.get(
            source.url,
            timeout=8,
            allow_redirects=True,
            headers={"User-Agent": "DEF-OI-Monitor/1.0"},
        )
        ok = resp.status_code < 400
    except Exception:
        ok = False

    if ok:
        if (source.ping_failures_count or 0) >= 3 and not source.is_validated:
            source.is_validated = True
            _log.info(
                "Source réactivée après récupération : %s (%s)",
                source.name,
                source.url,
            )
        source.ping_failures_count = 0
    else:
        source.ping_failures_count = (source.ping_failures_count or 0) + 1
        if source.ping_failures_count >= 3:
            source.is_validated = False
            _log.error(
                "Source désactivée après %d échecs consécutifs : %s (%s)",
                source.ping_failures_count,
                source.name,
                source.url,
            )

    source.last_ping_at = _dt_src.now(_tz_src.utc).replace(tzinfo=None)
    db.commit()
    return ok
```

- [ ] **Step 3.3 : Ajouter `import logging` + `_log` + modifier `_ping_source()` dans `source_registry.py`**

- [ ] **Step 3.4 : Vérifier que tous les tests ping passent**

```
pytest tests/test_ping.py -v
```

Expected : PASSED (tous les tests, anciens + nouveaux)

- [ ] **Step 3.5 : Commit**

```
git add source_registry.py
git commit -m "feat(registry): log ERROR désactivation source + INFO réactivation"

git add tests/test_ping.py
git commit -m "test(registry): log alerte désactivation + log info réactivation source"
```

---

## Task 5: Decay temporel dans score_adaptive.py

**Files:**
- Modify: `score_adaptive.py:1-5,54-100`
- Modify: `tests/test_score_adaptive.py`

**Contexte:** Les décisions GO/NOGO de plus de 180 jours doivent peser 50 % moins dans le calcul des poids. Le champ `date_extraction` (DateTime) du modèle `Tender` donne la date de collecte, utilisée comme proxy de la date de décision.

### Étape 5.1 — Écrire les tests unitaires qui échouent

Ouvrir `tests/test_score_adaptive.py`. Ajouter à la fin :

```python
# ── Sprint 2 : decay temporel ─────────────────────────────────────────────────


def test_age_weight_recent_returns_one():
    """Un tender collecté il y a 30 jours → poids 1.0."""
    from score_adaptive import _age_weight
    from datetime import datetime, timedelta

    class FakeTender:
        date_extraction = datetime.utcnow() - timedelta(days=30)

    assert _age_weight(FakeTender()) == 1.0


def test_age_weight_old_returns_half():
    """Un tender collecté il y a 200 jours → poids 0.5."""
    from score_adaptive import _age_weight
    from datetime import datetime, timedelta

    class FakeTender:
        date_extraction = datetime.utcnow() - timedelta(days=200)

    assert _age_weight(FakeTender()) == 0.5


def test_age_weight_boundary_180_days():
    """Exactement 180 jours → encore récent (poids 1.0) ; 181 jours → vieux (0.5)."""
    from score_adaptive import _age_weight
    from datetime import datetime, timedelta

    class FakeTender:
        pass

    t180 = FakeTender()
    t180.date_extraction = datetime.utcnow() - timedelta(days=180)
    assert _age_weight(t180) == 1.0

    t181 = FakeTender()
    t181.date_extraction = datetime.utcnow() - timedelta(days=181)
    assert _age_weight(t181) == 0.5


def test_age_weight_none_date_returns_one():
    """date_extraction absente → poids neutre 1.0."""
    from score_adaptive import _age_weight

    class FakeTender:
        date_extraction = None

    assert _age_weight(FakeTender()) == 1.0


def test_decay_old_decisions_still_produce_valid_score(db, make_tender):
    """Avec uniquement des décisions > 180 jours, recompute fonctionne toujours."""
    from score_adaptive import recompute_adaptive_scores
    from datetime import datetime, timedelta

    old_date = datetime.utcnow() - timedelta(days=200)
    for i in range(8):
        t = make_tender(
            status="Gagné",
            title=f"SSI ERP installation {i}",
            description="détection incendie SSI CMSI",
        )
        t.date_extraction = old_date
    for i in range(2):
        t = make_tender(
            status="Perdu",
            title=f"nettoyage jardinage {i}",
            description="espaces verts entretien",
        )
        t.date_extraction = old_date
    db.flush()

    undecided = make_tender(
        status="À qualifier",
        title="Installation SSI ERP",
        description="détection incendie",
    )
    nb = recompute_adaptive_scores(db)
    assert nb >= 1
    db.refresh(undecided)
    assert undecided.adaptive_score is not None
    assert 0 <= undecided.adaptive_score <= 100
```

- [ ] **Step 5.1 : Ajouter les 5 nouveaux tests dans `tests/test_score_adaptive.py`**

- [ ] **Step 5.2 : Vérifier que les tests unitaires échouent**

```
pytest tests/test_score_adaptive.py::test_age_weight_recent_returns_one tests/test_score_adaptive.py::test_age_weight_old_returns_half -v
```

Expected : FAILED — `ImportError: cannot import name '_age_weight' from 'score_adaptive'`

### Étape 5.3 — Implémenter le decay dans `score_adaptive.py`

**Après les imports existants** (ligne 3, après `from datetime import datetime`), ajouter l'import `timedelta` :
```python
from datetime import datetime, timedelta
```

**Après `_STOP_WORDS`** (vers ligne 57, avant `_tokenize`), ajouter :
```python
def _age_weight(tender) -> float:
    """Retourne 0.5 pour les tenders collectés > 180 jours, 1.0 sinon."""
    dt = getattr(tender, "date_extraction", None)
    if dt is None:
        return 1.0
    days_old = (datetime.utcnow() - dt).days
    return 0.5 if days_old > 180 else 1.0
```

**Dans `recompute_adaptive_scores()`** — remplacer les deux blocs counter (lignes 92-98) :

```python
        # AVANT
        pos_counter: Counter = Counter()
        for t in pos_tenders:
            pos_counter.update(_tokenize((t.title or "") + " " + (t.description or "")))

        neg_counter: Counter = Counter()
        for t in neg_tenders:
            neg_counter.update(_tokenize((t.title or "") + " " + (t.description or "")))
```

par :

```python
        pos_counter: Counter = Counter()
        for t in pos_tenders:
            w = _age_weight(t)
            for token in _tokenize((t.title or "") + " " + (t.description or "")):
                pos_counter[token] += w

        neg_counter: Counter = Counter()
        for t in neg_tenders:
            w = _age_weight(t)
            for token in _tokenize((t.title or "") + " " + (t.description or "")):
                neg_counter[token] += w
```

- [ ] **Step 5.3 : Modifier `score_adaptive.py` (import timedelta + `_age_weight` + counters pondérés)**

- [ ] **Step 5.4 : Vérifier que tous les tests score_adaptive passent**

```
pytest tests/test_score_adaptive.py -v
```

Expected : PASSED (tous, anciens + nouveaux)

- [ ] **Step 5.5 : Commit**

```
git add score_adaptive.py
git commit -m "feat(scoring): decay temporel — decisions > 180j pesent 50%"

git add tests/test_score_adaptive.py
git commit -m "test(scoring): decay temporel — _age_weight + integration"
```

---

## Task 6: Extraction CPV BOAMP dans scraper_boamp.py

**Files:**
- Modify: `scraper_boamp.py:130-173`
- Create: `tests/test_boamp_cpv.py`

**Contexte:** `_normalise()` construit déjà `description` depuis `descripteur_libelle` (liste de libellés CPV). Il faut ajouter la clé `cpv` (string joinée par virgule) dans le dict retourné.

### Étape 6.1 — Écrire les tests qui échouent

Créer `tests/test_boamp_cpv.py` :

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_boamp import _normalise


def test_normalise_cpv_joined_from_descripteur_libelle():
    """descripteur_libelle liste → cpv = valeurs jointes par ', '."""
    raw = {
        "idweb": "AO-2026-001",
        "objet": "Maintenance SSI",
        "dateparution": "2026-01-15",
        "datelimitereponse": "2026-02-15",
        "descripteur_libelle": ["45312100", "Systèmes d'alarme incendie"],
        "url_avis": "",
    }
    result = _normalise(raw, "974")
    assert "cpv" in result
    assert result["cpv"] == "45312100, Systèmes d'alarme incendie"


def test_normalise_cpv_empty_when_no_descripteurs():
    """descripteur_libelle absent → cpv = ''."""
    raw = {
        "idweb": "AO-2026-002",
        "objet": "Construction bâtiment",
        "dateparution": "2026-01-15",
    }
    result = _normalise(raw, "974")
    assert "cpv" in result
    assert result["cpv"] == ""


def test_normalise_cpv_string_input_passthrough():
    """descripteur_libelle string (incohérence API) → cpv = la string telle quelle."""
    raw = {
        "idweb": "AO-2026-003",
        "objet": "Test",
        "dateparution": "2026-01-15",
        "descripteur_libelle": "45312100",
    }
    result = _normalise(raw, "974")
    assert result["cpv"] == "45312100"
```

- [ ] **Step 6.1 : Créer `tests/test_boamp_cpv.py`**

- [ ] **Step 6.2 : Vérifier que les tests échouent**

```
pytest tests/test_boamp_cpv.py -v
```

Expected : FAILED — `KeyError: 'cpv'`

### Étape 6.3 — Implémenter l'extraction CPV dans `scraper_boamp.py`

Dans `_normalise()` (ligne 138-143), remplacer :
```python
    descripteurs = raw.get("descripteur_libelle") or []
    description = (
        " ".join(descripteurs) if isinstance(descripteurs, list) else str(descripteurs)
    )
```
par :
```python
    descripteurs = raw.get("descripteur_libelle") or []
    cpv = (
        ", ".join(descripteurs)
        if isinstance(descripteurs, list)
        else str(descripteurs or "")
    )
    description = cpv
```

Dans le `return` de `_normalise()` (vers ligne 163), ajouter la clé `cpv` :
```python
    return {
        "name": raw.get("objet") or f"Marché BOAMP {idweb}",
        "url": url,
        "source": "BOAMP",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "departement": dept,
        "description": description,
        "boamp_id": idweb,
        "cpv": cpv,
    }
```

- [ ] **Step 6.3 : Modifier `_normalise()` dans `scraper_boamp.py`**

- [ ] **Step 6.4 : Vérifier que les tests passent**

```
pytest tests/test_boamp_cpv.py -v
```

Expected : PASSED (3 tests)

- [ ] **Step 6.5 : Commit**

```
git add scraper_boamp.py
git commit -m "feat(scraper): boamp — extraction champ cpv depuis descripteur_libelle"

git add tests/test_boamp_cpv.py
git commit -m "test(scraper): boamp — cpv extrait de descripteur_libelle"
```

---

## Validation finale

- [ ] **Lancer la suite complète**

```
pytest tests/ -q
```

Expected : 0 failures. Le compte total de tests doit être supérieur à 329 (baseline Sprint 1).

- [ ] **Vérifier le décompte**

```
pytest tests/ -q --tb=no | tail -3
```

Si des tests échouent, indiquer lesquels et pourquoi avant de continuer.

---

## Self-Review

### Couverture spec
| Tâche spec | Tâche plan | Couverte ? |
|---|---|---|
| Exclusion contextuelle filters.py | Task 1 | ✅ |
| Retry réseau scraper_decp.py | Task 2 | ✅ |
| VAAO/Nukema: pas de requests.get (Playwright) | Documenté Task 2 | ✅ |
| Log ERROR désactivation source | Task 3 | ✅ |
| Log INFO + restore is_validated | Task 4 | ✅ |
| Decay 180j score_adaptive | Task 5 | ✅ |
| CPV BOAMP | Task 6 | ✅ |

### Placeholders
Aucun TBD, TODO ou "implement later" dans ce plan.

### Cohérence des types
- `_age_weight(tender) -> float` : défini Task 5 étape 5.3, utilisé dans les counters de la même tâche.
- `_log` : `logging.Logger` ajouté Task 3 step 3.3, utilisé dans `_ping_source()` de la même tâche.
- `retry_get` : importé depuis `scraper_utils` en Task 2 step 2.3, patché par `monkeypatch.setattr(scraper_decp, "retry_get", ...)` dans les tests.
- Champ `cpv` : `str`, ajouté dans `_normalise()` Task 6 step 6.3, testé avec `assert result["cpv"] == ...`.
