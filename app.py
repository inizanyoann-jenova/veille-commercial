from datetime import datetime, timedelta, date as _date
import hashlib as _hl
import html as _html
import re
from collections import Counter, defaultdict

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func as _func, or_

from database import SessionLocal, init_db
from apscheduler.schedulers.background import BackgroundScheduler as _BgScheduler
from export_excel import generate_executive_report
from llm_analyzer import (
    analyze_tender,
    auto_analyze_pending,
    auto_analyze_claude,
    _KW_SSI,
    _KW_CMSI,
    _KW_VIDEO,
    _KW_COURANTS_FAIBLES,
    _KW_MAINTENANCE,
    _KW_PENALITES,
    _KW_ERP,
    _match,
)
from source_registry import list_sources, add_source, remove_source, toggle_enabled
from models import Tender

from fiche_logic import SCORE_GO, SCORE_ETUDE, _compute_fiche_data

TENDER_TAGS = [
    "Partenaire requis",
    "En attente DCE",
    "Budget bloqué",
    "À voir avec DG",
    "Offre déposée",
    "Recours prévu",
]

# ── domaine detection ─────────────────────────────────────────────────────────

DOMAINES = {
    "🔥 SSI / Détection incendie": _KW_SSI,
    "💨 CMSI / Désenfumage": _KW_CMSI,
    "📷 Vidéosurveillance / CCTV": _KW_VIDEO,
    "⚡ Courants faibles": _KW_COURANTS_FAIBLES,
}


def detect_domaine(title: str, description: str = "") -> str:
    t = f" {(title + ' ' + description).lower()} "
    found = [label for label, keywords in DOMAINES.items() if any(_match(kw, t) for kw in keywords)]
    return ", ".join(found) if found else "Autre"


# ── territoire detection ──────────────────────────────────────────────────────

TERRITOIRES = {
    "🏝️ La Réunion": [
        "la réunion", "la reunion", " 974 ", "(974)", "ile bourbon",
        "ile de la reunion",
        # Communes
        "saint-denis", "saint-pierre", "saint-paul", "le tampon", "saint-louis",
        "le port", "sainte-marie", "saint-benoît", "saint-benoit", "saint-joseph",
        "saint-leu", "sainte-suzanne", "saint-andré", "saint-andre",
        "bras-panon", "cilaos", "entre-deux", "étang-salé", "etang-sale",
        "petite-île", "la plaine-des-palmistes",
        "saint-philippe", "sainte-rose", "salazie", "les trois-bassins",
        "trois-bassins", "les avirons", "la possession", "saint-gilles",
        # Codes postaux 974xx
        "97400", "97410", "97411", "97412", "97413", "97414", "97416",
        "97417", "97418", "97419", "97420", "97421", "97422", "97423",
        "97424", "97425", "97426", "97427", "97428", "97429", "97430",
        "97431", "97432", "97433", "97434", "97436", "97437", "97438",
        "97439", "97440", "97441", "97442", "97450", "97460", "97470",
        "97480", "97490",
    ],
    "🏝️ Mayotte": [
        "mayotte", " 976 ", "(976)", "petite-terre", "grande-terre",
        # Communes
        "mamoudzou", "dzaoudzi", "pamandzi", "koungou", "bandraboua",
        "bouéni", "boueni", "chiconi", "chirongui", "dembéni", "dembeni",
        "kani-kéli", "kani-keli", "mtsamboro", "m'tsangamouji",
        "ouangani", "sada", "tsingoni", "acoua",
        # Codes postaux 976xx
        "97600", "97610", "97615", "97616", "97617", "97618", "97619",
        "97620", "97625", "97630", "97640", "97650", "97660", "97670", "97680",
    ],
    "🇫🇷 France métropole": [
        "france", "paris", "lyon", "marseille", "bordeaux", "nantes", "toulouse",
        "lille", "strasbourg", "rennes", "nice", "montpellier",
    ],
    "🌍 Madagascar": [
        "madagascar", "antananarivo", "tamatave", "toamasina", "mahajanga",
        "fianarantsoa", "toliara",
    ],
    "🌊 Maurice": [
        "mauritius", "île maurice", "ile maurice", "port-louis", "port louis",
        "beau bassin", "curepipe", "vacoas",
    ],
    "🌙 Comores": [
        "comores", "comoros", "moroni", "anjouan", "mohéli", "moheli", "grande comore",
    ],
}

# Groupes de filtres rapides
GROUPES = {
    "🇫🇷 France (DOM inclus)": ["🏝️ La Réunion", "🏝️ Mayotte", "🇫🇷 France métropole"],
    "🌏 International (Océan Indien)": ["🌍 Madagascar", "🌊 Maurice", "🌙 Comores"],
}


def detect_territoire(title: str, description: str = "") -> str:
    t = f" {(title + ' ' + description).lower()} "
    found = []
    for label, keywords in TERRITOIRES.items():
        if any(kw in t for kw in keywords):
            found.append(label)
    return ", ".join(found) if found else "Non précisé"



st.set_page_config(
    page_title="DEF OI — Veille Marchés",
    page_icon="🔥",
    layout="wide",
)

init_db()

# ── Scheduler ré-validation hebdomadaire ──────────────────────────────────────

if "scheduler_started" not in st.session_state:
    from source_registry import _run_weekly_ping as _rwp, Source as _SrcSched
    from datetime import datetime as _dts

    def _maybe_run_catchup():
        from database import SessionLocal as _SL_c
        from source_registry import Source as _SrcC, _ping_source as _ps
        _db_c = _SL_c()
        try:
            _now_c = _dts.utcnow()
            stale = _db_c.query(_SrcC).filter(_SrcC.is_validated == True).all()
            for s in stale:
                if s.last_ping_at is None or (_now_c - s.last_ping_at.replace(tzinfo=None)).days >= 8:
                    _ps(_db_c, s)
        finally:
            _db_c.close()

    import threading as _threading
    _threading.Thread(target=_maybe_run_catchup, daemon=True).start()

    _scheduler = _BgScheduler()
    _scheduler.add_job(_rwp, "interval", weeks=1, id="weekly_ping")
    _scheduler.start()
    st.session_state["scheduler_started"] = True

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="css"] { font-family: 'Inter', system-ui, -apple-system, sans-serif !important; }

#MainMenu, footer, header { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }

.main .block-container {
    padding-top: 1.2rem;
    padding-left: 2.5rem;
    padding-right: 2.5rem;
    max-width: 100%;
}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1c1c2e 0%, #16213e 55%, #0f3460 100%) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.25);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] h2 {
    font-size: 1.05rem !important; font-weight: 800 !important;
    color: #fff !important; letter-spacing: -0.01em;
}
[data-testid="stSidebar"] p { color: #94a3b8 !important; font-size: 0.78rem !important; }
[data-testid="stSidebar"] label {
    color: #94a3b8 !important; font-size: 0.71rem !important;
    font-weight: 600 !important; text-transform: uppercase; letter-spacing: 0.07em;
}
[data-testid="stSidebar"] h3 {
    color: #cbd5e1 !important; font-size: 0.71rem !important;
    font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.09em;
}
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08) !important; margin: 0.7rem 0 !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.13) !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] > div:first-child:hover {
    border-color: rgba(204,34,34,0.6) !important;
}
[data-testid="stSidebar"] button[kind="primary"] {
    background: linear-gradient(135deg, #cc2222 0%, #e03333 100%) !important;
    border: none !important; border-radius: 10px !important;
    color: #fff !important; font-weight: 700 !important; font-size: 0.84rem !important;
    box-shadow: 0 4px 14px rgba(204,34,34,0.4) !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(204,34,34,0.5) !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 8px !important; color: #e2e8f0 !important;
    font-size: 0.8rem !important; font-weight: 500 !important;
    transition: all 0.2s !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(204,34,34,0.28) !important;
    border-color: rgba(204,34,34,0.55) !important;
}

/* ── Boutons ─────────────────────────────────────────────────────────────── */
.stButton > button {
    border-radius: 8px !important; font-weight: 600 !important;
    font-size: 0.85rem !important; transition: all 0.2s !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #cc2222, #e03333) !important;
    border: none !important; color: #fff !important;
    box-shadow: 0 2px 8px rgba(204,34,34,0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 5px 16px rgba(204,34,34,0.42) !important;
}
.stButton > button[kind="secondary"]:hover {
    border-color: #cc2222 !important; color: #cc2222 !important;
    background: rgba(204,34,34,0.04) !important;
}
.stDownloadButton > button {
    background: linear-gradient(135deg, #cc2222, #e03333) !important;
    border: none !important; border-radius: 10px !important;
    color: #fff !important; font-weight: 700 !important;
    box-shadow: 0 4px 16px rgba(204,34,34,0.35) !important;
    transition: all 0.25s !important; font-size: 0.95rem !important;
}
.stDownloadButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 26px rgba(204,34,34,0.48) !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────────── */
[data-baseweb="select"] > div:first-child {
    border-radius: 8px !important; border-color: #e5e7eb !important;
    font-size: 0.87rem !important; transition: border-color 0.2s, box-shadow 0.2s !important;
}
[data-baseweb="select"] > div:first-child:focus-within {
    border-color: #cc2222 !important;
    box-shadow: 0 0 0 3px rgba(204,34,34,0.1) !important;
}
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
    border-radius: 8px !important; font-size: 0.87rem !important;
}

/* ── Alerts ──────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
    border-radius: 10px !important; border: none !important;
    font-size: 0.86rem !important;
}

/* ── Expanders ───────────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
    border: 1px solid #e5e7eb !important;
    border-radius: 12px !important; overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
[data-testid="stExpander"] > details > summary {
    background: #fafafa !important; padding: 0.8rem 1.2rem !important;
    font-weight: 600 !important; font-size: 0.88rem !important; color: #374151 !important;
}
[data-testid="stExpander"] > details > summary:hover { background: #f3f4f6 !important; }

/* ── Data editor ─────────────────────────────────────────────────────────── */
[data-testid="stDataEditor"] {
    border-radius: 12px !important; overflow: hidden;
    border: 1px solid #e5e7eb !important;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
[data-testid="stDataEditor"] th {
    background: #f9fafb !important; color: #6b7280 !important;
    font-weight: 700 !important; font-size: 0.69rem !important;
    text-transform: uppercase; letter-spacing: 0.07em;
    border-bottom: 1px solid #e5e7eb !important;
}

/* ── Séparateurs ─────────────────────────────────────────────────────────── */
hr { border: none !important; border-top: 1px solid #f3f4f6 !important; margin: 1.25rem 0 !important; }

/* ── st.metric (fiches commerciales) ─────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #f0f2f5; border-radius: 10px;
    padding: 12px 16px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
[data-testid="stMetricLabel"] {
    color: #9ca3af !important; font-size: 0.69rem !important;
    text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600 !important;
}
[data-testid="stMetricValue"] {
    color: #111827 !important; font-size: 1.55rem !important;
    font-weight: 800 !important; letter-spacing: -0.02em;
}

/* ── Cartes KPI custom ───────────────────────────────────────────────────── */
.kpi-grid {
    display: flex; gap: 12px; margin: 0.2rem 0 1.2rem 0; flex-wrap: nowrap;
}
.kpi-card {
    flex: 1; background: #fff; border-radius: 12px;
    padding: 18px 20px 14px; position: relative; overflow: hidden;
    border: 1px solid #f0f2f5;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.03);
    transition: box-shadow 0.2s, transform 0.2s;
}
.kpi-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.1); transform: translateY(-2px); }
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, #cc2222, #e55555);
}
.kpi-card.green::before  { background: linear-gradient(90deg, #16a34a, #4ade80); }
.kpi-card.blue::before   { background: linear-gradient(90deg, #2563eb, #60a5fa); }
.kpi-card.orange::before { background: linear-gradient(90deg, #d97706, #fbbf24); }
.kpi-card.purple::before { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
.kpi-card.teal::before   { background: linear-gradient(90deg, #0891b2, #22d3ee); }
.kpi-value {
    font-size: 1.85rem; font-weight: 800; color: #111827;
    line-height: 1.1; margin-bottom: 5px; letter-spacing: -0.02em;
}
.kpi-label {
    font-size: 0.67rem; font-weight: 600; color: #9ca3af;
    text-transform: uppercase; letter-spacing: 0.08em;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.kpi-sub { font-size: 0.71rem; font-weight: 700; color: #6b7280; margin-top: 2px; }

/* ── En-tête de page ─────────────────────────────────────────────────────── */
.page-header {
    display: flex; align-items: flex-end; justify-content: space-between;
    padding: 0.25rem 0 1.2rem 0; border-bottom: 2px solid #f3f4f6; margin-bottom: 1.5rem;
}
.page-header h1 {
    font-size: 1.7rem !important; font-weight: 800 !important;
    color: #111827 !important; letter-spacing: -0.03em;
    margin: 0 0 2px 0 !important; line-height: 1.2 !important;
}
.page-header h1 em { font-style: normal; color: #cc2222; }
.page-header p { font-size: 0.77rem; color: #9ca3af; margin: 0; }
.page-header-badge {
    background: #fef2f2; border: 1px solid #fecaca; border-radius: 20px;
    padding: 4px 12px; font-size: 0.72rem; font-weight: 700;
    color: #cc2222; white-space: nowrap;
}

/* ── Titres de section ───────────────────────────────────────────────────── */
.section-header { margin: 1.5rem 0 0.8rem 0; }
.section-title {
    display: flex; align-items: center; gap: 10px;
    font-size: 1rem; font-weight: 700; color: #111827;
    padding-bottom: 10px; border-bottom: 2px solid #f3f4f6;
}
.section-dot {
    width: 8px; height: 8px; background: #cc2222;
    border-radius: 50%; flex-shrink: 0;
}
.section-subtitle { font-size: 0.75rem; color: #9ca3af; margin: 4px 0 0 18px; }

/* ── Label CA pipeline ───────────────────────────────────────────────────── */
.ca-label {
    font-size: 0.69rem; font-weight: 700; color: #9ca3af;
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 0.8rem 0 0 0; padding-top: 0.6rem;
    border-top: 1px dashed #e5e7eb;
}
</style>
""", unsafe_allow_html=True)


# ── helpers ──────────────────────────────────────────────────────────────────

def new_db():
    return SessionLocal()


def _run_auto_analysis():
    """Lance l'analyse locale sur tous les marchés non encore analysés."""
    db = new_db()
    try:
        auto_analyze_pending(db)
    finally:
        db.close()


def _gonogo(score: int) -> str:
    if score >= SCORE_GO:
        return "🟢 GO"
    elif score >= SCORE_ETUDE:
        return "🟡 Étudier"
    return "🔴 Passer"


def _kpi_row(items: list[tuple], colors: list[str] | None = None) -> str:
    if colors is None:
        colors = [""] * len(items)
    cards = "".join(
        f'<div class="kpi-card {c}"><div class="kpi-value">{v}</div><div class="kpi-label">{l}</div></div>'
        for (l, v), c in zip(items, colors)
    )
    return f'<div class="kpi-grid">{cards}</div>'


def _section_html(title: str, subtitle: str | None = None) -> str:
    sub = f'<p class="section-subtitle">{subtitle}</p>' if subtitle else ""
    return f'<div class="section-header"><div class="section-title"><span class="section-dot"></span>{title}</div>{sub}</div>'


# Auto-analyse au démarrage (une seule fois par session)
if "auto_analyzed" not in st.session_state:
    _run_auto_analysis()
    st.session_state["auto_analyzed"] = True
st.session_state.setdefault("new_tender_ids", set())


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
                    "_deadline_dt": t.deadline,
                    "_desc": (t.description or "").lower(),
                    "_tags": t.tags or [],
                }
            )
        return rows
    finally:
        db.close()


def delete_tender(tender_id: str) -> None:
    """Suppression douce : marque comme blacklisté pour ne jamais réapparaître après collecte."""
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.is_blacklisted = True
            db.commit()
    finally:
        db.close()


def toggle_saved(tender_id: str, value: bool) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.is_saved = value
            db.commit()
    finally:
        db.close()


@st.cache_data(ttl=60)
def load_saved_tenders() -> list[dict]:
    db = new_db()
    try:
        tenders = (
            db.query(Tender)
            .filter(Tender.is_saved == True, Tender.is_blacklisted != True)
            .order_by(Tender.publication_date.desc())
            .all()
        )
        rows = []
        for t in tenders:
            a = t.llm_analysis or {}
            domaine = detect_domaine(t.title or "", t.description or "")
            territoire = detect_territoire(t.title or "", t.description or "")
            rows.append({
                "ID": t.id,
                "Titre": t.title or "Sans titre",
                "Source": t.source or "",
                "Territoire": territoire,
                "Domaine": domaine,
                "Statut": t.status or "À qualifier",
                "Type": a.get("type_marche") or t.type_opportunite or "—",
                "Publication": t.publication_date.strftime("%d/%m/%Y") if t.publication_date else "—",
                "Secteur": t.secteur or "Public",
            })
        return rows
    finally:
        db.close()


@st.cache_data(ttl=300)
def load_chart_data() -> list[dict]:
    """Charge les données pour les graphiques (title + description pour détection territoire/domaine)."""
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


@st.cache_data(ttl=60)
def load_pipeline() -> dict[str, list[dict]]:
    """Retourne les marchés publics groupés par statut pour la vue pipeline."""
    db = new_db()
    try:
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


def save_status(tender_id: str, new_status: str) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.status = new_status
            db.commit()
    finally:
        db.close()


def save_notes(tender_id: str, notes: str) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.notes = notes or None
            db.commit()
    finally:
        db.close()


def save_tags(tender_id: str, tags: list[str]) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.tags = tags
            db.commit()
    finally:
        db.close()


def save_amount(tender_id: str, amount: int | None) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.amount = amount
            db.commit()
    finally:
        db.close()


def run_analysis(tender_id: str) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if not t:
            return
        result = analyze_tender(
            f"{t.title or ''} {t.description or ''}",
            source_url=t.source if t.source and t.source.startswith("http") else None,
        )
        t.llm_analysis = result
        t.relevance_score = result.get("score_pertinence", 0)
        t.is_maintenance = result.get("type_marche", "").lower() == "maintenance"
        db.commit()
    finally:
        db.close()


def _sort_rows(rows: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "Score ↓":
        return sorted(rows, key=lambda r: -(r.get("Score") or 0))
    elif sort_by == "Publication ↓":
        return sorted(rows, key=lambda r: r.get("_deadline_dt") or datetime.min, reverse=True)
    else:  # Date limite ↑ (défaut)
        return sorted(rows, key=lambda r: (
            r.get("_deadline_dt") is None,
            r.get("_deadline_dt") or datetime.max,
        ))


@st.cache_data(ttl=60)
def load_kpis_public() -> dict:
    db = new_db()
    try:
        pub = or_(Tender.secteur == "Public", Tender.secteur == None)
        return {
            "total": db.query(Tender).filter(pub).count(),
            "a_qualifier": db.query(Tender).filter(pub, Tender.status == "À qualifier").count(),
            "en_cours": db.query(Tender).filter(pub, Tender.status == "En cours").count(),
            "gagnes": db.query(Tender).filter(pub, Tender.status == "Gagné").count(),
            "soumis": db.query(Tender).filter(pub, Tender.status == "Soumis").count(),
        }
    finally:
        db.close()


@st.cache_data(ttl=60)
def load_kpis_ca() -> dict:
    db = new_db()
    try:
        pub = or_(Tender.secteur == "Public", Tender.secteur == None)

        def _sum(statuts):
            res = db.query(_func.sum(Tender.amount)).filter(
                pub, Tender.status.in_(statuts), Tender.amount != None
            ).scalar()
            return res or 0

        en_cours = _sum(["En cours"])
        soumis = _sum(["Soumis"])
        gagne = _sum(["Gagné"])
        return {"en_cours": en_cours, "soumis": soumis, "gagne": gagne, "pipeline": en_cours + soumis}
    finally:
        db.close()


@st.cache_data(ttl=60)
def load_kpis_priv() -> dict:
    db = new_db()
    try:
        return {
            "permis": db.query(Tender).filter(Tender.secteur == "Privé", Tender.type_opportunite == "Permis Construire").count(),
            "presse": db.query(Tender).filter(Tender.secteur == "Privé", Tender.type_opportunite == "Presse").count(),
            "instit": db.query(Tender).filter(Tender.secteur == "Privé", Tender.type_opportunite == "Institution").count(),
            "devbanks": db.query(Tender).filter(Tender.type_opportunite == "Banque Dev.").count(),
            "qualif_priv": db.query(Tender).filter(Tender.secteur == "Privé", Tender.status == "À qualifier").count(),
        }
    finally:
        db.close()


# ── sidebar ───────────────────────────────────────────────────────────────────

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
    for err in errors:
        st.warning(err)


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
        if st.button("✕ Fermer", key="close_new_tenders_section"):
            st.session_state["new_tender_ids"] = set()
            st.rerun(scope="fragment")

    for t in top5:
        a = t.llm_analysis or {}
        score = _score(t)
        domaine = detect_domaine(t.title or "", t.description or "")
        territoire = detect_territoire(t.title or "", t.description or "")
        justif_raw = (a.get("justification_score") or "")[:120]
        justif = _html.escape(justif_raw)

        if score >= SCORE_GO:
            color_class = ""
            badge = f"🟢 GO — Score {score}/100"
        elif score >= SCORE_ETUDE:
            color_class = "orange"
            badge = f"🟡 Étudier — Score {score}/100"
        else:
            color_class = "teal"
            badge = f"🔴 Passer — Score {score}/100"

        title_short = _html.escape((t.title or "Sans titre")[:90])
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


with st.sidebar:
    st.markdown("## 🔥 DEF Océan Indien")
    st.markdown("**Veille Marchés Publics**")
    st.markdown("---")
    search_query = ""  # défini dans la page principale

    _now = datetime.now()
    _cy = _now.year
    periode_labels = {
        "30 derniers jours": (_now - timedelta(days=30), True),
        f"Cette année ({_cy})": (datetime(_cy, 1, 1), False),
        f"2 ans": (datetime(_cy - 1, 1, 1), False),
        f"3 ans": (datetime(_cy - 2, 1, 1), False),
        "Tout": (None, False),
    }
    selected_periode = st.selectbox(
        "Période",
        list(periode_labels.keys()),
        index=2,  # défaut : 2 ans
    )
    date_from, strict_date = periode_labels[selected_periode]

    st.markdown("**Territoire**")
    selected_groupe = st.selectbox(
        "Groupe rapide",
        ["Tous"] + list(GROUPES.keys()),
        label_visibility="collapsed",
    )
    selected_territoires = st.multiselect(
        "Affiner par territoire",
        options=list(TERRITOIRES.keys()),
        placeholder="Tous les territoires",
    )

    selected_domaines = st.multiselect(
        "Filtrer par domaine",
        options=list(DOMAINES.keys()),
        placeholder="Tous les domaines",
    )

    maintenance_only = st.checkbox("Maintenance uniquement")
    only_recent = st.checkbox("🆕 Nouveaux (24h)")
    urgent_only = st.checkbox("🚨 Délais < 14 jours")
    selected_status = st.selectbox(
        "Filtrer par statut",
        ["Tous", "À qualifier", "En cours", "Soumis", "Gagné", "Perdu"],
    )
    selected_decisions = st.multiselect(
        "Filtrer par décision",
        options=["🟢 GO", "🟡 Étudier", "🔴 Passer"],
        placeholder="Toutes les décisions",
    )
    sort_by = st.selectbox(
        "Trier par",
        ["Date limite ↑", "Score ↓", "Publication ↓"],
        index=0,
    )
    selected_tags = st.multiselect(
        "🏷️ Filtrer par tag",
        options=TENDER_TAGS,
        placeholder="Tous les tags",
    )
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
                value=st.session_state.get(f"src_filter_{_src_name}", True),
                key=f"src_filter_{_src_name}",
            )

    if st.button("🤖 Analyser en lot (Claude)", use_container_width=True,
                 help="Analyse les 10 marchés prioritaires non encore traités par Claude"):
        _prog_bar = st.progress(0.0)
        _prog_text = st.empty()

        def _claude_progress(i, n, title):
            if n > 0:
                _prog_bar.progress(i / n)
            _prog_text.text(f"({i}/{n}) {title[:50]}…" if title else "Terminé")

        _db_g = new_db()
        try:
            _nb_done, _retry_after = auto_analyze_claude(_db_g, max_per_run=10, progress_cb=_claude_progress)
        finally:
            _db_g.close()

        _prog_bar.empty()
        _prog_text.empty()
        st.cache_data.clear()

        if _nb_done:
            st.success(f"✅ {_nb_done} marché(s) analysé(s) via Claude.")

        if _retry_after >= 0:  # quota atteint
            _mins = max(1, _retry_after // 60)
            st.warning(f"⚠️ Quota Claude atteint — réessayez dans ~{_mins} min.")
        elif not _nb_done:
            st.info("Tous les marchés ont déjà été analysés par Claude.")

    st.markdown("---")
    col_nav1, col_nav2, col_nav3 = st.columns(3)
    with col_nav1:
        st.page_link("pages/parametres.py", label="⚙️ Paramètres", use_container_width=True)
    with col_nav2:
        st.page_link("pages/guide.py", label="📖 Guide", use_container_width=True)
    with col_nav3:
        st.page_link("pages/analytics.py", label="📈 Analytics", use_container_width=True)


@st.cache_data(ttl=300)
def _generate_report_cached() -> bytes:
    db = new_db()
    try:
        return generate_executive_report(db)
    finally:
        db.close()


# ── header + export ───────────────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
  <div class="page-header-left">
    <h1>🔥 DEF Océan Indien — <em>Veille Marchés</em></h1>
    <p>Périmètre : La Réunion (974) &amp; Mayotte (976) · SSI · CMSI · Détection incendie · Vidéosurveillance</p>
  </div>
  <div class="page-header-badge">Marchés Publics &amp; Privés</div>
</div>
""", unsafe_allow_html=True)

# Large export button
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    st.download_button(
        label="📊  Télécharger le Rapport Direction (Excel)",
        data=_generate_report_cached(),
        file_name=f"Rapport_Direction_DEF_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )

st.markdown("---")

# ── Nouveaux marchés post-collecte ────────────────────────────────────────────
_render_new_tenders_section()

# ── KPI metrics ───────────────────────────────────────────────────────────────

_kpis = load_kpis_public()
st.markdown(_kpi_row([
    ("Total marchés", _kpis["total"]),
    ("À qualifier", _kpis["a_qualifier"]),
    ("En cours", _kpis["en_cours"]),
    ("Soumis", _kpis["soumis"]),
    ("Gagnés 🏆", _kpis["gagnes"]),
], colors=["", "orange", "blue", "purple", "green"]), unsafe_allow_html=True)

# KPI CA pipeline
_kpis_ca = load_kpis_ca()
if _kpis_ca["pipeline"] > 0 or _kpis_ca["gagne"] > 0:
    st.markdown('<p class="ca-label">CA Pipeline — montants renseignés</p>', unsafe_allow_html=True)
    st.markdown(_kpi_row([
        ("CA En cours", f"{_kpis_ca['en_cours']:,.0f} €".replace(",", " ")),
        ("CA Soumis", f"{_kpis_ca['soumis']:,.0f} €".replace(",", " ")),
        ("CA Gagné 🏆", f"{_kpis_ca['gagne']:,.0f} €".replace(",", " ")),
        ("CA Total pipeline", f"{_kpis_ca['pipeline']:,.0f} €".replace(",", " ")),
    ], colors=["blue", "orange", "green", ""]), unsafe_allow_html=True)

st.markdown("---")

# ── signaux privés KPI ────────────────────────────────────────────────────────

_kpis_priv = load_kpis_priv()
st.markdown('<p class="ca-label">Signaux privés</p>', unsafe_allow_html=True)
st.markdown(_kpi_row([
    ("Permis construire", _kpis_priv["permis"]),
    ("Articles presse", _kpis_priv["presse"]),
    ("Institutions", _kpis_priv["instit"]),
    ("Banques Dev.", _kpis_priv["devbanks"]),
    ("Privé — À qualifier", _kpis_priv["qualif_priv"]),
], colors=["teal", "blue", "purple", "orange", ""]), unsafe_allow_html=True)

# ── Tendances & Statistiques ──────────────────────────────────────────────────

with st.expander("📈 Tendances & Statistiques", expanded=False):
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
                    _wk = r["pub"].strftime("%G-W%V")
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

st.markdown("---")

# ── Filtres territoriaux communs ──────────────────────────────────────────────

terr_actifs = selected_territoires[:]
if selected_groupe != "Tous":
    terr_actifs = list(set(terr_actifs + GROUPES[selected_groupe]))

status_options = ["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]


def _render_fiche(tender_id: str, key_suffix: str) -> None:
    db_det = new_db()
    try:
        t = db_det.query(Tender).filter(Tender.id == tender_id).first()
        if not t:
            return
        a = t.llm_analysis or {}
        domaine = detect_domaine(t.title or "", t.description or "")
        territoire = detect_territoire(t.title or "", t.description or "")
        score = a.get("score_pertinence", t.relevance_score or 0)

        # ── Délai restant ─────────────────────────────────────────────────────
        jours_restants = None
        if t.deadline:
            try:
                today = _date.today()
                dl = t.deadline.date() if hasattr(t.deadline, "date") else t.deadline
                jours_restants = (dl - today).days
            except Exception:
                pass

        data = _compute_fiche_data(
            score, jours_restants, domaine, territoire,
            bool(t.is_maintenance), t.title or "", a,
        )

        # ── BLOC 1 : Header de décision ───────────────────────────────────────
        tag = a.get("tag_pertinence") or _gonogo(score)
        header_line = f"**{tag}** — Score {score}/100 · {domaine} · {territoire}"
        if score >= SCORE_GO:
            st.success(header_line)
        elif score >= SCORE_ETUDE:
            st.warning(header_line)
        else:
            st.error(header_line)
        if a.get("justification_score"):
            st.caption(f"💡 {a['justification_score']}")

        # ── BLOC 2 : Métriques condensées ────────────────────────────────────
        m1, m2, m3, m4, m5 = st.columns(5)
        if jours_restants is not None:
            m1.metric("Délai (j)", jours_restants)
        else:
            m1.metric("Délai (j)", "—")
        m2.metric("Type", a.get("type_marche") or t.type_opportunite or "—")
        m3.metric("Maintenance", "Oui" if t.is_maintenance else "Non")
        m4.metric("Concurrents", len(a.get("marques_concurrentes_citees", [])))
        source_a = a.get("_source", "local")
        m5.metric("Analyse", "Claude IA" if source_a in ("claude", "gemini") else "Règles")

        # ── BLOC 3 : Plan d'action ────────────────────────────────────────────
        st.markdown(f"#### {data['label_action']}")
        for i, step in enumerate(data["steps"], 1):
            st.markdown(f"{i}. {step}")
        for risque in data["risques"]:
            st.warning(risque)

        # ── BLOC 4 : Atouts DEF OI ────────────────────────────────────────────
        st.markdown("#### Pourquoi c'est pertinent pour DEF OI")
        for atout in data["atouts"]:
            st.markdown(atout)

        # ── BLOC 5 : Détail technique (expander) ──────────────────────────────
        with st.expander("📊 Détail du score & mots-clés"):
            st.markdown("**Décomposition du score DEF**")
            if source_a in ("claude", "gemini"):
                st.caption("Estimation indicative — le score affiché est celui de l'IA, pas la somme ci-dessous.")
            for nom, val, maxval in [
                ("Pertinence métier", data["sm"], 45),
                ("Proximité géographique", data["sg"], 30),
                ("Mots-clés dans le titre", data["sk"], 15),
                ("Maintenance / Récurrence", data["smaint"], 10),
            ]:
                pct = val / maxval if maxval > 0 else 0
                st.markdown(f"**{nom}** — `{val}/{maxval}`")
                st.progress(pct)

            st.markdown("---")
            st.markdown("**Mots-clés métier détectés**")
            full_text = f" {((t.title or '') + ' ' + (t.description or '')).lower()} "

            def _find_kws(kw_list: list, label: str) -> bool:
                hits = []
                for kw in kw_list:
                    if kw.startswith(r"\b"):
                        if re.search(kw, full_text):
                            hits.append(re.sub(r"\\b", "", kw).strip())
                    elif kw in full_text:
                        hits.append(kw.strip())
                hits = list(dict.fromkeys(hits))
                if hits:
                    st.markdown(f"**{label} :** {' · '.join(f'`{h}`' for h in hits[:8])}")
                return bool(hits)

            any_hit = any([
                _find_kws(_KW_SSI, "🔥 SSI / Incendie"),
                _find_kws(_KW_CMSI, "💨 CMSI / Désenfumage"),
                _find_kws(_KW_VIDEO, "📷 Vidéosurveillance"),
                _find_kws(_KW_COURANTS_FAIBLES, "⚡ Courants faibles"),
                _find_kws(_KW_MAINTENANCE, "🔧 Maintenance"),
                _find_kws(_KW_ERP, "🏢 Bâtiment ERP"),
                _find_kws(_KW_PENALITES, "⚠️ Pénalités / Risques"),
            ])
            if not any_hit:
                st.caption("Aucun mot-clé métier détecté dans le titre ni la description.")

            st.markdown("---")
            st.markdown("**Contexte**")
            territoire_ia = a.get("territoire_ia") or territoire
            domaines_ia = a.get("domaines_concernes", [])
            concurrents = a.get("marques_concurrentes_citees", [])
            st.markdown(f"🏷️ **Type :** {a.get('type_marche') or t.type_opportunite or 'Inconnu'}")
            st.markdown(f"🌍 **Territoire (IA) :** {territoire_ia}")
            if domaines_ia:
                st.markdown(f"🔧 **Domaines :** {', '.join(domaines_ia)}")
            st.markdown(f"🏢 **Secteur :** {getattr(t, 'secteur', None) or 'Public'}")
            if concurrents:
                st.markdown(f"🏭 **Concurrents :** {', '.join(concurrents)}")

            st.markdown("---")
            st.markdown("**Description brute**")
            if t.description and t.description.strip():
                st.write(t.description)
            else:
                st.caption("Aucune description textuelle disponible.")
                st.markdown(f"**Titre complet :** {t.title or '—'}")
                if getattr(t, "source", None):
                    st.markdown(f"**Source :** {t.source}")
                st.info("Consulter directement la plateforme source pour accéder au cahier des charges complet.")

        st.markdown("---")

        # ── BLOC 6 : Actions rapides ──────────────────────────────────────────
        col_save, col_qualify, col_reanalyze, _ = st.columns([2, 2, 2, 4])
        with col_save:
            star = bool(t.is_saved)
            label_star = "⭐ Sauvegardé" if star else "⭐ Sauvegarder"
            if st.button(label_star, key=f"fiche_save_{key_suffix}_{tender_id}"):
                toggle_saved(tender_id, not star)
                st.cache_data.clear()
                st.rerun()
        with col_qualify:
            if t.status not in ("En cours", "Soumis", "Gagné", "Perdu"):
                if st.button("✅ Qualifier → En cours", key=f"fiche_qualify_{key_suffix}_{tender_id}"):
                    save_status(tender_id, "En cours")
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.caption(f"Statut : {t.status}")
        with col_reanalyze:
            if st.button("🤖 Réanalyser", key=f"reanalyze_{key_suffix}_{tender_id}",
                         help="Relance l'analyse Claude pour affiner le score et la justification"):
                with st.spinner("Analyse Claude en cours…"):
                    run_analysis(tender_id)
                st.cache_data.clear()
                st.rerun()

        with st.expander("📝 Notes internes", expanded=bool(t.notes)):
            _notes_new = st.text_area(
                "Annotations commerciales (non exportées)",
                value=t.notes or "",
                height=80,
                key=f"notes_area_{key_suffix}_{tender_id}",
            )
            if st.button("💾 Enregistrer", key=f"save_notes_{key_suffix}_{tender_id}"):
                save_notes(tender_id, _notes_new)
                st.success("Notes enregistrées.")

        with st.expander("🏷️ Tags", expanded=bool(t.tags)):
            _selected_tags = st.multiselect(
                "Étiquettes",
                options=TENDER_TAGS,
                default=[tg for tg in (t.tags or []) if tg in TENDER_TAGS],
                key=f"tags_ms_{key_suffix}_{tender_id}",
            )
            if st.button("💾 Sauvegarder les tags", key=f"save_tags_{key_suffix}_{tender_id}"):
                save_tags(tender_id, _selected_tags)
                st.cache_data.clear()
                st.success("Tags sauvegardés.")
    finally:
        db_det.close()


def _render_editor_section(
    rows: list[dict],
    section_title: str,
    section_subtitle: str,
    fiche_title: str,
    fiche_label: str,
    editor_key: str,
    sel_all_key: str,
    sel_title_key: str,
    del_btn_key: str,
    sel_box_key: str,
) -> None:
    st.markdown(_section_html(section_title, section_subtitle), unsafe_allow_html=True)

    if not rows:
        st.info("Aucun résultat. Lancez la collecte depuis le menu latéral ou ajustez les filtres.")
        return

    import io as _io
    df = pd.DataFrame(rows)

    # ── Export CSV ────────────────────────────────────────────────────────────
    _export_cols = [c for c in df.columns if not c.startswith("_") and c not in ("ID", "Secteur")]
    _csv_buf = _io.StringIO()
    df[_export_cols].to_csv(_csv_buf, index=False)
    st.download_button(
        "📥 Exporter vue filtrée (CSV)",
        data=_csv_buf.getvalue().encode("utf-8-sig"),
        file_name=f"DEF_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key=f"csv_{editor_key}",
    )

    # ── Tableau principal (clic pour sélectionner) ────────────────────────────
    st.caption("👆 Cliquez sur une ligne pour la sélectionner et afficher son analyse ci-dessous")
    view_event = st.dataframe(
        df.drop(columns=["ID", "Secteur", "_deadline_dt"], errors="ignore"),
        column_config={
            "Go/No-Go": st.column_config.TextColumn("Décision", width="small"),
            "Titre": st.column_config.TextColumn("Titre du Marché", width="large"),
            "Source": st.column_config.LinkColumn("Source", width="small"),
            "Territoire": st.column_config.TextColumn("Territoire", width="medium"),
            "Domaine": st.column_config.TextColumn("Domaine", width="medium"),
            "Score": st.column_config.ProgressColumn("Score DEF", min_value=0, max_value=100, format="%d"),
            "Date Limite": st.column_config.TextColumn("Date Limite", width="small"),
            "Publication": st.column_config.TextColumn("Publication", width="small"),
            "Statut": st.column_config.TextColumn("Statut", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Montant (€)": st.column_config.NumberColumn("Montant (€)", format="%d €", width="small"),
            "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
        },
        column_order=["Go/No-Go", "Titre", "Source", "Territoire", "Domaine", "Score", "Montant (€)", "Date Limite", "Publication", "Statut", "Type", "⭐"],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"{editor_key}_view",
    )

    # Clic sur une ligne → met à jour le dropdown d'analyse
    if view_event.selection.rows:
        selected_row_idx = view_event.selection.rows[0]
        if selected_row_idx < len(df):
            st.session_state[sel_title_key] = df.iloc[selected_row_idx]["Titre"]

    # ── Édition rapide (statut, montant, étoile, suppression) ─────────────────
    with st.expander("✏️ Modifier statut / montant / étoile / supprimer"):
        _all = st.session_state.get(sel_all_key, False)
        _, col_selall = st.columns([8, 1])
        with col_selall:
            if st.button("☑️ Tout" if not _all else "☐ Aucun", key=f"btn_{sel_all_key}"):
                st.session_state[sel_all_key] = not _all
                st.session_state.pop(editor_key, None)
                st.rerun()

        df_edit = df.copy()
        df_edit.insert(0, "🗑️", st.session_state.get(sel_all_key, False))

        edited = st.data_editor(
            df_edit,
            column_config={
                "🗑️": st.column_config.CheckboxColumn("🗑️", width="small"),
                "⭐": st.column_config.CheckboxColumn("⭐", width="small", help="Sauvegarder cet article"),
                "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
                "Secteur": st.column_config.TextColumn("Secteur", disabled=True, width="small"),
                "Go/No-Go": st.column_config.TextColumn("Décision", width="small", disabled=True),
                "Titre": st.column_config.TextColumn("Titre du Marché", width="large", disabled=True),
                "Source": st.column_config.LinkColumn("Source", width="small"),
                "Territoire": st.column_config.TextColumn("Territoire", width="medium", disabled=True),
                "Domaine": st.column_config.TextColumn("Domaine", width="medium", disabled=True),
                "Score": st.column_config.NumberColumn("Score DEF", min_value=0, max_value=100, width="small", disabled=True),
                "Date Limite": st.column_config.TextColumn("Date Limite", width="small", disabled=True),
                "Publication": st.column_config.TextColumn("Publication", width="small", disabled=True),
                "Statut": st.column_config.SelectboxColumn("Statut", options=status_options, width="medium"),
                "Type": st.column_config.TextColumn("Type", width="small", disabled=True),
                "Maint.": st.column_config.TextColumn("Maint.", width="small", disabled=True),
                "Concurrents": st.column_config.TextColumn("Concurrents", width="medium", disabled=True),
                "Montant (€)": st.column_config.NumberColumn("Montant (€)", min_value=0, step=1000, format="%d €", width="small"),
            },
            column_order=["🗑️", "⭐", "Go/No-Go", "Titre", "Source", "Territoire", "Domaine", "Score", "Montant (€)", "Date Limite", "Publication", "Statut", "Type", "Maint.", "Concurrents", "ID"],
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key=editor_key,
        )

        to_delete = edited[edited["🗑️"] == True]["ID"].tolist()
        if to_delete:
            if st.button(f"🗑️ Supprimer {len(to_delete)} élément(s) sélectionné(s)", key=del_btn_key, type="secondary"):
                for tid in to_delete:
                    delete_tender(tid)
                st.session_state.pop(sel_all_key, None)
                st.cache_data.clear()
                st.rerun()

        editor_state = st.session_state.get(editor_key, {})
        for row_idx, changes in editor_state.get("edited_rows", {}).items():
            if "Statut" in changes:
                save_status(df_edit.iloc[row_idx]["ID"], changes["Statut"])
                st.cache_data.clear()
                st.rerun()
            if "Montant (€)" in changes:
                save_amount(df_edit.iloc[row_idx]["ID"], changes["Montant (€)"])
                st.cache_data.clear()
                st.rerun()
            if "⭐" in changes:
                toggle_saved(df_edit.iloc[row_idx]["ID"], changes["⭐"])
                st.cache_data.clear()
                st.rerun()

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


# ── Widget Urgences ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load_urgences_cached() -> list[dict]:
    from database import load_urgences
    db = SessionLocal()
    try:
        return load_urgences(db)
    finally:
        db.close()


def _render_urgences():
    urgences = _load_urgences_cached()
    if not urgences:
        return
    st.markdown("#### ⏰ Marchés GO — délais imminents")
    cols = st.columns(min(len(urgences), 4))
    for col, u in zip(cols, urgences[:4]):
        j = u["jours"]
        if j < 7:
            bg, border, badge = "#fef2f2", "#fecaca", f"🔴 {j}j restants"
        elif j < 15:
            bg, border, badge = "#fffbeb", "#fde68a", f"🟡 {j}j restants"
        else:
            bg, border, badge = "#f0fdf4", "#bbf7d0", f"🟢 {j}j restants"
        title_short = _html.escape(u["title"][:55]) + ("…" if len(u["title"]) > 55 else "")
        col.markdown(
            f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
            f'padding:10px;font-size:0.82rem"><strong>{title_short}</strong><br>'
            f'{badge} · Score : {u["score"]}</div>',
            unsafe_allow_html=True,
        )
    if len(urgences) > 4:
        st.caption(f"… et {len(urgences) - 4} autre(s) marché(s) GO avec deadline dans les 30 jours.")
    st.markdown("---")


_render_urgences()


# ── Recherche ─────────────────────────────────────────────────────────────────

search_query = st.text_input(
    "🔍 Rechercher un marché",
    placeholder="Mot-clé dans le titre ou la description…",
    key="search_query_main",
)

# ── Filtre post-collecte par source ──────────────────────────────────────────
_collection_src_ids = st.session_state.get("collection_source_ids", {})
_excluded_new_ids: set = set()
if _collection_src_ids:
    for _src, _ids in _collection_src_ids.items():
        if not st.session_state.get(f"src_filter_{_src}", True):
            _excluded_new_ids.update(_ids)
if _excluded_new_ids:
    st.caption(f"🔍 {len(_excluded_new_ids)} offre(s) masquée(s) par le filtre source (sidebar)")

# ── Tableau Marchés Publics ───────────────────────────────────────────────────

rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_pub = [r for r in rows_pub if (
        _sq in r["Titre"].lower()
        or _sq in r["Source"].lower()
        or _sq in r["Territoire"].lower()
        or _sq in r["Domaine"].lower()
        or _sq in r["_desc"]
    )]
def _is_urgent(r: dict) -> bool:
    dl = r.get("_deadline_dt")
    if dl is None:
        return False
    try:
        d = dl.date() if hasattr(dl, "date") else dl
        return (d - datetime.now().date()).days <= 14
    except Exception:
        return False

if urgent_only:
    rows_pub = [r for r in rows_pub if _is_urgent(r)]
if terr_actifs:
    rows_pub = [r for r in rows_pub if any(terr in r["Territoire"] for terr in terr_actifs)]
if selected_domaines:
    rows_pub = [r for r in rows_pub if any(d in r["Domaine"] for d in selected_domaines)]
if selected_decisions:
    rows_pub = [r for r in rows_pub if r["Go/No-Go"] in selected_decisions]
if selected_tags:
    rows_pub = [r for r in rows_pub if any(tg in (r["_tags"] or []) for tg in selected_tags)]
rows_pub = _sort_rows(rows_pub, sort_by)
if _excluded_new_ids:
    rows_pub = [r for r in rows_pub if r["ID"] not in _excluded_new_ids]

_render_editor_section(
    rows=rows_pub,
    section_title=f"📋 Marchés Publics — {len(rows_pub)} résultats",
    section_subtitle="Modifiez le statut, le montant ou l'étoile directement dans le tableau",
    fiche_title="📋 Fiche commerciale — Marché Public",
    fiche_label="Sélectionner un marché public",
    editor_key="pub_editor",
    sel_all_key="_sel_all_pub",
    sel_title_key="_sel_title_pub",
    del_btn_key="del_pub",
    sel_box_key="sel_pub",
)

# ── Tableau Signaux Privés ────────────────────────────────────────────────────

rows_priv = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Privé", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_priv = [r for r in rows_priv if (
        _sq in r["Titre"].lower()
        or _sq in r["Source"].lower()
        or _sq in r["Territoire"].lower()
        or _sq in r["Domaine"].lower()
        or _sq in r["_desc"]
    )]
if urgent_only:
    rows_priv = [r for r in rows_priv if _is_urgent(r)]
if terr_actifs:
    rows_priv = [r for r in rows_priv if any(terr in r["Territoire"] for terr in terr_actifs)]
if selected_domaines:
    rows_priv = [r for r in rows_priv if any(d in r["Domaine"] for d in selected_domaines)]
if selected_decisions:
    rows_priv = [r for r in rows_priv if r["Go/No-Go"] in selected_decisions]
if selected_tags:
    rows_priv = [r for r in rows_priv if any(tg in (r["_tags"] or []) for tg in selected_tags)]
rows_priv = _sort_rows(rows_priv, sort_by)
if _excluded_new_ids:
    rows_priv = [r for r in rows_priv if r["ID"] not in _excluded_new_ids]

_render_editor_section(
    rows=rows_priv,
    section_title=f"🏗️ Signaux Privés — {len(rows_priv)} résultats",
    section_subtitle="Permis de construire, articles presse, institutions, banques de développement",
    fiche_title="🏗️ Fiche commerciale — Signal Privé",
    fiche_label="Sélectionner un signal privé",
    editor_key="priv_editor",
    sel_all_key="_sel_all_priv",
    sel_title_key="_sel_title_priv",
    del_btn_key="del_priv",
    sel_box_key="sel_priv",
)

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
            st.caption(f"{_ca:,.0f} €".replace(",", " "))
        for _it in _items[:3]:
            _short = _it["title"][:55]
            if st.button(_short, key=f"pipe_{_pipe_status}_{_it['id']}", use_container_width=True):
                st.session_state["_sel_title_pub"] = _it["title"]
        if len(_items) > 3:
            st.caption(f"+ {len(_items) - 3} autres")

st.markdown("---")

# ── saisie manuelle ───────────────────────────────────────────────────────────

with st.expander("➕ Ajouter une opportunité manuellement (AWS, achatpublic.com, profil acheteur…)"):
    with st.form("form_manual", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            m_title = st.text_input("Titre du marché *", placeholder="Ex : Maintenance SSI CHU Réunion")
            m_source_name = st.selectbox(
                "Plateforme source",
                ["achatpublic.com", "AWS (Achat Web Sécurisé)", "Marchés Sécurisés",
                 "Profil acheteur direct", "LinkedIn / Contact", "Autre"],
            )
            m_url = st.text_input("Lien URL", placeholder="https://...")
        with col_b:
            m_deadline = st.date_input("Date limite de réponse", value=None)
            m_pub_date = st.date_input("Date de publication", value=None)
            m_dept = st.selectbox("Territoire", [
                "974 — La Réunion", "976 — Mayotte",
                "Madagascar", "Maurice", "Comores", "Autre / Non précisé",
            ])

        m_desc = st.text_area("Description / Objet", placeholder="Coller ici le descriptif du marché…", height=80)

        submitted = st.form_submit_button("Enregistrer l'opportunité", use_container_width=True, type="primary")

        if submitted:
            if not m_title.strip():
                st.error("Le titre est obligatoire.")
            else:
                tid = "MANUAL-" + _hl.md5(f"{m_title}{m_url}{m_deadline}".encode()).hexdigest()[:10]
                db_m = new_db()
                try:
                    if db_m.query(Tender).filter(Tender.id == tid).first():
                        st.warning("Cette opportunité existe déjà.")
                    else:
                        _url = m_url.strip()
                        analyse = analyze_tender(
                            f"{m_title.strip()} {m_desc.strip()}",
                            source_url=_url if _url.startswith("http") else None,
                        )
                        db_m.add(Tender(
                            id=tid,
                            title=m_title.strip(),
                            description=m_desc.strip(),
                            source=m_url.strip() or m_source_name,
                            publication_date=datetime.combine(m_pub_date, datetime.min.time()) if m_pub_date else None,
                            deadline=datetime.combine(m_deadline, datetime.min.time()) if m_deadline else None,
                            status="À qualifier",
                            relevance_score=analyse.get("score_pertinence", 0),
                            is_maintenance=analyse.get("type_marche", "").lower() == "maintenance",
                            llm_analysis=analyse,
                        ))
                        db_m.commit()
                        st.cache_data.clear()
                        st.success(f"✅ « {m_title} » ajouté — Score DEF : {analyse.get('score_pertinence', 0)}/100.")
                finally:
                    db_m.close()

st.markdown("---")

# ── Gestion des sources ──────────────────────────────────────────────────────

with st.expander("⚙️ Gérer les sources de veille"):
    db_gs = new_db()
    try:
        all_gs = list_sources(db_gs)
    finally:
        db_gs.close()

    st.markdown("#### Sources configurées")

    for s in all_gs:
        col_name, col_cat, col_type, col_toggle, col_del = st.columns([3, 1, 1, 1, 1])
        with col_name:
            _valid_badge = "✅" if s.is_validated else "⬜"
            st.markdown(f"{_valid_badge} **{s.name}**")
        with col_cat:
            st.caption(s.category)
        with col_type:
            if s.scraper_module:
                st.markdown("🤖 Auto")
            else:
                st.markdown("👤 Manuel")
        with col_toggle:
            label_toggle = "✅" if s.enabled else "❌"
            if st.button(label_toggle, key=f"toggle_{s.id}", help="Activer/Désactiver"):
                db_t = new_db()
                try:
                    toggle_enabled(db_t, s.id)
                finally:
                    db_t.close()
                st.cache_data.clear()
                st.rerun()
        with col_del:
            if s.scraper_module is None:  # uniquement les sources manuelles
                if st.button("🗑️", key=f"del_{s.id}", help="Supprimer cette source"):
                    db_d = new_db()
                    try:
                        remove_source(db_d, s.id)
                    finally:
                        db_d.close()
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.markdown("—")  # sources auto protégées

    st.markdown("---")
    st.markdown("#### Ajouter une source de veille")

    with st.form("form_add_source", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            new_name = st.text_input("Nom de la source *", placeholder="Ex : SEAO Québec")
            new_url = st.text_input("URL *", placeholder="https://...")
        with col_b:
            new_cat = st.selectbox("Catégorie", ["Public", "Privé", "International"])
            new_notes = st.text_input("Notes (optionnel)", placeholder="Ex : Appels d'offres Québec")

        submitted_src = st.form_submit_button("➕ Ajouter la source", use_container_width=True)
        if submitted_src:
            if not new_name.strip() or not new_url.strip():
                st.error("Le nom et l'URL sont obligatoires.")
            elif not new_url.strip().startswith(("http://", "https://")):
                st.error("L'URL doit commencer par http:// ou https://")
            else:
                db_a = new_db()
                try:
                    add_source(db_a, name=new_name.strip(), url=new_url.strip(),
                               category=new_cat, notes=new_notes.strip() or None)
                finally:
                    db_a.close()
                st.success(f"✅ « {new_name} » ajoutée comme source {new_cat}.")
                st.cache_data.clear()
                st.rerun()

st.markdown("---")

# ── Mes sauvegardes ───────────────────────────────────────────────────────────

st.markdown(_section_html("⭐ Mes sauvegardes", "Articles et marchés mis de côté pour référence"), unsafe_allow_html=True)

saved_rows = load_saved_tenders()

if not saved_rows:
    st.info("Aucune sauvegarde. Cochez la colonne ⭐ dans les tableaux ci-dessus pour garder un article de côté.")
else:
    st.caption(f"{len(saved_rows)} élément(s) sauvegardé(s)")
    df_saved = pd.DataFrame(saved_rows)
    df_saved.insert(0, "Retirer", False)

    edited_saved = st.data_editor(
        df_saved,
        column_config={
            "Retirer": st.column_config.CheckboxColumn("🗑️ Retirer", width="small", help="Décocher pour retirer des sauvegardes"),
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Titre": st.column_config.TextColumn("Titre", width="large", disabled=True),
            "Source": st.column_config.LinkColumn("Source", width="small"),
            "Territoire": st.column_config.TextColumn("Territoire", width="medium", disabled=True),
            "Domaine": st.column_config.TextColumn("Domaine", width="medium", disabled=True),
            "Statut": st.column_config.TextColumn("Statut", width="small", disabled=True),
            "Type": st.column_config.TextColumn("Type", width="small", disabled=True),
            "Publication": st.column_config.TextColumn("Publication", width="small", disabled=True),
            "Secteur": st.column_config.TextColumn("Secteur", width="small", disabled=True),
        },
        column_order=["Retirer", "Titre", "Source", "Territoire", "Domaine", "Statut", "Type", "Publication", "Secteur", "ID"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="saved_editor",
    )

    to_unsave = edited_saved[edited_saved["Retirer"] == True]["ID"].tolist()
    if to_unsave:
        if st.button(f"Retirer {len(to_unsave)} élément(s) des sauvegardes", type="secondary"):
            for tid in to_unsave:
                toggle_saved(tid, False)
            st.cache_data.clear()
            st.rerun()

st.markdown("---")
st.caption("DEF Océan Indien © 2025 · Outil de Veille Commerciale Interne")
