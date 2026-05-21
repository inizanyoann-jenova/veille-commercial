# Spec — Statut analyse Mistral dans la sidebar post-collecte

**Date :** 2026-05-21  
**Statut :** Approuvé

---

## Contexte

Après un clic sur "⚡ Lancer la collecte", l'app collecte les marchés puis lance uniquement
une analyse locale (`_run_auto_analysis`). L'analyse Mistral/LLM ne se déclenche que via un
bouton séparé "🤖 Analyser en lot". Il n'existe pas de retour visuel dans la sidebar indiquant
si Mistral a traité les nouveaux marchés.

## Objectif

1. Déclencher automatiquement l'analyse Mistral (ou Claude selon `LLM_PROVIDER`) après chaque collecte.
2. Afficher un bloc visuel dans la sidebar montrant le résultat de cette analyse.

---

## Architecture

### Déclenchement (app.py — `_collect_all_enabled_sources`)

Après `_run_auto_analysis()` et `_clear_tender_caches()`, si `all_new_ids` est non vide :

- Appel de `auto_analyze_claude(db, max_per_run=10)` (route déjà vers Mistral ou Claude via `LLM_PROVIDER`)
- `nb_attempted = min(len(all_new_ids), 10)` calculé avant l'appel
- Résultat stocké dans `st.session_state["llm_analysis_status"]` :

```python
{
    "nb_done": int,       # marchés analysés avec succès
    "nb_failed": int,     # nb_attempted - nb_done (retours None de l'API)
    "retry_after": int,   # -1 = pas de quota, >= 0 = secondes à attendre
    "provider": str,      # "mistral" ou "claude"
    "error": str | None,  # exception inattendue
}
```

- Si aucun nouveau marché, la clé n'est pas écrite → le bloc n'apparaît pas dans la sidebar.

### Affichage (app.py — `_render_collection_status_sidebar`)

Fragment Streamlit existant (`@st.fragment`). Ajout à la fin :

- Lit `st.session_state.get("llm_analysis_status")`
- Si absent : ne rend rien
- Si présent :
  - Header violet `"Analyse IA — {Provider}"`
  - **Cas erreur inattendue** : bloc rouge avec message tronqué à 120 chars
  - **Cas quota atteint** (`retry_after >= 0`) : `st.warning` avec délai en minutes
  - **Cas succès** : 2 métriques côte à côte — ✅ Analysés / 📋 En attente

---

## Comportement aux limites

| Situation | Comportement |
|---|---|
| `all_new_ids` vide après collecte | Analyse LLM non déclenchée, bloc absent |
| Clé API Mistral absente | Exception catchée → bloc rouge avec message d'erreur |
| Quota API atteint (`retry_after >= 0`) | `st.warning` avec délai estimé en minutes |
| 0 marché analysé (tous déjà traités) | Bloc affiché avec `nb_done = 0`, `En attente = 0` |

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `app.py` | `_collect_all_enabled_sources()` : ajout déclenchement LLM auto |
| `app.py` | `_render_collection_status_sidebar()` : ajout bloc visuel Analyse IA |

Aucun nouveau fichier. Aucune modification de `llm_analyzer.py`.
