# Panneau statut collecte — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher dans la sidebar un panneau permanent post-collecte montrant le statut (OK / erreur / nb résultats) de chaque source automatique.

**Architecture:** On enrichit `_collect_all_enabled_sources()` pour persister un `collection_status` (liste de dicts) dans `session_state`, puis on ajoute un fragment `_render_collection_status_sidebar()` appelé depuis la sidebar à la place de l'affichage actuel par checkboxes.

**Tech Stack:** Python 3.11, Streamlit, SQLAlchemy — uniquement `app.py`.

---

## Fichiers touchés

| Fichier | Action |
|---------|--------|
| `app.py` | Modifier `_collect_all_enabled_sources()` (l.835–932) + ajouter fragment + modifier sidebar (l.1094–1101) |

---

### Task 1 — Persister le statut de chaque source dans session_state

**Files:**
- Modify: `app.py:847-932`

- [ ] **Step 1 : Ajouter `per_source_status` et `_src_error` dans la boucle**

Dans `_collect_all_enabled_sources()`, remplacer le bloc existant (lignes 847–932) par ce qui suit. Les seuls changements par rapport au code actuel sont : ajout de `per_source_status`, `_src_error`, un `append` après le diff d'IDs, et le `session_state` final. Le reste est identique.

```python
    per_source_new: dict[str, int] = {}
    per_source_ids: dict[str, set] = {}
    per_source_status: list[dict] = []   # <-- nouveau
    errors = []

    with st.spinner("Collecte en cours…"):
        for source in sources:
            if source.is_manual or not source.scraper_module:
                continue
            if not source.enabled:
                continue
            _src_error: str | None = None          # <-- nouveau
            try:
                mod = importlib.import_module(source.scraper_module)
                func = getattr(mod, source.scraper_func)
                func()
            except Exception as exc:
                _src_error = str(exc)              # <-- nouveau
                errors.append(f"{source.name} : {exc}")
                try:
                    from models import ScraperRun as _SR_cleanup
                    from database import finish_scraper_run as _fsr
                    _db_cleanup = new_db()
                    try:
                        _orphan = _db_cleanup.query(_SR_cleanup).filter(
                            _SR_cleanup.source_name == source.name,
                            _SR_cleanup.status == "running",
                        ).order_by(_SR_cleanup.id.desc()).first()
                        if _orphan:
                            _fsr(_db_cleanup, _orphan.id, nb_found=0, nb_new=0, error=str(exc))
                    finally:
                        _db_cleanup.close()
                except Exception:
                    pass
            # One query after each scraper, diffed against running known set
            _db_post = new_db()
            try:
                current_ids = {row.id for row in _db_post.query(Tender.id).all()}
            finally:
                _db_post.close()
            new_ids = current_ids - known_ids
            known_ids = current_ids
            if new_ids:
                per_source_ids[source.name] = new_ids
                per_source_new[source.name] = len(new_ids)
            per_source_status.append({             # <-- nouveau
                "name": source.name,
                "nb_new": len(new_ids),
                "error": _src_error,
            })
```

- [ ] **Step 2 : Persister `collection_status` et supprimer `st.warning(err)`**

Remplacer le bloc de fin de la fonction (lignes 890–932) — seuls ajouts : la ligne `st.session_state["collection_status"]` et la suppression des deux lignes `for err in errors: st.warning(err)` :

```python
    _run_auto_analysis()
    st.cache_data.clear()

    all_new_ids = {tid for ids in per_source_ids.values() for tid in ids}
    st.session_state["new_tender_ids"] = all_new_ids
    st.session_state["collection_results"] = per_source_new
    st.session_state["collection_source_ids"] = per_source_ids
    st.session_state["collection_status"] = per_source_status   # <-- nouveau

    # Réinitialise les filtres source (supprime l'état d'une collecte précédente)
    for k in [k for k in st.session_state if k.startswith("src_filter_")]:
        del st.session_state[k]
    for src in per_source_new:
        st.session_state[f"src_filter_{src}"] = True

    total = sum(per_source_new.values())
    if total and all_new_ids:
        _db_res = new_db()
        try:
            _new_tenders = _db_res.query(Tender).filter(
                Tender.id.in_(all_new_ids)
            ).all()

            def _sc(t) -> int:
                return (t.llm_analysis or {}).get("score_pertinence", t.relevance_score or 0)

            _go = sum(1 for t in _new_tenders if _sc(t) >= SCORE_GO)
            _etude = sum(1 for t in _new_tenders if SCORE_ETUDE <= _sc(t) < SCORE_GO)
            _pass = sum(1 for t in _new_tenders if _sc(t) < SCORE_ETUDE)
            _claude_ok = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("_source") in ("claude", "gemini"))
        finally:
            _db_res.close()

        st.success(
            f"✅ {total} nouveau(x) marché(s) importé(s) — "
            f"🟢 {_go} GO · 🟡 {_etude} À étudier · 🔴 {_pass} Passer"
            + (f" · 🤖 {_claude_ok} analysé(s) par IA" if _claude_ok else "")
        )
    elif total:
        st.success(f"✅ {total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée.")
    # NOTE: les erreurs ne sont plus affichées ici — elles apparaissent dans _render_collection_status_sidebar()
```

- [ ] **Step 3 : Vérification manuelle**

Ouvrir `app.py` et confirmer :
- `per_source_status` est déclaré ligne ~849
- `_src_error` est assigné dans le `except` avant `errors.append`
- `per_source_status.append(...)` est présent après le bloc `if new_ids:`
- `st.session_state["collection_status"] = per_source_status` est présent après `st.cache_data.clear()`
- Les deux lignes `for err in errors: st.warning(err)` ont disparu

- [ ] **Step 4 : Commit**

```bash
git add app.py
git commit -m "feat: persister collection_status par source dans session_state"
```

---

### Task 2 — Ajouter le fragment `_render_collection_status_sidebar()`

**Files:**
- Modify: `app.py` — insérer après la définition de `_render_new_tenders_section` (l.935)

- [ ] **Step 1 : Insérer le fragment après `_render_new_tenders_section`**

Trouver la ligne contenant `@st.fragment` suivi de `def _render_new_tenders_section` (vers l.935). Insérer le nouveau fragment juste **après** la fonction complète `_render_new_tenders_section` (avant la prochaine fonction/section).

```python
@st.fragment
def _render_collection_status_sidebar() -> None:
    status: list[dict] | None = st.session_state.get("collection_status")
    if not status:
        return

    errored = [s for s in status if s["error"]]
    ok_count = len(status) - len(errored)
    total_new = sum(s["nb_new"] for s in status)

    header_color = "#f87171" if errored else "#22c55e"
    st.markdown(
        f"<div style='font-size:0.72rem;font-weight:700;color:{header_color};"
        f"text-transform:uppercase;letter-spacing:.07em;margin-bottom:6px;'>"
        f"Dernière collecte — {ok_count}/{len(status)} OK</div>",
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    c1.metric("✅ OK", ok_count)
    c2.metric("❌ Err", len(errored))
    c3.metric("📋", total_new, help="Marchés collectés")

    if errored:
        st.markdown(
            "<div style='font-size:0.72rem;font-weight:700;color:#f87171;"
            "text-transform:uppercase;letter-spacing:.07em;margin:8px 0 4px;'>"
            "⚠ Sources en erreur</div>",
            unsafe_allow_html=True,
        )
        for s in errored:
            st.markdown(
                f"<div style='background:#1a0a0a;border:1px solid rgba(248,113,113,.3);"
                f"border-radius:6px;padding:6px 8px;margin-bottom:4px;'>"
                f"<span style='color:#f87171;font-weight:600;font-size:0.8rem;'>✗ {s['name']}</span>"
                f"<br><span style='color:#64748b;font-size:0.72rem;font-style:italic;'>"
                f"{s['error'][:120]}</span></div>",
                unsafe_allow_html=True,
            )

    with st.expander("▾ Toutes les sources"):
        for s in status:
            if s["error"]:
                icon, color, detail = "✗", "#f87171", "erreur"
            elif s["nb_new"] > 0:
                icon, color = "✓", "#22c55e"
                detail = f"{s['nb_new']} résultat{'s' if s['nb_new'] > 1 else ''}"
            else:
                icon, color, detail = "·", "#fbbf24", "0 résultat"
            st.markdown(
                f"<div style='display:flex;justify-content:space-between;align-items:center;"
                f"padding:2px 0;font-size:0.78rem;'>"
                f"<span style='color:{color};'>{icon} {s['name']}</span>"
                f"<span style='color:#64748b;font-size:0.7rem;'>{detail}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
```

- [ ] **Step 2 : Vérification syntaxique**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK` (pas d'erreur de syntaxe).

- [ ] **Step 3 : Commit**

```bash
git add app.py
git commit -m "feat: ajouter _render_collection_status_sidebar fragment"
```

---

### Task 3 — Câbler le composant dans la sidebar

**Files:**
- Modify: `app.py:1094-1101`

- [ ] **Step 1 : Remplacer le bloc de la sidebar**

Localiser ce bloc existant (vers l.1094) :

```python
    _col_results = st.session_state.get("collection_results", {})
    if _col_results:
        st.markdown("**Résultats — filtrer par source :**")
        for _src_name, _nb_new in sorted(_col_results.items()):
            st.checkbox(
                f"{_src_name} ({_nb_new})",
                key=f"src_filter_{_src_name}",
            )
```

Le remplacer par :

```python
    _render_collection_status_sidebar()

    _col_results = st.session_state.get("collection_results", {})
    if _col_results:
        st.markdown("**Filtrer par source :**")
        for _src_name, _nb_new in sorted(_col_results.items()):
            st.checkbox(
                f"{_src_name} ({_nb_new})",
                key=f"src_filter_{_src_name}",
            )
```

- [ ] **Step 2 : Vérification syntaxique**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 3 : Test fonctionnel — lancer l'app**

```bash
streamlit run app.py
```

Ouvrir l'app dans le navigateur et vérifier :

1. **Avant toute collecte** : aucun panneau visible sous le bouton "Lancer la collecte"
2. **Après la collecte** (cliquer "⚡ Lancer la collecte") :
   - Le header "Dernière collecte — X/Y OK" apparaît en vert (si tout OK) ou rouge (si erreurs)
   - 3 métriques affichées : OK / Err / Marchés
   - Si une source est en erreur : bloc rouge avec nom + message d'erreur tronqué à 120 chars
   - L'expander "▾ Toutes les sources" liste les 17 sources avec icône et détail
   - Les checkboxes de filtre par source (existing) apparaissent toujours en dessous

- [ ] **Step 4 : Commit final**

```bash
git add app.py
git commit -m "feat: panneau statut collecte dans la sidebar (KPIs + erreurs + détail sources)"
```
