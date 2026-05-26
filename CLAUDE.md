# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DEF Océan Indien — Outil de Veille Marchés Publics**
Commercial intelligence tool for public procurement markets in La Réunion (974) and Mayotte (976). Covers SSI, CMSI, fire detection, smoke extraction, CCTV, and courants faibles sectors.

## Commands

### Launch (full stack)

```powershell
.\start.ps1          # Démarre backend (port 8000) + frontend Vite (port 5173)
.\start.bat          # Alternative batch
```

### Backend only

```powershell
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at `http://localhost:8000/docs`.

### Frontend dev server

```powershell
cd frontend
npm install          # First time
npm run dev          # Dev server — port 5173
npm run build
npm run lint
npm test             # Vitest (run once)
npm run test:watch
```

### Python tests

```powershell
pytest               # All tests
pytest tests/test_database_helpers.py          # Single file
pytest tests/test_filters.py::test_name        # Single test
pytest -x            # Stop on first failure
```

### Install

```powershell
pip install -r requirements.txt
playwright install chromium   # Required for Playwright scrapers
```

## Architecture

### Dual-backend situation

There are **two FastAPI backends** in the repo:

- `api.py` (root) — legacy, mostly superseded
- `backend/main.py` — **active backend** started by `start.ps1`; it `sys.path.insert`s the root directory to import shared modules

All scrapers, models, and business logic live at the **root level** and are shared. The `backend/` folder only contains `main.py` and `test_main.py`.

### Data flow

```text
Scrapers (scraper_*.py)
   → scraper_utils.retry_get/post() — shared HTTP retry with backoff
   → playwright_base.login() — for authenticated sites
   → Tender records (SQLite via SQLAlchemy)
        → filters.py — keyword inclusion/exclusion scoring
        → llm_analyzer.py — Mistral AI deep analysis
        → score_adaptive.py — ML-like adaptive scoring from past decisions
        → export_excel.py / email_digest.py — outputs
```

### Key modules

| Module | Role |
| --- | --- |
| `models.py` | SQLAlchemy ORM: `Tender` (id, title, description, url, source, deadline, relevance_score, secteur, amount, llm_analysis, llm_structured, adaptive_score…), `Source`, `Credential`, `ScraperRun`, `DuplicateCandidate`, `ScoreWeight` |
| `database.py` | Engine, session, whitelist migrations, helper queries (`load_urgences`, `load_pipeline_data`, `detect_duplicates`, `clean_obsolete_data`, `reset_tenders_db`, `start_scraper_run`, `finish_scraper_run`) |
| `source_registry.py` | Source catalog (20+ sources), CRUD, weekly ping, `init_sources()` |
| `filters.py` | Keyword lists (`INCLUSION_KEYWORDS`, `EXCLUSION_KEYWORDS`) for relevance scoring |
| `llm_analyzer.py` | Mistral AI tender analysis; `analyze_tender()`, `auto_analyze_pending(limit=None)`, `auto_analyze_mistral()` (reads `LLM_BATCH_SIZE`, `MISTRAL_DELAY`, `EXCLUSION_SIGNAL_THRESHOLD` env), `reset_mistral_client()`. Aliases: `auto_analyze_claude = auto_analyze_gemini = auto_analyze_mistral` |
| `score_adaptive.py` | Adaptive scoring trained on GO/NOGO decisions via `ScoreWeight` table |
| `playwright_base.py` | Generic `login()` helper used by authenticated scrapers |
| `credential_manager.py` | Fernet-encrypted credentials for authenticated scrapers |
| `fiche_logic.py` | "Fiche marché" business logic (detailed view data) |
| `health_check.py` | HTTP reachability checks for all sources |

### Scraper conventions

Each `scraper_*.py` exposes a single `fetch()` function (no db parameter) registered in `source_registry._DEFAULT_SOURCES`. It returns `list[dict]` with keys: `name`, `url`, `source`, `date_found`, plus domain-specific fields. Scrapers using Playwright call `playwright_base.login()` with selectors and credentials from `credential_manager`. All HTTP calls go through `scraper_utils.retry_get()` / `retry_post()`.

Active scrapers: `scraper_boamp`, `scraper_decp`, `scraper_ted`, `scraper_dept974`, `scraper_nukema`, `scraper_marcheonline`, `scraper_marchessecurises`, `scraper_marchespublicsinfo`, `scraper_instao`, `scraper_tendersgo`, `scraper_vaao`, `scraper_afd`, `scraper_devbanks`, `scraper_isdb`, `scraper_permis`, `scraper_presse`, `scraper_chm`.

`POST /api/collect` pipeline: fetch → `_dict_to_tender()` → `insert_if_new()` (rejects if no `publication_date` or already known) → `auto_analyze_pending()` + `auto_analyze_mistral()` post-collect. Counter `nb_rejected_no_date` is returned in the response.

### Database / migrations

SQLite file: `def_oi_veille.db`. No Alembic — migrations are a **whitelist** in `database._MIGRATIONS` (list of `(table, col_name, col_def)` tuples). To add a column, append to that list. Schema is initialized by `init_db()` on startup.

Tender status lifecycle: `À qualifier` → `Archivé` (auto after 30 days) or manually → `Soumis` → `Gagné` / `Perdu`.

### Frontend

React 19 + Vite + Tailwind (Ocean Deep theme) + TanStack Query + Recharts.

- `frontend/src/services/api.js` — Axios client, base URL `http://localhost:8000`
- `frontend/src/hooks/useTenders.js` — TanStack Query hooks (inclut `useMistralStatus`, `useSaveMistralKey`, `useResetDb`, `useArchiveOld`, `useDetectDuplicates`)
- `frontend/src/utils/theme.js` — `applyTheme()`, `applyBrightness()`, `loadSavedBrightness()`; CSS var `--app-brightness` appliquée sur la zone de contenu
- `frontend/src/components/` — TendersTable (filtre GO/NO-GO), KpiGrid, Sidebar, KanbanColumn, TenderDetail (lien annonce cliquable), UrgenceCard, ScraperRunsTable, DuplicatePair
- `frontend/src/pages/` — Dashboard, Analytics, Pipeline, Direction, Parametres (onglets: Connexion, Intégrations, Apparence, Doublons, Export), Urgences, Guide
- `frontend/src/components/TendersTable.jsx` — Filtres : statut, secteur, GO/NO-GO (`GONOGOS = ['Tous', 'GO', 'Étudier', 'Passer']`), date, maintenance
- `frontend/src/components/UrgenceCard.jsx` — Carte urgence : badge J-X (couleur par délai), score, description/résumé LLM, secteur, montant, lien annonce externe

### Testing conventions

- **Backend**: pytest with `tests/conftest.py` providing `db` (in-memory SQLite with per-test rollback) and `make_tender` factory fixtures. No mocking of the database.
- **Frontend**: Vitest + Testing Library; test files colocated in `frontend/src/components/`.

## Environment variables (`.env`)

```env
MISTRAL_API_KEY=...           # LLM analysis (Mistral, not OpenAI) — éditable via Paramètres → Intégrations
DIGEST_SMTP_HOST=...
DIGEST_SMTP_PORT=587
DIGEST_SMTP_USER=...
DIGEST_SMTP_PASSWORD=...
DIGEST_TO=...
DIGEST_HOUR=7                 # Daily digest hour (default 7)
SCRAPER_WINDOW_DAYS=30        # Fenêtre de collecte BOAMP / insert (défaut 30j)
LLM_BATCH_SIZE=10             # Nombre de tenders analysés par auto_analyze_mistral()
MISTRAL_DELAY=1.0             # Délai en secondes entre requêtes Mistral (défaut 1.0)
EXCLUSION_SIGNAL_THRESHOLD=2  # Signal technique min pour ignorer la pénalité exclusion
```

Copy `.env.example` to `.env`. La clé Mistral peut aussi être mise à jour à chaud via `POST /api/settings/mistral-key` (appelle `reset_mistral_client()` pour rechargement immédiat).

## Key API endpoints (backend/main.py)

| Endpoint | Description |
| --- | --- |
| `GET /api/tenders` | Liste filtrée (status, secteur, date_from, maintenance_only, only_recent) |
| `POST /api/collect` | Lance les scrapers → insère → analyse LLM post-collecte |
| `POST /api/tenders/{id}/analyze` | Analyse LLM manuelle d'un marché |
| `POST /api/analyze-pending` | Analyse LLM en arrière-plan (tous les en attente) |
| `POST /api/settings/mistral-key` | Sauvegarde + hot-reload de la clé Mistral |
| `GET /api/settings/mistral-status` | `{"configured": bool}` |
| `POST /api/admin/reset-db` | Vide tenders/runs/doublons (sources + credentials préservés) |
| `POST /api/admin/archive-old` | Archive les tenders À qualifier > N jours |
| `POST /api/detect-duplicates` | Détecte et enregistre les paires doublon |
| `GET /api/duplicates` | Paires non résolues |
| `GET /api/health` | Ping HTTP de toutes les sources |
| `GET /api/export/excel` | Rapport Excel exécutif |
| `GET /api/credentials` | Statut des 8 sites authentifiés |
| `POST /api/credentials/{site}/test` | Test Playwright de connexion (subprocess isolé) |

## Git commit rules

Create **one commit per file** — do not bundle multiple file changes into a single commit.

## Urgences — champs attendus par le frontend

`GET /api/urgences` doit retourner pour chaque item :

```text
id, title, relevance_score, jours_restants, source, url,
description, secteur, amount, llm_resume
```

`load_urgences()` dans `database.py` est la source de vérité. Le frontend (`Urgences.jsx` + `UrgenceCard.jsx`) attend exactement ces noms.
