# Filtre ERP Implicite — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capturer les opportunités de marché public pertinentes pour DEF OI (réhabilitation d'école, construction d'hôpital…) même sans mot-clé SSI explicite, et les signaler avec le tag "Potentiel SSI implicite".

**Architecture:** Nouvelle fonction `classify_relevance(text)` dans `filters.py` retournant `(bool, list[str])`. Les 12 scrapers remplacent leur appel `is_relevant_def()` par `classify_relevance()` et injectent les tags dans le `Tender`. `app.py` ajoute le tag à `TENDER_TAGS` et affiche un bandeau dans la fiche.

**Tech Stack:** Python, SQLAlchemy (Tender model), Streamlit (app.py)

---

## Fichiers modifiés

| Fichier | Rôle de la modification |
|---|---|
| `filters.py` | Ajouter `classify_relevance()`, conserver les wrappers existants |
| `tests/test_filters.py` | Ajouter tests pour `classify_relevance()` |
| `scraper_marcheonline.py` | Remplacer `is_relevant_def` → `classify_relevance` |
| `scraper_boamp.py` | idem |
| `scraper_decp.py` | idem |
| `scraper_marchespublicsinfo.py` | idem |
| `scraper_instao.py` | idem |
| `scraper_dept974.py` | idem |
| `scraper_ted.py` | idem |
| `scraper_ungm.py` | idem |
| `scraper_vaao.py` | idem |
| `scraper_marchessecurises.py` | idem |
| `scraper_nukema.py` | idem |
| `scraper_tendersgo.py` | idem |
| `app.py` | Ajouter tag TENDER_TAGS + bandeau fiche |

---

## Task 1 : `classify_relevance()` dans `filters.py` (TDD)

**Files:**
- Modify: `tests/test_filters.py`
- Modify: `filters.py`

- [ ] **Step 1 : Écrire les tests échouants dans `tests/test_filters.py`**

Ajouter ces tests à la fin du fichier (après les tests existants) :

```python
from filters import classify_relevance


# ── classify_relevance ────────────────────────────────────────────────────────

def test_classify_ssi_direct_retourne_true_sans_tag():
    ok, tags = classify_relevance("Installation SSI — Lycée Paul Vergès")
    assert ok is True
    assert tags == []


def test_classify_cmsi_direct_retourne_true_sans_tag():
    ok, tags = classify_relevance("Maintenance CMSI centre commercial Saint-Denis")
    assert ok is True
    assert tags == []


def test_classify_rehabilitation_ecole_retourne_tag_implicite():
    ok, tags = classify_relevance("Réhabilitation de l'école primaire Sainte-Marie")
    assert ok is True
    assert "Potentiel SSI implicite" in tags


def test_classify_construction_hopital_retourne_tag_implicite():
    ok, tags = classify_relevance("Construction d'un hôpital neuf à Saint-Pierre")
    assert ok is True
    assert "Potentiel SSI implicite" in tags


def test_classify_erp_sans_chantier_retourne_false():
    """ERP seul sans mot construction → non pertinent."""
    ok, tags = classify_relevance("L'école de Saint-Denis accueille de nouveaux élèves")
    assert ok is False
    assert tags == []


def test_classify_exclusion_gardiennage_retourne_false():
    ok, tags = classify_relevance("Marché de gardiennage et SSI pour la mairie")
    assert ok is False
    assert tags == []


def test_classify_hors_sujet_retourne_false():
    ok, tags = classify_relevance("Achat de fournitures de bureau")
    assert ok is False
    assert tags == []


def test_classify_renovation_mairie_retourne_tag_implicite():
    ok, tags = classify_relevance("Rénovation de la mairie de Saint-Leu — Lot général")
    assert ok is True
    assert "Potentiel SSI implicite" in tags
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
pytest tests/test_filters.py -k "classify" -v
```

Résultat attendu : `ImportError` ou `AttributeError` — `classify_relevance` n'existe pas encore.

- [ ] **Step 3 : Implémenter `classify_relevance()` dans `filters.py`**

Ajouter après la définition de `_COMPILED_BOUNDARY` (après la ligne `}`), avant `def is_relevant_def`:

```python
def classify_relevance(text: str) -> tuple[bool, list[str]]:
    """Retourne (pertinent, tags).

    tags contient ["Potentiel SSI implicite"] quand la capture est via
    la logique construction+ERP, sans mot-clé DEF OI direct.
    """
    text_lower = text.lower()

    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False, []

    for kw in INCLUSION_KEYWORDS:
        if kw in _WORD_BOUNDARY_KW:
            if _COMPILED_BOUNDARY[kw].search(text_lower):
                return True, []
        elif kw in text_lower:
            return True, []

    has_chantier = any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
    has_erp = any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)
    if has_chantier and has_erp:
        return True, ["Potentiel SSI implicite"]

    return False, []
```

- [ ] **Step 4 : Transformer `is_relevant_def` et `is_prive_relevant` en wrappers**

Remplacer le corps des deux fonctions existantes :

```python
def is_relevant_def(text: str) -> bool:
    return classify_relevance(text)[0]


def is_prive_relevant(text: str) -> bool:
    return classify_relevance(text)[0]
```

> Note : `is_construction_relevant` n'est pas un wrapper — elle reste inchangée car elle sert un autre usage (vérification indépendante).

- [ ] **Step 5 : Lancer tous les tests filters**

```
pytest tests/test_filters.py -v
```

Résultat attendu : tous les tests PASS, aucune régression sur les tests existants.

- [ ] **Step 6 : Commit**

```
git add filters.py tests/test_filters.py
git commit -m "feat: classify_relevance — capture ERP implicite avec tag Potentiel SSI implicite"
```

---

## Task 2 : Mise à jour des 12 scrapers

**Files:** `scraper_marcheonline.py`, `scraper_boamp.py`, `scraper_decp.py`, `scraper_marchespublicsinfo.py`, `scraper_instao.py`, `scraper_dept974.py`, `scraper_ted.py`, `scraper_ungm.py`, `scraper_vaao.py`, `scraper_marchessecurises.py`, `scraper_nukema.py`, `scraper_tendersgo.py`

Le pattern est identique dans chaque fichier. **Ne pas modifier `scraper_presse.py`** — il utilise déjà `is_prive_relevant` qui est maintenant un wrapper.

### Pattern de changement (à appliquer dans chaque scraper)

**Import — remplacer :**
```python
from filters import is_relevant_def
```
**par :**
```python
from filters import classify_relevance
```

**Filtre + création du Tender — remplacer le bloc :**
```python
if not is_relevant_def(<texte>):
    continue
# ... calcul de tender_id ...
t = Tender(
    ...,
    # pas de tags= ou tags=[]
)
```
**par :**
```python
relevant, extra_tags = classify_relevance(<texte>)
if not relevant:
    continue
# ... calcul de tender_id ...
t = Tender(
    ...,
    tags=extra_tags,
)
```

> Si le `Tender(...)` a déjà `tags=[]`, remplacer `tags=[]` par `tags=extra_tags`.
> Si le `Tender(...)` n'a pas de `tags=`, l'ajouter.

- [ ] **Step 1 : Modifier `scraper_marcheonline.py`**

Ligne 8 : `from filters import is_relevant_def` → `from filters import classify_relevance`

Ligne 102, remplacer :
```python
if not title or not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not title or not relevant:
    continue
```

Dans `Tender(...)` (ligne ~107), ajouter `tags=extra_tags,` après `is_maintenance=False,`.

- [ ] **Step 2 : Modifier `scraper_boamp.py`**

Import : `from filters import classify_relevance`

Ligne 77, remplacer :
```python
if not is_relevant_def(full_text):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(full_text)
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,` après `llm_analysis=None,`.

- [ ] **Step 3 : Modifier `scraper_decp.py`**

Import : `from filters import classify_relevance`

Ligne 56, remplacer :
```python
if not is_relevant_def(full_text):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(full_text)
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,` (après `llm_analysis=None,`).

- [ ] **Step 4 : Modifier `scraper_marchespublicsinfo.py`**

Import : `from filters import classify_relevance`

Ligne 50, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 5 : Modifier `scraper_instao.py`**

Import : `from filters import classify_relevance`

Ligne 60, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 6 : Modifier `scraper_dept974.py`**

Import : `from filters import classify_relevance`

Ligne 45, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 7 : Modifier `scraper_ted.py`**

Import : `from filters import classify_relevance`

Ligne 57, remplacer :
```python
if not is_relevant_def(f"{title} {description}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {description}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 8 : Modifier `scraper_ungm.py`**

Import : `from filters import classify_relevance`

Ligne 69, remplacer :
```python
if not full_text.strip() or not is_relevant_def(full_text):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(full_text)
if not full_text.strip() or not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 9 : Modifier `scraper_vaao.py`**

Import : `from filters import classify_relevance`

Ligne 49, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 10 : Modifier `scraper_marchessecurises.py`**

Import : `from filters import classify_relevance`

Ligne 60, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 11 : Modifier `scraper_nukema.py`**

Import : `from filters import classify_relevance`

Ligne 69, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 12 : Modifier `scraper_tendersgo.py`**

Import : `from filters import classify_relevance`

Ligne 60, remplacer :
```python
if not is_relevant_def(f"{title} {desc}"):
    continue
```
par :
```python
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
```

Dans `Tender(...)`, ajouter `tags=extra_tags,`.

- [ ] **Step 13 : Vérifier qu'aucun scraper n'importe encore `is_relevant_def`**

```
grep -r "is_relevant_def" scraper_*.py
```

Résultat attendu : aucune ligne.

- [ ] **Step 14 : Lancer la suite de tests existante**

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py -x
```

Résultat attendu : tous les tests PASS.

- [ ] **Step 15 : Commit**

```
git add scraper_marcheonline.py scraper_boamp.py scraper_decp.py scraper_marchespublicsinfo.py scraper_instao.py scraper_dept974.py scraper_ted.py scraper_ungm.py scraper_vaao.py scraper_marchessecurises.py scraper_nukema.py scraper_tendersgo.py
git commit -m "feat: scrapers — classify_relevance remplace is_relevant_def, tags injectés dans Tender"
```

---

## Task 3 : `app.py` — Tag + bandeau fiche

**Files:**
- Modify: `app.py:37-44` (TENDER_TAGS)
- Modify: `app.py:1339-1341` (après BLOC 1 de la fiche)

- [ ] **Step 1 : Ajouter "Potentiel SSI implicite" à TENDER_TAGS**

Dans `app.py`, remplacer :

```python
TENDER_TAGS = [
    "Partenaire requis",
    "En attente DCE",
    "Budget bloqué",
    "À voir avec DG",
    "Offre déposée",
    "Recours prévu",
]
```

par :

```python
TENDER_TAGS = [
    "Potentiel SSI implicite",
    "Partenaire requis",
    "En attente DCE",
    "Budget bloqué",
    "À voir avec DG",
    "Offre déposée",
    "Recours prévu",
]
```

- [ ] **Step 2 : Ajouter le bandeau dans `_render_fiche`**

Dans `app.py`, après le bloc BLOC 1 (après `st.caption(f"💡 {a['justification_score']}")` autour de la ligne 1340), ajouter :

```python
        # ── Bandeau SSI implicite ─────────────────────────────────────────────
        if "Potentiel SSI implicite" in (t.tags if isinstance(t.tags, list) else []):
            st.info(
                "⚠️ **Potentiel SSI implicite** — capturé via type de bâtiment (ERP) "
                "sans mot-clé SSI direct. Confirmer lors de la qualification."
            )
```

- [ ] **Step 3 : Lancer les tests**

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py -x
```

Résultat attendu : tous PASS.

- [ ] **Step 4 : Commit**

```
git add app.py
git commit -m "feat: app — tag Potentiel SSI implicite + bandeau fiche"
```
