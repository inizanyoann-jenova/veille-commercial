# Mistral Status Sidebar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déclencher automatiquement l'analyse Mistral après chaque collecte et afficher un bloc visuel de statut dans la sidebar.

**Architecture:** On modifie `_collect_all_enabled_sources()` pour appeler `auto_analyze_claude()` après la collecte et stocker le résultat dans `st.session_state["llm_analysis_status"]`. Le fragment existant `_render_collection_status_sidebar()` lit cette clé et affiche un bloc visuel violet "Analyse IA". La vérification se fait par non-régression des tests existants + vérification manuelle dans l'app.

**Tech Stack:** Python 3.11, Streamlit, pytest, `llm_analyzer.auto_analyze_claude`

---

## File Map

| Fichier | Changement |
|---|---|
| `app.py` | Modifier `_collect_all_enabled_sources()` (lignes ~1293-1295) et `_render_collection_status_sidebar()` (ligne ~1443) |

Aucun nouveau fichier. `app.py` ne peut pas être importé dans les tests sans contexte Streamlit, donc la vérification se fait via non-régression + vérification manuelle.

---

### Task 1 : Auto-trigger Mistral dans `_collect_all_enabled_sources`

**Files:**
- Modify: `app.py:1293-1295`

- [ ] **Step 1 : Vérifier le contexte exact avant modification**

Lire [app.py](app.py) lignes 1288-1296 et confirmer que le bloc ressemble à :

```python
        # Mise à jour de l'état et affichage
        _update_session_state(per_source_new, per_source_status, all_new_ids)
        _display_results(total, go_count, etude_count, pass_count, claude_ok, errors, all_new_ids)

    # Analyse automatique post-collecte
    _run_auto_analysis()
    _clear_tender_caches()
```

- [ ] **Step 2 : Remplacer le bloc post-collecte**

Dans [app.py](app.py), remplacer :

```python
    # Analyse automatique post-collecte
    _run_auto_analysis()
    _clear_tender_caches()
```

par :

```python
    # Analyse automatique post-collecte (locale)
    _run_auto_analysis()

    # Analyse LLM automatique si de nouveaux marchés existent
    if all_new_ids:
        _nb_attempted = min(len(all_new_ids), 10)
        _db_llm = new_db()
        try:
            _nb_done, _retry_after = auto_analyze_claude(_db_llm, max_per_run=10)
            st.session_state["llm_analysis_status"] = {
                "nb_done": _nb_done,
                "nb_failed": _nb_attempted - _nb_done,
                "retry_after": _retry_after,
                "provider": os.getenv("LLM_PROVIDER", "mistral"),
                "error": None,
            }
        except Exception as _exc:
            st.session_state["llm_analysis_status"] = {
                "nb_done": 0,
                "nb_failed": _nb_attempted,
                "retry_after": -1,
                "provider": os.getenv("LLM_PROVIDER", "mistral"),
                "error": str(_exc),
            }
        finally:
            _db_llm.close()

    _clear_tender_caches()
```

`os` est importé ligne 6 de `app.py`. `auto_analyze_claude` est importé depuis `llm_analyzer` ligne 23.

- [ ] **Step 3 : Lancer la suite de tests non-régression**

```bash
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py -x
```

Résultat attendu : tous les tests passent (aucune régression introduite par la modification).

- [ ] **Step 4 : Commit**

```bash
git add app.py
git commit -m "feat: auto-trigger Mistral/LLM analysis after scraping and store status in session_state"
```

---

### Task 2 : Bloc visuel dans `_render_collection_status_sidebar`

**Files:**
- Modify: `app.py:1427-1443`

- [ ] **Step 1 : Repérer la dernière ligne du fragment**

Dans [app.py](app.py), la fonction `_render_collection_status_sidebar()` se termine ligne ~1443 avec la fermeture du `with st.expander("▾ Toutes les sources"):` :

```python
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:2px 0;font-size:0.78rem;'>"
                f"<span style='color:{color};'>{icon} {_html.escape(s['name'])}</span>"
                f"<span style='color:#64748b;font-size:0.7rem;'>{detail}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
```

- [ ] **Step 2 : Ajouter le bloc LLM à la fin du fragment**

Après la dernière ligne du `with st.expander(...)` (et toujours à l'intérieur de `_render_collection_status_sidebar`), ajouter :

```python
    llm_status = st.session_state.get("llm_analysis_status")
    if llm_status:
        provider_label = llm_status["provider"].capitalize()
        st.markdown("---")
        st.markdown(
            f"<div style='font-size:0.72rem;font-weight:700;color:#a78bfa;"
            f"text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;'>"
            f"Analyse IA — {provider_label}</div>",
            unsafe_allow_html=True,
        )
        if llm_status["error"]:
            st.markdown(
                f"<div style='background:#1a0a1a;border:1px solid rgba(248,113,113,.3);"
                f"border-radius:6px;padding:6px 8px;'>"
                f"<span style='color:#f87171;font-size:0.8rem;'>"
                f"✗ {_html.escape(llm_status['error'][:120])}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
        elif llm_status["retry_after"] >= 0:
            _mins = max(1, llm_status["retry_after"] // 60)
            st.warning(f"⚠️ Quota atteint — réessayez dans ~{_mins} min.")
        else:
            _c1, _c2 = st.columns(2)
            _c1.metric("✅ Analysés", llm_status["nb_done"])
            _c2.metric("❌ Échecs", llm_status["nb_failed"])
```

`_html` est importé ligne 3 de `app.py` (`import html as _html`).

- [ ] **Step 3 : Relancer les tests non-régression**

```bash
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py -x
```

Résultat attendu : tous les tests passent.

- [ ] **Step 4 : Vérifier visuellement dans l'app**

Lancer l'app :

```bash
streamlit run app.py
```

Scénarios à tester :

| Scénario | Résultat attendu |
|---|---|
| Clic "⚡ Lancer la collecte" avec nouveaux marchés | Bloc violet "Analyse IA — Mistral" apparaît avec métriques ✅/❌ |
| Clic "⚡ Lancer la collecte" sans nouveaux marchés | Bloc LLM absent |
| Clé API Mistral absente / invalide | Bloc rouge avec message d'erreur |
| Quota Mistral atteint | `st.warning` avec délai en minutes |

- [ ] **Step 5 : Commit**

```bash
git add app.py
git commit -m "feat: show Mistral/LLM analysis status block in sidebar after scraping"
```
