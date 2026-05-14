# Design — Lot 2 : Graphiques Plotly + Pipeline + Page Analytics
**Date :** 2026-05-14
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** 3 améliorations de visualisation — `app.py` (2 sections) + `pages/analytics.py` (nouveau fichier)

---

## Contexte

Ce lot transforme l'app de liste en outil de pilotage commercial avec des graphiques de tendance, une vue pipeline par statut, et une page analytics dédiée sur l'historique complet.

---

## Architecture

| Composant | Fichier | Type |
|---|---|---|
| Graphiques tendances | `app.py` | Nouvelle section dans expander |
| Vue pipeline | `app.py` | Nouvelle section après les tableaux |
| Page analytics | `pages/analytics.py` | Nouveau fichier Streamlit |

Aucun changement au modèle de données ni aux scrapers.

---

## Feature 1 — Graphiques Plotly tendances

### Emplacement dans `app.py`
Nouvelle section avec `st.expander("📈 Tendances & Statistiques", expanded=False)` insérée **entre les KPI et le séparateur avant les tableaux** (après le bloc CA pipeline existant).

### Données
Fonction `load_chart_data()` avec `@st.cache_data(ttl=300)` :

```python
@st.cache_data(ttl=300)
def load_chart_data() -> dict:
    db = new_db()
    try:
        tenders = db.query(
            Tender.publication_date,
            Tender.relevance_score,
            Tender.llm_analysis,
            Tender.title,
            Tender.description,
            Tender.secteur,
        ).filter(Tender.is_blacklisted != True).all()
        return {"tenders": tenders}
    finally:
        db.close()
```

### 3 graphiques affichés en colonnes

**Graphique 1 — Publications par semaine (30 dernières semaines)**
```python
import plotly.express as px
# Agréger publication_date par semaine ISO, compter les entrées
# Afficher un bar chart vertical, couleur #cc2222
```
- Axe X : semaine (format `Sem. N\nAnnée`)
- Axe Y : nombre de marchés
- Barres couleur rouge DEF (`#cc2222`)
- Titre : "Publications / semaine"

**Graphique 2 — Répartition par territoire (donut)**
```python
# detect_territoire() sur chaque tender → compter par label
# Top 4 territoires + "Autres"
# Donut (pie avec hole=0.5)
```
- Labels : 🏝️ La Réunion, 🏝️ Mayotte, 🌍 Madagascar, etc.
- Titre : "Par territoire"

**Graphique 3 — Répartition par domaine (barres horizontales)**
```python
# detect_domaine() sur chaque tender → compter par label
# Barres horizontales triées par count décroissant
```
- Labels : 🔥 SSI, 💨 CMSI, 📷 Vidéo, ⚡ CF, Autre
- Titre : "Par domaine"

### Rendu
```python
col1, col2, col3 = st.columns(3)
with col1: st.plotly_chart(fig_semaines, use_container_width=True)
with col2: st.plotly_chart(fig_territoire, use_container_width=True)
with col3: st.plotly_chart(fig_domaine, use_container_width=True)
```

---

## Feature 2 — Vue pipeline kanban-like

### Emplacement dans `app.py`
Nouvelle section **après** les deux `_render_editor_section` (marchés publics et privés), avant la section saisie manuelle si elle existe.

### Structure
```python
st.markdown(_section_html("🗂️ Pipeline Commercial", "Vue par statut — marchés publics"), unsafe_allow_html=True)
```

5 colonnes pour les statuts : `À qualifier` / `En cours` / `Soumis` / `Gagné` / `Perdu`

Chaque colonne affiche :
1. Titre du statut + badge count (HTML custom)
2. CA total de la colonne (si montants renseignés) — format `X XXX €`
3. Les 3 premiers titres de marchés (tronqués à 55 chars) en liste, cliquables via `st.button` qui met à jour `st.session_state["_sel_title_pub"]` pour sélectionner le marché dans le tableau

### Données
```python
@st.cache_data(ttl=60)
def load_pipeline() -> dict[str, list[dict]]:
    """Retourne les marchés publics groupés par statut."""
    db = new_db()
    try:
        from sqlalchemy import or_
        tenders = db.query(Tender).filter(
            Tender.is_blacklisted != True,
            or_(Tender.secteur == "Public", Tender.secteur == None),
        ).all()
        result = {s: [] for s in ["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]}
        for t in tenders:
            s = t.status or "À qualifier"
            if s in result:
                result[s].append({"id": t.id, "title": t.title or "Sans titre", "amount": t.amount})
        return result
    finally:
        db.close()
```

### Comportement
- Lecture seule — pas de drag-and-drop
- Cliquer un titre → met à jour `st.session_state["_sel_title_pub"]` → le tableau du dessus sélectionne ce marché dans le selectbox
- Pipeline marchés publics uniquement (les privés ont leur propre logique de statut moins avancée)

---

## Feature 3 — Page Analytics (`pages/analytics.py`)

### Structure de la page

```
⚙️ Analytics — DEF OI
│
├── KPIs globaux (4 métriques)
│   Total collecté | Taux GO | CA Gagné | Sources actives
│
├── 📈 Évolution mensuelle (courbe)
│   Marchés collectés par mois sur toute la durée
│
├── 🏆 Top 5 sources par volume
│   Tableau simple : source → nombre de marchés
│
└── 🥧 Publics vs Privés
    Donut : répartition secteur
```

### Données
Toutes issues de requêtes SQLAlchemy directes sur `Tender`. Pas de nouveau modèle.

**KPIs globaux :**
```python
total = db.query(Tender).filter(Tender.is_blacklisted != True).count()
nb_go = db.query(Tender).filter(Tender.relevance_score >= 65, Tender.is_blacklisted != True).count()
taux_go = round(nb_go / total * 100) if total else 0
ca_gagne = db.query(func.sum(Tender.amount)).filter(Tender.status == "Gagné", Tender.amount != None).scalar() or 0
nb_sources = db.query(func.count(func.distinct(Tender.source))).scalar()
```

**Évolution mensuelle :**
```python
# GROUP BY strftime('%Y-%m', publication_date)
# → liste de (mois, count) triée chronologiquement
# → st.line_chart ou plotly line
```

**Top 5 sources :**
```python
# GROUP BY source, ORDER BY count DESC, LIMIT 5
# → st.dataframe simple, 2 colonnes : Source | Marchés
```

**Publics vs Privés :**
```python
# Compter secteur == "Public" (ou None) vs secteur == "Privé"
# → donut Plotly
```

### Navigation
Lien vers cette page dans la sidebar de `app.py` via `st.page_link("pages/analytics.py", label="📈 Analytics")`, ajouté à côté de Paramètres et Guide.

---

## Dépendances techniques

- `plotly` — à vérifier dans `requirements.txt` (probablement déjà présent via Streamlit)
- Toutes les autres dépendances déjà présentes

---

## Ce qui n'est PAS dans ce périmètre
- Drag-and-drop dans le pipeline (React requis)
- Export des graphiques en PNG/PDF
- Filtres de date sur la page Analytics
- Pipeline pour les marchés privés
- Graphique score moyen par source
