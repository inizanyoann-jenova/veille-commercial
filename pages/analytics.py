from collections import defaultdict

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import distinct, func, or_

from database import SessionLocal, init_db
from models import Tender

SCORE_GO = 65

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


@st.cache_data(ttl=120)
def _load_analytics_kpis() -> dict:
    db = SessionLocal()
    try:
        total = db.query(Tender).filter(Tender.is_blacklisted != True).count()
        nb_go = db.query(Tender).filter(
            Tender.relevance_score >= SCORE_GO, Tender.is_blacklisted != True
        ).count()
        ca_gagne = db.query(func.sum(Tender.amount)).filter(
            Tender.status == "Gagné", Tender.amount != None
        ).scalar() or 0
        nb_sources = db.query(
            func.count(distinct(Tender.source))
        ).filter(Tender.source != None, Tender.source != "").scalar() or 0
        return {"total": total, "nb_go": nb_go, "ca_gagne": ca_gagne, "nb_sources": nb_sources}
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_pub_months() -> list[str]:
    db = SessionLocal()
    try:
        rows = db.query(Tender.publication_date).filter(
            Tender.is_blacklisted != True, Tender.publication_date != None
        ).all()
        return [r[0].strftime("%Y-%m") for r in rows]
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_top_sources() -> list[tuple]:
    db = SessionLocal()
    try:
        return (
            db.query(Tender.source, func.count(Tender.id).label("count"))
            .filter(Tender.is_blacklisted != True, Tender.source != None, Tender.source != "")
            .group_by(Tender.source)
            .order_by(func.count(Tender.id).desc())
            .limit(5)
            .all()
        )
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_secteur_counts() -> dict:
    db = SessionLocal()
    try:
        nb_public = db.query(Tender).filter(
            Tender.is_blacklisted != True,
            or_(Tender.secteur == "Public", Tender.secteur == None),
        ).count()
        nb_prive = db.query(Tender).filter(
            Tender.is_blacklisted != True, Tender.secteur == "Privé"
        ).count()
        return {"public": nb_public, "prive": nb_prive}
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_conversion_kpis() -> dict:
    db = SessionLocal()
    try:
        nb_soumis = db.query(Tender).filter(Tender.status == "Soumis").count()
        nb_gagne = db.query(Tender).filter(Tender.status == "Gagné").count()
        taux = round(nb_gagne / nb_soumis * 100) if nb_soumis > 0 else None
        return {"nb_soumis": nb_soumis, "nb_gagne": nb_gagne, "taux_conversion": taux}
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_win_rate_by_source() -> list[tuple]:
    db = SessionLocal()
    try:
        from sqlalchemy import case
        rows = (
            db.query(
                Tender.source,
                func.count(Tender.id).label("nb_soumis"),
                func.sum(
                    case((Tender.status == "Gagné", 1), else_=0)
                ).label("nb_gagne"),
            )
            .filter(Tender.status.in_(["Soumis", "Gagné"]), Tender.source != None, Tender.source != "")
            .group_by(Tender.source)
            .order_by(func.sum(case((Tender.status == "Gagné", 1), else_=0)).desc())
            .limit(5)
            .all()
        )
        return [(r.source, r.nb_gagne, r.nb_soumis) for r in rows]
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_avg_delay_go() -> float | None:
    db = SessionLocal()
    try:
        rows = (
            db.query(Tender.publication_date, Tender.deadline)
            .filter(
                Tender.relevance_score >= SCORE_GO,
                Tender.publication_date != None,
                Tender.deadline != None,
                Tender.is_blacklisted != True,
            )
            .all()
        )
        if not rows:
            return None
        delays = [(r.deadline - r.publication_date).days for r in rows if r.deadline > r.publication_date]
        return round(sum(delays) / len(delays)) if delays else None
    finally:
        db.close()


# ── KPIs globaux ──────────────────────────────────────────────────────────────

_kpis = _load_analytics_kpis()
_total = _kpis["total"]
_taux_go = round(_kpis["nb_go"] / _total * 100) if _total else 0
_ca_gagne = _kpis["ca_gagne"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total marchés collectés", _total)
k2.metric(f"Taux GO (score ≥ {SCORE_GO})", f"{_taux_go} %")
k3.metric("CA Gagné 🏆", f"{_ca_gagne:,.0f} €".replace(",", " ") if _ca_gagne else "—")
k4.metric("Sources distinctes", _kpis["nb_sources"])

st.markdown("### 🏆 Performance commerciale")

_conv = _load_conversion_kpis()
_wr = _load_win_rate_by_source()
_delay = _load_avg_delay_go()

kc1, kc2, kc3 = st.columns(3)
kc1.metric(
    "Taux de conversion Soumis → Gagné",
    f"{_conv['taux_conversion']} %" if _conv["taux_conversion"] is not None else "—",
    help=f"{_conv['nb_gagne']} gagné(s) sur {_conv['nb_soumis']} soumis",
)
kc2.metric(
    "Délai moyen traitement GO",
    f"{_delay} j" if _delay is not None else "—",
    help="Moyenne publication → deadline sur les marchés avec score ≥ 65",
)
kc3.metric(
    "Sources actives (Soumis/Gagné)",
    len(_wr),
)

if _wr:
    st.markdown("**Win rate par source (top 5)**")
    import pandas as _pd_wr
    _df_wr = _pd_wr.DataFrame(
        [{"Source": src, "Gagnés": ng, "Soumis": ns,
          "Win rate": f"{round(ng/ns*100)}%" if ns > 0 else "—"}
         for src, ng, ns in _wr]
    )
    st.dataframe(_df_wr, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Évolution mensuelle ───────────────────────────────────────────────────────

st.markdown("### 📅 Évolution mensuelle")

month_counts: dict[str, int] = defaultdict(int)
for m in _load_pub_months():
    month_counts[m] += 1

if month_counts:
    _months = sorted(month_counts.keys())
    _fig_line = px.line(
        x=_months,
        y=[month_counts[m] for m in _months],
        labels={"x": "Mois", "y": "Marchés collectés"},
        color_discrete_sequence=["#cc2222"],
        markers=True,
    )
    _fig_line.update_layout(showlegend=False, margin=dict(t=10, b=10, l=0, r=0), height=280)
    st.plotly_chart(_fig_line, use_container_width=True)
else:
    st.caption("Aucune donnée de publication disponible.")

st.markdown("---")

# ── Top 5 sources + Publics vs Privés ────────────────────────────────────────

col_src, col_sect = st.columns(2)

with col_src:
    st.markdown("### 🏆 Top 5 sources par volume")
    top_sources = _load_top_sources()
    if top_sources:
        _df_src = pd.DataFrame(top_sources, columns=["Source", "Marchés"])
        st.dataframe(_df_src, hide_index=True, use_container_width=True)
    else:
        st.caption("Aucune source enregistrée.")

with col_sect:
    st.markdown("### 🥧 Publics vs Privés")
    _secteurs = _load_secteur_counts()
    if _secteurs["public"] + _secteurs["prive"] > 0:
        _fig_sect = px.pie(
            values=[_secteurs["public"], _secteurs["prive"]],
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
