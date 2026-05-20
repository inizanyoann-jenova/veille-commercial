# Sidebar Collecte — Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign la section "Sources de collecte" de la sidebar : avant collecte = bouton seul ; après collecte = checkboxes par source ayant trouvé des offres, qui filtrent la vue principale.

**Architecture:**
- La collecte cesse de prendre une sélection de sources en paramètre : elle collecte toutes les sources activées/validées.
- L'état post-collecte est stocké dans `st.session_state` : `collection_results` (nb par source) et `collection_source_ids` (IDs de tenders par source).
- Le filtre de la vue principale exclut les IDs des sources décochées, sans toucher aux tenders historiques.
- La configuration des sources (activer/désactiver) est déplacée dans Paramètres.

**Tech Stack:** Python, Streamlit, SQLAlchemy, session_state

---

## Fichiers modifiés

| Fichier | Rôle des modifications |
|---|---|
| `app.py:772-847` | Réécriture de `_collect_selected_sources` → collecte tout sans paramètre, trace IDs par source |
| `app.py:1003-1060` | Remplacement du bloc "Sources de collecte" de la sidebar |
| `app.py:1660-1690` | Ajout du filtre source post-collecte sur rows_pub et rows_priv |
| `pages/parametres.py` | Ajout de la section "⚡ Sources à collecter" avec toggles activer/désactiver |

---

## Task 1 : Réécrire la fonction de collecte

**Files:**
- Modify: `app.py:772-847`

- [ ] **Step 1 : Remplacer la fonction `_collect_selected_sources`**

Remplacer entièrement la fonction existante (lines 772-847) par :

```python
def _collect_all_enabled_sources() -> None:
    """Lance les scrapers de toutes les sources activées/validées. Stocke les résultats par source dans session_state."""
    import importlib

    _db_snap = new_db()
    try:
        ids_before_all = {row.id for row in _db_snap.query(Tender.id).all()}
    finally:
        _db_snap.close()

    db_s = new_db()
    try:
        sources = list_sources(db_s)
    finally:
        db_s.close()

    per_source_new: dict[str, int] = {}
    per_source_ids: dict[str, set] = {}
    errors = []

    with st.spinner("Collecte en cours…"):
        for source in sources:
            if source.is_manual or not source.scraper_module:
                continue
            if not source.enabled or not source.is_validated:
                continue
            _db_pre = new_db()
            try:
                ids_before_src = {row.id for row in _db_pre.query(Tender.id).all()}
            finally:
                _db_pre.close()
            try:
                import sys as _sys
                if source.scraper_module in _sys.modules:
                    mod = importlib.reload(_sys.modules[source.scraper_module])
                else:
                    mod = importlib.import_module(source.scraper_module)
                func = getattr(mod, source.scraper_func)
                func()
            except Exception as exc:
                errors.append(f"{source.name} : {exc}")
            _db_post = new_db()
            try:
                ids_after_src = {row.id for row in _db_post.query(Tender.id).all()}
            finally:
                _db_post.close()
            new_ids = ids_after_src - ids_before_src
            if new_ids:
                per_source_ids[source.name] = new_ids
                per_source_new[source.name] = len(new_ids)

    _run_auto_analysis()
    st.cache_data.clear()

    _db_snap2 = new_db()
    try:
        ids_after_all = {row.id for row in _db_snap2.query(Tender.id).all()}
    finally:
        _db_snap2.close()

    all_new_ids = ids_after_all - ids_before_all
    st.session_state["new_tender_ids"] = all_new_ids
    st.session_state["collection_results"] = per_source_new
    st.session_state["collection_source_ids"] = per_source_ids

    # Initialise le filtre : toutes les sources avec résultats sont cochées
    for src in per_source_new:
        st.session_state.setdefault(f"src_filter_{src}", True)

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
    for err in errors:
        st.warning(err)
```

- [ ] **Step 2 : Commit**

```bash
git add app.py
git commit -m "refactor: réécriture collecte — collecte toutes sources activées, trace IDs par source"
```

---

## Task 2 : Réécrire la section sidebar "Sources de collecte"

**Files:**
- Modify: `app.py:1003-1098` (bloc from `st.markdown("---")` / `st.markdown("### ⚡ Sources de collecte")` jusqu'à la fin du bloc `with st.sidebar:`)

- [ ] **Step 1 : Identifier précisément le bloc à remplacer**

Le bloc à remplacer est lines 1003-1098 dans `app.py` (tout le contenu depuis `st.markdown("---")` / `"### ⚡ Sources de collecte"` jusqu'à la fin du `with st.sidebar:` block).

Contenu exact du `old_string` à cibler (pour Edit) :

```python
    st.markdown("---")
    st.markdown("### ⚡ Sources de collecte")

    db_src = new_db()
    try:
        all_sources = list_sources(db_src)
    finally:
        db_src.close()

    CATEGORY_ICONS = {"Public": "📋 Public", "Privé": "🏗️ Privé", "International": "🌍 International"}
    selected_source_ids: list[int] = []

    for cat in ["Public", "Privé", "International"]:
        cat_sources = [
            s for s in all_sources
            if s.category == cat and s.enabled and (s.is_manual or s.is_validated)
        ]
        if not cat_sources:
            continue
        st.markdown(f"**{CATEGORY_ICONS[cat]}**")
        for s in cat_sources:
            if s.is_manual:
                col1, col2 = st.columns([5, 1])
                with col1:
                    st.checkbox(
                        s.name,
                        value=False,
                        key=f"src_chk_{s.id}",
                        help="Source manuelle — aucun scraper automatique. Cliquez ↗ pour consulter le site.",
                    )
                with col2:
                    st.link_button("↗", url=s.url, help=f"Ouvrir {s.name}")
            else:
                checked = st.checkbox(
                    s.name,
                    value=True,
                    key=f"src_chk_{s.id}",
                )
                if checked:
                    selected_source_ids.append(s.id)
                _runs = load_last_scraper_runs()
                _last = _runs.get(s.name)
                if _last:
                    _ago = datetime.utcnow() - _last["started_at"].replace(tzinfo=None)
                    _d = _ago.days
                    _h = int(_ago.total_seconds() // 3600)
                    if _last["status"] == "error":
                        st.caption(f"⚠️ Erreur il y a {'%dj' % _d if _d else '%dh' % _h}")
                    else:
                        _label = f"{_d}j" if _d >= 1 else f"{_h}h"
                        st.caption(f"Collecte il y a {_label} — {_last['nb_new']} nouveaux")
                if s.ping_failures_count and s.ping_failures_count >= 1 and s.is_validated:
                    st.caption(f"⚠️ Ping échoué {s.ping_failures_count}x")

    st.markdown("")
    if st.button("⚡ Collecter la sélection", use_container_width=True, type="primary",
                 disabled=len(selected_source_ids) == 0):
        _collect_selected_sources(selected_source_ids)
```

- [ ] **Step 2 : Remplacer par le nouveau bloc sidebar**

`new_string` à utiliser :

```python
    st.markdown("---")
    st.markdown("### ⚡ Collecte")

    if st.button("⚡ Lancer la collecte", use_container_width=True, type="primary"):
        _collect_all_enabled_sources()

    _col_results = st.session_state.get("collection_results", {})
    if _col_results:
        st.markdown("**Résultats — filtrer par source :**")
        for _src_name, _nb_new in sorted(_col_results.items()):
            st.checkbox(
                f"{_src_name} ({_nb_new})",
                key=f"src_filter_{_src_name}",
            )
```

- [ ] **Step 3 : Commit**

```bash
git add app.py
git commit -m "feat: sidebar collecte — bouton seul avant collecte, checkboxes résultats après"
```

---

## Task 3 : Appliquer le filtre source dans la vue principale

**Files:**
- Modify: `app.py:1660-1690`

- [ ] **Step 1 : Ajouter la logique de filtre source après les filtres existants**

Juste après la ligne `rows_pub = _sort_rows(rows_pub, sort_by)` (actuellement line ~1690), ajouter :

```python
_collection_src_ids = st.session_state.get("collection_source_ids", {})
if _collection_src_ids:
    _excluded_ids: set = set()
    for _src, _ids in _collection_src_ids.items():
        if not st.session_state.get(f"src_filter_{_src}", True):
            _excluded_ids.update(_ids)
    if _excluded_ids:
        rows_pub = [r for r in rows_pub if r["ID"] not in _excluded_ids]
```

Et de même pour `rows_priv`, juste après `rows_priv = _sort_rows(rows_priv, sort_by)` :

```python
if _collection_src_ids:
    if _excluded_ids:
        rows_priv = [r for r in rows_priv if r["ID"] not in _excluded_ids]
```

Note : `_excluded_ids` est calculé une seule fois (bloc rows_pub) puis réutilisé pour rows_priv — s'assurer que le bloc rows_pub est traité en premier.

- [ ] **Step 2 : Refactoriser pour éviter la duplication de `_excluded_ids`**

Placer le calcul de `_excluded_ids` AVANT les deux blocs de filtrage :

```python
# Juste avant "rows_pub = load_tenders(...)"
_collection_src_ids = st.session_state.get("collection_source_ids", {})
_excluded_new_ids: set = set()
if _collection_src_ids:
    for _src, _ids in _collection_src_ids.items():
        if not st.session_state.get(f"src_filter_{_src}", True):
            _excluded_new_ids.update(_ids)
```

Puis après `rows_pub = _sort_rows(rows_pub, sort_by)` :

```python
if _excluded_new_ids:
    rows_pub = [r for r in rows_pub if r["ID"] not in _excluded_new_ids]
```

Et après `rows_priv = _sort_rows(rows_priv, sort_by)` :

```python
if _excluded_new_ids:
    rows_priv = [r for r in rows_priv if r["ID"] not in _excluded_new_ids]
```

- [ ] **Step 3 : Commit**

```bash
git add app.py
git commit -m "feat: filtre vue principale par source post-collecte"
```

---

## Task 4 : Ajouter la gestion des sources dans Paramètres

**Files:**
- Modify: `pages/parametres.py`

- [ ] **Step 1 : Ajouter les imports nécessaires en tête de fichier**

Après les imports existants (line ~9), ajouter :

```python
from database import SessionLocal as _SL_src
from source_registry import Source as _SrcModel, toggle_enabled as _toggle_enabled
```

- [ ] **Step 2 : Insérer la section Sources après `st.title("⚙️ Paramètres")`**

Insérer juste AVANT `st.header("🤖 Intelligence Artificielle…")` :

```python
# ── Section sources à collecter ───────────────────────────────────────────────
st.header("⚡ Sources à collecter")
st.caption("Activez ou désactivez les sources prises en compte lors du lancement de la collecte.")

_db_src_p = _SL_src()
try:
    _all_sources_p = _db_src_p.query(_SrcModel).order_by(_SrcModel.display_order).all()
finally:
    _db_src_p.close()

_CAT_ICONS = {"Public": "📋 Public", "Privé": "🏗️ Privé", "International": "🌍 International"}
for _cat in ["Public", "Privé", "International"]:
    _cat_src = [s for s in _all_sources_p if s.category == _cat]
    if not _cat_src:
        continue
    st.subheader(_CAT_ICONS[_cat])
    for _s in _cat_src:
        _col_toggle, _col_label = st.columns([1, 9])
        with _col_toggle:
            _new_enabled = st.toggle(
                "Activée",
                value=bool(_s.enabled),
                key=f"src_enabled_{_s.id}",
                label_visibility="collapsed",
            )
        with _col_label:
            _status_icon = "✅" if _s.is_validated else ("📋" if _s.is_manual else "⚠️")
            st.markdown(f"{_status_icon} **{_s.name}**")
        if _new_enabled != bool(_s.enabled):
            _db_tog = _SL_src()
            try:
                _toggle_enabled(_db_tog, _s.id)
            finally:
                _db_tog.close()
            st.rerun()

st.markdown("---")
```

- [ ] **Step 3 : Vérifier que `toggle_enabled` dans source_registry.py accepte (db, source_id)**

Lire `source_registry.py` pour confirmer la signature de `toggle_enabled` :

```bash
grep -n "def toggle_enabled" source_registry.py
```

Si la signature est différente, adapter l'appel en conséquence.

- [ ] **Step 4 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat(paramètres): section sources à collecter avec toggles activer/désactiver"
```

---

## Task 5 : Vérification finale

- [ ] **Step 1 : Lancer l'app et vérifier le parcours utilisateur**

```bash
streamlit run app.py
```

Checklist de test :
1. La sidebar n'affiche que "⚡ Lancer la collecte" (pas de liste de sources)
2. Cliquer "Lancer la collecte" déclenche la collecte de toutes les sources activées
3. Après collecte, la sidebar affiche les checkboxes des sources avec résultats
4. Décocher une source masque ses nouvelles offres dans la vue principale
5. Re-cocher la source les fait réapparaître
6. Dans Paramètres, la section "Sources à collecter" est présente avec des toggles
7. Désactiver une source depuis Paramètres la retire des prochaines collectes

- [ ] **Step 2 : Vérifier les tests existants**

```bash
python -m pytest tests/ -v --tb=short 2>&1 | head -80
```

Expected : aucun test ne casse (les tests existants n'exercent pas `_collect_selected_sources` directement).

- [ ] **Step 3 : Commit final si corrections mineures**

```bash
git add -p
git commit -m "fix: ajustements post-vérification sidebar collecte redesign"
```

---

## Récapitulatif des règles métier respectées

| Règle | Implémentation |
|---|---|
| Sélection des sources → Paramètres | Section "Sources à collecter" avec toggles dans `pages/parametres.py` |
| Avant collecte : bouton seul | `if "collection_results" not in session_state` → un seul bouton visible |
| Après collecte : sources avec résultats | `st.session_state["collection_results"]` → checkboxes générées dynamiquement |
| Seuls les sites avec offres trouvées apparaissent | `per_source_new` ne contient que les sources avec `len(new_ids) > 0` |
| Toutes cochées par défaut | `st.session_state.setdefault(f"src_filter_{src}", True)` à la fin de la collecte |
| Décocher masque les offres | `_excluded_new_ids` construit depuis les sources décochées, appliqué sur rows |
