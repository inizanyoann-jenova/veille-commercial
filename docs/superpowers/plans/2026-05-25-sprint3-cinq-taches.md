# Sprint 3 — 5 Tâches Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rendre la collecte asynchrone, alerter par email les marchés GO ≥ 80, afficher les stats scrapers, paginer la table, remplacer la détection de doublons par SimHash.

**Architecture:** Chaque tâche est indépendante et peut être exécutée séparément. Le backend reçoit le gros des changements (tasks 1, 2, 3, 5), le frontend les tasks 1, 3, 4. Pas de nouvelle table DB ni migration — seule database.py est enrichie de nouvelles fonctions.

**Tech Stack:** FastAPI + BackgroundTasks, SQLite/SQLAlchemy, React 19 + TanStack Query, Vitest + Testing Library, Python pur (SimHash).

---

## Règles projet

- **Un commit par fichier modifié** (voir CLAUDE.md)
- **TDD** : test échoue → implémenter → test passe
- `pytest tests/ -q` doit rester à 0 échec après chaque tâche
- Plans dans `docs/superpowers/plans/`

---

## Cartographie des fichiers

| Tâche | Fichiers modifiés | Nouveaux fichiers |
|-------|-------------------|-------------------|
| 1 — Async collect | `backend/main.py`, `frontend/src/services/api.js`, `frontend/src/hooks/useTenders.js`, `frontend/src/components/Sidebar.jsx` | `tests/test_collect_async.py` |
| 2 — Email GO ≥ 80 | `email_digest.py`, `backend/main.py` | `tests/test_go_alert.py` |
| 3 — Stats scrapers | `database.py`, `backend/main.py`, `frontend/src/services/api.js`, `frontend/src/hooks/useTenders.js`, `frontend/src/pages/Parametres.jsx` | `tests/test_scraper_stats.py` |
| 4 — Pagination | `frontend/src/components/TendersTable.jsx` | `frontend/src/components/TendersTable.test.jsx` |
| 5 — SimHash | `database.py` | `tests/test_simhash.py` |

---

## Task 1 : /api/collect asynchrone

**Principe :** `POST /api/collect` retourne immédiatement `{"job_id": "...", "status": "running"}`. La collecte tourne en `BackgroundTasks`. Un dict Python `_COLLECT_JOBS` stocke l'état. `GET /api/collect/status/{job_id}` expose l'état. Le frontend remplace le polling bloquant par un polling React Query toutes les 3 s.

**Fichiers :**
- Modifier : `backend/main.py:1084-1223` (endpoint collect + nouveau endpoint status + dict jobs)
- Modifier : `frontend/src/services/api.js:58-59` (collect + getCollectStatus)
- Modifier : `frontend/src/hooks/useTenders.js:64-74` (useCollectMutation avec polling)
- Modifier : `frontend/src/components/Sidebar.jsx:127-131` (adapt collectResult format)
- Créer : `tests/test_collect_async.py`

---

### Task 1 — Step 1 : Écrire les tests du status endpoint

- [ ] **Step 1.1 : Créer `tests/test_collect_async.py`**

```python
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from main import app
    return TestClient(app)


def test_collect_status_unknown_job(client):
    r = client.get("/api/collect/status/nonexistent-id")
    assert r.status_code == 404
    assert r.json()["detail"] == "Job inconnu"


def test_collect_status_known_job(client):
    from main import _COLLECT_JOBS
    _COLLECT_JOBS["test-job-123"] = {
        "status": "done",
        "results": [{"source": "boamp", "status": "ok", "nb_found": 5, "nb_new": 2}],
    }
    r = client.get("/api/collect/status/test-job-123")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "done"
    assert len(data["results"]) == 1
    assert data["results"][0]["nb_new"] == 2
    del _COLLECT_JOBS["test-job-123"]
```

- [ ] **Step 1.2 : Vérifier que le test échoue**

```powershell
cd backend
pytest ..\tests\test_collect_async.py -v
```

Résultat attendu : `FAILED` — `ImportError: cannot import name '_COLLECT_JOBS'` ou `404 route not found`.

---

### Task 1 — Step 2 : Implémenter le backend async

- [ ] **Step 2.1 : Modifier `backend/main.py`**

Ajouter en haut du fichier, après les imports (après la ligne `import hashlib`):

```python
import uuid as _uuid
```

Ajouter après la définition `_log = logging.getLogger(__name__)` (ligne ~66):

```python
# ── Jobs de collecte asynchrone ───────────────────────────────────────────────
_COLLECT_JOBS: dict[str, dict] = {}
```

Remplacer entièrement `@app.post("/api/collect", ...)` (lignes 1084-1223) par :

```python
@app.post("/api/collect", status_code=202, summary="Lancer la collecte (asynchrone)")
def collect(body: CollectRequest, background_tasks: BackgroundTasks):
    """
    Lance les scrapers en arrière-plan et retourne immédiatement un job_id.
    Interroger GET /api/collect/status/{job_id} pour suivre l'état.
    """
    job_id = str(_uuid.uuid4())
    _COLLECT_JOBS[job_id] = {"status": "running", "results": []}
    background_tasks.add_task(_run_collect_job, job_id, body.source_names)
    return {"job_id": job_id, "status": "running"}


@app.get("/api/collect/status/{job_id}", summary="État d'un job de collecte")
def collect_status(job_id: str):
    job = _COLLECT_JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job inconnu")
    return job


def _run_collect_job(job_id: str, source_names: Optional[list[str]]) -> None:
    """Tâche background : exécute les scrapers et met à jour _COLLECT_JOBS."""
    db = SessionLocal()
    try:
        sources = list_sources(db)
        if source_names:
            sources = [s for s in sources if s.name in source_names]
        sources = [
            s for s in sources
            if not s.is_manual and s.scraper_module and s.enabled and s.is_validated
        ]
    finally:
        db.close()

    if not sources:
        _COLLECT_JOBS[job_id] = {
            "status": "error",
            "results": [],
            "error": "Aucune source active et validée trouvée",
        }
        return

    pre_db = SessionLocal()
    try:
        known_ids: set = load_existing_ids(pre_db)
    finally:
        pre_db.close()

    results: list[dict] = []

    for source in sources:
        run_id = None
        run_db = SessionLocal()
        try:
            run_id = start_scraper_run(run_db, source.name)
        finally:
            run_db.close()

        try:
            mod = importlib.import_module(source.scraper_module)
            func = getattr(mod, source.scraper_func)
            items: list[dict] = func() or []
            nb_found = len(items)
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
                insert_db.commit()
                finish_scraper_run(insert_db, run_id, nb_found=nb_found, nb_new=nb_new)
            except Exception:
                insert_db.rollback()
                raise
            finally:
                insert_db.close()
            results.append({
                "source": source.name,
                "status": "ok",
                "nb_found": nb_found,
                "nb_new": nb_new,
                "nb_rejected_no_date": nb_rejected_no_date,
            })

        except Exception as exc:
            _log.critical(
                "SCRAPER FAILURE [%s] — %s: %s",
                source.name, type(exc).__name__, exc, exc_info=True,
            )
            if run_id is not None:
                err_db = SessionLocal()
                try:
                    finish_scraper_run(err_db, run_id, nb_found=0, nb_new=0, error=str(exc))
                finally:
                    err_db.close()
            results.append({"source": source.name, "status": "error", "error": type(exc).__name__})

    # Analyse automatique post-collecte (Task 2 — alertes GO ≥ 80 ajoutées ici)
    analysis_db = None
    try:
        analysis_db = SessionLocal()
        auto_analyze_pending(analysis_db)
        auto_analyze_claude(analysis_db, max_per_run=9999)
    except Exception as exc:
        _log.warning("Analyse post-collecte échouée : %s", exc, exc_info=True)
    finally:
        if analysis_db is not None:
            analysis_db.close()

    nb_ok = sum(1 for r in results if r["status"] == "ok")
    nb_err = sum(1 for r in results if r["status"] == "error")
    final_status = "error" if nb_ok == 0 and nb_err > 0 else "partial" if nb_err > 0 else "done"

    _COLLECT_JOBS[job_id] = {
        "status": final_status,
        "nb_ok": nb_ok,
        "nb_error": nb_err,
        "results": results,
    }
```

- [ ] **Step 2.2 : Vérifier que les tests passent**

```powershell
cd backend
pytest ..\tests\test_collect_async.py -v
```

Résultat attendu : `2 passed`.

- [ ] **Step 2.3 : Vérifier toute la suite pytest**

```powershell
pytest tests/ -q
```

Résultat attendu : `0 failed`.

- [ ] **Step 2.4 : Committer `backend/main.py`**

```powershell
git add backend/main.py
git commit -m "feat(collect): collecte asynchrone — job_id + GET /api/collect/status/{job_id}"
```

- [ ] **Step 2.5 : Committer `tests/test_collect_async.py`**

```powershell
git add tests/test_collect_async.py
git commit -m "test(collect): status endpoint — job inconnu 404, job connu 200"
```

---

### Task 1 — Step 3 : Adapter le frontend

- [ ] **Step 3.1 : Modifier `frontend/src/services/api.js`**

Remplacer la ligne `collect` :

```js
// Avant (ligne 58-59):
export const collect = (source_names = null) =>
  api.post('/collect', { source_names }).then((r) => r.data)

// Après:
export const collect = (source_names = null) =>
  api.post('/collect', { source_names }).then((r) => r.data)

export const getCollectStatus = (job_id) =>
  api.get(`/collect/status/${job_id}`).then((r) => r.data)
```

(Garder la ligne `collect` identique, ajouter `getCollectStatus` juste après.)

- [ ] **Step 3.2 : Committer `frontend/src/services/api.js`**

```powershell
git add frontend/src/services/api.js
git commit -m "feat(api): getCollectStatus — poll GET /api/collect/status/{job_id}"
```

- [ ] **Step 3.3 : Modifier `frontend/src/hooks/useTenders.js`**

En haut du fichier, ajouter `useState, useEffect` aux imports React et `getCollectStatus` :

```js
// Ligne 1 — ajouter useState et useEffect:
import { useQuery, useMutation, useQueryClient, useState, useEffect } from '@tanstack/react-query'
// Note: useState et useEffect viennent de 'react', pas de tanstack
```

Correction — les bons imports :

```js
// Ligne 1 existante:
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
// Ajouter après la ligne 1:
import { useState, useEffect } from 'react'
```

Ajouter `getCollectStatus` dans l'import des services (ligne 2-12) :

```js
import {
  getTenders, getTender, getKpisPublic, getKpisCa, getKpisPriv,
  getPipeline, getUrgences, getScraperRuns, getSources, getChartData,
  collect, analyzePending, updateStatus, updateSaved, updateNotes,
  updateTags, updateAmount, deleteTender, analyzeTender,
  getDuplicates, resolveDuplicate, detectDuplicates, archiveOld, resetDb,
  getCredentials, saveCredential, deleteCredential, testCredential,
  saveMistralKey,
  getMistralStatus,
  generateScraper, deleteSource,
  getCollectStatus,          // ← ajouter cette ligne
} from '../services/api'
```

Remplacer `useCollectMutation` (lignes 64-74) par :

```js
export const useCollectMutation = () => {
  const qc = useQueryClient()
  const [jobId, setJobId] = useState(null)
  const [jobDone, setJobDone] = useState(null)

  const { data: jobStatus } = useQuery({
    queryKey: ['collect-status', jobId],
    queryFn: () => getCollectStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const d = query.state.data
      if (!d || d.status === 'running') return 3000
      return false
    },
    staleTime: 0,
  })

  useEffect(() => {
    if (jobStatus && jobStatus.status !== 'running') {
      setJobDone(jobStatus)
      setJobId(null)
      qc.invalidateQueries({ queryKey: ['scraper-runs'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
      qc.invalidateQueries({ queryKey: ['tenders'] })
    }
  }, [jobStatus, qc])

  const { mutate: startCollect, isPending: isStarting } = useMutation({
    mutationFn: (source_names) => collect(source_names),
    onSuccess: (data) => {
      setJobDone(null)
      setJobId(data.job_id)
    },
  })

  return {
    mutate: startCollect,
    isPending: isStarting || !!jobId,
    data: jobDone,
    reset: () => { setJobId(null); setJobDone(null) },
  }
}
```

- [ ] **Step 3.4 : Adapter `frontend/src/components/Sidebar.jsx`**

Le `collectResult` dans Sidebar attend `{ results: [...] }`. Le nouveau `jobDone` a aussi `results`. Pas de changement nécessaire dans `Sidebar.jsx` — l'interface est identique.

Vérifier quand même que `showResults` reste cohérent :

```jsx
// Ligne 131 de Sidebar.jsx — vérifier que c'est:
const showResults = !!collectResult && !collecting
// Si collectResult peut avoir status="error" global, adapter:
const showResults = !!collectResult && !collecting && collectResult.status !== 'error'
```

Si la ligne 131 est déjà `!!collectResult && !collecting`, ne rien changer.

- [ ] **Step 3.5 : Committer `frontend/src/hooks/useTenders.js`**

```powershell
git add frontend/src/hooks/useTenders.js
git commit -m "feat(hooks): useCollectMutation — polling asynchrone job_id toutes les 3s"
```

- [ ] **Step 3.6 : Tester le frontend en démarrant l'app**

```powershell
.\start.ps1
```

Aller sur `http://localhost:5173`, cliquer "⟳ Lancer la collecte" dans la sidebar.
- Le bouton doit passer en état "Collecte + analyse en cours…" immédiatement
- L'interface reste responsive (pas de blocage)
- Après quelques minutes, les résultats apparaissent

---

## Task 2 : Notification email score ≥ 80

**Principe :** Ajouter `send_go_alert(tender, smtp_config)` dans `email_digest.py`. Dans `_run_collect_job` (backend/main.py), capturer les IDs GO avant analyse, envoyer alertes pour les nouveaux GO après analyse. Ne rien envoyer si `DIGEST_SMTP_HOST` n'est pas défini.

**Fichiers :**
- Modifier : `email_digest.py` (nouvelle fonction `send_go_alert`)
- Modifier : `backend/main.py:_run_collect_job` (logique d'alerte)
- Créer : `tests/test_go_alert.py`

---

### Task 2 — Step 1 : Écrire les tests

- [ ] **Step 1.1 : Créer `tests/test_go_alert.py`**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock


class _FakeTender:
    title = "Système SSI bâtiment A"
    relevance_score = 85
    deadline = None
    url = "https://example.com/tender/1"


_SMTP_CFG = {
    "host": "smtp.test.local",
    "port": 587,
    "user": "test@test.local",
    "password": "secret",
    "to": "dest@test.local",
}


def test_send_go_alert_calls_smtp():
    from email_digest import send_go_alert

    with patch("smtplib.SMTP") as mock_smtp_cls:
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_go_alert(_FakeTender(), _SMTP_CFG)

        mock_smtp_cls.assert_called_once_with("smtp.test.local", 587)
        server.send_message.assert_called_once()


def test_send_go_alert_subject_contains_title():
    from email_digest import send_go_alert

    sent_msgs = []

    with patch("smtplib.SMTP") as mock_smtp_cls:
        server = MagicMock()
        server.send_message.side_effect = lambda msg: sent_msgs.append(msg)
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        send_go_alert(_FakeTender(), _SMTP_CFG)

    assert len(sent_msgs) == 1
    subject = sent_msgs[0]["Subject"]
    assert "[GO]" in subject
    assert "Système SSI bâtiment A" in subject


def test_send_go_alert_returns_true_on_success():
    from email_digest import send_go_alert

    with patch("smtplib.SMTP") as mock_smtp_cls:
        server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        result = send_go_alert(_FakeTender(), _SMTP_CFG)

    assert result is True


def test_send_go_alert_returns_false_on_smtp_error():
    from email_digest import send_go_alert

    with patch("smtplib.SMTP", side_effect=ConnectionRefusedError("refused")):
        result = send_go_alert(_FakeTender(), _SMTP_CFG)

    assert result is False
```

- [ ] **Step 1.2 : Vérifier échec**

```powershell
pytest tests/test_go_alert.py -v
```

Résultat attendu : `FAILED` — `ImportError: cannot import name 'send_go_alert'`.

---

### Task 2 — Step 2 : Implémenter `email_digest.py`

- [ ] **Step 2.1 : Ajouter `send_go_alert` à `email_digest.py`**

Ajouter à la fin du fichier (après la fonction `send_digest`) :

```python
def send_go_alert(tender, smtp_config: dict) -> bool:
    """Envoie une alerte email pour un marché GO (score ≥ 80).
    Retourne True si l'email a été envoyé, False sinon."""
    deadline_str = tender.deadline.strftime("%d/%m/%Y") if tender.deadline else "—"
    subject = f"[GO] {tender.title or 'Sans titre'}"
    body_html = f"""<html><body style='font-family:Inter,sans-serif;max-width:600px;margin:0 auto;padding:24px;color:#111827'>
  <h2 style='color:#166534'>✅ Nouveau marché GO — Score {tender.relevance_score}</h2>
  <table style='width:100%;border-collapse:collapse;font-size:0.95em'>
    <tr><td style='padding:6px 0;color:#6b7280;width:120px'>Titre</td>
        <td style='padding:6px 0;font-weight:600'>{tender.title or '—'}</td></tr>
    <tr><td style='padding:6px 0;color:#6b7280'>Score</td>
        <td style='padding:6px 0'>{tender.relevance_score}</td></tr>
    <tr><td style='padding:6px 0;color:#6b7280'>Deadline</td>
        <td style='padding:6px 0'>{deadline_str}</td></tr>
    <tr><td style='padding:6px 0;color:#6b7280'>Lien</td>
        <td style='padding:6px 0'><a href='{tender.url or "#"}'>{tender.url or "—"}</a></td></tr>
  </table>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_config["user"]
    msg["To"] = smtp_config["to"]
    msg.attach(MIMEText(body_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(msg)
        return True
    except Exception:
        return False
```

- [ ] **Step 2.2 : Vérifier les tests**

```powershell
pytest tests/test_go_alert.py -v
```

Résultat attendu : `4 passed`.

- [ ] **Step 2.3 : Committer `email_digest.py`**

```powershell
git add email_digest.py
git commit -m "feat(email): send_go_alert — alerte email score >= 80"
```

- [ ] **Step 2.4 : Committer `tests/test_go_alert.py`**

```powershell
git add tests/test_go_alert.py
git commit -m "test(email): send_go_alert — sujet [GO], SMTP mock, erreur"
```

---

### Task 2 — Step 3 : Intégrer l'alerte dans `_run_collect_job`

- [ ] **Step 3.1 : Modifier `backend/main.py` — section analyse post-collecte dans `_run_collect_job`**

Remplacer le bloc analyse (après la boucle `for source in sources`) par :

```python
    # Analyse automatique post-collecte + alertes GO ≥ 80
    analysis_db = None
    try:
        analysis_db = SessionLocal()
        auto_analyze_pending(analysis_db)

        # Capturer les IDs déjà GO avant l'analyse Claude
        pre_go_ids: set[str] = {
            r[0]
            for r in analysis_db.query(Tender.id)
            .filter(Tender.relevance_score >= 80, Tender.status == "À qualifier")
            .all()
        }

        auto_analyze_claude(analysis_db, max_per_run=9999)
        analysis_db.expire_all()

        # Envoyer alertes pour les nouveaux GO
        smtp_host = os.getenv("DIGEST_SMTP_HOST")
        if smtp_host:
            smtp_cfg = {
                "host": smtp_host,
                "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
                "user": os.getenv("DIGEST_SMTP_USER", ""),
                "password": os.getenv("DIGEST_SMTP_PASSWORD", ""),
                "to": os.getenv("DIGEST_TO", ""),
            }
            try:
                from email_digest import send_go_alert as _send_go_alert

                new_go = analysis_db.query(Tender).filter(
                    Tender.relevance_score >= 80,
                    Tender.status == "À qualifier",
                    Tender.id.notin_(pre_go_ids) if pre_go_ids else True,
                ).all()
                for t in new_go:
                    _send_go_alert(t, smtp_cfg)
                    _log.info("Alerte GO envoyée pour : %s (score=%s)", t.title, t.relevance_score)
            except Exception as exc:
                _log.warning("Alertes GO échouées : %s", exc, exc_info=True)

    except Exception as exc:
        _log.warning("Analyse post-collecte échouée : %s", exc, exc_info=True)
    finally:
        if analysis_db is not None:
            analysis_db.close()
```

**Note :** `Tender.id.notin_(pre_go_ids) if pre_go_ids else True` évite le `IN ()` vide qui failait sous SQLite.

- [ ] **Step 3.2 : Ajouter l'import `Tender` en haut de `_run_collect_job` si non disponible**

`Tender` est déjà importé en tête de fichier (`from models import Credential, DuplicateCandidate, ScraperRun, Tender`). ✓

- [ ] **Step 3.3 : Vérifier la suite pytest complète**

```powershell
pytest tests/ -q
```

Résultat attendu : `0 failed`.

- [ ] **Step 3.4 : Committer `backend/main.py`**

```powershell
git add backend/main.py
git commit -m "feat(collect): alerte email GO >= 80 apres auto_analyze_claude"
```

---

## Task 3 : Tableau de bord taux de succès scrapers

**Principe :** `get_scraper_stats(db)` dans `database.py` agrège les `ScraperRun` des 30 derniers jours. `GET /api/scraper-stats` l'expose. `useScraperStats` hook + tableau dans l'onglet Sources de `Parametres.jsx`.

**Fichiers :**
- Modifier : `database.py` (ajouter `get_scraper_stats`)
- Modifier : `backend/main.py` (endpoint `GET /api/scraper-stats`)
- Modifier : `frontend/src/services/api.js` (ajouter `getScraperStats`)
- Modifier : `frontend/src/hooks/useTenders.js` (ajouter `useScraperStats`)
- Modifier : `frontend/src/pages/Parametres.jsx` (tableau dans onglet Sources)
- Créer : `tests/test_scraper_stats.py`

---

### Task 3 — Step 1 : Écrire les tests

- [ ] **Step 1.1 : Créer `tests/test_scraper_stats.py`**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_scraper_stats_empty_db(db):
    from database import get_scraper_stats

    stats = get_scraper_stats(db)
    assert stats == []


def test_scraper_stats_one_ok_run(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id = start_scraper_run(db, "boamp")
    finish_scraper_run(db, run_id, nb_found=10, nb_new=5)

    stats = get_scraper_stats(db)
    assert len(stats) == 1
    s = stats[0]
    assert s["source_name"] == "boamp"
    assert s["runs_30j"] == 1
    assert s["runs_ok"] == 1
    assert s["runs_empty"] == 0


def test_scraper_stats_empty_run(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id = start_scraper_run(db, "decp")
    finish_scraper_run(db, run_id, nb_found=3, nb_new=0)

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["runs_empty"] == 1
    assert s["runs_ok"] == 1


def test_scraper_stats_error_run(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id = start_scraper_run(db, "vaao")
    finish_scraper_run(db, run_id, nb_found=0, nb_new=0, error="Timeout")

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["runs_ok"] == 0
    assert s["runs_30j"] == 1


def test_scraper_stats_avg_duration(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats
    from models import ScraperRun

    run_id = start_scraper_run(db, "ted")
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    run.finished_at = run.started_at + timedelta(seconds=42)
    db.commit()

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["avg_duration_s"] == pytest.approx(42.0, abs=1.0)


def test_scraper_stats_excludes_old_runs(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats
    from models import ScraperRun

    run_id = start_scraper_run(db, "boamp")
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    run.started_at = datetime.utcnow() - timedelta(days=35)
    run.finished_at = run.started_at + timedelta(seconds=10)
    run.status = "ok"
    db.commit()

    stats = get_scraper_stats(db)
    assert stats == []


def test_scraper_stats_last_run_at(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id1 = start_scraper_run(db, "boamp")
    finish_scraper_run(db, run_id1, nb_found=5, nb_new=2)
    run_id2 = start_scraper_run(db, "boamp")
    finish_scraper_run(db, run_id2, nb_found=3, nb_new=1)

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["last_run_at"] is not None
    assert s["runs_30j"] == 2
```

- [ ] **Step 1.2 : Vérifier échec**

```powershell
pytest tests/test_scraper_stats.py -v
```

Résultat attendu : `FAILED` — `ImportError: cannot import name 'get_scraper_stats'`.

---

### Task 3 — Step 2 : Implémenter `get_scraper_stats` dans `database.py`

- [ ] **Step 2.1 : Ajouter `get_scraper_stats` à `database.py`**

Ajouter à la fin du fichier `database.py` (après `reset_tenders_db`) :

```python
def get_scraper_stats(db, days: int = 30) -> list[dict]:
    """Statistiques d'exécution des scrapers pour les N derniers jours.
    Retourne une liste triée par source_name."""
    from models import ScraperRun

    cutoff = _dt.now(_tz.utc).replace(tzinfo=None) - _td(days=days)
    runs = (
        db.query(ScraperRun)
        .filter(ScraperRun.started_at >= cutoff)
        .all()
    )

    aggregated: dict[str, dict] = {}
    for r in runs:
        name = r.source_name
        if name not in aggregated:
            aggregated[name] = {
                "runs_30j": 0,
                "runs_ok": 0,
                "runs_empty": 0,
                "total_duration_s": 0.0,
                "runs_with_duration": 0,
                "last_run_at": None,
            }
        agg = aggregated[name]
        agg["runs_30j"] += 1
        if r.status == "ok":
            agg["runs_ok"] += 1
            if (r.nb_new or 0) == 0:
                agg["runs_empty"] += 1
        if r.finished_at and r.started_at:
            duration = (r.finished_at - r.started_at).total_seconds()
            agg["total_duration_s"] += duration
            agg["runs_with_duration"] += 1
        if r.finished_at:
            if agg["last_run_at"] is None or r.finished_at > agg["last_run_at"]:
                agg["last_run_at"] = r.finished_at

    result = []
    for name in sorted(aggregated):
        agg = aggregated[name]
        n_dur = agg["runs_with_duration"]
        avg_dur = round(agg["total_duration_s"] / n_dur, 1) if n_dur > 0 else None
        last_at = agg["last_run_at"]
        result.append({
            "source_name": name,
            "runs_30j": agg["runs_30j"],
            "runs_ok": agg["runs_ok"],
            "runs_empty": agg["runs_empty"],
            "avg_duration_s": avg_dur,
            "last_run_at": last_at.isoformat() if last_at else None,
        })
    return result
```

- [ ] **Step 2.2 : Vérifier les tests**

```powershell
pytest tests/test_scraper_stats.py -v
```

Résultat attendu : `7 passed`.

- [ ] **Step 2.3 : Vérifier toute la suite pytest**

```powershell
pytest tests/ -q
```

Résultat attendu : `0 failed`.

- [ ] **Step 2.4 : Committer `database.py`**

```powershell
git add database.py
git commit -m "feat(db): get_scraper_stats — agregation ScraperRun par source sur 30j"
```

- [ ] **Step 2.5 : Committer `tests/test_scraper_stats.py`**

```powershell
git add tests/test_scraper_stats.py
git commit -m "test(db): get_scraper_stats — ok, vide, erreur, duree, exclusion anciens"
```

---

### Task 3 — Step 3 : Endpoint backend

- [ ] **Step 3.1 : Ajouter `GET /api/scraper-stats` dans `backend/main.py`**

Ajouter après l'endpoint `GET /api/scraper-runs` (après la ligne ~905) :

```python
@app.get("/api/scraper-stats", summary="Statistiques de collecte par source (30j)")
def get_scraper_stats_endpoint(db: Session = Depends(get_db)):
    from database import get_scraper_stats
    return get_scraper_stats(db)
```

- [ ] **Step 3.2 : Vérifier l'endpoint via curl ou test**

```powershell
# Démarrer le backend puis :
Invoke-WebRequest -Uri "http://localhost:8000/api/scraper-stats" | Select-Object -ExpandProperty Content
```

Résultat attendu : liste JSON (peut être vide si aucun run).

- [ ] **Step 3.3 : Committer `backend/main.py`**

```powershell
git add backend/main.py
git commit -m "feat(api): GET /api/scraper-stats — stats collecte 30j par source"
```

---

### Task 3 — Step 4 : Hook et service frontend

- [ ] **Step 4.1 : Ajouter `getScraperStats` dans `frontend/src/services/api.js`**

Ajouter après `getScraperRuns` :

```js
export const getScraperStats = () =>
  api.get('/scraper-stats').then((r) => r.data)
```

- [ ] **Step 4.2 : Committer `frontend/src/services/api.js`**

```powershell
git add frontend/src/services/api.js
git commit -m "feat(api): getScraperStats — GET /api/scraper-stats"
```

- [ ] **Step 4.3 : Ajouter `useScraperStats` dans `frontend/src/hooks/useTenders.js`**

Ajouter `getScraperStats` aux imports de services, puis ajouter le hook à la fin du fichier :

```js
// Dans l'import (ajouter getScraperStats):
import {
  // ... imports existants ...
  getScraperStats,
} from '../services/api'

// À la fin du fichier, après useDeleteSource:
export const useScraperStats = () =>
  useQuery({
    queryKey: ['scraper-stats'],
    queryFn: getScraperStats,
    staleTime: 60_000,
  })
```

- [ ] **Step 4.4 : Committer `frontend/src/hooks/useTenders.js`**

```powershell
git add frontend/src/hooks/useTenders.js
git commit -m "feat(hooks): useScraperStats — query GET /api/scraper-stats"
```

---

### Task 3 — Step 5 : Tableau dans `Parametres.jsx`

- [ ] **Step 5.1 : Modifier `frontend/src/pages/Parametres.jsx`**

Ajouter `useScraperStats` aux imports du hook (ligne ~17) :

```js
import {
  useAnalyzePending,
  useDuplicates,
  useDetectDuplicates,
  useResolveDuplicate,
  useArchiveOld,
  useResetDb,
  useCredentials,
  useSaveCredential,
  useDeleteCredential,
  useTestCredential,
  useSaveMistralKey,
  useMistralStatus,
  useScraperStats,          // ← ajouter
} from '../hooks/useTenders'
```

Ajouter le composant `ScraperStatsTable` après `IntegrationsTab` (avant la section `// ── Page principale`):

```jsx
// ── Tableau stats scrapers ────────────────────────────────────────────────────

function ScraperStatsTable() {
  const { data: stats = [], isLoading } = useScraperStats()

  if (isLoading) {
    return <p className="font-sans text-sm text-ocean-muted">Chargement…</p>
  }
  if (stats.length === 0) {
    return (
      <p className="font-sans text-sm text-ocean-muted italic">
        Aucune collecte enregistrée sur les 30 derniers jours.
      </p>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-ocean-border">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="text-ocean-muted uppercase tracking-wider bg-black/20">
            <th className="text-left px-3 py-2">Source</th>
            <th className="text-right px-3 py-2">Collectes</th>
            <th className="text-right px-3 py-2">OK</th>
            <th className="text-right px-3 py-2">Vides</th>
            <th className="text-right px-3 py-2">Durée moy.</th>
            <th className="text-left px-3 py-2">Dernière</th>
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => {
            const okRate = s.runs_30j > 0 ? Math.round((s.runs_ok / s.runs_30j) * 100) : 0
            const rateColor =
              okRate < 50 ? 'text-ocean-coral' : okRate < 80 ? 'text-ocean-gold' : 'text-ocean-teal'
            return (
              <tr key={s.source_name} className="border-t border-ocean-border/50 hover:bg-ocean-cyan/2">
                <td className="px-3 py-2 text-ocean-text">{s.source_name}</td>
                <td className="px-3 py-2 text-right text-ocean-muted">{s.runs_30j}</td>
                <td className={`px-3 py-2 text-right ${rateColor}`}>
                  {s.runs_ok}{' '}
                  <span className="text-ocean-muted">({okRate}%)</span>
                </td>
                <td className="px-3 py-2 text-right text-ocean-muted">{s.runs_empty}</td>
                <td className="px-3 py-2 text-right text-ocean-muted">
                  {s.avg_duration_s != null ? `${s.avg_duration_s}s` : '—'}
                </td>
                <td className="px-3 py-2 text-ocean-muted">
                  {s.last_run_at
                    ? new Date(s.last_run_at).toLocaleString('fr-FR', {
                        day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
                      })
                    : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
```

Dans la section rendu de la page principale, remplacer :

```jsx
{activeTab === 'sources' && <SourceGenerator />}
```

par :

```jsx
{activeTab === 'sources' && (
  <div className="space-y-8">
    <div>
      <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest mb-3">
        📊 Statistiques de collecte — 30 derniers jours
      </h3>
      <ScraperStatsTable />
    </div>
    <SourceGenerator />
  </div>
)}
```

- [ ] **Step 5.2 : Committer `frontend/src/pages/Parametres.jsx`**

```powershell
git add frontend/src/pages/Parametres.jsx
git commit -m "feat(ui): onglet Sources — tableau stats scrapers 30j"
```

- [ ] **Step 5.3 : Vérifier visuellement**

Lancer `.\start.ps1`, aller dans Paramètres → onglet Sources. Le tableau doit apparaître au-dessus du générateur.

---

## Task 4 : Pagination frontend "Charger plus"

**Principe :** `TendersTable` gère localement `offset` (0 au départ) et accumule les pages dans `allTenders`. Le bouton "Charger 200 de plus" apparaît seulement si la dernière page retourne exactement 200 résultats. Quand les filtres changent, on repart à offset=0.

**Fichiers :**
- Modifier : `frontend/src/components/TendersTable.jsx`
- Créer : `frontend/src/components/TendersTable.test.jsx`

---

### Task 4 — Step 1 : Écrire les tests Vitest

- [ ] **Step 1.1 : Créer `frontend/src/components/TendersTable.test.jsx`**

```jsx
import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import TendersTable from './TendersTable'

// Mock des hooks
vi.mock('../hooks/useTenders', () => ({
  useTenders: vi.fn(),
  useAnalyzeTender: vi.fn(() => ({ mutate: vi.fn() })),
}))

import { useTenders } from '../hooks/useTenders'

const makeTenders = (n, offset = 0) =>
  Array.from({ length: n }, (_, i) => ({
    id: `T${offset + i}`,
    title: `Marché ${offset + i}`,
    relevance_score: 50,
    status: 'À qualifier',
    source: 'test',
    gonogo: 'GO',
    domaine: 'SSI',
    territoire: 'La Réunion',
    publication_date: '2026-01-01',
    deadline: null,
    llm_analysis: null,
    url: null,
    is_maintenance: false,
  }))

const defaultProps = {
  status: 'Tous',
  secteur: 'Public',
  searchText: '',
  gonogo: 'Tous',
  onStatusChange: vi.fn(),
  onSecteurChange: vi.fn(),
  onSearchChange: vi.fn(),
  onGonogoChange: vi.fn(),
  onRowClick: vi.fn(),
}

describe('TendersTable — pagination', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('affiche le bouton "Charger 200 de plus" si la page a exactement 200 résultats', () => {
    useTenders.mockReturnValue({
      data: makeTenders(200),
      isLoading: false,
      isFetching: false,
      isError: false,
    })
    render(<TendersTable {...defaultProps} />)
    expect(screen.getByRole('button', { name: /Charger 200 de plus/i })).toBeDefined()
  })

  it("n'affiche pas le bouton si la page a moins de 200 résultats", () => {
    useTenders.mockReturnValue({
      data: makeTenders(42),
      isLoading: false,
      isFetching: false,
      isError: false,
    })
    render(<TendersTable {...defaultProps} />)
    expect(screen.queryByRole('button', { name: /Charger 200 de plus/i })).toBeNull()
  })

  it("n'affiche pas le bouton si la page est vide", () => {
    useTenders.mockReturnValue({
      data: [],
      isLoading: false,
      isFetching: false,
      isError: false,
    })
    render(<TendersTable {...defaultProps} />)
    expect(screen.queryByRole('button', { name: /Charger 200 de plus/i })).toBeNull()
  })
})
```

- [ ] **Step 1.2 : Vérifier échec**

```powershell
cd frontend
npm test -- TendersTable.test.jsx
```

Résultat attendu : tests échouent (bouton absent).

---

### Task 4 — Step 2 : Implémenter la pagination dans `TendersTable.jsx`

- [ ] **Step 2.1 : Modifier `frontend/src/components/TendersTable.jsx`**

Ajouter `useEffect` aux imports React (ligne 1) :

```jsx
import { useMemo, useState, useCallback, useEffect } from 'react'
```

Remplacer le début de la fonction `TendersTable` (les premières lignes après la signature de fonction) :

```jsx
// Avant:
const { data: tenders = [], isLoading, isError } = useTenders({ status, secteur })

// Après:
const LIMIT = 200
const [offset, setOffset] = useState(0)
const [allTenders, setAllTenders] = useState([])

useEffect(() => {
  setOffset(0)
  setAllTenders([])
}, [status, secteur])

const { data: page = [], isLoading, isFetching, isError } = useTenders({
  status,
  secteur,
  limit: LIMIT,
  offset,
})

useEffect(() => {
  setAllTenders((prev) => {
    if (page.length === 0 && offset === 0) return []
    if (offset === 0) return page
    const existingIds = new Set(prev.map((t) => t.id))
    return [...prev, ...page.filter((t) => !existingIds.has(t.id))]
  })
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [page])

const hasMore = !isFetching && page.length === LIMIT
```

Remplacer toutes les références à `tenders` par `allTenders` dans le corps de la fonction (filtre, rendu) :

```jsx
// Avant:
const filtered = useMemo(() => {
  let result = tenders
  // ...

// Après:
const filtered = useMemo(() => {
  let result = allTenders
  // ...
```

Ajouter le bouton "Charger plus" après le `</table>` (juste avant `</div>` de `overflow-x-auto`) :

```jsx
          </table>
          {hasMore && (
            <div className="flex justify-center py-3 border-t border-ocean-border">
              <button
                onClick={() => setOffset((o) => o + LIMIT)}
                disabled={isFetching}
                className="px-4 py-2 bg-ocean-cyan/10 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
              >
                {isFetching ? 'Chargement…' : 'Charger 200 de plus'}
              </button>
            </div>
          )}
        </div>
```

- [ ] **Step 2.2 : Vérifier les tests Vitest**

```powershell
cd frontend
npm test -- TendersTable.test.jsx
```

Résultat attendu : `3 passed`.

- [ ] **Step 2.3 : Vérifier qu'aucun test frontend existant n'est cassé**

```powershell
npm test
```

Résultat attendu : `0 failed`.

- [ ] **Step 2.4 : Committer `frontend/src/components/TendersTable.jsx`**

```powershell
git add frontend/src/components/TendersTable.jsx
git commit -m "feat(ui): pagination TendersTable — bouton Charger 200 de plus avec offset"
```

- [ ] **Step 2.5 : Committer `frontend/src/components/TendersTable.test.jsx`**

```powershell
git add frontend/src/components/TendersTable.test.jsx
git commit -m "test(ui): TendersTable — affichage bouton charger-plus selon taille page"
```

- [ ] **Step 2.6 : Vérifier visuellement dans l'app**

Lancer `.\start.ps1`. Sur le Dashboard (table marchés), si plus de 200 marchés → bouton apparaît en bas. Clic → 200 de plus s'ajoutent sans remplacer.

---

## Task 5 : SimHash pour détection doublons

**Principe :** Implémenter `_simhash(text: str) -> int` (fingerprint 64 bits) et `_hamming_distance(a, b)`. Refactorer `detect_duplicates` pour utiliser un bucketing LSH sur 4 bandes de 16 bits. Pas de dépendance externe. Interface publique `detect_duplicates(db, max_tenders=2000)` inchangée (ajout du paramètre avec valeur par défaut — rétrocompatible car l'existant appelle `detect_duplicates(db)`).

**Fichiers :**
- Modifier : `database.py` (fonctions `_simhash`, `_hamming_distance`, refactor `detect_duplicates`)
- Créer : `tests/test_simhash.py`

---

### Task 5 — Step 1 : Écrire les tests

- [ ] **Step 1.1 : Créer `tests/test_simhash.py`**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime


# ── Tests unitaires SimHash ───────────────────────────────────────────────────

def test_simhash_returns_int():
    from database import _simhash
    h = _simhash("hello world")
    assert isinstance(h, int)


def test_simhash_64_bits():
    from database import _simhash
    h = _simhash("test text")
    assert 0 <= h < (1 << 64)


def test_simhash_deterministic():
    from database import _simhash
    text = "Installation système SSI détection incendie bâtiment A"
    assert _simhash(text) == _simhash(text)


def test_simhash_empty_string():
    from database import _simhash
    h = _simhash("")
    assert isinstance(h, int)


def test_hamming_distance_identical():
    from database import _hamming_distance
    assert _hamming_distance(0xABCDEF, 0xABCDEF) == 0


def test_hamming_distance_one_bit():
    from database import _hamming_distance
    assert _hamming_distance(0b1000, 0b1001) == 1


def test_hamming_distance_max():
    from database import _hamming_distance
    assert _hamming_distance(0, (1 << 64) - 1) == 64


def test_simhash_similar_texts_close_hamming():
    from database import _simhash, _hamming_distance
    h1 = _simhash("Installation SSI bâtiment A Réunion 2026")
    h2 = _simhash("Installation SSI bâtiment A Réunion 2026 marché public")
    # Textes très proches → distance Hamming < 20
    assert _hamming_distance(h1, h2) < 20


def test_simhash_different_texts_far_hamming():
    from database import _simhash, _hamming_distance
    h1 = _simhash("Installation système SSI détection incendie")
    h2 = _simhash("Permis construire lotissement résidentiel voirie")
    # Textes différents → distance Hamming > 8
    assert _hamming_distance(h1, h2) > 8


# ── Tests intégration detect_duplicates avec SimHash ─────────────────────────

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make(db, id, title, source, deadline=None):
    from models import Tender
    t = Tender(
        id=id,
        title=title,
        description="",
        source=source,
        publication_date=datetime(2026, 1, 15),
        deadline=deadline,
        status="À qualifier",
        relevance_score=50,
        is_blacklisted=False,
        tags=[],
        secteur="Public",
    )
    db.add(t)
    db.flush()
    return t


def test_detect_duplicates_identical_titles_different_sources(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Installation système SSI détection incendie bâtiment A", "boamp", dl)
    _make(db, "B1", "Installation système SSI détection incendie bâtiment A", "decp", dl)

    n = detect_duplicates(db)
    assert n >= 1


def test_detect_duplicates_same_source_not_flagged(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Installation système SSI détection incendie", "boamp", dl)
    _make(db, "A2", "Installation système SSI détection incendie", "boamp", dl)

    n = detect_duplicates(db)
    assert n == 0


def test_detect_duplicates_different_deadlines_not_flagged(db):
    from database import detect_duplicates

    _make(db, "A1", "Installation système SSI incendie bâtiment A", "boamp", datetime(2026, 8, 1))
    _make(db, "B1", "Installation système SSI incendie bâtiment A", "decp", datetime(2026, 9, 15))

    n = detect_duplicates(db)
    assert n == 0  # deadline diff > 3 jours


def test_detect_duplicates_completely_different_titles(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Permis construire lotissement résidentiel voirie", "boamp", dl)
    _make(db, "B1", "Installation vidéosurveillance CCTV parking souterrain", "decp", dl)

    n = detect_duplicates(db)
    assert n == 0


def test_detect_duplicates_max_tenders_param(db):
    """Vérifier que max_tenders limite le nombre traité sans erreur."""
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    for i in range(10):
        _make(db, f"T{i}", f"Marché SSI bâtiment {i}", f"source_{i}", dl)

    n = detect_duplicates(db, max_tenders=5)
    assert isinstance(n, int)


def test_detect_duplicates_no_duplicate_twice(db):
    """Une paire ne doit pas être insérée deux fois."""
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Installation système SSI incendie bâtiment complet", "boamp", dl)
    _make(db, "B1", "Installation système SSI incendie bâtiment complet", "decp", dl)

    n1 = detect_duplicates(db)
    n2 = detect_duplicates(db)
    assert n1 >= 1
    assert n2 == 0  # deuxième appel ne doit pas réinsérer
```

- [ ] **Step 1.2 : Vérifier échec**

```powershell
pytest tests/test_simhash.py -v
```

Résultat attendu : `FAILED` — `ImportError: cannot import name '_simhash'`.

---

### Task 5 — Step 2 : Implémenter SimHash dans `database.py`

- [ ] **Step 2.1 : Ajouter `_simhash` et `_hamming_distance` à `database.py`**

Ajouter après la ligne `from difflib import SequenceMatcher as _SM` (vers ligne ~111) :

```python
import hashlib as _hashlib
from collections import defaultdict as _defaultdict


def _simhash(text: str) -> int:
    """Fingerprint SimHash 64 bits d'un texte."""
    words = text.lower().split()
    v = [0] * 64
    for word in words:
        h = int(_hashlib.md5(word.encode("utf-8", errors="replace")).hexdigest(), 16)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(64) if v[i] > 0)


def _hamming_distance(a: int, b: int) -> int:
    """Distance de Hamming entre deux entiers 64 bits."""
    return bin(a ^ b).count("1")
```

- [ ] **Step 2.2 : Refactorer `detect_duplicates` dans `database.py`**

Remplacer entièrement la fonction `detect_duplicates` (lignes ~153-275) par :

```python
_DEDUP_MAX_TENDERS = 2000


def detect_duplicates(db, max_tenders: int = _DEDUP_MAX_TENDERS) -> int:
    """Détecte les paires de marchés dupliqués via SimHash 64 bits + bucketing LSH.
    Retourne le nombre de nouvelles paires insérées.
    Interface publique identique à l'ancienne implémentation O(N²)."""
    from models import Tender, DuplicateCandidate

    # Chargement des paires existantes
    existing_raw = db.query(
        DuplicateCandidate.tender_id_a, DuplicateCandidate.tender_id_b
    ).all()
    existing_pairs: set[tuple] = {(min(a, b), max(a, b)) for a, b in existing_raw}

    # Chargement et tri des tenders (les plus récents en premier)
    tenders = (
        db.query(Tender)
        .filter(Tender.is_blacklisted.is_(False), Tender.title.is_not(None), Tender.title != "")
        .all()
    )
    if len(tenders) > max_tenders:
        tenders = sorted(
            tenders,
            key=lambda t: (
                t.publication_date.replace(tzinfo=None) if t.publication_date else _dt.min
            ),
            reverse=True,
        )[:max_tenders]

    # Calcul des fingerprints SimHash
    fingerprints: dict[str, int] = {t.id: _simhash(t.title) for t in tenders}
    tender_map: dict[str, Tender] = {t.id: t for t in tenders}

    # Bucketing LSH : 4 bandes de 16 bits chacune
    BANDS = 4
    BAND_BITS = 16
    buckets: list[dict] = [_defaultdict(list) for _ in range(BANDS)]
    for tid, sh in fingerprints.items():
        for band_idx in range(BANDS):
            key = (sh >> (band_idx * BAND_BITS)) & 0xFFFF
            buckets[band_idx][key].append(tid)

    # Collecte des paires candidates (même bucket dans au moins 1 bande)
    candidate_pairs: set[tuple] = set()
    for band in buckets:
        for bucket_items in band.values():
            if len(bucket_items) < 2:
                continue
            for i in range(len(bucket_items)):
                for j in range(i + 1, len(bucket_items)):
                    pair_key = (min(bucket_items[i], bucket_items[j]), max(bucket_items[i], bucket_items[j]))
                    if pair_key not in existing_pairs:
                        candidate_pairs.add(pair_key)

    # Vérification des candidats : distance Hamming + source + deadline
    new_pairs = 0
    for aid, bid in candidate_pairs:
        a = tender_map.get(aid)
        b = tender_map.get(bid)
        if a is None or b is None:
            continue
        if a.source == b.source:
            continue
        if _hamming_distance(fingerprints[aid], fingerprints[bid]) > 8:
            continue
        # Vérification deadline à ±3 jours
        if a.deadline and b.deadline:
            dl_a = a.deadline.replace(tzinfo=None)
            dl_b = b.deadline.replace(tzinfo=None)
            if abs((dl_a - dl_b).days) > 3:
                continue
        elif a.deadline or b.deadline:
            continue

        sim_score = round(1.0 - _hamming_distance(fingerprints[aid], fingerprints[bid]) / 64.0, 3)
        db.add(
            DuplicateCandidate(
                tender_id_a=aid,
                tender_id_b=bid,
                similarity_score=sim_score,
                detected_at=_dt.now(_tz.utc).replace(tzinfo=None),
            )
        )
        existing_pairs.add((aid, bid))
        new_pairs += 1

    if new_pairs > 0:
        db.commit()

    _log.info("detect_duplicates (SimHash): %d nouvelles paires", new_pairs)
    return new_pairs
```

**Note :** Supprimer les variables inutilisées de l'ancienne implémentation (`_DEDUP_MAX_SECONDS`, `ratio_cache`, etc.) — elles ne doivent plus exister après le remplacement.

- [ ] **Step 2.3 : Vérifier les tests SimHash**

```powershell
pytest tests/test_simhash.py -v
```

Résultat attendu : `12 passed`.

- [ ] **Step 2.4 : Vérifier toute la suite pytest**

```powershell
pytest tests/ -q
```

Résultat attendu : `0 failed`. Les tests existants dans `tests/test_doublons.py` doivent toujours passer.

- [ ] **Step 2.5 : Committer `database.py`**

```powershell
git add database.py
git commit -m "feat(db): detect_duplicates — SimHash 64 bits + bucketing LSH 4 bandes"
```

- [ ] **Step 2.6 : Committer `tests/test_simhash.py`**

```powershell
git add tests/test_simhash.py
git commit -m "test(db): SimHash — _simhash, _hamming_distance, detect_duplicates LSH"
```

---

## Vérification finale

- [ ] **Run complet pytest**

```powershell
pytest tests/ -q
```

Résultat attendu : **0 failed**, tous les tests du sprint 3 passent.

- [ ] **Run tests frontend**

```powershell
cd frontend
npm test
```

Résultat attendu : `0 failed`.

- [ ] **Test en conditions réelles**

```powershell
.\start.ps1
```

Vérifier :
1. Collecte asynchrone → bouton "Lancer la collecte" revient sans blocage, résultats arrivent après polling
2. Paramètres → Sources → tableau de stats scraper visible
3. Table marchés → si > 200 tenders, bouton "Charger 200 de plus" présent en bas

---

## Auto-revue du plan

**Couverture spec :**
- ✅ Task 1 : `_COLLECT_JOBS` dict + `BackgroundTasks` + `GET /api/collect/status/{job_id}` + polling React Query 3s + invalidation cache
- ✅ Task 2 : `send_go_alert(tender, smtp_config)` + capture pre/post IDs GO + guard `DIGEST_SMTP_HOST`
- ✅ Task 3 : `get_scraper_stats(db)` + endpoint + hook + tableau dans Paramètres Sources
- ✅ Task 4 : offset + accumulation + bouton conditionnel (`page.length === LIMIT`)
- ✅ Task 5 : `_simhash` pur Python + LSH 4 bandes + interface `detect_duplicates(db, max_tenders=2000)`

**Vérification placeholders :** aucun TBD, aucun "implement later".

**Cohérence types :**
- `_COLLECT_JOBS` dict → `_run_collect_job` écrit `{status, results}` → frontend lit `jobDone.results`
- `get_scraper_stats` → retourne `list[dict]` avec clés `source_name, runs_30j, runs_ok, runs_empty, avg_duration_s, last_run_at`
- `detect_duplicates(db, max_tenders=2000)` → rétrocompatible car appelé comme `detect_duplicates(db)`
- `_simhash` → int 64 bits → `_hamming_distance` → int 0-64
