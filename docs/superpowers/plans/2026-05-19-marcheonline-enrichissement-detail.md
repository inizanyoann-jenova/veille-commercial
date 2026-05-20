# Marché Online — Enrichissement par fiche détail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Faire remonter les AOs pertinents de Marché Online en visitant chaque fiche détail pour obtenir une vraie description avant le filtre de pertinence.

**Architecture:** Le scraper devient bi-phasé — Phase 1 collecte les liens depuis les pages de liste (comme avant), Phase 2 visite chaque nouvelle fiche détail pour extraire la description complète, puis applique `classify_relevance` sur titre + description réelle. `existing_ids` empêche de re-visiter les fiches déjà connues.

**Tech Stack:** Python, Playwright (sync), SQLAlchemy, `re`, `hashlib`

---

## Fichiers touchés

| Fichier | Action |
|---|---|
| `scraper_marcheonline.py` | Modifier — ajouter `_parse_detail_html`, `_extract_detail`, refactorer la boucle principale |
| `tests/test_marcheonline_detail.py` | Créer — tests unitaires pour `_parse_detail_html` |

---

### Task 1 : Écrire les tests unitaires pour `_parse_detail_html` (TDD — rouge)

**Files:**
- Create: `tests/test_marcheonline_detail.py`

- [ ] **Step 1 : Créer le fichier de tests**

```python
# tests/test_marcheonline_detail.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_marcheonline import _parse_detail_html


def test_itemprop_description_simple():
    html = '<p itemprop="description">Installation SSI bâtiment hôpital Réunion</p>'
    result = _parse_detail_html(html)
    assert "SSI" in result
    assert "hôpital" in result


def test_ao_objet_class():
    html = '<div class="ao-objet">Installation désenfumage lycée Saint-Denis</div>'
    result = _parse_detail_html(html)
    assert "désenfumage" in result


def test_objet_marche_class():
    html = '<span class="objet-marche">Travaux réhabilitation EHPAD Mayotte</span>'
    result = _parse_detail_html(html)
    assert "réhabilitation" in result


def test_no_match_returns_empty_string():
    html = '<div class="unrelated">Contenu sans rapport</div>'
    assert _parse_detail_html(html) == ""


def test_short_match_ignored():
    # Texte trop court (< 10 chars) → ignoré pour éviter les faux positifs
    html = '<p itemprop="description">Lot 3</p>'
    assert _parse_detail_html(html) == ""


def test_strips_nested_html_tags():
    html = '<p itemprop="description"><strong>CMSI</strong> et désenfumage pour collège</p>'
    result = _parse_detail_html(html)
    assert "CMSI" in result
    assert "<" not in result


def test_description_lot_class():
    html = '<div class="description-lot">Vidéosurveillance campus universitaire 974</div>'
    result = _parse_detail_html(html)
    assert "Vidéosurveillance" in result
```

- [ ] **Step 2 : Vérifier que les tests échouent (la fonction n'existe pas encore)**

```bash
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
python -m pytest tests/test_marcheonline_detail.py -v
```

Résultat attendu : `ImportError` ou `AttributeError` — `_parse_detail_html` n'existe pas.

---

### Task 2 : Implémenter `_parse_detail_html` et `_extract_detail`

**Files:**
- Modify: `scraper_marcheonline.py`

- [ ] **Step 1 : Ajouter les constantes et les deux fonctions après `_get_next_url`**

Ouvrir `scraper_marcheonline.py`. Après la fonction `_get_next_url` (ligne ~76), insérer :

```python
_DETAIL_PATTERNS = [
    r'itemprop=["\']description["\'][^>]*>(.*?)</\w+',
    r'class=["\']ao-objet["\'][^>]*>(.*?)</\w+',
    r'class=["\']objet-marche["\'][^>]*>(.*?)</\w+',
    r'class=["\']description-lot["\'][^>]*>(.*?)</\w+',
    r'class=["\']ao-description["\'][^>]*>(.*?)</\w+',
]


def _parse_detail_html(html: str) -> str:
    """Extrait la description depuis le HTML brut d'une fiche détail."""
    for pattern in _DETAIL_PATTERNS:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            text = _strip_tags(m.group(1)).strip()
            if len(text) > 10:
                return text
    return ""


def _extract_detail(page, url: str) -> str:
    """Navigue vers la fiche détail et retourne la description complète.

    Retourne "" en cas d'erreur — ne propage pas l'exception pour ne pas
    interrompre la collecte.
    """
    if not url:
        return ""
    try:
        page.goto(url, timeout=20000)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        return _parse_detail_html(page.content())
    except Exception as exc:
        _log.warning("Marché Online : fiche détail inaccessible %s — %s", url, exc)
        return ""
```

- [ ] **Step 2 : Lancer les tests unitaires pour valider l'implémentation**

```bash
python -m pytest tests/test_marcheonline_detail.py -v
```

Résultat attendu : 7 tests `PASSED`.

- [ ] **Step 3 : Commit**

```bash
git add scraper_marcheonline.py tests/test_marcheonline_detail.py
git commit -m "feat: marcheonline — _parse_detail_html + _extract_detail (TDD)"
```

---

### Task 3 : Refactorer la boucle principale en deux phases

**Files:**
- Modify: `scraper_marcheonline.py` — fonction `fetch_marcheonline_tenders`

- [ ] **Step 1 : Remplacer le corps de la boucle Playwright dans `fetch_marcheonline_tenders`**

Localiser le bloc `with sync_playwright() as pw:` dans `fetch_marcheonline_tenders`. Remplacer **tout le contenu** de ce bloc par :

```python
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                try:
                    if creds:
                        login(page, _LOGIN_URL, creds[0], creds[1], _LOGIN_SELECTORS)

                    # ── Phase 1 : collecte des liens depuis les pages de liste ──
                    candidates = []
                    for base_url in _URLS:
                        current_url = base_url
                        page_count  = 0
                        while page_count < 10:
                            page.goto(current_url, timeout=30000)
                            page.wait_for_load_state("networkidle", timeout=30000)
                            html  = page.content()
                            for card in _extract_from_comments(html):
                                if card.get("title", "").strip():
                                    candidates.append(card)
                            next_url = _get_next_url(html, current_url)
                            if not next_url or next_url == current_url:
                                break
                            current_url = next_url
                            page_count += 1

                    # ── Phase 2 : enrichissement détail + filtre pertinence ────
                    for card in candidates:
                        title = card.get("title", "").strip()
                        url   = card.get("url", "")
                        tid   = f"MARCHEONLINE-{hashlib.md5(f'{title}{url}'.encode()).hexdigest()}"
                        if tid in existing_ids:
                            continue

                        detail_desc = _extract_detail(page, url)
                        desc = detail_desc or card.get("description", "").strip()

                        relevant, extra_tags = classify_relevance(f"{title} {desc}")
                        if not relevant:
                            continue

                        t = Tender(
                            id=tid, title=title, description=desc, source=url,
                            publication_date=parse_date(card.get("date")),
                            deadline=parse_date(card.get("deadline")),
                            status="À qualifier", relevance_score=0,
                            is_maintenance=False, llm_analysis=None,
                            secteur="Public", type_opportunite="Marché Public",
                            tags=extra_tags,
                        )
                        if insert_if_new(db, t, existing_ids):
                            inserted += 1
                finally:
                    page.close()
            finally:
                browser.close()
```

- [ ] **Step 2 : Vérifier l'import — `classify_relevance` est déjà importé**

S'assurer que la ligne d'import en haut du fichier contient bien :
```python
from filters import classify_relevance
```
(Elle y est déjà — aucun changement d'import nécessaire.)

- [ ] **Step 3 : Lancer les tests existants pour vérifier la non-régression**

```bash
python -m pytest tests/test_marcheonline_detail.py tests/test_scrapers_new.py -v
```

Résultat attendu : tous les tests `PASSED`.

- [ ] **Step 4 : Commit**

```bash
git add scraper_marcheonline.py
git commit -m "feat: marcheonline — collecte bi-phasée avec visite des fiches détail"
```

---

### Task 4 : Smoke test de la collecte réelle

> Cette tâche nécessite une connexion Internet et un compte Marché Online configuré dans `CredentialManager`.

- [ ] **Step 1 : Lancer la collecte et observer les logs**

```bash
python -m scraper_marcheonline
```

Résultat attendu : des lignes de log du type :
```
INFO  Marché Online : fiche détail https://www.marchesonline.com/appels-offres/avis/... visitée
INFO  Marché Online : X inséré(s)
```

- [ ] **Step 2 : Vérifier en base que des marchés remontent**

```bash
python -c "
from database import SessionLocal, init_db
from models import Tender
init_db()
db = SessionLocal()
rows = db.query(Tender).filter(Tender.id.like('MARCHEONLINE-%')).all()
print(f'{len(rows)} marchés Marché Online en base')
for r in rows[:5]:
    print(' -', r.title[:80])
db.close()
"
```

Résultat attendu : au moins 1 marché Marché Online présent avec un vrai titre d'AO.

---

## Récapitulatif des fichiers

| Fichier | Changements |
|---|---|
| `scraper_marcheonline.py` | +`_DETAIL_PATTERNS`, +`_parse_detail_html`, +`_extract_detail`, refactoring boucle principale bi-phasée, limite 5→10 pages |
| `tests/test_marcheonline_detail.py` | Nouveau — 7 tests unitaires pour `_parse_detail_html` |
