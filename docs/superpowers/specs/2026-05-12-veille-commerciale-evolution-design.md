# Design — Évolution Application Veille Commerciale DEF OI

**Date :** 2026-05-12  
**Projet :** Application de veille marchés DEF Océan Indien  
**Stack :** Python · Streamlit · SQLite/SQLAlchemy · Gemini API  
**Scope :** 4 fonctionnalités d'évolution sur base existante

---

## Contexte

L'application existante collecte des marchés publics via des scrapers spécialisés (BOAMP, TED, AFD, Banque Mondiale, Permis de construire, Presse IO, Banques de Développement) et les stocke dans une base SQLite. Un moteur hybride (règles locales + Gemini) attribue un score de pertinence 0–100. L'interface Streamlit permet de filtrer, qualifier et exporter les opportunités.

Toutes les sources actuelles sont conservées sans modification.

---

## Architecture cible

```
┌─────────────────────────────────────────────────────────┐
│                      app.py (Streamlit)                  │
│  Sidebar : checkboxes dynamiques par catégorie           │
│  Page "Sources" : CRUD interface gestion des sites       │
├──────────────┬──────────────┬───────────────────────────┤
│ Scrapers     │ source_      │  generic_scraper.py        │
│ existants    │ registry.py  │  (RSS → HTML fallback)     │
│ (inchangés)  │  (CRUD)      │                            │
├──────────────┴──────────────┴───────────────────────────┤
│                  SQLite def_oi_veille.db                  │
│  TABLE tenders  (existante, inchangée)                    │
│  TABLE sources  (nouvelle) ← registre dynamique          │
├─────────────────────────────────────────────────────────┤
│             llm_analyzer.py (enrichi)                    │
│  Score combiné = 70 % Gemini + 30 % local                │
│  System Prompt réécrit (SSI/CMSI/QHSE complet)          │
└─────────────────────────────────────────────────────────┘
```

---

## Fonctionnalité 1 — Nouvelles sources

### Sources avec scraper automatique (API/flux public)

| Source | Fichier | Méthode technique |
|--------|---------|-------------------|
| DECP / PLACE (incl. Réunion dept 974/976) | `scraper_decp.py` | API data.economie.gouv.fr — filtre `departement_code=974` et `departement_code=976` + mots-clés métier |
| UNGM | `scraper_ungm.py` | Scraping HTML `https://www.ungm.org/Public/Notice/SearchNotices` (requests + BeautifulSoup) |

> **Note :** `scraper_reunion.py` initialement prévu est supprimé du scope — la Région Réunion publie ses marchés via BOAMP (déjà collecté) et DECP (couvert par `scraper_decp.py` avec filtre département 974). Cela évite les doublons.

Ces scrapers suivent exactement le même pattern que les scrapers existants : `fetch_*() -> int` (retourne le nombre d'enregistrements insérés).

### Sources en mode "accès guidé" (manuel)

Pré-chargées dans la table `sources` avec `is_manual = TRUE`. Aucun scraping automatique : un bouton "🔗 Ouvrir" ouvre l'URL dans le navigateur. L'utilisateur peut ensuite coller manuellement une offre via le formulaire existant.

| Source | Catégorie | URL |
|--------|-----------|-----|
| Marché Online | Public | https://www.marcheonline.com |
| Marchés Publics Info | Public | https://www.marches-publics.info |
| e-marchés publics | Public | https://www.e-marches-publics.fr |
| France Marchés | Privé | https://www.france-marches.fr |
| Marchés Sécurisés | Privé | https://www.marches-securises.fr |
| Achatpublic.com | Privé | https://www.achatpublic.com |
| Dematis | Privé | https://www.dematis.com |
| Instao | Privé | https://www.instao.fr |
| Vaao | Privé | https://www.vaao.fr |
| Nukema | Privé | https://www.nukema.fr |
| Deepbloo | International | https://www.deepbloo.com |
| Tenders Go | International | https://www.tendersgo.com |
| Marchés internationaux | International | https://www.marches-internationaux.com |

---

## Fonctionnalité 2 — Gestion dynamique des sources

### Table SQLite `sources`

```sql
CREATE TABLE IF NOT EXISTS sources (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    url            TEXT NOT NULL,
    category       TEXT NOT NULL,      -- 'Public' | 'Privé' | 'International'
    scraper_module TEXT DEFAULT NULL,  -- ex: 'scraper_boamp', NULL si manuel
    scraper_func   TEXT DEFAULT NULL,  -- ex: 'fetch_boamp_tenders'
    is_manual      INTEGER DEFAULT 0,  -- 1 = pas de scraping automatique
    enabled        INTEGER DEFAULT 1,
    notes          TEXT DEFAULT NULL,
    display_order  INTEGER DEFAULT 99
);
```

### Fichier `source_registry.py`

Encapsule tout le CRUD sur la table `sources` :

- `init_sources(db)` — insère les sources par défaut si la table est vide
- `list_sources(db, category=None)` → `list[Source]`
- `add_source(db, name, url, category, ...)` → `Source`
- `remove_source(db, source_id)` → `bool`
- `toggle_enabled(db, source_id)` → `bool`

### Interface de gestion (dans `app.py`)

Section dédiée dans un expander ou un onglet Streamlit "⚙️ Gérer les sources" :

- Tableau listant toutes les sources avec toggle activé/désactivé
- Formulaire "Ajouter une source" : nom, URL, catégorie (Public/Privé/International), notes
- Bouton "🗑️ Supprimer" par ligne (sources manuelles uniquement ; les sources avec scraper dédié sont protégées contre la suppression accidentelle)
- Les sources avec `scraper_module` non null affichent un badge "Auto" ; les autres affichent "Manuel"

---

## Fonctionnalité 3 — Sélection des sources à la carte

### Remplacement des boutons fixes dans le sidebar

Le sidebar actuel contient 7 boutons de collecte indépendants. Ils sont remplacés par :

1. **Checkboxes dynamiques** groupées par catégorie, générées depuis la table `sources`
2. **Un seul bouton** "⚡ Collecter la sélection"
3. Pour les sources `is_manual = True` : checkbox désactivée + bouton "🔗 Ouvrir"

Maquette sidebar :

```
╔══════════════════════════════╗
║  ⚡ Sources de collecte      ║
╠══════════════════════════════╣
║  📋 PUBLIC                   ║
║  ☑ BOAMP — Journal Officiel  ║
║  ☑ DECP / PLACE              ║
║  ☑ TED Europe                ║
║  ☑ Marchés Réunion           ║
║  ☐ Marché Online  [🔗 Ouvrir]║
╠══════════════════════════════╣
║  🏗️ PRIVÉ                    ║
║  ☑ Permis de construire      ║
║  ☑ Presse & Institutions IO  ║
║  ☑ Banques Dev. (BAD/BEI)    ║
╠══════════════════════════════╣
║  🌍 INTERNATIONAL             ║
║  ☑ UNGM                      ║
║  ☑ Banque Mondiale           ║
║  ☑ AFD                       ║
╠══════════════════════════════╣
║  [⚡ Collecter la sélection] ║
╚══════════════════════════════╝
```

### Logique d'exécution

```python
def run_selected_sources(selected_source_ids: list[int], db):
    for source in list_sources(db):
        if source.id not in selected_source_ids:
            continue
        if source.is_manual or not source.scraper_module:
            continue
        module = importlib.import_module(source.scraper_module)
        func = getattr(module, source.scraper_func)
        func()
```

La sélection est persistée en `st.session_state` le temps de la session (pas de persistance cross-session nécessaire).

---

## Fonctionnalité 4 — Analyse IA enrichie

### Score combiné

```python
def compute_combined_score(gemini_score: int, local_score: int,
                            gemini_available: bool) -> int:
    if gemini_available:
        return round(gemini_score * 0.70 + local_score * 0.30)
    return local_score
```

### Nouveaux champs dans `llm_analysis` (JSON)

Les champs existants sont conservés. Ajout de :

| Champ | Type | Description |
|-------|------|-------------|
| `tag_pertinence` | string | `"Très pertinent"` / `"À évaluer"` / `"Hors périmètre"` |
| `domaines_concernes` | list[str] | Sous-domaines détectés (SSI, CMSI, Vidéosurveillance, Courants faibles, QHSE, Maintenance) |
| `justification_score` | string | 1-2 phrases expliquant le score |
| `territoire_ia` | string | Territoire détecté par Gemini |

### System Prompt Gemini (réécrit)

```
Tu es un analyste commercial expert pour DEF Océan Indien, entreprise 
spécialisée en systèmes de sécurité incendie (SSI/CMSI), vidéosurveillance,
courants faibles, et problématiques QHSE (Qualité, Hygiène, Sécurité,
Environnement).

Zone prioritaire : La Réunion (974) et Mayotte (976).
Zone secondaire : Madagascar, Maurice, Comores, France métropole, International.

Cœur de métier DEF OI :
1. SSI : centrales incendie, détecteurs, déclencheurs manuels, CMSI, équipements
   d'alarme de type 1 à 4, tableaux de signalisation
2. Désenfumage / CMSI : volets de désenfumage, extracteurs de fumée, commandes
   manuelles centralisées
3. Vidéosurveillance / CCTV : caméras IP, enregistreurs NVR/DVR, VMS, analytics
4. Courants faibles : contrôle d'accès, interphonie, GTC/GTB, anti-intrusion
5. Maintenance réglementaire : vérifications annuelles SSI, MCO, contrats de
   service, GMAO
6. QHSE : audits incendie, formations sécurité incendie, accompagnement
   réglementaire ERP

EXCLURE impérativement (ne pas scorer > 20) :
- Gardiennage, agents de sécurité, SSIAP, rondes de sécurité
- Sécurité civile, pompiers, secours
- Génie civil pur, VRD, extincteurs seuls (sans composante SSI)
- Électricité générale (HT/BT) sans courants faibles

Réponds UNIQUEMENT en JSON valide avec cette structure exacte :
{
  "score_pertinence": <entier 0-100>,
  "tag_pertinence": "Très pertinent" | "À évaluer" | "Hors périmètre",
  "type_marche": "Travaux" | "Maintenance" | "Fourniture" | "Mixte" | "Inconnu",
  "domaines_concernes": ["SSI", "CMSI", "Vidéosurveillance", "Courants faibles",
                          "QHSE", "Maintenance"],
  "territoire": "La Réunion" | "Mayotte" | "Océan Indien" | "France métropole" |
                 "International" | "Non précisé",
  "marques_concurrentes_citees": ["liste des marques"],
  "risques_penalites": "description courte ou null",
  "justification_score": "1-2 phrases expliquant le score attribué"
}

Barème de score :
- 80-100 : marché SSI/CMSI/vidéosurveillance directement dans le cœur de métier,
           territoire prioritaire (974/976)
- 60-79  : domaine métier présent ET territoire secondaire, OU courants faibles/
           QHSE sur 974/976
- 40-59  : signal ERP à fort potentiel SSI (construction hôpital, école, hôtel),
           marché mixte à évaluer
- 20-39  : faiblement pertinent, hors zone prioritaire ou domaine trop large
- 0-19   : hors périmètre DEF OI, à ignorer
```

### Affichage enrichi dans la fiche commerciale

- Le `tag_pertinence` s'affiche en badge coloré à côté du score
- Les `domaines_concernes` s'affichent en chips/tags
- La `justification_score` s'affiche sous le bandeau Go/No-Go

---

## Fichiers créés / modifiés

### Nouveaux fichiers

| Fichier | Rôle |
|---------|------|
| `source_registry.py` | CRUD table `sources` + données initiales |
| `scraper_decp.py` | Collecte DECP/PLACE (API data.economie.gouv.fr, depts 974/976) |
| `scraper_ungm.py` | Collecte UNGM (scraping HTML BeautifulSoup) |

### Fichiers modifiés

| Fichier | Modifications |
|---------|---------------|
| `database.py` | Ajout `init_sources_table()` dans `init_db()` |
| `llm_analyzer.py` | System Prompt enrichi, score combiné, nouveaux champs JSON |
| `app.py` | Sidebar dynamique, section gestion des sources, affichage enrichi fiche commerciale |

### Fichiers inchangés

`models.py`, `filters.py`, `export_excel.py`, `scraper_boamp.py`, `scraper_ted.py`, `scraper_afd.py`, `scraper_worldbank.py`, `scraper_permis.py`, `scraper_presse.py`, `scraper_devbanks.py`

---

## Contraintes et règles

- Tous les scrapers existants sont conservés sans modification
- La table `tenders` n'est pas altérée (les nouveaux champs LLM restent dans la colonne JSON `llm_analysis`)
- Les sources avec `scraper_module` non null ne peuvent pas être supprimées via l'interface (protection contre la perte accidentelle)
- Le fallback local reste actif si Gemini est indisponible ou quota dépassé
- La sélection des sources n'est pas persistée entre sessions (session_state Streamlit suffit)
- Toutes les sources manuelles pré-chargées ont `is_manual = TRUE` et n'affichent pas de checkbox cochable pour la collecte automatique

---

## Ordre d'implémentation recommandé

1. `source_registry.py` + migration `database.py` (fondation)
2. `llm_analyzer.py` — System Prompt enrichi + score combiné
3. `scraper_decp.py` + `scraper_ungm.py`
4. `app.py` — sidebar dynamique + sélection à la carte
5. `app.py` — section gestion des sources (CRUD UI)
6. `app.py` — affichage enrichi fiche commerciale (nouveaux champs LLM)
