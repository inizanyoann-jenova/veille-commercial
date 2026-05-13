# Design — Lisibilité : Cartes post-collecte + Tableau enrichi
**Date :** 2026-05-13
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** Amélioration de la lisibilité dans `app.py` uniquement — section cartes après collecte + enrichissement du tableau existant

---

## Contexte et problème résolu

L'utilisateur lance une collecte chaque matin, puis doit évaluer les nouveaux marchés. Actuellement :
- Le tableau est dense et ne hiérarchise pas visuellement les opportunités prioritaires
- L'analyse IA est enfouie dans un expander — impossible de voir les infos clés sans cliquer et scroller

Ce design résout ces deux points sans changer le modèle de données, les scrapers, ni les pages Paramètres/Guide.

---

## Architecture des changements

**Fichier modifié :** `app.py` uniquement.

Trois modifications ciblées, indépendantes les unes des autres :

1. **Tracking des nouveaux IDs** — snapshot avant/après collecte dans `st.session_state`
2. **Section cartes post-collecte** — affichage conditionnel en haut de page, encapsulée dans `@st.fragment`
3. **Tableau enrichi** — remplacement du `st.data_editor` par `st.dataframe` avec `column_config`

Aucun changement sur : modèles SQLAlchemy, scrapers, pages, CSS global (on réutilise les classes existantes `.kpi-card`, `.kpi-grid`).

---

## Section 1 — Tracking des nouveaux marchés

### Logique de snapshot

Dans la fonction `_collect_selected_sources()`, avant de lancer les scrapers :

```python
# Snapshot des IDs existants avant collecte
db = new_db()
existing_ids = {t.id for t in db.query(Tender.id).all()}
db.close()
```

Après la collecte :

```python
db = new_db()
all_ids = {t.id for t in db.query(Tender.id).all()}
db.close()
st.session_state["new_tender_ids"] = all_ids - existing_ids
```

### Session state

- `st.session_state["new_tender_ids"]` : `set[str]` — IDs des marchés apparus pendant cette session
- Initialisé à `set()` au démarrage si absent
- Vidé quand l'utilisateur clique "✕ Fermer" sur la section cartes

---

## Section 2 — Cartes post-collecte

### Déclenchement

La section s'affiche uniquement si `st.session_state.get("new_tender_ids")` est non vide. Elle est positionnée **entre le header de page et les KPI**, pour être visible immédiatement sans scroll.

### Contenu d'une carte

Chaque carte reprend le style CSS `.kpi-card` déjà présent. Structure HTML + boutons natifs Streamlit :

```
┌──────────────────────────────────────────────────────────────────┐
│ ▌ 🟢 GO — Score 82/100                        [✕ Fermer tout]   │
│                                                                  │
│  Maintenance SSI — Centre Hospitalier Félix Guyon               │
│  🏝️ La Réunion  ·  🔥 SSI / Détection incendie                  │
│                                                                  │
│  💡 "Marché de maintenance annuelle sur système SSI, cœur de    │
│      métier DEF OI, territoire prioritaire 974."                 │
│                                                                  │
│  [⭐ Sauvegarder]   [✅ Qualifier]   [🔗 Voir source]            │
└──────────────────────────────────────────────────────────────────┘
```

**Règles :**

| Élément | Logique |
|---|---|
| Bandeau couleur gauche | Rouge si score ≥ 65, orange si 35–64, gris si < 35 (classes CSS `.kpi-card`, `.kpi-card.orange`, existantes) |
| Titre | Tronqué à 90 caractères |
| Territoire + Domaine | Détectés via les fonctions `detect_territoire()` / `detect_domaine()` existantes |
| Justification IA | `llm_analysis["justification_score"]` tronquée à 120 chars. Fallback : liste des mots-clés métier détectés |
| Nombre de cartes affichées | 5 maximum, triées par score décroissant |
| Lien "Voir tous les nouveaux" | Affiché si plus de 5 nouveaux marchés — scrolle vers le tableau filtré |
| Bouton ✕ Fermer | Vide `st.session_state["new_tender_ids"]`, fait disparaître la section |

**Boutons d'action sur chaque carte :**
- `⭐ Sauvegarder` → appelle `toggle_saved(id, True)` + `st.cache_data.clear()`
- `✅ Qualifier` → appelle `save_status(id, "En cours")` + `st.cache_data.clear()`
- `🔗 Voir source` → `st.link_button()` vers `t.source`

### Fragment

La section cartes est encapsulée dans `@st.fragment` pour que les actions sur les boutons ne rechargent pas le reste de la page (KPI, tableau).

```python
@st.fragment
def _render_new_tenders_section():
    ...
```

---

## Section 3 — Tableau enrichi

### Remplacement data_editor → dataframe

Le `st.data_editor` actuel passe en `st.dataframe` (lecture seule). Les actions d'édition (statut, montant, étoile) restent dans les expanders de détail, inchangés.

**Avantage :** `st.dataframe` + `column_config` permet les barres de progression et les liens cliquables, non disponibles dans `st.data_editor`.

### Configuration des colonnes

```python
st.dataframe(
    df,
    column_config={
        "Score": st.column_config.ProgressColumn(
            "Score",
            min_value=0,
            max_value=100,
            format="%d",
        ),
        "Source": st.column_config.LinkColumn(
            "Source",
            display_text="Ouvrir ↗",
        ),
        "ID": None,           # masquée
        "Secteur": None,      # masquée
        "Concurrents": None,  # masquée
        "Maint.": None,       # masquée
    },
    hide_index=True,
    use_container_width=True,
)
```

### Filtre rapide "Nouveaux (24h)"

Ajouté dans la sidebar, au-dessus des filtres existants. Implémenté comme `st.checkbox` :

```python
only_recent = st.checkbox("🆕 Nouveaux (24h)", value=False)
```

Quand coché, `load_tenders()` filtre sur `publication_date >= datetime.now() - timedelta(hours=24)`.
La checkbox n'apparaît que si au moins un marché a été publié dans les dernières 24h (évite le bruit).

---

## Ce qui n'est PAS dans ce périmètre

- Layout maître-détail (Option C) — évolution future
- Notifications email — fonctionnalité séparée
- Modification des scrapers, modèles, ou pages Paramètres/Guide
- Mode sombre global
- Graphiques/charts Plotly

---

## Dépendances techniques

Toutes déjà présentes dans le projet :
- Streamlit ≥ 1.33 (pour `@st.fragment`)
- `st.column_config` disponible depuis Streamlit 1.22
- Fonctions `detect_territoire()`, `detect_domaine()`, `toggle_saved()`, `save_status()`, `load_tenders()` — inchangées, réutilisées telles quelles
