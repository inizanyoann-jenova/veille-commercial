# Backend SRE Supervision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrer le scheduler vers le lifespan FastAPI, ajouter un error handler CRITICAL autour des scrapers, et rendre `POST /api/collect` résilient avec un retour partiel 200/500.

**Architecture:** Modification unique de `backend/main.py`. Le scheduler APScheduler (déjà utilisé dans `app.py`) est répliqué dans le gestionnaire `lifespan` FastAPI. La route `/api/collect` devient synchrone pour renvoyer un bilan par source. Chaque scraper est isolé dans un try/except CRITICAL avec placeholder Sentry.

**Tech Stack:** FastAPI 0.95+, APScheduler 3.11.2, SQLAlchemy, Python 3.12+

---

## Fichiers impactés

| Action | Fichier | Rôle |
|--------|---------|------|
| Modifier | `backend/main.py` | Toute la logique métier backend |
| Modifier | `backend/test_main.py` | Tests existants + nouveaux |

---

## Task 1 : Remplacer `@app.on_event("startup")` par `lifespan` + APScheduler

**Files:**
- Modify: `backend/main.py:202-213` (bloc `@app.on_event("startup")`)
- Modify: `backend/main.py:187-198` (déclaration `app = FastAPI(...)`)

- [ ] **Step 1.1 : Écrire le test de démarrage du scheduler**

Ajouter dans `backend/test_main.py` :

```python
from unittest.mock import patch, MagicMock
from httpx import AsyncClient, ASGITransport
import pytest

@pytest.mark.anyio
async def test_lifespan_starts_and_stops_scheduler():
    """Le scheduler doit démarrer au startup et s'arrêter proprement."""
    with patch("main.BackgroundScheduler") as mock_cls:
        mock_scheduler = MagicMock()
        mock_cls.return_value = mock_scheduler

        from main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/tenders")
            assert resp.status_code == 200
            mock_scheduler.start.assert_called_once()

        mock_scheduler.shutdown.assert_called_once_with(wait=False)
```

- [ ] **Step 1.2 : Vérifier que le test échoue (pas encore de lifespan)**

```
cd backend && python -m pytest test_main.py::test_lifespan_starts_and_stops_scheduler -v
```
Résultat attendu : `FAILED` (ImportError ou assertion error)

- [ ] **Step 1.3 : Implémenter le lifespan dans `backend/main.py`**

Remplacer les imports (ajouter en haut) :
```python
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
```

Ajouter ces deux fonctions job **avant** la déclaration de `app`, juste après les constantes métier (ligne ~134) :

```python
def _send_daily_digest() -> None:
    """Job APScheduler — envoi digest email quotidien."""
    try:
        from email_digest import send_digest as _sd
        required = ["DIGEST_SMTP_HOST", "DIGEST_SMTP_PORT", "DIGEST_TO"]
        missing = [p for p in required if not os.getenv(p)]
        if missing:
            _log.error("Digest email: paramètres SMTP manquants: %s", missing)
            return
        cfg = {
            "host": os.getenv("DIGEST_SMTP_HOST"),
            "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
            "user": os.getenv("DIGEST_SMTP_USER"),
            "password": os.getenv("DIGEST_SMTP_PASSWORD"),
            "to": os.getenv("DIGEST_TO"),
        }
        _sd(cfg)
        _log.info("Digest quotidien envoyé")
    except Exception as exc:
        _log.error("Échec envoi digest email : %s", exc, exc_info=True)


def _weekly_adaptive_scores() -> None:
    """Job APScheduler — recalcul hebdomadaire des scores adaptatifs."""
    try:
        from score_adaptive import recompute_adaptive_scores as _r
        _r()
        _log.info("Scores adaptatifs recalculés")
    except Exception as exc:
        _log.error("Échec recalcul scores adaptatifs : %s", exc, exc_info=True)


def _weekly_source_ping() -> None:
    """Job APScheduler — ping hebdomadaire des sources."""
    try:
        from source_registry import _run_weekly_ping as _rwp
        _rwp()
    except Exception as exc:
        _log.error("Échec weekly_ping : %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    init_db()
    db = SessionLocal()
    try:
        n = clean_obsolete_data(db, days=30)
        if n:
            _log.info("Startup: %d tenders archivés (>30 jours)", n)
    except Exception:
        _log.warning("clean_obsolete_data échoué au démarrage", exc_info=True)
    finally:
        db.close()

    scheduler = BackgroundScheduler(
        job_defaults={"max_instances": 1, "coalesce": True}
    )
    scheduler.add_job(_weekly_source_ping, "interval", weeks=1, id="weekly_ping")
    scheduler.add_job(
        _weekly_adaptive_scores, "interval", weeks=1, id="weekly_adaptive_scores"
    )
    digest_hour = int(os.getenv("DIGEST_HOUR", "7"))
    if os.getenv("DIGEST_SMTP_HOST") and os.getenv("DIGEST_TO"):
        scheduler.add_job(
            _send_daily_digest, "cron", hour=digest_hour, minute=0, id="daily_digest"
        )
    scheduler.start()
    _log.info("Scheduler APScheduler démarré (%d jobs)", len(scheduler.get_jobs()))

    yield  # ── Application en cours ──────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    _log.info("Scheduler APScheduler arrêté")
```

Modifier la déclaration `app = FastAPI(...)` pour passer `lifespan=lifespan` :

```python
app = FastAPI(
    title="DEF OI — Veille Marchés API",
    description="API REST pour la veille marchés DEF Océan Indien",
    version="1.0.0",
    lifespan=lifespan,
)
```

**Supprimer entièrement** le bloc `@app.on_event("startup")` (lignes 202-213).

- [ ] **Step 1.4 : Lancer le test**

```
cd backend && python -m pytest test_main.py::test_lifespan_starts_and_stops_scheduler -v
```
Résultat attendu : `PASSED`

- [ ] **Step 1.5 : Commit**

```bash
git add backend/main.py backend/test_main.py
git commit -m "feat(backend): migrate startup to FastAPI lifespan with APScheduler"
```

---

## Task 2 : Error Handler CRITICAL autour des scrapers

**Files:**
- Modify: `backend/main.py:662-666` (bloc `except Exception` dans `_run_collection`)

- [ ] **Step 2.1 : Écrire le test CRITICAL handler**

Ajouter dans `backend/test_main.py` :

```python
import logging
from unittest.mock import patch, MagicMock

def test_collect_critical_log_on_scraper_failure(caplog):
    """Un scraper qui lève une exception doit générer un log CRITICAL."""
    import importlib
    import main as m

    failing_source = MagicMock()
    failing_source.is_manual = False
    failing_source.scraper_module = "fake_module"
    failing_source.scraper_func = "fake_func"
    failing_source.enabled = True
    failing_source.is_validated = True
    failing_source.name = "FakeSource"

    with patch("main.list_sources", return_value=[failing_source]), \
         patch("main.SessionLocal") as mock_sl, \
         patch("main.start_scraper_run", return_value=99), \
         patch("main.finish_scraper_run"), \
         patch("importlib.import_module", side_effect=RuntimeError("playwright crash")), \
         caplog.at_level(logging.CRITICAL, logger="main"):
        
        # On appelle directement la route collect via TestClient
        from fastapi.testclient import TestClient
        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})
    
    assert any("CRITICAL" in r.levelname and "FakeSource" in r.message for r in caplog.records), \
        "Aucun log CRITICAL trouvé pour le scraper en échec"
```

- [ ] **Step 2.2 : Vérifier que le test échoue**

```
cd backend && python -m pytest test_main.py::test_collect_critical_log_on_scraper_failure -v
```
Résultat attendu : `FAILED` (log level est ERROR, pas CRITICAL)

- [ ] **Step 2.3 : Remplacer le bloc except dans `_run_collection`**

Dans `backend/main.py`, localiser le bloc (actuellement lignes ~662-666) :

```python
                except Exception as exc:
                    err_db = SessionLocal()
                    finish_scraper_run(err_db, run_id, nb_found=0, nb_new=0, error=str(exc))
                    err_db.close()
                    _log.error("Erreur scraper %s : %s", source.name, exc, exc_info=True)
```

Remplacer par :

```python
                except Exception as exc:
                    _log.critical(
                        "SCRAPER FAILURE [%s] — %s: %s",
                        source.name, type(exc).__name__, exc,
                        exc_info=True,
                    )
                    err_db = SessionLocal()
                    try:
                        finish_scraper_run(
                            err_db, run_id, nb_found=0, nb_new=0, error=str(exc)
                        )
                    finally:
                        err_db.close()

                    # ── Alertes externes (activer en production) ──────────
                    # import sentry_sdk
                    # sentry_sdk.capture_exception(exc)
                    #
                    # from email_digest import send_alert_email
                    # send_alert_email(
                    #     subject=f"[DEF OI] Scraper FAILED: {source.name}",
                    #     body=f"{type(exc).__name__}: {exc}",
                    # )
                    # ─────────────────────────────────────────────────────
```

- [ ] **Step 2.4 : Vérifier que le test passe**

```
cd backend && python -m pytest test_main.py::test_collect_critical_log_on_scraper_failure -v
```
Résultat attendu : `PASSED`

- [ ] **Step 2.5 : Commit**

```bash
git add backend/main.py backend/test_main.py
git commit -m "feat(backend): add CRITICAL error handler around scraper execution with Sentry placeholder"
```

---

## Task 3 : Résilience `POST /api/collect` — retour 200 partiel ou 500 propre

**Files:**
- Modify: `backend/main.py:626-682` (route `/api/collect`)

- [ ] **Step 3.1 : Écrire les tests de résilience**

Ajouter dans `backend/test_main.py` :

```python
def test_collect_returns_500_when_no_sources():
    """Aucune source active → 500 avec message clair."""
    import main as m
    from fastapi.testclient import TestClient

    with patch("main.list_sources", return_value=[]):
        client = TestClient(m.app, raise_server_exceptions=False)
        resp = client.post("/api/collect", json={})
    
    assert resp.status_code == 500
    body = resp.json()
    assert "Aucune source" in body.get("detail", "")


def test_collect_returns_200_partial_on_mixed_results():
    """Une source OK + une source KO → 200 avec status='partial'."""
    import main as m
    from fastapi.testclient import TestClient

    ok_source = MagicMock()
    ok_source.is_manual = False
    ok_source.scraper_module = "mod_ok"
    ok_source.scraper_func = "run"
    ok_source.enabled = True
    ok_source.is_validated = True
    ok_source.name = "SourceOK"

    fail_source = MagicMock()
    fail_source.is_manual = False
    fail_source.scraper_module = "mod_fail"
    fail_source.scraper_func = "run"
    fail_source.enabled = True
    fail_source.is_validated = True
    fail_source.name = "SourceFAIL"

    def mock_import(name):
        mod = MagicMock()
        if name == "mod_fail":
            mod.run.side_effect = RuntimeError("timeout")
        return mod

    with patch("main.list_sources", return_value=[ok_source, fail_source]), \
         patch("main.SessionLocal") as mock_sl, \
         patch("main.start_scraper_run", return_value=1), \
         patch("main.finish_scraper_run"), \
         patch("main.auto_analyze_pending"), \
         patch("main.auto_analyze_claude"), \
         patch("importlib.import_module", side_effect=mock_import):
        
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 2
        mock_sl.return_value.__enter__ = lambda s: mock_db
        mock_sl.return_value.__exit__ = MagicMock(return_value=False)
        mock_sl.return_value = mock_db

        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})
    
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "partial"
    assert body["nb_ok"] == 1
    assert body["nb_error"] == 1
    assert len(body["results"]) == 2


def test_collect_returns_200_ok_when_all_succeed():
    """Toutes les sources OK → 200 avec status='ok'."""
    import main as m
    from fastapi.testclient import TestClient

    ok_source = MagicMock()
    ok_source.is_manual = False
    ok_source.scraper_module = "mod_ok"
    ok_source.scraper_func = "run"
    ok_source.enabled = True
    ok_source.is_validated = True
    ok_source.name = "SourceOK"

    with patch("main.list_sources", return_value=[ok_source]), \
         patch("main.SessionLocal") as mock_sl, \
         patch("main.start_scraper_run", return_value=1), \
         patch("main.finish_scraper_run"), \
         patch("main.auto_analyze_pending"), \
         patch("main.auto_analyze_claude"), \
         patch("importlib.import_module", return_value=MagicMock()):
        
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 3
        mock_sl.return_value = mock_db

        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})
    
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["nb_ok"] == 1
    assert body["nb_error"] == 0
```

- [ ] **Step 3.2 : Vérifier que les tests échouent**

```
cd backend && python -m pytest test_main.py::test_collect_returns_500_when_no_sources test_main.py::test_collect_returns_200_partial_on_mixed_results test_main.py::test_collect_returns_200_ok_when_all_succeed -v
```
Résultat attendu : 3 × `FAILED`

- [ ] **Step 3.3 : Réécrire la route `POST /api/collect`**

Dans `backend/main.py`, remplacer entièrement le bloc `@app.post("/api/collect", ...)` (lignes 626-682) par :

```python
# ── POST /api/collect ─────────────────────────────────────────────────────────

class CollectResult(BaseModel):
    source: str
    status: str  # "ok" | "error"
    nb_new: Optional[int] = None
    error: Optional[str] = None


@app.post("/api/collect", summary="Lancer la collecte (toutes sources ou liste)")
def collect(body: CollectRequest):
    """
    Exécute les scrapers de façon synchrone et renvoie un bilan par source.
    - 200 {"status": "ok"} : toutes sources OK
    - 200 {"status": "partial"} : au moins une source KO, mais au moins une OK
    - 500 : aucune source configurée/active, ou toutes les sources ont échoué
    """
    db = SessionLocal()
    try:
        sources = list_sources(db)
        if body.source_names:
            sources = [s for s in sources if s.name in body.source_names]
        sources = [
            s for s in sources
            if not s.is_manual and s.scraper_module and s.enabled and s.is_validated
        ]
    finally:
        db.close()

    if not sources:
        raise HTTPException(
            status_code=500,
            detail="Aucune source active et validée trouvée — collecte annulée"
        )

    pre_db = SessionLocal()
    known_ids: set = {row.id for row in pre_db.query(Tender.id).all()}
    pre_db.close()

    results: list[dict] = []

    for source in sources:
        run_db = SessionLocal()
        run_id = start_scraper_run(run_db, source.name)
        run_db.close()
        try:
            mod = importlib.import_module(source.scraper_module)
            func = getattr(mod, source.scraper_func)
            func()
            post_db = SessionLocal()
            try:
                new_count = post_db.query(Tender).filter(
                    ~Tender.id.in_(known_ids)
                ).count()
                finish_scraper_run(post_db, run_id, nb_found=new_count, nb_new=new_count)
            finally:
                post_db.close()
            results.append({"source": source.name, "status": "ok", "nb_new": new_count})

        except Exception as exc:
            _log.critical(
                "SCRAPER FAILURE [%s] — %s: %s",
                source.name, type(exc).__name__, exc,
                exc_info=True,
            )
            err_db = SessionLocal()
            try:
                finish_scraper_run(
                    err_db, run_id, nb_found=0, nb_new=0, error=str(exc)
                )
            finally:
                err_db.close()

            # ── Alertes externes (activer en production) ──────────────────
            # import sentry_sdk
            # sentry_sdk.capture_exception(exc)
            #
            # from email_digest import send_alert_email
            # send_alert_email(
            #     subject=f"[DEF OI] Scraper FAILED: {source.name}",
            #     body=f"{type(exc).__name__}: {exc}",
            # )
            # ─────────────────────────────────────────────────────────────

            results.append({
                "source": source.name,
                "status": "error",
                "error": type(exc).__name__,
            })

    # Analyse automatique post-collecte
    try:
        analysis_db = SessionLocal()
        try:
            auto_analyze_pending(analysis_db)
            auto_analyze_claude(analysis_db, max_per_run=10)
        finally:
            analysis_db.close()
    except Exception as exc:
        _log.warning("Analyse post-collecte échouée : %s", exc, exc_info=True)

    nb_ok = sum(1 for r in results if r["status"] == "ok")
    nb_err = sum(1 for r in results if r["status"] == "error")

    if nb_ok == 0 and nb_err > 0:
        raise HTTPException(
            status_code=500,
            detail={
                "message": f"Toutes les sources ont échoué ({nb_err}/{len(results)})",
                "results": results,
            },
        )

    return {
        "status": "partial" if nb_err > 0 else "ok",
        "nb_ok": nb_ok,
        "nb_error": nb_err,
        "message": f"{nb_ok} source(s) collectée(s), {nb_err} erreur(s)",
        "results": results,
    }
```

**Note :** Supprimer l'import `BackgroundTasks` de la ligne d'import FastAPI si plus utilisé ailleurs, et supprimer le paramètre `background_tasks: BackgroundTasks` des routes qui n'en ont plus besoin (vérifier `/api/analyze-pending`).

- [ ] **Step 3.4 : Lancer les 3 tests**

```
cd backend && python -m pytest test_main.py::test_collect_returns_500_when_no_sources test_main.py::test_collect_returns_200_partial_on_mixed_results test_main.py::test_collect_returns_200_ok_when_all_succeed -v
```
Résultat attendu : 3 × `PASSED`

- [ ] **Step 3.5 : Lancer la suite complète pour s'assurer aucune régression**

```
cd backend && python -m pytest test_main.py -v
```
Résultat attendu : tous `PASSED`

- [ ] **Step 3.6 : Commit**

```bash
git add backend/main.py backend/test_main.py
git commit -m "feat(backend): make /api/collect synchronous with partial 200 or clean 500 response"
```

---

## Task 4 : Vérification finale

- [ ] **Step 4.1 : Démarrer le backend et vérifier les logs scheduler**

```
cd backend && uvicorn main:app --reload --port 8000
```
Résultat attendu dans les logs :
```
INFO  Scheduler APScheduler démarré (2 jobs)
```
(3 jobs si DIGEST_SMTP_HOST défini)

- [ ] **Step 4.2 : Tester `/api/collect` via curl**

```bash
curl -s -X POST http://localhost:8000/api/collect \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool
```
Résultat attendu :
```json
{
  "status": "ok",
  "nb_ok": 5,
  "nb_error": 0,
  "message": "5 source(s) collectée(s), 0 erreur(s)",
  "results": [...]
}
```

- [ ] **Step 4.3 : Commit final si ajustements nécessaires**

```bash
git add backend/main.py
git commit -m "fix(backend): post-review adjustments on SRE supervision"
```
