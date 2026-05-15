# Clic tableau → fiche directe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Supprimer le selectbox intermédiaire dans `_render_editor_section` pour que le clic sur une ligne du tableau affiche directement la fiche commerciale, sans friction.

**Architecture:** Un seul fichier modifié — `app.py`. La sélection passe d'un stockage par titre (`sel_title_key`) à un stockage par ID (`_sel_id_{editor_key}`). Le selectbox est supprimé et remplacé par un affichage conditionnel direct. La section Pipeline est mise à jour pour écrire dans la nouvelle clé.

**Tech Stack:** Streamlit, SQLAlchemy, Python 3.11+

---

## Fichiers touchés

| Fichier | Action | Lignes concernées |
|---|---|---|
| `app.py` | Modifier | 1399–1555 (fonction `_render_editor_section`) |
| `app.py` | Modifier | 1653–1703 (deux call sites) |
| `app.py` | Modifier | 1728–1729 (section Pipeline) |

Aucun nouveau fichier. Aucune migration base de données. Aucun test unitaire possible sur du code Streamlit UI — validation par test manuel.

---

### Task 1 : Modifier la signature de `_render_editor_section`

**Fichier :** `app.py:1399-1410`

- [ ] **Remplacer la signature actuelle** (lignes 1399–1410) par :

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

Les paramètres supprimés : `fiche_label`, `sel_title_key`, `sel_box_key`.

- [ ] **Vérifier** que Python ne lève pas d'erreur de syntaxe :

```bash
python -c "import ast, open; ast.parse(open('app.py').read())"
```

ou simplement :

```bash
python -m py_compile app.py
```

Résultat attendu : aucune sortie (pas d'erreur).

- [ ] **Commit :**

```bash
git add app.py
git commit -m "refactor: supprimer params selectbox de _render_editor_section"
```

---

### Task 2 : Remplacer le gestionnaire de clic (titre → ID)

**Fichier :** `app.py:1458-1462`

- [ ] **Remplacer** le bloc commenté "Clic sur une ligne → met à jour le dropdown d'analyse" (lignes 1458–1462) par :

```python
    _sel_id_key = f"_sel_id_{editor_key}"
    if view_event.selection.rows:
        selected_row_idx = view_event.selection.rows[0]
        if selected_row_idx < len(df):
            st.session_state[_sel_id_key] = df.iloc[selected_row_idx]["ID"]
```

- [ ] **Vérifier** la syntaxe :

```bash
python -m py_compile app.py
```

Résultat attendu : aucune sortie.

- [ ] **Commit :**

```bash
git add app.py
git commit -m "refactor: stocker ID au lieu du titre lors du clic tableau"
```

---

### Task 3 : Remplacer le bloc selectbox par le rendu direct

**Fichier :** `app.py:1529-1555`

Le bloc à remplacer est tout ce qui suit le `with st.expander(...)`, soit les lignes 1529–1555 :

```python
    # ── Analyse de la ligne sélectionnée ──────────────────────────────────────
    st.markdown("---")
    st.markdown(_section_html(fiche_title, "Analyse détaillée de l'élément sélectionné"), unsafe_allow_html=True)

    # Déduplique les labels pour éviter la collision de titres identiques
    _seen_titles: dict[str, int] = {}
    _options: list[tuple[str, str]] = []  # (label affiché, ID)
    for r in rows:
        raw = r["Titre"]
        n = _seen_titles.get(raw, 0)
        _seen_titles[raw] = n + 1
        _options.append((raw if n == 0 else f"{raw} [{n + 1}]", r["ID"]))
    _id_by_label = {label: tid for label, tid in _options}
    _labels = [label for label, _ in _options]
    _default = 0
    _sel_t = st.session_state.get(sel_title_key)
    if _sel_t:
        for _i, _r in enumerate(rows):
            if _r["Titre"] == _sel_t:
                _default = _i
                break
    chosen_label = st.selectbox(fiche_label, _labels, index=_default, key=sel_box_key)

    if chosen_label:
        _render_fiche(_id_by_label[chosen_label], editor_key)

    st.markdown("---")
```

- [ ] **Remplacer** l'intégralité de ce bloc par :

```python
    # ── Analyse de la ligne sélectionnée ──────────────────────────────────────
    st.markdown("---")
    st.markdown(_section_html(fiche_title, "Analyse détaillée de l'élément sélectionné"), unsafe_allow_html=True)

    _sel_id = st.session_state.get(f"_sel_id_{editor_key}")
    if _sel_id:
        _render_fiche(_sel_id, editor_key)
    else:
        st.info("👆 Cliquez sur une ligne du tableau pour afficher son analyse.")

    st.markdown("---")
```

- [ ] **Vérifier** la syntaxe :

```bash
python -m py_compile app.py
```

Résultat attendu : aucune sortie.

- [ ] **Commit :**

```bash
git add app.py
git commit -m "feat: clic tableau affiche fiche directement, sans selectbox"
```

---

### Task 4 : Mettre à jour les deux call sites

**Fichier :** `app.py:1653-1703`

Les deux appels à `_render_editor_section` passent encore les anciens paramètres supprimés. Il faut les retirer.

- [ ] **Remplacer** l'appel Marchés Publics (lignes ~1653–1664) par :

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

- [ ] **Remplacer** l'appel Signaux Privés (lignes ~1692–1703) par :

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

- [ ] **Vérifier** la syntaxe :

```bash
python -m py_compile app.py
```

Résultat attendu : aucune sortie.

- [ ] **Commit :**

```bash
git add app.py
git commit -m "fix: mettre à jour call sites _render_editor_section (params supprimés)"
```

---

### Task 5 : Mettre à jour la section Pipeline

**Fichier :** `app.py:1728-1729`

Le Pipeline utilisait `_sel_title_pub` pour pré-sélectionner la fiche. Cette clé n'existe plus — il faut écrire dans `_sel_id_pub_editor` avec l'ID du marché.

- [ ] **Localiser** le bloc (environ ligne 1728) :

```python
if st.button(_short, key=f"pipe_{_pipe_status}_{_it['id']}", use_container_width=True):
    st.session_state["_sel_title_pub"] = _it["title"]
```

- [ ] **Remplacer** par :

```python
if st.button(_short, key=f"pipe_{_pipe_status}_{_it['id']}", use_container_width=True):
    st.session_state["_sel_id_pub_editor"] = _it["id"]
```

- [ ] **Vérifier** la syntaxe :

```bash
python -m py_compile app.py
```

Résultat attendu : aucune sortie.

- [ ] **Commit :**

```bash
git add app.py
git commit -m "fix: pipeline utilise _sel_id_pub_editor au lieu de _sel_title_pub"
```

---

### Task 6 : Test manuel dans le navigateur

- [ ] **Lancer l'application :**

```bash
streamlit run app.py
```

- [ ] **Vérifier — état initial :**
  - La section "Fiche commerciale — Marché Public" affiche `👆 Cliquez sur une ligne du tableau pour afficher son analyse.`
  - Même chose pour "Fiche commerciale — Signal Privé"
  - Aucun selectbox visible dans les deux sections

- [ ] **Vérifier — clic sur une ligne Marchés Publics :**
  - Cliquer sur n'importe quelle ligne du tableau Marchés Publics
  - La page se recharge et la fiche correspondante s'affiche directement sous le tableau
  - Le titre de la fiche correspond au marché cliqué

- [ ] **Vérifier — clic sur une ligne Signaux Privés :**
  - Même comportement dans la section Signaux Privés

- [ ] **Vérifier — Pipeline :**
  - Dans le Pipeline Commercial, cliquer sur un marché (bouton avec le titre tronqué)
  - La fiche de ce marché s'affiche dans la section Marchés Publics

- [ ] **Vérifier — changement de filtre :**
  - Sélectionner un marché (fiche visible)
  - Changer un filtre sidebar (ex : territoire)
  - Si le marché est toujours dans les résultats filtrés : la fiche reste affichée
  - Si le marché sort des résultats filtrés : la fiche s'affiche quand même (l'ID reste valide en base)

- [ ] **Commit final si tout passe :**

```bash
git add app.py
git commit -m "chore: validation manuelle clic tableau → fiche directe OK"
```
