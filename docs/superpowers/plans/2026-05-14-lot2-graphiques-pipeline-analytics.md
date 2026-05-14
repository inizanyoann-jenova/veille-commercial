# Lot 2 — Graphiques + Pipeline + Analytics : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter des graphiques de tendance Plotly, une vue pipeline commerciale et une page Analytics dédiée à l'app de veille marchés.

**Architecture:** Task 1 et 2 modifient `app.py` (section expander charts + section pipeline). Task 3 crée `pages/analytics.py`. Plotly est ajouté à `requirements.txt`. Toutes les données viennent de requêtes SQLAlchemy directes sur `Tender`, sans changer le modèle.

**Tech Stack:** Streamlit ≥ 1.33, Plotly Express, SQLAlchemy, Python 3.11+

---

## Fichiers modifiés / créés

- Modify: `requirements.txt` — ajout de `plotly>=5.0.0`
- Modify: `app.py` — deux nouvelles sections + lien sidebar
- Create: `pages/analytics.py` — page Analytics complète

---

### Task 1 : Graphiques Plotly tendances dans app.py

**Files:**
- Modify: `requirements.txt`
- Modify: `app.py` — nouvelle fonction `load_chart_data()` + section expander

- [ ] **Step 1 : Ajouter plotly à requirements.txt**

Ouvrir `requirements.txt` et ajouter à la fin :

```
plotly>=5.0.0
```

Installer localement :

```bash
pip install "plotly>=5.0.0"
```

Expected output : `Successfully installed plotly-X.X.X`

- [ ] **Step 2 : Ajouter la fonction `load_chart_data` dans app.py**

Dans `app.py`, trouver la zone des fonctions `@st.cache_data` (après `load_saved_tenders()`, vers la ligne 770). Insérer juste avant `def save_status(`:

```python
@st.cache_data(ttl=300)
def load_chart_data() -> list[dict]:
    """Charge les données légères pour les graphiques (sans description)."""
    db = new_db()
    try:
        rows = db.query(
            Tender.publication_date,
            Tender.title,
            Tender.description,
            Tender.secteur,
        ).filter(Tender.is_blacklisted != True).all()
        return [
            {
                "pub": r.publication_date,
                "title": r.title or "",
                "desc": r.description or "",
                "secteur": r.secteur,
            }
            for r in rows
        ]
    finally:
        db.close()
```

- [ ] **Step 3 : Ajouter la section expander "Tendances & Statistiques" dans app.py**

Trouver la ligne (vers 1213) :
```python
st.markdown("---")

# ── Filtres territoriaux communs ──────────────────────────────────────────────
```

Insérer juste **avant** ce `st.markdown("---")` :

```python
# ── Tendances & Statistiques ──────────────────────────────────────────────────

with st.expander("📈 Tendances & Statistiques", expanded=False):
    import plotly.express as px
    from collections import Counter, defaultdict

    _chart_rows = load_chart_data()

    if not _chart_rows:
        st.caption("Aucune donnée disponible — lancez une collecte d'abord.")
    else:
        _col1, _col2, _col3 = st.columns(3)

        # ── Graphique 1 : Publications par semaine (30 dernières semaines) ──
        with _col1:
            _cutoff = datetime.now() - timedelta(weeks=30)
            _week_counts: dict[str, int] = defaultdict(int)
            for r in _chart_rows:
                if r["pub"] and r["pub"] >= _cutoff:
                    _wk = r["pub"].strftime("%Y-W%V")
                    _week_counts[_wk] += 1
            _weeks = sorted(_week_counts.keys())
            _fig1 = px.bar(
                x=[f"S{w.split('-W')[1]}\n{w.split('-W')[0]}" for w in _weeks],
                y=[_week_counts[w] for w in _weeks],
                color_discrete_sequence=["#cc2222"],
                labels={"x": "", "y": "Marchés"},
            )
            _fig1.update_layout(
                title="Publications / semaine",
                showlegend=False,
                margin=dict(t=40, b=10, l=0, r=0),
                height=260,
            )
            st.plotly_chart(_fig1, use_container_width=True)

        # ── Graphique 2 : Donut territoire ───────────────────────────────────
        with _col2:
            _terr_counts: Counter = Counter()
            for r in _chart_rows:
                _terr = detect_territoire(r["title"], r["desc"])
                for _lbl in _terr.split(", "):
                    _terr_counts[_lbl.strip()] += 1
            _top4 = _terr_counts.most_common(4)
            _autres_terr = sum(v for k, v in _terr_counts.items() if k not in dict(_top4))
            _t_labels = [k for k, _ in _top4] + (["Autres"] if _autres_terr > 0 else [])
            _t_values = [v for _, v in _top4] + ([_autres_terr] if _autres_terr > 0 else [])
            _fig2 = px.pie(
                values=_t_values,
                names=_t_labels,
                hole=0.5,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            _fig2.update_layout(
                title="Par territoire",
                margin=dict(t=40, b=10, l=0, r=0),
                height=260,
            )
            st.plotly_chart(_fig2, use_container_width=True)

        # ── Graphique 3 : Barres domaine ─────────────────────────────────────
        with _col3:
            _dom_counts: Counter = Counter()
            for r in _chart_rows:
                _dom = detect_domaine(r["title"], r["desc"])
                for _lbl in _dom.split(", "):
                    _dom_counts[_lbl.strip()] += 1
            _d_labels = list(reversed([k for k, _ in _dom_counts.most_common()]))
            _d_values = list(reversed([v for _, v in _dom_counts.most_common()]))
            _fig3 = px.bar(
                x=_d_values,
                y=_d_labels,
                orientation="h",
                color_discrete_sequence=["#cc2222"],
                labels={"x": "Marchés", "y": ""},
            )
            _fig3.update_layout(
                title="Par domaine",
                showlegend=False,
                margin=dict(t=40, b=10, l=0, r=0),
                height=260,
            )
            st.plotly_chart(_fig3, use_container_width=True)
```

- [ ] **Step 4 : Vérifier manuellement**

```bash
streamlit run app.py
```

- Déplier "📈 Tendances & Statistiques"
- 3 graphiques s'affichent côte à côte : barres rouges / donut / barres horizontales
- Si la base est vide : message "Aucune donnée disponible"

- [ ] **Step 5 : Commit**

```bash
git add requirements.txt app.py
git commit -m "feat: graphiques Plotly tendances dans expander"
```

---

### Task 2 : Vue pipeline kanban-like + lien sidebar Analytics

**Files:**
- Modify: `app.py` — nouvelle fonction `load_pipeline()` + section pipeline + lien sidebar

- [ ] **Step 1 : Ajouter `load_pipeline` dans app.py**

Dans `app.py`, juste après la fonction `load_chart_data()` (Task 1), ajouter :

```python
@st.cache_data(ttl=60)
def load_pipeline() -> dict[str, list[dict]]:
    """Retourne les marchés publics groupés par statut pour la vue pipeline."""
    db = new_db()
    try:
        from sqlalchemy import or_
        tenders = (
            db.query(Tender)
            .filter(
                Tender.is_blacklisted != True,
                or_(Tender.secteur == "Public", Tender.secteur == None),
            )
            .all()
        )
        result: dict[str, list[dict]] = {
            s: [] for s in ["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]
        }
        for t in tenders:
            s = t.status or "À qualifier"
            if s in result:
                result[s].append({"id": t.id, "title": t.title or "Sans titre", "amount": t.amount})
        return result
    finally:
        db.close()
```

- [ ] **Step 2 : Ajouter la section pipeline dans app.py**

Trouver le commentaire juste après le deuxième `_render_editor_section` (vers la ligne 1461) :
```python
# ── saisie manuelle ───────────────────────────────────────────────────────────
```

Insérer juste **avant** ce commentaire :

```python
# ── Pipeline commercial ───────────────────────────────────────────────────────

st.markdown(_section_html("🗂️ Pipeline Commercial", "Marchés publics — vue par statut"), unsafe_allow_html=True)

_pipeline = load_pipeline()
_STATUS_ICONS = {
    "À qualifier": "📋",
    "En cours": "🔄",
    "Soumis": "📤",
    "Gagné": "🏆",
    "Perdu": "❌",
}
_pipe_cols = st.columns(5)
for _pipe_col, _pipe_status in zip(_pipe_cols, ["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]):
    _items = _pipeline.get(_pipe_status, [])
    _ca = sum(it["amount"] for it in _items if it["amount"])
    with _pipe_col:
        st.markdown(f"**{_STATUS_ICONS[_pipe_status]} {_pipe_status}**")
        st.markdown(f"`{len(_items)}` marché(s)")
        if _ca:
            st.caption(f"{_ca:,.0f} €".replace(",", " "))
        for _it in _items[:3]:
            _short = _it["title"][:55]
            if st.button(_short, key=f"pipe_{_pipe_status}_{_it['id']}", use_container_width=True):
                st.session_state["_sel_title_pub"] = _it["title"]
        if len(_items) > 3:
            st.caption(f"+ {len(_items) - 3} autres")

st.markdown("---")

```

- [ ] **Step 3 : Ajouter le lien Analytics dans la sidebar**

Trouver dans `app.py` le bloc navigation sidebar (vers la ligne 1089) :
```python
    st.markdown("---")
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        st.page_link("pages/parametres.py", label="⚙️ Paramètres", use_container_width=True)
    with col_nav2:
        st.page_link("pages/guide.py", label="📖 Guide", use_container_width=True)
```

Remplacer par :
```python
    st.markdown("---")
    col_nav1, col_nav2, col_nav3 = st.columns(3)
    with col_nav1:
        st.page_link("pages/parametres.py", label="⚙️ Paramètres", use_container_width=True)
    with col_nav2:
        st.page_link("pages/guide.py", label="📖 Guide", use_container_width=True)
    with col_nav3:
        st.page_link("pages/analytics.py", label="📈 Analytics", use_container_width=True)
```

- [ ] **Step 4 : Vérifier manuellement**

```bash
streamlit run app.py
```

- La section "🗂️ Pipeline Commercial" apparaît sous les tableaux avec 5 colonnes
- Chaque colonne affiche count + CA + 3 premiers titres en boutons
- Cliquer un bouton dans le pipeline sélectionne le marché dans le tableau du dessus (via `_sel_title_pub`)
- Le lien "📈 Analytics" apparaît dans la sidebar (la page n'existe pas encore — OK pour ce commit)

- [ ] **Step 5 : Commit**

```bash
git add app.py
git commit -m "feat: vue pipeline commercial + lien Analytics sidebar"
```

---

### Task 3 : Page Analytics (pages/analytics.py)

**Files:**
- Create: `pages/analytics.py`

- [ ] **Step 1 : Créer pages/analytics.py**

Créer le fichier `pages/analytics.py` avec ce contenu complet :

```python
from collections import Counter, defaultdict
from datetime import datetime

import plotly.express as px
import streamlit as st
from sqlalchemy import func

from database import SessionLocal, init_db
from models import Tender

st.set_page_config(page_title="Analytics — DEF OI", page_icon="📈", layout="wide")
init_db()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.main .block-container { padding-top: 1.2rem; padding-left: 2.5rem; padding-right: 2.5rem; max-width: 100%; }
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #f0f2f5; border-radius: 10px;
    padding: 12px 16px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
[data-testid="stMetricLabel"] { color: #9ca3af !important; font-size: 0.69rem !important; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600 !important; }
[data-testid="stMetricValue"] { color: #111827 !important; font-size: 1.55rem !important; font-weight: 800 !important; letter-spacing: -0.02em; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 📈 Analytics — DEF OI")
st.caption("Historique complet de la veille marchés")
st.markdown("---")

# ── KPIs globaux ──────────────────────────────────────────────────────────────

db = SessionLocal()
try:
    total = db.query(Tender).filter(Tender.is_blacklisted != True).count()
    nb_go = db.query(Tender).filter(
        Tender.relevance_score >= 65, Tender.is_blacklisted != True
    ).count()
    taux_go = round(nb_go / total * 100) if total else 0
    ca_gagne = db.query(func.sum(Tender.amount)).filter(
        Tender.status == "Gagné", Tender.amount != None
    ).scalar() or 0
    from sqlalchemy import distinct as _distinct
    nb_sources = db.query(
        func.count(_distinct(Tender.source))
    ).filter(Tender.source != None, Tender.source != "").scalar() or 0
finally:
    db.close()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total marchés collectés", total)
k2.metric("Taux GO (score ≥ 65)", f"{taux_go} %")
k3.metric("CA Gagné 🏆", f"{ca_gagne:,.0f} €".replace(",", " ") if ca_gagne else "—")
k4.metric("Sources distinctes", nb_sources)

st.markdown("---")

# ── Évolution mensuelle ───────────────────────────────────────────────────────

st.markdown("### 📅 Évolution mensuelle")

db = SessionLocal()
try:
    pub_dates = db.query(Tender.publication_date).filter(
        Tender.is_blacklisted != True, Tender.publication_date != None
    ).all()
finally:
    db.close()

month_counts: dict[str, int] = defaultdict(int)
for (pub,) in pub_dates:
    month_counts[pub.strftime("%Y-%m")] += 1

if month_counts:
    _months = sorted(month_counts.keys())
    _fig_line = px.line(
        x=_months,
        y=[month_counts[m] for m in _months],
        labels={"x": "Mois", "y": "Marchés collectés"},
        color_discrete_sequence=["#cc2222"],
        markers=True,
    )
    _fig_line.update_layout(
        showlegend=False,
        margin=dict(t=10, b=10, l=0, r=0),
        height=280,
    )
    st.plotly_chart(_fig_line, use_container_width=True)
else:
    st.caption("Aucune donnée de publication disponible.")

st.markdown("---")

# ── Top 5 sources + Publics vs Privés ────────────────────────────────────────

col_src, col_sect = st.columns(2)

with col_src:
    st.markdown("### 🏆 Top 5 sources par volume")
    db = SessionLocal()
    try:
        top_sources = (
            db.query(Tender.source, func.count(Tender.id).label("count"))
            .filter(Tender.is_blacklisted != True, Tender.source != None, Tender.source != "")
            .group_by(Tender.source)
            .order_by(func.count(Tender.id).desc())
            .limit(5)
            .all()
        )
    finally:
        db.close()

    if top_sources:
        import pandas as pd
        _df_src = pd.DataFrame(top_sources, columns=["Source", "Marchés"])
        st.dataframe(_df_src, hide_index=True, use_container_width=True)
    else:
        st.caption("Aucune source enregistrée.")

with col_sect:
    st.markdown("### 🥧 Publics vs Privés")
    db = SessionLocal()
    try:
        from sqlalchemy import or_
        nb_public = db.query(Tender).filter(
            Tender.is_blacklisted != True,
            or_(Tender.secteur == "Public", Tender.secteur == None),
        ).count()
        nb_prive = db.query(Tender).filter(
            Tender.is_blacklisted != True, Tender.secteur == "Privé"
        ).count()
    finally:
        db.close()

    if nb_public + nb_prive > 0:
        _fig_sect = px.pie(
            values=[nb_public, nb_prive],
            names=["Public", "Privé"],
            hole=0.5,
            color_discrete_sequence=["#cc2222", "#2563eb"],
        )
        _fig_sect.update_layout(margin=dict(t=10, b=10, l=0, r=0), height=260)
        st.plotly_chart(_fig_sect, use_container_width=True)
    else:
        st.caption("Aucune donnée disponible.")

st.markdown("---")
st.page_link("app.py", label="← Retour à la veille marchés")
```

- [ ] **Step 2 : Vérifier manuellement**

```bash
streamlit run app.py
```

- Cliquer "📈 Analytics" dans la sidebar
- La page s'affiche avec : 4 KPIs, courbe mensuelle, top 5 sources, donut secteurs
- Si la base est vide : les sections affichent les captions "Aucune donnée"
- Le lien "← Retour à la veille marchés" fonctionne

- [ ] **Step 3 : Commit**

```bash
git add pages/analytics.py
git commit -m "feat: page Analytics avec KPIs, tendances et répartitions"
```

---

## Vérification finale

- [ ] `pip install -r requirements.txt` — pas d'erreur
- [ ] `streamlit run app.py` — l'expander "📈 Tendances & Statistiques" affiche 3 graphiques
- [ ] La section "🗂️ Pipeline Commercial" affiche 5 colonnes avec les marchés publics
- [ ] Le lien "📈 Analytics" est visible dans la sidebar et ouvre la bonne page
- [ ] La page Analytics affiche KPIs, courbe, top 5 sources, donut secteurs
- [ ] Cliquer un titre dans le pipeline scroll/sélectionne le marché dans le tableau (via `_sel_title_pub`)
