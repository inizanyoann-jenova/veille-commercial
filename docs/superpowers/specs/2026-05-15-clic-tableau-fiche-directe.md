# Design — Clic tableau → fiche directe (sans selectbox)

**Date :** 2026-05-15
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** `app.py` — fonction `_render_editor_section` + section pipeline
**Approche retenue :** Approche A — suppression du selectbox, sélection par ID direct

---

## Problème

Cliquer sur une ligne du tableau met déjà à jour un `st.selectbox` via session state, mais l'utilisateur doit :
1. Scroller jusqu'au selectbox (situé après le bloc d'édition)
2. Constater que la valeur a changé
3. L'analyse s'affiche seulement là

Le selectbox est redondant et crée une friction inutile.

---

## Solution

Supprimer le selectbox. La sélection d'une ligne stocke directement l'ID du marché en session state, et `_render_fiche()` est appelé immédiatement avec cet ID. Si aucune ligne n'est sélectionnée, un message guide invite à cliquer.

---

## Changements dans `_render_editor_section`

### Signature

Deux paramètres supprimés : `sel_title_key` et `sel_box_key`.
Un comportement interne change : la clé session state utilisée devient `_sel_id_{editor_key}`.

```python
def _render_editor_section(
    rows: list[dict],
    section_title: str,
    section_subtitle: str,
    fiche_title: str,
    editor_key: str,
    sel_all_key: str,
    del_btn_key: str,
) -> None:
```

### Sélection au clic

**Avant (lignes ~1459-1462) :**
```python
if view_event.selection.rows:
    selected_row_idx = view_event.selection.rows[0]
    if selected_row_idx < len(df):
        st.session_state[sel_title_key] = df.iloc[selected_row_idx]["Titre"]
```

**Après :**
```python
_sel_id_key = f"_sel_id_{editor_key}"
if view_event.selection.rows:
    selected_row_idx = view_event.selection.rows[0]
    if selected_row_idx < len(df):
        st.session_state[_sel_id_key] = df.iloc[selected_row_idx]["ID"]
```

### Zone d'analyse

**Supprimer** (lignes ~1533-1553) : tout le bloc `_seen_titles`, `_options`, `_id_by_label`, `_labels`, `_default`, `_sel_t`, `st.selectbox`.

**Remplacer par :**
```python
st.markdown("---")
st.markdown(_section_html(fiche_title, "Analyse détaillée de l'élément sélectionné"), unsafe_allow_html=True)

_sel_id = st.session_state.get(f"_sel_id_{editor_key}")
if _sel_id:
    _render_fiche(_sel_id, editor_key)
else:
    st.info("👆 Cliquez sur une ligne du tableau pour afficher son analyse.")
```

---

## Changements dans la section Pipeline (lignes ~1728-1729)

Le pipeline utilisait `_sel_title_pub` (titre). Il doit maintenant utiliser l'ID.

**Avant :**
```python
if st.button(_short, key=f"pipe_{_pipe_status}_{_it['id']}", use_container_width=True):
    st.session_state["_sel_title_pub"] = _it["title"]
```

**Après :**
```python
if st.button(_short, key=f"pipe_{_pipe_status}_{_it['id']}", use_container_width=True):
    st.session_state["_sel_id_pub_editor"] = _it["id"]
```

---

## Appels à `_render_editor_section`

Les deux appels existants perdent les paramètres `sel_title_key`, `fiche_label` et `sel_box_key`.

**Marchés Publics (lignes ~1653-1664) :**
```python
_render_editor_section(
    rows=rows_pub,
    section_title=f"📋 Marchés Publics — {len(rows_pub)} résultats",
    section_subtitle="Modifiez le statut, le montant ou l'étoile directement dans le tableau",
    fiche_title="📋 Fiche commerciale — Marché Public",
    editor_key="pub_editor",
    sel_all_key="_sel_all_pub",
    del_btn_key="del_pub",
)
```

**Signaux Privés (lignes ~1692-1703) :**
```python
_render_editor_section(
    rows=rows_priv,
    section_title=f"🏗️ Signaux Privés — {len(rows_priv)} résultats",
    section_subtitle="Permis de construire, articles presse, institutions, banques de développement",
    fiche_title="🏗️ Fiche commerciale — Signal Privé",
    editor_key="priv_editor",
    sel_all_key="_sel_all_priv",
    del_btn_key="del_priv",
)
```

---

## Gestion des états limites

| Situation | Comportement |
|---|---|
| Premier chargement | `st.info("👆 Cliquez sur une ligne du tableau pour afficher son analyse.")` |
| Filtre changé, sélection toujours dans les résultats | Fiche reste affichée (l'ID en session state est toujours valide) |
| Filtre changé, sélection hors résultats filtrés | Fiche s'affiche quand même — `_render_fiche` fait un `db.query` direct sur l'ID, indépendamment des filtres de la vue |
| Ligne supprimée | `_render_fiche` ne trouve pas le tender en base → retour silencieux → message guide réapparaît |

---

## Ce qui ne change pas

- La logique de `_render_fiche()` — inchangée
- Le tableau `st.dataframe` avec `on_select="rerun"` — inchangé
- Le bloc d'édition rapide (statut, montant, étoile, suppression) — inchangé
- Les filtres sidebar — inchangés
- La section Signaux Privés suit exactement le même pattern que Marchés Publics

---

## Critères de succès

1. Cliquer sur une ligne dans le tableau Marchés Publics affiche immédiatement la fiche, sans interagir avec un selectbox
2. Même comportement dans Signaux Privés
3. Cliquer sur un marché dans le Pipeline commercial affiche sa fiche dans la section Marchés Publics
4. Au premier chargement ou sans sélection, le message guide `👆 Cliquez sur une ligne…` s'affiche
5. Aucune régression sur l'édition rapide (statut, montant, étoile, suppression)
