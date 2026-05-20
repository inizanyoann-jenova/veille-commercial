# Spec — Panneau de statut post-collecte (sidebar)

**Date :** 2026-05-20  
**Scope :** app.py uniquement — sidebar, fonction de collecte

---

## Contexte

Après un clic sur "⚡ Lancer la collecte", l'utilisateur n'a aucune visibilité sur les sources qui ont fonctionné ou échoué, même lorsqu'aucun résultat nouveau n'est trouvé. La sidebar affiche uniquement les sources ayant ramené des résultats (via checkboxes). Les erreurs sont affichées en ligne dans le spinner, puis disparaissent.

---

## Objectif

Afficher dans la sidebar, sous le bouton "Lancer la collecte", un panneau permanent (jusqu'à la prochaine collecte) montrant le statut de chaque source automatique.

---

## Données

### Nouvelle clé `session_state["collection_status"]`

Liste de dicts, une entrée par source automatique tentée :

```python
[
  {"name": "BOAMP",   "nb_new": 12, "error": None},
  {"name": "Nukema",  "nb_new": 0,  "error": "ConnectionTimeout: 30s"},
  {"name": "TED",     "nb_new": 3,  "error": None},
  # ... toutes les sources enabled non-manuelles
]
```

- `nb_new` : nombre de marchés nouveaux ajoutés par cette source (0 si aucun ou si erreur)
- `error` : message d'erreur stringifié (`str(exc)`) ou `None`

---

## Modifications

### 1. `_collect_all_enabled_sources()` — app.py:835

Ajouter `per_source_status: list[dict] = []` avant la boucle.

Dans la boucle, avant le `try`, initialiser `_src_error: str | None = None`. Dans le bloc `except`, assigner `_src_error = str(exc)`. Après le diff d'IDs :
```python
per_source_status.append({
    "name": source.name,
    "nb_new": len(new_ids),   # 0 si erreur ou rien trouvé
    "error": _src_error,
})
```
Note : en Python 3, `exc` est supprimé du scope à la sortie du bloc `except` — d'où la variable intermédiaire `_src_error`.

À la fin, persister : `st.session_state["collection_status"] = per_source_status`

Supprimer l'affichage des erreurs via `st.warning(err)` (ligne 931-932) — géré par le nouveau composant.

### 2. `_render_collection_status_sidebar()` — nouveau `@st.fragment`

Emplacement dans app.py : juste avant la sidebar (ou en début de section sidebar), appelé depuis la sidebar.

**Structure :**

```
── Dernière collecte ──────────
  [ 16 OK ]  [ 1 Err ]  [ 29 marchés ]

  ⚠ SOURCES EN ERREUR
  ┌────────────────────────────┐
  │ ✗ Nukema              err  │
  │   ConnectionTimeout: 30s   │
  └────────────────────────────┘

  ▾ voir toutes les sources (st.expander)
    ✓ BOAMP ........... 12 résultats
    ✓ DECP .............  4 résultats
    · VAAO .............  0 résultat
    ✗ Nukema .......... erreur
    ...
```

**Codes couleur :**
- `#22c55e` (vert) — source OK avec résultats > 0
- `#fbbf24` (jaune) — source OK mais 0 résultat
- `#f87171` (rouge) — source en erreur

**Logique d'affichage :**
- Si `collection_status` absent du session_state : ne rien afficher
- KPI row : 3 colonnes Streamlit (`st.columns(3)`) avec `st.metric`
- Section erreurs : affichée uniquement si au moins 1 erreur, avec `st.markdown` stylé (HTML inline pour correspondre au thème sombre)
- Expander : liste toutes les sources avec icône + nom + nb résultats

### 3. Sidebar — app.py:1094

Remplacer le bloc lignes 1094–1101 (checkboxes "Résultats — filtrer par source") par :

```python
_render_collection_status_sidebar()

# Checkboxes de filtre (inchangées, toujours affichées si collection_results présent)
_col_results = st.session_state.get("collection_results", {})
if _col_results:
    st.markdown("**Filtrer par source :**")
    for _src_name, _nb_new in sorted(_col_results.items()):
        st.checkbox(f"{_src_name} ({_nb_new})", key=f"src_filter_{_src_name}")
```

---

## Comportement attendu

| Scénario | Affichage |
|----------|-----------|
| Toutes sources OK, résultats trouvés | KPIs verts, section erreurs absente, expander liste tout en vert/jaune |
| Toutes sources OK, 0 résultat | KPIs verts, "0 marchés", expander liste tout en jaune |
| 1+ sources en erreur | KPI erreur rouge, section erreurs visible avec message, expander liste tout |
| Pas encore de collecte | Rien affiché (session_state vide) |

---

## Non-scope

- Pas de persistance BDD du statut (déjà géré par `ScraperRun`)
- Pas de modification des scrapers
- Pas de modification des autres pages
- Pas de nouveau test automatisé (composant UI pur)
