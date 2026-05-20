# Spec : Nouvelles sources automatiques — Batch 2

**Date :** 2026-05-20
**Statut :** validé utilisateur

## Contexte

L'application dispose déjà de sources automatiques (BOAMP, TED, Banque Mondiale, JICA, presse OI complète…). Ce batch ajoute 5 nouvelles sources automatiques réparties en deux groupes d'implémentation.

> Note : Clicanoo, Mayotte Hebdo et JIR étaient déjà présents dans `FLUX_PRESSE` — le périmètre a été recadré après inspection du code.

---

## Sources à ajouter

### Groupe A — RSS dans `scraper_devbanks.py` (ajout aux listes existantes)

| # | Nom | URL flux | Zone |
|---|-----|----------|------|
| 1 | UNDP Procurement | `https://procurement-notices.undp.org/rss_notices.cfm` | Zone IO / Global |
| 2 | ADB — Asian Dev. Bank | `https://www.adb.org/rss/projects.xml` | Zone IO / Asie |

**Implémentation :** ajouter ces 2 tuples `(zone, nom, url)` dans la liste `FLUX_DEVBANKS` de `scraper_devbanks.py`. Le filtrage géo + secteur existant (`_is_relevant_devbank`) s'applique automatiquement.

**Entrées `_DEFAULT_SOURCES` :** 2 nouvelles entrées dans `source_registry.py` avec `scraper_module="scraper_devbanks"`, `scraper_func="fetch_devbanks"`, `is_manual=False`.

---

### Groupe B — Scrapers HTML dédiés (nouveaux fichiers)

#### B1 — `scraper_isdb.py` — IsDB (Banque Islamique de Développement)
- **URL cible :** `https://www.isdb.org/project-procurement`
- **Pertinence :** projets Comores, Mayotte, Madagascar
- **Méthode :** scraping HTML avec `requests` + `BeautifulSoup`
- **Filtrage :** géo OI + `INCLUSION_KEYWORDS`
- **Entrée source_registry :** catégorie `International`, `display_order=55`

#### B2 — `scraper_semader.py` — SEMADER Réunion
- **URL cible :** `https://www.semader.re/appels-d-offres`
- **Pertinence :** aménagement, logement, infrastructure Réunion
- **Méthode :** scraping HTML
- **Filtrage :** `INCLUSION_KEYWORDS` (secteurs SSI/CMSI/vidéo/courants faibles)
- **Entrée source_registry :** catégorie `Public`, `display_order=9`

#### B3 — `scraper_chm.py` — Centre Hospitalier Mayotte
- **URL cible :** `https://www.chm-mayotte.fr/appels-d-offres`
- **Pertinence :** marchés hospitaliers Mayotte (SSI, câblage, sécurité)
- **Méthode :** scraping HTML
- **Filtrage :** `INCLUSION_KEYWORDS`
- **Entrée source_registry :** catégorie `Public`, `display_order=37`

---

## Architecture

Aucun changement d'infrastructure. Le pattern appliqué est identique aux scrapers existants :

```
scraper_XXX.py
  └── fetch_XXX() — fonction principale appelée par app.py
        ├── init_db() + SessionLocal()
        ├── start_scraper_run() / finish_scraper_run()
        ├── load_existing_ids() — évite les doublons
        └── insert_if_new() — insertion conditionnelle
```

Les scrapers HTML utilisent `requests` + `BeautifulSoup4` (déjà présents dans l'environnement).

---

## Gestion des erreurs

- Timeout `requests` : 15s (comme les autres scrapers)
- Exception catchée → log warning + `finish_scraper_run(error=...)` pour que le panneau statut l'affiche
- Si la structure HTML change : le scraper lève une exception silencieuse, la source apparaît en erreur dans le panneau statut

---

## Fichiers modifiés / créés

| Fichier | Action |
|---------|--------|
| `scraper_devbanks.py` | Ajout 2 tuples dans `FLUX_DEVBANKS` |
| `source_registry.py` | Ajout 5 entrées dans `_DEFAULT_SOURCES` |
| `scraper_isdb.py` | Création |
| `scraper_semader.py` | Création |
| `scraper_chm.py` | Création |

---

## Critères de succès

- Les 5 sources apparaissent en "🤖 Auto" dans la page Paramètres
- Le bouton "Collecter" les exécute sans erreur
- Les marchés collectés sont filtrés (pas de flood non-pertinent)
- Le panneau statut collecte affiche leur état
