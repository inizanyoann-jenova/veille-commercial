# Spec — Refonte de la fiche marché (layout vertical plat)

**Date :** 2026-05-14
**Périmètre :** `app.py` — fonctions `_render_fiche()` et `_render_strategic_analysis()`
**Problème résolu :** La fiche d'un marché enchaîne 6 blocs de colonnes différents (3+2, 1+1, 1+1) ce qui rend la lecture confuse. L'utilisateur ne sait pas où regarder.
**Approche retenue :** Layout vertical plat (approche B) — sections empilées de haut en bas par ordre de priorité décisionnelle, 2 colonnes maximum.

---

## Architecture cible

### Fonctions impactées

| Fonction | Fichier | Changement |
|---|---|---|
| `_render_fiche()` | `app.py` | Refactorisation complète |
| `_render_strategic_analysis()` | `app.py` | Remplacée par `_render_fiche_body()` |

### Principe de refactorisation

`_render_strategic_analysis()` sera absorbée dans `_render_fiche()` — la séparation en deux fonctions n'a plus de raison d'être une fois le layout aplati. La nouvelle fonction unique `_render_fiche()` délègue le corps à `_render_fiche_body(t, a, domaine, territoire, score)` pour rester testable.

---

## Design des blocs

### Bloc 1 — Header de décision (pleine largeur)

Un seul appel `st.success / st.warning / st.error` contenant :
```
{tag} — Score {score}/100 · {domaine} · {territoire}
```
Suivi d'un `st.caption(justification_score)` si disponible.

**Supprime :** les 4 `st.metric` du haut actuels (Type, Score DEF, Concurrents, Maintenance) qui dupliquaient l'info.

### Bloc 2 — Métriques condensées (une ligne)

`st.columns(5)` affichant dans l'ordre :
1. **Délai restant** — `st.metric("Délai", f"{jours_restants} j")` avec delta coloré
2. **Type** — type de marché (marché public, maintenance, etc.)
3. **Maintenance** — Oui / Non
4. **Concurrents** — nombre de marques citées
5. **Source IA** — "Claude" ou "Règles métier"

### Bloc 3 — Plan d'action (pleine largeur)

```python
st.markdown(f"#### {label_action}")
for i, step in enumerate(steps, 1):
    st.markdown(f"{i}. {step}")
if justif:
    st.info(f"💡 {justif}")
```

Si des risques sont identifiés (pénalités, délai court, concurrents), `st.warning()` immédiatement après les steps — pas dans une colonne séparée.

### Bloc 4 — Atouts DEF OI (pleine largeur)

```python
st.markdown("#### Pourquoi c'est pertinent pour DEF OI")
for atout in atouts:
    st.markdown(atout)
```

Pleine largeur au lieu de la colonne droite actuelle. Les bullets ✅ existants sont conservés tels quels.

### Bloc 5 — Détail technique (expander, fermé par défaut)

`st.expander("📊 Détail du score & mots-clés")` contenant :
- Décomposition du score avec barres `st.progress()` (4 lignes : métier, géo, titre, maintenance)
- Mots-clés métier détectés dans titre + description
- Contexte : type, territoire IA, secteur, concurrents nommés
- Description brute (déjà dans un expander imbriqué — à aplatir ici)

Les informations de ce bloc sont secondaires : elles restent accessibles sans polluer la vue principale.

### Bloc 6 — Actions rapides (pleine largeur, toujours visible)

Ligne de boutons en colonnes [2, 2, 2, 4] :
```
[⭐ Sauvegarder]  [✅ Qualifier → En cours]  [🤖 Réanalyser]
```

Puis `st.expander("📝 Notes internes", expanded=bool(t.notes))` avec le textarea existant.

Les boutons sont remontés avant les notes (actuellement ils étaient après le grand bloc d'analyse).

---

## Comportement des données

Aucun changement de données. `_render_fiche()` reçoit les mêmes paramètres. Les calculs de `jours_restants`, `sm`, `sg`, `sk`, `smaint`, `atouts`, `risques`, `steps`, `label_action` sont identiques — seul le rendu change.

---

## Ce qui ne change pas

- Les fonctions `toggle_saved()`, `save_status()`, `save_notes()`, `run_analysis()` — non touchées
- `_render_new_tenders_section()` — non touchée
- `_render_editor_section()` — non touchée
- Le CSS existant — conservé intégralement
- La page `pages/analytics.py` — non touchée

---

## Critères de succès

1. `_render_fiche()` n'utilise plus de colonnes imbriquées (pas de `st.columns` dans `st.columns`)
2. Aucune information n'est supprimée — tout est accessible soit directement soit via l'expander Bloc 5
3. Le plan d'action et les atouts sont visibles sans scroller plus de 2 écrans
4. Les boutons d'action (Qualifier, Réanalyser) sont visibles avant les notes
