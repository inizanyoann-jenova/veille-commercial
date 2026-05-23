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

### Frontend
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
```
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
|---|---|
| `models.py` | SQLAlchemy ORM: `Tender` (id, title, description, url, source, deadline, relevance_score, secteur, amount, llm_analysis, llm_structured, adaptive_score…), `Source`, `Credential`, `ScraperRun`, `DuplicateCandidate`, `ScoreWeight` |
| `database.py` | Engine, session, whitelist migrations, helper queries (`load_urgences`, `load_pipeline_data`, `detect_duplicates`, `clean_obsolete_data`) |
| `source_registry.py` | Source catalog (20+ sources), CRUD, weekly ping, `init_sources()` |
| `filters.py` | Keyword lists (`INCLUSION_KEYWORDS`, `EXCLUSION_KEYWORDS`) for relevance scoring |
| `llm_analyzer.py` | Mistral AI tender analysis; `analyze_tender()`, `auto_analyze_pending()` |
| `score_adaptive.py` | Adaptive scoring trained on GO/NOGO decisions via `ScoreWeight` table |
| `playwright_base.py` | Generic `login()` helper used by authenticated scrapers |
| `credential_manager.py` | Fernet-encrypted credentials for authenticated scrapers |
| `fiche_logic.py` | "Fiche marché" business logic (detailed view data) |
| `health_check.py` | HTTP reachability checks for all sources |

### Scraper conventions
Each `scraper_*.py` exposes a single `fetch()` function (no db parameter) registered in `source_registry._DEFAULT_SOURCES`. It returns `list[dict]` with keys: `name`, `url`, `source`, `date_found`, plus domain-specific fields. Scrapers using Playwright call `playwright_base.login()` with selectors and credentials from `credential_manager`. All HTTP calls go through `scraper_utils.retry_get()` / `retry_post()`.

> **Known bug:** `backend/main.py:collect()` calls `func()` (the scraper's `fetch()`) but discards the return value — scraped results are never persisted to DB. The `Tender.url` field (added via migration) will be NULL until this bridge is implemented.

### Database / migrations
SQLite file: `def_oi_veille.db`. No Alembic — migrations are a **whitelist** in `database._MIGRATIONS` (list of `(table, col_name, col_def)` tuples). To add a column, append to that list. Schema is initialized by `init_db()` on startup.

Tender status lifecycle: `À qualifier` → `Archivé` (auto after 30 days) or manually → `Soumis` → `Gagné` / `Perdu`.

### Frontend
React 19 + Vite + Tailwind + TanStack Query + Recharts.
- `frontend/src/services/api.js` — Axios client, base URL `http://localhost:8000`
- `frontend/src/hooks/useTenders.js` — TanStack Query hooks
- `frontend/src/components/` — TendersTable, KpiGrid, Sidebar, KanbanColumn, TenderDetail, UrgenceCard, etc.
- `frontend/src/pages/` — Dashboard, Analytics, Pipeline, Direction, Parametres, Urgences, Guide
- `frontend/src/components/UrgenceCard.jsx` — Carte urgence : badge J-X (couleur par délai), score, description/résumé LLM, secteur, montant, lien annonce externe

### Testing conventions
- **Backend**: pytest with `tests/conftest.py` providing `db` (in-memory SQLite with per-test rollback) and `make_tender` factory fixtures. No mocking of the database.
- **Frontend**: Vitest + Testing Library; test files colocated in `frontend/src/components/`.

## Environment variables (`.env`)
```
MISTRAL_API_KEY=...       # LLM analysis (Mistral, not OpenAI)
DIGEST_SMTP_HOST=...
DIGEST_SMTP_PORT=587
DIGEST_SMTP_USER=...
DIGEST_SMTP_PASSWORD=...
DIGEST_TO=...
DIGEST_HOUR=7             # Daily digest hour (default 7)
```
Copy `.env.example` to `.env`.

## Git commit rules
Create **one commit per file** — do not bundle multiple file changes into a single commit.

## Urgences — champs attendus par le frontend

`GET /api/urgences` doit retourner pour chaque item :

```text
id, title, relevance_score, jours_restants, source, url,
description, secteur, amount, llm_resume
```

`load_urgences()` dans `database.py` est la source de vérité. Le frontend (`Urgences.jsx` + `UrgenceCard.jsx`) attend exactement ces noms.
