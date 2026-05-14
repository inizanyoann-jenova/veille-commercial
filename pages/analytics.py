from collections import defaultdict

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
k3.metric("CA Gagné 🏆", f"{ca_gagne:,.0f} €".replace(",", " ") if ca_gagne else "—")
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
