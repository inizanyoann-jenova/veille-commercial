# Spec — Nettoyage anomalies architecture (A→E)

**Date :** 2026-05-22
**Scope :** 5 corrections ciblées, pas de refactoring étendu

---

## A — Source model → models.py (re-export transparent)

**Problème :** la classe `Source` est définie dans `source_registry.py` alors que tous les autres modèles SQLAlchemy (`Tender`, `Credential`, `ScraperRun`, etc.) sont dans `models.py`.

**Correction :**

- `models.py` : ajouter la classe `Source` avec ses 12 colonnes (id, name, url, category, scraper_module, scraper_func, is_manual, enabled, notes, display_order, is_validated, ping_failures_count, last_ping_at). Même `Base`.
- `source_registry.py` : remplacer la définition de la classe et `from models import Base` par `from models import Base, Source`. Les imports existants (`from source_registry import Source`) continuent de fonctionner sans modification — `Source` reste accessible dans le namespace du module.

**Fichiers modifiés :** `models.py`, `source_registry.py`
**Fichiers non touchés :** tous les tests, `database.py`, `health_check.py`, `backend/main.py`

---

## B — Supprimer la whitelist tautologique dans database.py

**Problème :** `_VALID_COLS` est construit par dérivation de `_MIGRATIONS` elle-même. Le check `if col_name not in _VALID_COLS` dans `_run_migrations` ne peut jamais être vrai — il est redondant.

**Correction :**

- Supprimer la ligne `_VALID_COLS = {col for _, col, _ in _MIGRATIONS}` (actuellement ligne 36).
- Supprimer le bloc `if col_name not in _VALID_COLS: raise ValueError(...)` dans `_run_migrations`.
- Conserver `_VALID_TABLES` et son check (significatif) et le commentaire de sécurité.

**Fichiers modifiés :** `database.py`

---

## C — Double-comptage nb_new dans collect() — aucun changement

**Problème documenté :** le snapshot `known_ids` est pris avant la boucle, donc `nb_new` pour une source peut inclure les insertions des sources précédentes.

**Décision :** acceptable. `nb_new` est une métrique indicative affichée dans l'UI, pas une valeur contractuelle. Le commentaire existant dans `backend/main.py` (ligne ~751) documente déjà le comportement.

**Fichiers modifiés :** aucun

---

## D — CORS : restreindre les wildcards dans backend/main.py

**Problème :** `allow_methods=["*"]` et `allow_headers=["*"]` même si les origines sont déjà restreintes à localhost.

**Correction :**

```python
allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "Authorization"],
```

Les verbes couvrent toutes les routes existantes. `Authorization` est inclus pour les futurs besoins d'auth. `Content-Type` est requis pour les corps JSON.

**Fichiers modifiés :** `backend/main.py` (bloc `add_middleware`)

---

## E — Supprimer api.py après migration des routes manquantes

**Problème :** deux backends coexistent. `api.py` n'est pas utilisé au démarrage (les scripts `start.bat` / `start.ps1` lancent `backend/main.py`), mais il contient 5 routes absentes de `backend/main.py`.

### Routes à migrer (toutes préfixées `/api/`)

| Route | Dépendances à importer |
|---|---|
| `GET /api/health` | `from health_check import run_all_health_checks` |
| `POST /api/sources` | `from source_registry import add_source` + schéma Pydantic `SourceCreate` |
| `DELETE /api/sources/{id}` | `from source_registry import remove_source` |
| `PATCH /api/sources/{id}/toggle` | `from source_registry import toggle_enabled` |
| `GET /api/export/excel` | `from export_excel import generate_executive_report` |

### Routes api.py NON migrées (équivalents déjà présents)

- `POST /scrape` → `POST /api/collect` (plus complet)
- `POST /auto-analyze` et `POST /auto-analyze/local` → `POST /api/analyze-pending` (couvre les deux)
- `GET /tenders` → `GET /api/tenders` (plus riche)

### Après migration

Supprimer `api.py` entièrement.

**Fichiers modifiés :** `backend/main.py`
**Fichiers supprimés :** `api.py`

---

## Ordre d'exécution recommandé

1. A — models.py + source_registry.py (1 commit chacun)
2. B — database.py (1 commit)
3. D — backend/main.py CORS (1 commit)
4. E — backend/main.py ajout routes (1 commit) puis suppression api.py (1 commit)

Chaque fichier = 1 commit (règle git du projet).
