# Design — Extension Marché Privé (couverture complète)
**Date :** 2026-05-02  
**Projet :** DEF Océan Indien — Veille Marchés  
**Périmètre :** Ajout de la veille marché privé & signaux privés à l'app Streamlit existante — couverture maximale : presse, institutions, permis de construire, banques de développement régionales

---

## Contexte

L'application couvre actuellement les marchés **publics** via BOAMP, TED, AFD et Banque Mondiale. L'objectif est d'ouvrir la veille aux **opportunités et signaux privés** : permis de construire (signal en amont), presse locale IO, flux institutionnels régionaux (Région, CCI, intercommunalités, bailleurs sociaux), et banques de développement régionales (BAD, BEI) pour Madagascar/Maurice/Comores. Périmètre métier inchangé : SSI/CMSI/Vidéosurveillance/Courants faibles.

---

## Architecture & flux de données

Trois nouveaux scrapers s'ajoutent aux 4 existants :

```
Sit@del2 API (data.gouv.fr)      ──► scraper_permis.py  ──► BDD SQLite (Tender)
Flux RSS presse + institutions IO ──► scraper_presse.py  ──► BDD SQLite (Tender)
BAD / BEI APIs & RSS              ──► scraper_devbanks.py ──► BDD SQLite (Tender)
```

Toutes les opportunités transitent par le même modèle `Tender` et la même base SQLite. Les fonctions `detect_territoire()`, `detect_domaine()`, `calc_score()` et `is_relevant_def()` existantes s'appliquent sans modification.

---

## Modèle de données

Deux colonnes ajoutées au modèle `Tender` existant :

| Colonne | Type | Valeurs possibles |
|---|---|---|
| `secteur` | String | `"Public"` / `"Privé"` |
| `type_opportunite` | String | `"Marché Public"` / `"Permis Construire"` / `"Presse"` / `"Institution"` / `"Banque Dev."` |

Les entrées existantes gardent `secteur=None` (compatibilité rétroactive).  
**Important :** SQLite ne supporte pas `ALTER TABLE ADD COLUMN` via `create_all()` sur une table existante — la migration doit être faite explicitement dans `init_db()` avec `ALTER TABLE IF NOT EXISTS`.

**Mapping des champs :**

| Champ `Tender` | Permis construire | Article presse/institution | Projet BAD/BEI |
|---|---|---|---|
| `title` | Objet du permis | Titre de l'article | Titre du projet |
| `description` | Adresse + surface + type | Résumé RSS | Description projet |
| `source` | URL data.gouv.fr | URL de l'article | URL fiche projet |
| `publication_date` | Date de dépôt | Date publication | Date approbation |
| `deadline` | `None` | `None` | Date clôture si dispo |
| `status` | `"À qualifier"` | `"À qualifier"` | `"À qualifier"` |
| `secteur` | `"Privé"` | `"Privé"` | `"Public"` |
| `type_opportunite` | `"Permis Construire"` | `"Presse"` ou `"Institution"` | `"Banque Dev."` |

---

## Scraper 1 — `scraper_permis.py`

**Source :** Dataset Sit@del2, DGALN / data.gouv.fr via API OpenDataSoft (même technologie que BOAMP).

**Filtres :**
- Départements : `974` et `976`
- Types bâtiments : ERP catégories 1–4, habitations collectives R+3 min, bâtiments industriels/entrepôts
- Fenêtre : 12 derniers mois (glissant)

**Sortie :** `type_opportunite="Permis Construire"`, `secteur="Privé"`. Déduplication sur identifiant permis.

---

## Scraper 2 — `scraper_presse.py`

Lit les flux RSS. Deux sous-catégories : **presse** et **institutions**.

### Presse locale

| Territoire | Média | Type | Notes |
|---|---|---|---|
| La Réunion | Le JIR | RSS | Journal de l'île |
| La Réunion | Le Quotidien | RSS | |
| La Réunion | Zinfos974 | RSS | Info continue |
| La Réunion | Imaz Press Réunion | RSS | |
| La Réunion | Réunion la 1ère | RSS | francetvinfo.fr/regions/reunion |
| La Réunion | Clicanoo.re | RSS | |
| La Réunion | Batiactu (DOM) | RSS | BTP national, catégorie DOM-TOM |
| Mayotte | Mayotte Hebdo | RSS | |
| Mayotte | Journal de Mayotte | RSS | lejournaldemayotte.yt |
| Mayotte | Kwezi.fr | RSS | |
| Mayotte | Mayotte la 1ère | RSS | francetvinfo.fr/regions/mayotte |
| Maurice | L'Express Maurice | RSS | lexpress.mu |
| Maurice | Le Défi Média | RSS | defimedia.info |
| Maurice | Business Magazine | RSS | Signaux projets privés |
| Madagascar | La Tribune de Madagascar | RSS | latribune.mg |
| Madagascar | L'Express de Madagascar | RSS | lexpressmada.com |
| Madagascar | Midi Madagasikara | RSS | |
| Comores | Alwatwan | RSS | |
| Comores | HZK-Presse | RSS | |
| Comores | La Gazette des Comores | RSS | |

### Flux institutionnels (Région, intercommunalités, bailleurs)

| Territoire | Institution | Type | Pertinence |
|---|---|---|---|
| La Réunion | Région Réunion | RSS actualités | Projets d'investissement régionaux |
| La Réunion | Conseil Départemental 974 | RSS | Projets publics co-financés |
| La Réunion | CCI Réunion | RSS / actualités | Projets entreprises |
| La Réunion | CINOR (intercommunalité Nord) | RSS | Chantiers intercommunaux |
| La Réunion | CIVIS (intercommunalité Sud) | RSS | |
| La Réunion | CIREST (intercommunalité Est) | RSS | |
| La Réunion | CASUD (intercommunalité Sud) | RSS | |
| La Réunion | TCO (Territoire Côte Ouest) | RSS | |
| La Réunion | SPL Horizon (aménagement) | RSS | Programmes neufs |
| La Réunion | SHLMR (bailleur social) | RSS/actus | Construction logements |
| La Réunion | Erilia Réunion | RSS/actus | Bailleur social |
| La Réunion | SODIAC | RSS/actus | Bailleur social |
| Mayotte | Conseil Départemental 976 | RSS | |
| Mayotte | CCI Mayotte | RSS | |
| Mayotte | SIM (Sté Immobilière Mayotte) | RSS/actus | Construction logements |

> Les URLs RSS exactes seront validées en début d'implémentation. Les institutions sans flux RSS structuré seront intégrées via scraping léger de leur page "Actualités" si disponible.

**Pipeline par entrée :**
1. Téléchargement via `feedparser`
2. Filtrage par `KEYWORDS_CONSTRUCTION` (presse) ou insertion directe (institutions)
3. Détection territoire via `detect_territoire()` existant
4. Calcul score via `calc_score()` existant
5. Déduplication sur hash MD5 de l'URL
6. Insertion `Tender` avec `type_opportunite="Presse"` ou `"Institution"`, `secteur="Privé"`

---

## Scraper 3 — `scraper_devbanks.py`

Banques de développement régionales couvrant la zone Océan Indien, complémentaires à l'AFD et la Banque Mondiale déjà présentes.

| Institution | Zone | Méthode d'accès | Notes |
|---|---|---|---|
| **BAD** (Banque Africaine de Développement) | Madagascar, Comores | API REST projectsportal.afdb.org | Projets actifs, filtrés par pays IO |
| **BEI** (Banque Européenne d'Investissement) | Tous (financement UE) | RSS news + API projets | eib.org/en/rss/all-news |
| **COI** (Commission de l'Océan Indien) | Zone IO entière | RSS actualités | Programmes régionaux (SWIO, ARCHIPELAGO…) |
| **JICA** (Japon) | Madagascar | RSS actualités | Active sur infrastructure Madagascar |
| **KfW** (Allemagne) | Madagascar, Maurice | RSS | Projets énergie/infrastructure |

**Pipeline :** même logique que scraper_afd.py et scraper_worldbank.py — filtrage par mots-clés métier + territoire IO.

**Sortie :** `type_opportunite="Banque Dev."`, `secteur="Public"` (ce sont des financements publics).

---

## Mots-clés construction (`filters.py`)

Nouvelle liste `KEYWORDS_CONSTRUCTION` :

```python
KEYWORDS_CONSTRUCTION = [
    "construction", "chantier", "permis de construire", "projet immobilier",
    "immeuble", "résidence", "hôtel", "hôpital", "clinique", "ehpad",
    "école", "lycée", "université", "centre commercial", "mall",
    "entrepôt", "usine", "réhabilitation", "rénovation", "extension",
    "bâtiment", "programme immobilier", "logements", "infrastructure",
    "complexe", "siège social", "campus",
]
```

---

## Interface (`app.py`)

### Sidebar — nouvelles sources

Après les 4 sources existantes, 3 nouveaux boutons :
- `🏗️ Collecter Permis de construire (974 & 976)`
- `📰 Collecter Presse & Institutions (IO)`
- `🌍 Collecter BAD / BEI / COI`

Ces 3 scrapers s'ajoutent au bouton `⚡ Toutes les sources`.

### Corps de page — nouvelle section

Entre le tableau marchés publics et l'expander "Saisie manuelle" :

```
── [Séparateur] ─────────────────────────────────────────────────
🏗️ Signaux & Opportunités Marché Privé / Institutions

[KPI : Permis construire] [KPI : Presse] [KPI : Institutions] [KPI : À qualifier]

Tableau filtrable (mêmes filtres sidebar) :
  Titre | Source | Territoire | Type | Score | Publication | Statut
```

La colonne `Type` distingue `Permis Construire` / `Presse` / `Institution` / `Banque Dev.` d'un coup d'œil.

---

## Ce qui n'est PAS dans ce périmètre

- Scraping de plateformes privées type achatpublic.com (trop fragile)
- Google News RSS (sources directes préférées)
- Analyse LLM automatique — reste à la demande comme pour le public
- Couverture permis de construire hors DOM (pas d'open data équivalent)

---

## Dépendances techniques

- `feedparser` — parsing RSS (à ajouter à `requirements.txt`)
- `requests` — déjà présent
- API Sit@del2 — endpoint public, sans authentification
- APIs BAD / BEI / COI — endpoints publics, sans authentification
