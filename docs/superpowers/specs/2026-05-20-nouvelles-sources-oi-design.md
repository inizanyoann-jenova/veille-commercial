---
name: nouvelles-sources-oi
description: Ajout de sources gratuites sans authentification pour La Réunion, Mayotte, Madagascar et Maurice + distinction visuelle automatique/manuel dans l'UI
metadata:
  type: project
---

# Spec — Nouvelles sources OI + distinction auto/manuel

## Contexte

L'application DEF OI collecte des marchés publics et opportunités commerciales dans la zone Océan Indien. Le registre de sources (`source_registry.py`) contient déjà 17 sources automatiques et 6 sources manuelles. Cette spec couvre :

1. L'ajout de **12 nouvelles sources** gratuites et sans authentification pour La Réunion (974), Mayotte (976), Madagascar et Maurice.
2. Un **scraper RSS générique** pour automatiser la collecte des sources presse OI.
3. Une **amélioration de l'UI** `pages/parametres.py` pour distinguer visuellement les sources automatiques des sources manuelles.

---

## Périmètre géographique

- La Réunion (974) — déjà bien couvert, ajout de collectivités locales manquantes
- Mayotte (976) — peu couvert actuellement
- Madagascar — non couvert actuellement
- Maurice (Mauritius) — non couvert actuellement

---

## 1. Nouvelles sources

### 1a. Marchés publics locaux — manuelles (`is_manual=True`)

| display_order | name | url | category |
|---|---|---|---|
| 9 | Région Réunion — Marchés publics | https://marches-publics.region.reunion.fr | Public |
| 9 | CINOR — Marchés publics | https://www.cinor.re/appels-offres | Public |
| 9 | TCO — Marchés publics | https://www.tco.re/marches-publics | Public |
| 9 | CHU Réunion — Marchés publics | https://www.chu-reunion.fr/appels-offres | Public |
| 14 | Département de Mayotte — Marchés | https://www.departement976.fr/marchespublics | Public |
| 14 | CADEMA — Marchés publics | https://www.cadema.yt | Public |
| 25 | ARMP Madagascar | https://www.armp.mg | International |
| 25 | CPB Mauritius — Procurement | https://procurement.govmu.org | International |

> Toutes ces sources sont des portails publics officiels, sans inscription requise. Elles sont déclarées `is_manual=True` car leurs structures HTML sont hétérogènes et sujettes à changement fréquent. Elles s'ouvrent via un bouton dans l'UI.

### 1b. Presse & veille économique — automatiques RSS

| display_order | name | url | scraper_module | scraper_func |
|---|---|---|---|---|
| 15 | L'Éco Austral | https://www.ecoaustral.com | scraper_rss | fetch_rss_feed |
| 15 | Mayotte Hebdo | https://www.mayotte-hebdo.com | scraper_rss | fetch_rss_feed |
| 15 | L'Express Madagascar | https://lexpress.mg | scraper_rss | fetch_rss_feed |
| 15 | L'Express Maurice | https://lexpress.mu | scraper_rss | fetch_rss_feed |

> Ces sources exposent des flux RSS/Atom publics, sans authentification. Un scraper générique `scraper_rss.py` gère les 4 sources.

### 1c. Banques de développement — manuelles

| display_order | name | url | category |
|---|---|---|---|
| 26 | IFC — Projets Afrique/OI | https://projects.ifc.org | International |
| 27 | AIIB — Projets approuvés | https://www.aiib.org/en/projects/approved | International |
| 28 | COI — Commission Océan Indien | https://www.commissionoceanindien.org | International |

---

## 2. Scraper RSS générique (`scraper_rss.py`)

### Responsabilité unique

Fetcher générique qui consomme n'importe quel flux RSS/Atom public et retourne une liste de dicts normalisés compatibles avec le pipeline de collecte existant.

### Interface

```python
def fetch_rss_feed(source_name: str, max_items: int = 30) -> list[dict]:
    """
    Résout l'URL RSS depuis _RSS_URLS[source_name] puis retourne une liste de dicts :
      - title (str)
      - url (str)
      - published_at (datetime | None)
      - source (str)  — = source_name
      - raw_text (str)  — description/résumé de l'item
    """
```

### Mapping URL RSS par source name

Un dict interne `_RSS_URLS` mappe `source_name → rss_url` :

```python
_RSS_URLS = {
    "L'Éco Austral":        "https://www.ecoaustral.com/feed",
    "Mayotte Hebdo":        "https://www.mayotte-hebdo.com/feed",
    "L'Express Madagascar": "https://lexpress.mg/feed",
    "L'Express Maurice":    "https://lexpress.mu/feed",
}
```

`fetch_rss_feed(source_name)` résout l'URL RSS en interne — le pipeline n'a pas à la connaître. Si `source_name` est absent du dict, la fonction lève `ValueError`.

### Dépendances

- `feedparser` (parsing RSS/Atom) — à ajouter dans `requirements.txt`
- Pas de Playwright, pas de session, pas d'auth

### Comportement en cas d'erreur

- Si le flux est inaccessible : retourne `[]` et loggue l'erreur (comportement identique aux autres scrapers)
- Si un item n'a pas de date : `published_at = None`

---

## 3. UI — distinction automatique / manuel dans `pages/parametres.py`

### Situation actuelle

Dans la section "⚡ Sources à collecter", les sources sont listées par catégorie (Public / Privé / International) sans distinction visuelle entre automatiques et manuelles. L'icône `📋` est utilisée pour les manuelles mais n'est pas expliquée.

### Changement proposé

Dans chaque bloc catégorie, ajouter deux sous-sections avec un séparateur visuel :

```
📋 Public
  — 🤖 Automatiques —
    [toggle] ✅ BOAMP — Journal Officiel
    [toggle] ⬜ VAAO
    ...
  — 👆 Manuelles (consultation guidée) —
    [toggle] 📋 Région Réunion — Marchés publics  [🔗 Ouvrir]
    [toggle] 📋 PLACE — Portail commandes publiques  [🔗 Ouvrir]
    ...
```

**Bouton "Ouvrir"** : `st.link_button("🔗 Ouvrir", url=s.url)` — ouvre l'URL dans un nouvel onglet. Ajouté uniquement sur les sources manuelles.

**Caption explicatif** sous chaque sous-section :
- Automatiques : *"Collecte déclenchée via le pipeline — aucune action requise"*
- Manuelles : *"À consulter manuellement — cliquez Ouvrir pour accéder au site"*

### Fichier modifié

`pages/parametres.py` — section "Sources à collecter" (lignes 31–56 actuellement).

---

## 4. Intégration dans `source_registry.py`

Les nouvelles sources sont ajoutées dans `_DEFAULT_SOURCES`. La fonction `init_sources()` est idempotente : elle n'insère que les sources dont le `name` n'existe pas encore en base. Aucune migration de base de données nécessaire.

---

## 5. Tests

- `tests/test_source_registry.py` — vérifier que les 12 nouvelles sources sont bien insérées par `init_sources()`
- `tests/test_scrapers_new.py` (ou nouveau fichier) — test unitaire de `fetch_rss_feed` avec un flux mock
- Pas de test UI (Streamlit)

---

## Fichiers impactés

| Fichier | Type de changement |
|---|---|
| `source_registry.py` | Ajout de 12 entrées dans `_DEFAULT_SOURCES` |
| `scraper_rss.py` | Nouveau fichier |
| `pages/parametres.py` | Refactor de la boucle d'affichage sources |
| `requirements.txt` | Ajout de `feedparser` |
| `tests/test_source_registry.py` | Ajout de cas de test |
| `tests/test_rss_scraper.py` | Nouveau fichier de test |
