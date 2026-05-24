# Reset DB + Date Priorité LLM — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un bouton de remise à zéro de la base de données et renforcer l'extraction de la date de publication dans le prompt LLM.

**Architecture:** Trois changements indépendants et ciblés — une fonction DB, un bouton UI dans la page Paramètres, et une réécriture d'une ligne du prompt système LLM.

**Tech Stack:** Python, SQLAlchemy, Streamlit, pytest, SQLite

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `database.py` | Ajouter `reset_tenders_db(db) -> int` après `delete_old_tenders` |
| `pages/parametres.py` | Ajouter section "Zone Danger" à la fin du fichier (après ligne 717) |
| `llm_analyzer.py` | Remplacer la ligne 598 (`date_publication`) dans `SYSTEM_PROMPT` |
| `tests/test_database_helpers.py` | Ajouter tests pour `reset_tenders_db` |
| `tests/test_llm_analyzer.py` | Ajouter test vérifiant que `date_publication` est dans le prompt |

---

## Task 1 — `reset_tenders_db()` dans `database.py`

**Files:**
- Modify: `database.py` (après la fonction `delete_old_tenders`, ~ligne 380)
- Test: `tests/test_database_helpers.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Ouvrir `tests/test_database_helpers.py` et ajouter à la fin :

```python
def test_reset_tenders_db_vide_les_trois_tables(db, make_tender):
    from models import ScraperRun, DuplicateCandidate
    from datetime import datetime
    from database import reset_tenders_db

    # Populate
    make_tender(id="T-RESET-1")
    make_tender(id="T-RESET-2")
    db.add(ScraperRun(source_name="test", started_at=datetime.utcnow(), status="done"))
    db.add(DuplicateCandidate(
        tender_id_a="T-RESET-1", tender_id_b="T-RESET-2",
        similarity_score=0.9, detected_at=datetime.utcnow(),
    ))
    db.flush()

    nb = reset_tenders_db(db)

    from models import Tender
    assert db.query(Tender).count() == 0
    assert db.query(ScraperRun).count() == 0
    assert db.query(DuplicateCandidate).count() == 0
    assert nb == 2  # nombre de tenders supprimés


def test_reset_tenders_db_preserve_sources(db):
    from database import reset_tenders_db
    from source_registry import Source

    nb_sources_avant = db.query(Source).count()
    reset_tenders_db(db)
    assert db.query(Source).count() == nb_sources_avant
```

- [ ] **Step 2 : Lancer le test pour vérifier qu'il échoue**

```
pytest tests/test_database_helpers.py::test_reset_tenders_db_vide_les_trois_tables tests/test_database_helpers.py::test_reset_tenders_db_preserve_sources -v
```

Résultat attendu : `ImportError: cannot import name 'reset_tenders_db'`

- [ ] **Step 3 : Implémenter `reset_tenders_db` dans `database.py`**

Ouvrir `database.py`. Localiser la fin de la fonction `delete_old_tenders` (~ligne 380). Ajouter **après** :

```python
def reset_tenders_db(db) -> int:
    """Vide tenders, scraper_runs et duplicate_candidates. Retourne le nb de tenders supprimés.

    Préserve : sources, credentials, score_weights.
    """
    from models import Tender, ScraperRun, DuplicateCandidate

    nb_tenders = db.query(Tender).count()
    db.query(DuplicateCandidate).delete(synchronize_session=False)
    db.query(ScraperRun).delete(synchronize_session=False)
    db.query(Tender).delete(synchronize_session=False)
    db.commit()
    _log.info("reset_tenders_db : %d tenders supprimés", nb_tenders)
    return nb_tenders
```

- [ ] **Step 4 : Lancer les tests pour vérifier qu'ils passent**

```
pytest tests/test_database_helpers.py::test_reset_tenders_db_vide_les_trois_tables tests/test_database_helpers.py::test_reset_tenders_db_preserve_sources -v
```

Résultat attendu : `2 passed`

- [ ] **Step 5 : Commit**

```bash
git add database.py tests/test_database_helpers.py
git commit -m "feat: add reset_tenders_db() to clear tenders/scraper_runs/duplicate_candidates"
```

---

## Task 2 — Bouton "Zone Danger" dans `pages/parametres.py`

**Files:**
- Modify: `pages/parametres.py` (ajouter à la fin, après ligne 717)

> Pas de test unitaire Streamlit — le comportement est testé visuellement via l'appli.

- [ ] **Step 1 : Ajouter l'import de `reset_tenders_db` en haut du fichier**

Ouvrir `pages/parametres.py`. La ligne 6 contient déjà :
```python
from database import init_db
```

Remplacer cette ligne par :
```python
from database import init_db, reset_tenders_db as _reset_tenders_db
```

- [ ] **Step 2 : Ajouter la section "Zone Danger" à la fin du fichier**

Ouvrir `pages/parametres.py`. Après la dernière ligne (717), ajouter :

```python
# ── Zone Danger ───────────────────────────────────────────────────────────────
st.markdown("---")
st.header("⚠️ Zone Danger")
st.caption("Ces actions sont irréversibles. La base de données ne peut pas être restaurée après suppression.")

_confirm_reset = st.checkbox(
    "Je confirme vouloir supprimer tous les marchés et l'historique de collecte",
    key="confirm_reset_db",
)

if st.button(
    "🗑️ Remettre la base à zéro",
    type="primary",
    disabled=not _confirm_reset,
    key="btn_reset_db",
):
    _db_reset = _SL_src()
    try:
        _nb_deleted = _reset_tenders_db(_db_reset)
    finally:
        _db_reset.close()
    st.success(f"✅ Base remise à zéro — {_nb_deleted} marché(s) supprimé(s).")
    st.rerun()
```

- [ ] **Step 3 : Lancer l'application et tester visuellement**

```
streamlit run app.py
```

Naviguer vers **⚙️ Paramètres** → tout en bas. Vérifier :
- Le bouton "🗑️ Remettre la base à zéro" est **grisé** par défaut
- Après avoir coché la checkbox, le bouton devient **actif**
- Après clic, un message vert confirme la suppression et la page se recharge

- [ ] **Step 4 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat: add reset database button in Parametres Zone Danger section"
```

---

## Task 3 — Date de publication en priorité absolue dans le prompt LLM

**Files:**
- Modify: `llm_analyzer.py` (ligne 598, dans `SYSTEM_PROMPT`)
- Test: `tests/test_llm_analyzer.py`

- [ ] **Step 1 : Écrire le test qui vérifie la présence de l'instruction renforcée**

Ouvrir `tests/test_llm_analyzer.py`. Ajouter à la fin :

```python
def test_system_prompt_contient_instruction_date_prioritaire():
    from llm_analyzer import SYSTEM_PROMPT
    assert "PRIORITÉ ABSOLUE" in SYSTEM_PROMPT
    assert "date_publication" in SYSTEM_PROMPT
    # S'assure que l'instruction passive n'est plus présente
    assert "si trouvée dans le texte, sinon null" not in SYSTEM_PROMPT
```

- [ ] **Step 2 : Lancer le test pour vérifier qu'il échoue**

```
pytest tests/test_llm_analyzer.py::test_system_prompt_contient_instruction_date_prioritaire -v
```

Résultat attendu : `FAILED` — `assert "PRIORITÉ ABSOLUE" in SYSTEM_PROMPT`

- [ ] **Step 3 : Remplacer la ligne 598 dans `SYSTEM_PROMPT`**

Ouvrir `llm_analyzer.py`. Localiser la ligne 598 :

```python
  "date_publication": "date de publication au format YYYY-MM-DD si trouvée dans le texte, sinon null",
```

Remplacer par :

```python
  "date_publication": "PRIORITÉ ABSOLUE — cherche la date de publication dans TOUTES les parties du texte : titre, corps, entête, référence, pied de page. Patterns à détecter : 'publié le', 'date de parution', 'mis en ligne le', 'date d\\'avis', 'paru le', 'date de publication', 'publié en', ainsi que tout format de date explicite (JJ/MM/AAAA, AAAA-MM-JJ, mois AAAA). Retourne la date au format YYYY-MM-DD. Si aucune date n\\'est trouvable nulle part dans le texte, retourne null.",
```

- [ ] **Step 4 : Lancer le test pour vérifier qu'il passe**

```
pytest tests/test_llm_analyzer.py::test_system_prompt_contient_instruction_date_prioritaire -v
```

Résultat attendu : `1 passed`

- [ ] **Step 5 : Lancer la suite de tests complète pour vérifier l'absence de régression**

```
pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : tous les tests passent.

- [ ] **Step 6 : Commit**

```bash
git add llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat: enforce absolute date extraction priority in LLM system prompt"
```

---

## Vérification finale

- [ ] Lancer la suite de tests complète

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py -x
```

Résultat attendu : tous les tests passent, aucune régression.
