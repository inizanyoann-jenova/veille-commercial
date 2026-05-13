# Lisibilité — Cartes post-collecte + Tableau enrichi : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Afficher les nouveaux marchés sous forme de cartes après chaque collecte, et enrichir le tableau avec une barre de progression pour le score.

**Architecture:** Trois modifications ciblées dans `app.py` uniquement. (1) Snapshot des IDs avant/après collecte stocké dans `st.session_state`. (2) Fonction `@st.fragment` qui affiche les cartes des nouveaux marchés en haut de page. (3) Remplacement de `NumberColumn` par `ProgressColumn` pour le score + nettoyage des colonnes affichées.

**Tech Stack:** Streamlit ≥ 1.33 (`@st.fragment`), SQLAlchemy, Python 3.11+

---

## Fichiers modifiés

- Modify: `app.py` — trois zones distinctes (voir tâches)

Aucun autre fichier n'est touché.

---

### Task 1 : Tracking des nouveaux IDs après collecte

**Files:**
- Modify: `app.py:644-647` (init session state)
- Modify: `app.py:807-843` (fonction `_collect_selected_sources`)

- [ ] **Step 1 : Initialiser `new_tender_ids` dans session state**

Juste après le bloc `auto_analyzed` (ligne 647), ajouter :

```python
# Auto-analyse au démarrage (une seule fois par session)
if "auto_analyzed" not in st.session_state:
    _run_auto_analysis()
    st.session_state["auto_analyzed"] = True

st.session_state.setdefault("new_tender_ids", set())
```

- [ ] **Step 2 : Modifier `_collect_selected_sources` pour snapshoter les IDs**

Remplacer la fonction entière (lignes 807–843) par :

```python
def _collect_selected_sources(selected_source_ids: list[int]) -> None:
    """Lance les scrapers des sources sélectionnées et affiche les résultats."""
    import importlib

    # Snapshot des IDs existants avant collecte
    _db_snap = new_db()
    try:
        ids_before = {row.id for row in _db_snap.query(Tender.id).all()}
    finally:
        _db_snap.close()

    db_s = new_db()
    try:
        sources = list_sources(db_s)
    finally:
        db_s.close()

    total = 0
    errors = []
    with st.spinner("Collecte en cours…"):
        for source in sources:
            if source.id not in selected_source_ids:
                continue
            if source.is_manual or not source.scraper_module:
                continue
            try:
                import sys as _sys
                if source.scraper_module in _sys.modules:
                    mod = importlib.reload(_sys.modules[source.scraper_module])
                else:
                    mod = importlib.import_module(source.scraper_module)
                func = getattr(mod, source.scraper_func)
                count = func()
                total += count
            except Exception as exc:
                errors.append(f"{source.name} : {exc}")

    _run_auto_analysis()
    st.cache_data.clear()

    # Calcul des nouveaux IDs apparus pendant cette collecte
    _db_snap2 = new_db()
    try:
        ids_after = {row.id for row in _db_snap2.query(Tender.id).all()}
    finally:
        _db_snap2.close()
    st.session_state["new_tender_ids"] = ids_after - ids_before

    if total:
        st.success(f"{total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée pour les sources sélectionnées.")
    for err in errors:
        st.warning(err)
```

- [ ] **Step 3 : Vérifier manuellement**

Lancer l'app : `streamlit run app.py`
Ouvrir la console Python (terminal) et vérifier qu'il n'y a pas d'erreur d'import.
Cliquer "⚡ Collecter la sélection" avec une source cochée.
Dans le terminal, vérifier que l'app ne plante pas.
`st.session_state["new_tender_ids"]` sera un set (peut être vide si aucun nouveau marché).

- [ ] **Step 4 : Commit**

```bash
git add app.py
git commit -m "feat: snapshot IDs avant/après collecte dans session_state"
```

---

### Task 2 : Section cartes post-collecte avec @st.fragment

**Files:**
- Modify: `app.py` — nouvelle fonction avant `with st.sidebar:` (ligne ~846), appel après le header (ligne ~1006)

- [ ] **Step 1 : Ajouter la fonction `_render_new_tenders_section`**

Insérer cette fonction **juste avant** la ligne `with st.sidebar:` (ligne 846) :

```python
@st.fragment
def _render_new_tenders_section() -> None:
    """Affiche les cartes des nouveaux marchés collectés lors de cette session."""
    new_ids = st.session_state.get("new_tender_ids", set())
    if not new_ids:
        return

    db = new_db()
    try:
        new_tenders = (
            db.query(Tender)
            .filter(Tender.id.in_(new_ids), Tender.is_blacklisted != True)
            .all()
        )
    finally:
        db.close()

    if not new_tenders:
        return

    def _score(t):
        a = t.llm_analysis or {}
        return a.get("score_pertinence", t.relevance_score or 0)

    new_tenders.sort(key=_score, reverse=True)
    top5 = new_tenders[:5]
    total = len(new_tenders)

    col_title, col_close = st.columns([9, 1])
    with col_title:
        st.markdown(f"### 🆕 {total} nouveau(x) marché(s) collecté(s)")
    with col_close:
        if st.button("✕ Fermer", key="close_new_tenders"):
            st.session_state["new_tender_ids"] = set()
            st.rerun(scope="fragment")

    for t in top5:
        a = t.llm_analysis or {}
        score = _score(t)
        domaine = detect_domaine(t.title or "", t.description or "")
        territoire = detect_territoire(t.title or "", t.description or "")
        justif = (a.get("justification_score") or "")[:120]

        if score >= 65:
            color_class = ""
            badge = f"🟢 GO — Score {score}/100"
        elif score >= 35:
            color_class = "orange"
            badge = f"🟡 Étudier — Score {score}/100"
        else:
            color_class = "teal"
            badge = f"🔴 Passer — Score {score}/100"

        title_short = (t.title or "Sans titre")[:90]
        justif_html = (
            f"<div style='font-size:0.82rem;color:#374151;font-style:italic;margin-bottom:10px;'>"
            f"💡 {justif}</div>"
            if justif else ""
        )

        st.markdown(
            f"""<div class="kpi-card {color_class}" style="margin-bottom:12px;padding:16px 20px;">
<div style="font-size:0.75rem;font-weight:700;color:#6b7280;margin-bottom:6px;">{badge}</div>
<div style="font-size:1rem;font-weight:700;color:#111827;margin-bottom:4px;">{title_short}</div>
<div style="font-size:0.8rem;color:#6b7280;margin-bottom:8px;">{territoire} · {domaine}</div>
{justif_html}</div>""",
            unsafe_allow_html=True,
        )

        col_save, col_qualify, col_src, _ = st.columns([2, 2, 2, 4])
        with col_save:
            if st.button("⭐ Sauvegarder", key=f"new_save_{t.id}"):
                toggle_saved(t.id, True)
                st.cache_data.clear()
                st.rerun(scope="fragment")
        with col_qualify:
            if st.button("✅ Qualifier", key=f"new_qualify_{t.id}"):
                save_status(t.id, "En cours")
                st.cache_data.clear()
                st.rerun(scope="fragment")
        with col_src:
            if t.source and t.source.startswith("http"):
                st.link_button("🔗 Source", url=t.source)

    if total > 5:
        st.caption(f"+ {total - 5} autre(s) nouveau(x) marché(s) — consultez le tableau ci-dessous.")

    st.markdown("---")
```

- [ ] **Step 2 : Appeler la fonction après le header**

Trouver le bloc header (autour de la ligne 1006) :

```python
st.markdown("---")

# ── KPI metrics ───────────────────────────────────────────────────────────────
```

Modifier pour intercaler l'appel :

```python
st.markdown("---")

# ── Nouveaux marchés post-collecte ────────────────────────────────────────────
_render_new_tenders_section()

# ── KPI metrics ───────────────────────────────────────────────────────────────
```

- [ ] **Step 3 : Vérifier manuellement**

Lancer : `streamlit run app.py`

Vérifier que la page s'affiche normalement quand `new_tender_ids` est vide (section absente).

Pour tester les cartes sans faire une vraie collecte, ouvrir la console Python Streamlit (ou ajouter temporairement dans l'app) :
```python
# Debug temporaire — à retirer après test
st.session_state["new_tender_ids"] = {"test-id-fictif"}
```
→ La section doit apparaître avec "1 nouveau marché collecté" et un message de type "marché introuvable" (ID fictif → liste vide → section absente).

Pour tester avec de vraies données : lancer une collecte réelle depuis la sidebar. Les cartes doivent apparaître immédiatement après la collecte avec les vrais marchés.

Vérifier :
- Le bouton "✕ Fermer" fait disparaître la section (fragment rerun)
- "⭐ Sauvegarder" et "✅ Qualifier" ne rechargent pas toute la page
- Les cartes GO sont rouges, Étudier oranges, Passer teal

- [ ] **Step 4 : Commit**

```bash
git add app.py
git commit -m "feat: section cartes post-collecte avec @st.fragment"
```

---

### Task 3 : ProgressColumn + masquer colonnes + filtre 24h

**Files:**
- Modify: `app.py:650-651` (signature `load_tenders`)
- Modify: `app.py:1180-1204` (tableau vue dans `_render_editor_section`)
- Modify: `app.py:886` (sidebar — checkbox filtre 24h)
- Modify: `app.py:1297-1330` (appels à `load_tenders`)

- [ ] **Step 1 : Ajouter le paramètre `only_recent` à `load_tenders`**

Remplacer la définition complète de `load_tenders` (lignes 650–708) par :

```python
@st.cache_data(ttl=60)
def load_tenders(
    status_filter: str,
    maintenance_only: bool,
    date_from: datetime | None,
    strict_date: bool = False,
    secteur: str = "Public",
    only_recent: bool = False,
) -> list[dict]:
    db = new_db()
    try:
        from sqlalchemy import or_
        from datetime import timedelta
        q = db.query(Tender).filter(Tender.is_blacklisted != True)

        if secteur == "Public":
            q = q.filter(or_(Tender.secteur == "Public", Tender.secteur == None))
        elif secteur == "Privé":
            q = q.filter(Tender.secteur == "Privé")

        if only_recent:
            cutoff = datetime.now() - timedelta(hours=24)
            q = q.filter(Tender.publication_date >= cutoff)

        if status_filter != "Tous":
            q = q.filter(Tender.status == status_filter)
        if maintenance_only:
            q = q.filter(Tender.is_maintenance == True)
        if date_from is not None:
            if strict_date:
                q = q.filter(Tender.publication_date >= date_from)
            else:
                q = q.filter(or_(
                    Tender.publication_date >= date_from,
                    Tender.deadline >= date_from,
                    Tender.publication_date == None,
                ))
        tenders = q.order_by(Tender.deadline).all()

        rows = []
        for t in tenders:
            a = t.llm_analysis or {}
            domaine = detect_domaine(t.title or "", t.description or "")
            territoire = detect_territoire(t.title or "", t.description or "")
            score = a.get("score_pertinence", t.relevance_score or 0)
            rows.append(
                {
                    "ID": t.id,
                    "Go/No-Go": _gonogo(score),
                    "Titre": t.title or "Sans titre",
                    "Source": t.source or "",
                    "Territoire": territoire,
                    "Domaine": domaine,
                    "Score": score,
                    "Date Limite": t.deadline.strftime("%d/%m/%Y") if t.deadline else "—",
                    "Publication": (
                        t.publication_date.strftime("%d/%m/%Y") if t.publication_date else "—"
                    ),
                    "Statut": t.status or "À qualifier",
                    "Type": a.get("type_marche") or t.type_opportunite or "—",
                    "Maint.": "✓" if t.is_maintenance else "",
                    "Concurrents": ", ".join(a.get("marques_concurrentes_citees", [])),
                    "Montant (€)": t.amount,
                    "⭐": bool(t.is_saved),
                    "Secteur": t.secteur or "Public",
                }
            )
        return rows
    finally:
        db.close()
```

- [ ] **Step 2 : Remplacer `NumberColumn` par `ProgressColumn` pour le Score dans la vue**

Dans `_render_editor_section`, dans le `st.dataframe` vue (pas le `st.data_editor`), remplacer :

```python
"Score": st.column_config.NumberColumn("Score DEF", min_value=0, max_value=100, width="small"),
```

par :

```python
"Score": st.column_config.ProgressColumn("Score DEF", min_value=0, max_value=100, format="%d"),
```

- [ ] **Step 3 : Masquer Maint. et Concurrents du tableau vue**

Dans le même `st.dataframe` vue, modifier `column_order` :

```python
column_order=[
    "Go/No-Go", "Titre", "Source", "Territoire", "Domaine",
    "Score", "Montant (€)", "Date Limite", "Publication", "Statut", "Type", "⭐"
],
```

(Maint. et Concurrents sont retirés de la liste — ils restent dans le `data_editor` de l'expander d'édition pour référence.)

- [ ] **Step 4 : Ajouter le checkbox "Nouveaux (24h)" dans la sidebar**

Juste après `maintenance_only = st.checkbox("Maintenance uniquement")` (ligne 886) :

```python
maintenance_only = st.checkbox("Maintenance uniquement")
only_recent = st.checkbox("🆕 Nouveaux (24h)")
```

- [ ] **Step 5 : Passer `only_recent` aux appels de `load_tenders`**

Remplacer les deux appels existants :

```python
rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public")
```

par :

```python
rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public", only_recent=only_recent)
```

Et :

```python
rows_priv = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Privé")
```

par :

```python
rows_priv = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Privé", only_recent=only_recent)
```

- [ ] **Step 6 : Vérifier manuellement**

Lancer : `streamlit run app.py`

Vérifier :
- La colonne Score affiche une barre de progression colorée (verte si haut, rouge si bas)
- Les colonnes Maint. et Concurrents ont disparu du tableau de visualisation
- La checkbox "🆕 Nouveaux (24h)" est présente dans la sidebar
- Cocher "Nouveaux (24h)" filtre le tableau (peut afficher 0 résultats si aucun marché récent — le message "Aucun résultat." doit apparaître proprement)

- [ ] **Step 7 : Commit**

```bash
git add app.py
git commit -m "feat: ProgressColumn score, masquer colonnes, filtre 24h"
```

---

## Vérification finale

- [ ] Lancer une collecte complète depuis la sidebar
- [ ] Vérifier que les cartes apparaissent en haut de page avec les bons scores et couleurs
- [ ] Cliquer "⭐ Sauvegarder" sur une carte → vérifier dans le tableau que l'étoile est cochée
- [ ] Cliquer "✅ Qualifier" → vérifier dans le tableau que le statut est passé à "En cours"
- [ ] Cliquer "✕ Fermer" → les cartes disparaissent, la page reste stable
- [ ] La barre de progression Score est visible dans le tableau
- [ ] Le filtre "Nouveaux (24h)" fonctionne sans erreur
