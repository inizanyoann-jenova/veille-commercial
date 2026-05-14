# Design — 5 améliorations DEF OI Veille Marchés

**Date :** 2026-05-15
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** `app.py` · `models.py` · `database.py` · `source_registry.py` · `pages/analytics.py` · `pages/parametres.py`
**Approche retenue :** Approche 3 — APScheduler hebdomadaire avec fallback au démarrage, tout en SQLite existant.

---

## Vue d'ensemble

Cinq améliorations indépendantes implémentées en une seule session :

| ID | Feature | Fichiers principaux |
|---|---|---|
| A | Recherche full-text sur les marchés | `app.py` |
| B | Historique de collecte par source | `database.py`, `models.py`, `app.py`, `pages/parametres.py`, scrapers |
| C | Ré-validation automatique hebdomadaire | `source_registry.py`, `database.py`, `app.py` |
| D | Tags prédéfinis sur les marchés | `models.py`, `database.py`, `app.py` |
| E | KPIs commerciaux enrichis dans Analytics | `pages/analytics.py` |

---

## A — Recherche full-text

### Comportement

- Barre `st.text_input("🔍 Rechercher un marché…")` placée en haut de `app.py`, au-dessus de la liste des marchés
- Filtre sur `Tender.title` et `Tender.description` via `func.lower(col).contains(term.lower())`
- Cumulable avec tous les filtres existants (territoire, domaine, statut, score) — logique **AND** : tous les filtres actifs s'appliquent simultanément
- Champ vide = aucun filtre supplémentaire (comportement neutre)

### Ce qui ne change pas

- Le composant de carte existant — inchangé
- Les filtres sidebar — inchangés, appliqués en plus de la recherche

### Aucune nouvelle table ni migration

---

## B — Historique de collecte

### Nouvelle table `scraper_runs`

```python
class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String, nullable=False)
    started_at  = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    nb_found    = Column(Integer, default=0)
    nb_new      = Column(Integer, default=0)
    error       = Column(String, nullable=True)
    status      = Column(String, default="running")  # "ok" | "error" | "running"
```

### Helpers dans `database.py`

```python
def start_scraper_run(db, source_name: str) -> int:
    """Crée un run, retourne son id."""

def finish_scraper_run(db, run_id: int, nb_found: int, nb_new: int, error: str | None = None) -> None:
    """Clôture un run existant."""
```

### Intégration dans les scrapers

Les 15 scrapers suivants sont concernés : `scraper_boamp`, `scraper_ted`, `scraper_afd`, `scraper_worldbank`, `scraper_permis`, `scraper_devbanks`, `scraper_presse`, `scraper_ungm`, `scraper_decp`, `scraper_marcheonline`, `scraper_vaao`, `scraper_dept974`, `scraper_tendersgo`, `scraper_nukema`, `scraper_marchespublicsinfo`, `scraper_instao`, `scraper_marchessecurises`.

Chaque scraper encadre sa collecte :
```python
run_id = start_scraper_run(db, "BOAMP")
try:
    ...
    finish_scraper_run(db, run_id, nb_found=n, nb_new=m)
except Exception as e:
    finish_scraper_run(db, run_id, nb_found=0, nb_new=0, error=str(e))
```

### Affichage

**Paramètres** — nouvelle section "📊 Historique de collecte" :
- Tableau par source : dernière date, nb trouvés, nb nouveaux, statut ✅/❌
- Les 10 derniers runs par source

**Sidebar (`app.py`)** — sous chaque source dans l'expander "Gérer les sources" :
- Texte compact : `"Dernière collecte il y a 4h — 12 trouvés"` ou `"⚠️ Erreur il y a 2j"`
- Calculé depuis `ScraperRun` en cache (`@st.cache_data(ttl=300)`)

---

## C — Ré-validation automatique hebdomadaire

### Nouvelles colonnes sur `Source`

```python
ping_failures_count = Column(Integer, default=0)
last_ping_at        = Column(DateTime, default=None)
```

Migration idempotente dans `init_db()` (même pattern que `is_validated`).

### Scheduler (`app.py`)

```python
from apscheduler.schedulers.background import BackgroundScheduler

def _run_weekly_ping():
    """Ping toutes les sources is_validated=True, invalide après 3 échecs consécutifs."""
    ...

scheduler = BackgroundScheduler()
scheduler.add_job(_run_weekly_ping, "interval", weeks=1)
scheduler.start()
```

Lancé une seule fois grâce au guard Streamlit :
```python
if "scheduler_started" not in st.session_state:
    scheduler.start()
    st.session_state["scheduler_started"] = True
```

### Fallback au démarrage

Au démarrage de l'app, si une source validée a `last_ping_at IS NULL` ou `last_ping_at < now() - 8 jours` → ping immédiat en background thread (non bloquant).

### Logique de ping

```python
def _ping_source(db, source) -> bool:
    try:
        resp = requests.get(source.url, timeout=8, allow_redirects=True)
        ok = resp.status_code < 400
    except Exception:
        ok = False

    if ok:
        source.ping_failures_count = 0
    else:
        source.ping_failures_count += 1
        if source.ping_failures_count >= 3:
            source.is_validated = False

    source.last_ping_at = datetime.utcnow()
    db.commit()
    return ok
```

### Affichage sidebar

Sources avec `ping_failures_count >= 1` et `is_validated=True` : badge `⚠️` à côté du nom dans l'expander "Gérer les sources".

---

## D — Tags prédéfinis

### Liste fixe

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

Définie dans `app.py`. Modifiable directement dans le code.

### Modèle

```python
# models.py — Tender
tags = Column(JSON, default=list)
```

Migration idempotente dans `init_db()`.

### UI

**Fiche marché** — `st.multiselect("Tags", options=TENDER_TAGS, default=tender.tags)`, sauvegardé sur changement.

**Cartes de la liste principale** — chips colorées sous le titre si `tender.tags` non vide :
```python
if tender.tags:
    st.markdown(" ".join(f"`{t}`" for t in tender.tags))
```

**Sidebar** — filtre optionnel `st.multiselect("Filtrer par tag", TENDER_TAGS)` dans la section filtres. Vide = pas de filtre.

---

## E — KPIs commerciaux enrichis

### Nouvelles métriques

Ajoutées dans `pages/analytics.py`, nouvelle ligne de 4 colonnes sous les métriques actuelles :

| KPI | Requête SQL |
|---|---|
| Taux de conversion | `COUNT(status="Gagné") / COUNT(status="Soumis") * 100` |
| CA prévisionnel | `SUM(amount) WHERE status IN ("Soumis", "En cours") AND amount IS NOT NULL` |
| Win rate par source | Tableau `source → nb_gagné / nb_soumis` (top 5) |
| Délai moyen traitement GO | `AVG(deadline - publication_date) WHERE relevance_score >= 65` |

### Affichage

- Les 3 premières métriques : `st.metric` dans une ligne de 4 colonnes (avec la 4e colonne pour le délai)
- Win rate par source : petit `st.dataframe` compact sous la ligne de KPIs, 5 lignes max
- Cachés via `@st.cache_data(ttl=120)` comme les KPIs existants

### Gestion des cas vides

- Taux de conversion = `"—"` si aucun marché "Soumis"
- CA prévisionnel = `0 €` si aucun marché avec montant
- Win rate = tableau vide masqué si pas de données

---

## Migrations requises

Toutes idempotentes, ajoutées dans `init_db()` de `database.py` :

```sql
-- Table scraper_runs (nouvelle)
CREATE TABLE IF NOT EXISTS scraper_runs (...)

-- Source : colonnes ping
ALTER TABLE sources ADD COLUMN ping_failures_count INTEGER DEFAULT 0
ALTER TABLE sources ADD COLUMN last_ping_at DATETIME DEFAULT NULL

-- Tender : colonne tags
ALTER TABLE tenders ADD COLUMN tags JSON DEFAULT '[]'
```

---

## Dépendances

| Package | Usage | Déjà présent ? |
|---|---|---|
| `apscheduler` | Scheduler hebdomadaire (feature C) | À vérifier |
| `requests` | HTTP ping (feature C) | Oui (`pages/parametres.py`) |

---

## Critères de succès

1. **A** — La barre de recherche filtre les marchés en temps réel, compatible avec les filtres sidebar existants
2. **B** — Chaque collecte est loguée ; la sidebar affiche "il y a Xh" et Paramètres montre l'historique complet
3. **C** — Le ping hebdomadaire tourne sans bloquer l'UI ; une source échouant 3 fois consécutives passe à `is_validated=False`
4. **D** — Les tags sont sauvegardés par marché, filtrables depuis la sidebar, visibles sur les cartes
5. **E** — Les 4 nouveaux KPIs s'affichent sans erreur même si les données sont nulles ou absentes

---

## Ce qui ne change pas

- La logique des scrapers existants (sauf ajout de `start/finish_scraper_run`)
- Le credential manager
- Les fiches marchés (sauf ajout du multiselect tags)
- Le CSS et le layout existants
- La logique `is_validated` déjà en place
