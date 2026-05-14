from datetime import datetime, timedelta
import html as _html

import pandas as pd
import streamlit as st

from database import SessionLocal, init_db
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
    if score >= 65:
        return "🟢 GO"
    elif score >= 35:
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


def _render_strategic_analysis(t, a: dict, domaine: str, territoire: str, score: int) -> None:
    """Analyse stratégique structurée d'un signal/marché."""
    import re
    from datetime import date as _date

    type_m = a.get("type_marche") or getattr(t, "type_opportunite", None) or "Inconnu"
    territoire_ia = a.get("territoire_ia") or territoire
    domaines = a.get("domaines_concernes", [])
    justif = a.get("justification_score", "")
    concurrents = a.get("marques_concurrentes_citees", [])
    desc_text = f" {(t.description or '').lower()} "
    title_l = (t.title or "").lower()

    # ── Sous-scores (estimation affichage) ────────────────────────────────────
    if "🔥 SSI" in domaine:          sm = 45
    elif "💨 CMSI" in domaine:       sm = 40
    elif "📷 Vidéo" in domaine:      sm = 40
    elif "⚡ Courants" in domaine:   sm = 30
    else:                              sm = 5

    if "La Réunion" in territoire or "Mayotte" in territoire:   sg = 30
    elif "Madagascar" in territoire or "Maurice" in territoire:  sg = 22
    elif "Comores" in territoire:                                 sg = 18
    elif "France" in territoire:                                  sg = 10
    else:                                                         sg = 0

    sk = 15 if any(kw in title_l for kw in [
        "ssi", "cmsi", "détection", "alarme incendie", "désenfumage",
        "vidéosurveillance", "cctv", "courants faibles",
    ]) else 0
    smaint = 10 if t.is_maintenance else 0

    # ── Délai restant ─────────────────────────────────────────────────────────
    jours_restants = None
    if t.deadline:
        try:
            today = _date.today()
            dl = t.deadline.date() if hasattr(t.deadline, "date") else t.deadline
            jours_restants = (dl - today).days
        except Exception:
            pass

    # ── Plan d'action ─────────────────────────────────────────────────────────
    if score >= 65:
        if jours_restants is not None and jours_restants < 0:
            label_action = "⚠️ Date limite dépassée"
            steps = [
                "Vérifier si une prorogation ou relance est possible",
                "Archiver dans le suivi commercial CRM",
            ]
        elif jours_restants is not None and jours_restants <= 7:
            label_action = "🚨 Action immédiate — délai critique"
            steps = [
                "Désigner un chargé d'affaires **aujourd'hui**",
                "Évaluer la faisabilité d'une réponse express",
                "Rassembler références SSI/CMSI et documents de candidature en urgence",
                "Contacter le pouvoir adjudicateur pour confirmer la date limite",
            ]
        elif jours_restants is not None and jours_restants <= 30:
            label_action = "🟢 Traiter en priorité"
            steps = [
                "Affecter un chargé d'affaires et ouvrir une affaire dans le CRM",
                "Télécharger le DCE complet et analyser le CCTP",
                "Préparer le mémoire technique + chiffrage détaillé",
                "Planifier la visite de site si requise par le cahier des charges",
            ]
        else:
            label_action = "🟢 Planifier la réponse"
            steps = [
                "Inscrire au planning commercial et assigner un responsable d'offre",
                "Télécharger le DCE et surveiller les éventuels amendements",
                "Préparer les documents de candidature (références, Kbis, qualifications Qualifelec/APSAD)",
                "Anticiper la visite de site et le chiffrage matériels/sous-traitance",
            ]
    elif score >= 35:
        label_action = "🟡 À évaluer — décision requise"
        steps = [
            "Lire le CCTP complet : vérifier qu'il y a bien une composante SSI/CMSI/Vidéo ou courants faibles exploitable par DEF OI",
            "Vérifier si DEF OI a des références sur ce type de prestation **et** sur ce territoire (critères de sélection souvent liés)",
            "Estimer la concurrence : chercher d'éventuels prix publics antérieurs et identifier les opérateurs déjà positionnés",
            "Si l'adéquation est confirmée, décision GO/NO-GO à remonter à la direction commerciale sous 48 h",
        ]
    else:
        label_action = "🔴 Hors périmètre DEF OI"
        steps = [
            "Archiver — pas de composante SSI/CMSI/Vidéo/courants faibles identifiée dans le périmètre DEF OI",
            "Ne pas mobiliser de ressources commerciales ; réévaluer uniquement si une nouvelle version du DCE précise une composante électronique de sécurité",
        ]

    st.markdown("#### 📊 Analyse stratégique")

    # ── Bloc 1 : Recommandation + Calendrier ──────────────────────────────────
    col_reco, col_cal = st.columns([3, 2])

    with col_reco:
        st.markdown(f"**{label_action}**")
        for step in steps:
            st.markdown(f"- {step}")
        if justif:
            st.info(f"💡 {justif}")

    with col_cal:
        st.markdown("**Calendrier**")
        if jours_restants is not None:
            if jours_restants < 0:
                st.error(f"Date limite dépassée ({abs(jours_restants)} j)")
            elif jours_restants <= 7:
                st.error(f"⚡ {jours_restants} jour(s) restant(s)")
            elif jours_restants <= 21:
                st.warning(f"⏳ {jours_restants} jour(s) restant(s)")
            else:
                st.success(f"🗓️ {jours_restants} jour(s) restant(s)")
            if t.deadline and hasattr(t.deadline, "strftime"):
                st.caption(f"Date limite : {t.deadline.strftime('%d/%m/%Y')}")
        else:
            st.caption("Date limite non renseignée")
        if t.publication_date and hasattr(t.publication_date, "strftime"):
            st.caption(f"Publié le : {t.publication_date.strftime('%d/%m/%Y')}")
        if t.amount:
            st.caption(f"Montant estimé : {t.amount:,.0f} €".replace(",", " "))

    # ── Bloc 2 : Score détaillé + Atouts / Risques ────────────────────────────
    col_score, col_forces = st.columns(2)

    with col_score:
        st.markdown("**Décomposition du score DEF**")
        for nom, val, maxval in [
            ("Pertinence métier", sm, 45),
            ("Proximité géographique", sg, 30),
            ("Mots-clés dans le titre", sk, 15),
            ("Maintenance / Récurrence", smaint, 10),
        ]:
            pct = val / maxval if maxval > 0 else 0
            st.markdown(f"**{nom}** — `{val}/{maxval}`")
            st.progress(pct)

    with col_forces:
        st.markdown("**Pourquoi c'est pertinent pour DEF OI**")
        atouts = []
        if sm >= 40:
            atouts.append("✅ **Cœur de métier** — SSI/CMSI/Vidéo : DEF OI dispose de l'expertise technique, des certifications (Qualifelec, APSAD) et des références pour répondre")
        elif sm >= 30:
            atouts.append("✅ **Périmètre DEF OI** — Courants faibles : prestation complémentaire au SSI, souvent regroupée dans les mêmes marchés")
        if sg == 30:
            atouts.append("✅ **Présence locale 974/976** — DEF OI connaît les donneurs d'ordre, les sites et les exigences locales ; avantage concurrentiel fort sur les entreprises métropolitaines")
        elif sg >= 18:
            atouts.append("✅ **Zone Océan Indien** — axe de développement stratégique de DEF OI ; peu de concurrents locaux qualifiés SSI/CMSI sur ces marchés")
        if smaint == 10:
            atouts.append("✅ **Maintenance** — CA récurrent et prévisible, taux de marge élevé, et levier pour consolider la relation client sur le long terme")
        if sk == 15:
            atouts.append("✅ **Signal direct** — les mots-clés métier SSI/CMSI/Vidéo apparaissent dans le titre : opportunité clairement identifiable sans ambiguïté")
        if not atouts:
            atouts.append("ℹ️ **Pertinence limitée** — aucun marqueur fort du cœur de métier DEF OI (SSI/CMSI/Vidéo) ni du territoire prioritaire (974/976) ; étudier le CCTP complet avant d'engager des ressources")
        for item in atouts:
            st.markdown(item)

        risques = []
        if concurrents:
            risques.append(f"⚠️ Concurrents nommés dans le DCE : {', '.join(concurrents[:4])}")
        if a.get("risques_penalites"):
            risques.append(f"⚠️ {a['risques_penalites']}")
        if jours_restants is not None and 0 <= jours_restants <= 14:
            risques.append("⚠️ Délai très court — risque de réponse technique insuffisante")
        if risques:
            st.markdown("**Risques identifiés**")
            for item in risques:
                st.markdown(item)

    # ── Bloc 3 : Mots-clés description + Contexte ────────────────────────────
    col_kw, col_ctx = st.columns(2)

    with col_kw:
        st.markdown("**Mots-clés métier détectés dans la description**")

        def _find_kws(kw_list: list, label: str) -> bool:
            hits = []
            for kw in kw_list:
                if kw.startswith(r"\b"):
                    if re.search(kw, desc_text):
                        hits.append(re.sub(r"\\b", "", kw).strip())
                elif kw in desc_text:
                    hits.append(kw.strip())
            if hits:
                chips = " · ".join(f"`{h}`" for h in hits[:6])
                st.markdown(f"**{label} :** {chips}")
            return bool(hits)

        # Scan titre + description ensemble
        full_text = f" {((t.title or '') + ' ' + (t.description or '')).lower()} "

        def _find_kws_full(kw_list: list, label: str) -> bool:
            hits = []
            for kw in kw_list:
                if kw.startswith(r"\b"):
                    if re.search(kw, full_text):
                        hits.append(re.sub(r"\\b", "", kw).strip())
                elif kw in full_text:
                    hits.append(kw.strip())
            hits = list(dict.fromkeys(hits))  # dédupliquer
            if hits:
                chips = " · ".join(f"`{h}`" for h in hits[:8])
                st.markdown(f"**{label} :** {chips}")
            return bool(hits)

        any_hit = any([
            _find_kws_full(_KW_SSI, "🔥 SSI / Incendie"),
            _find_kws_full(_KW_CMSI, "💨 CMSI / Désenfumage"),
            _find_kws_full(_KW_VIDEO, "📷 Vidéosurveillance"),
            _find_kws_full(_KW_COURANTS_FAIBLES, "⚡ Courants faibles"),
            _find_kws_full(_KW_MAINTENANCE, "🔧 Maintenance"),
            _find_kws_full(_KW_ERP, "🏢 Bâtiment ERP"),
            _find_kws_full(_KW_PENALITES, "⚠️ Pénalités / Risques"),
        ])
        if not any_hit:
            st.caption("Aucun mot-clé métier détecté dans le titre ni la description.")

        # Compteurs bruts si disponibles (analyse locale)
        nb_ssi_raw = a.get("_nb_ssi", 0)
        nb_cmsi_raw = a.get("_nb_cmsi", 0)
        nb_vid_raw = a.get("_nb_vid", 0)
        nb_cf_raw = a.get("_nb_cf", 0)
        nb_erp_raw = a.get("_nb_erp", 0)
        nb_excl_raw = a.get("_nb_excl", 0)
        if any([nb_ssi_raw, nb_cmsi_raw, nb_vid_raw, nb_cf_raw, nb_erp_raw]):
            st.caption(
                f"Indices détectés — SSI: {nb_ssi_raw} · CMSI: {nb_cmsi_raw} · "
                f"Vidéo: {nb_vid_raw} · CF: {nb_cf_raw} · ERP: {nb_erp_raw}"
                + (f" · ⚠️ Exclusion: {nb_excl_raw}" if nb_excl_raw else "")
            )

    with col_ctx:
        st.markdown("**Contexte & Informations**")
        st.markdown(f"🏷️ **Type :** {type_m}")
        st.markdown(f"🌍 **Territoire (IA) :** {territoire_ia}")
        if domaines:
            st.markdown(f"🔧 **Domaines :** {', '.join(domaines)}")
        st.markdown(f"🏢 **Secteur :** {getattr(t, 'secteur', None) or 'Public'}")
        if concurrents:
            st.markdown(f"🏭 **Concurrents :** {', '.join(concurrents)}")
        source_a = a.get("_source", "local")
        st.caption(
            "🤖 Score Claude (70%) + règles métier (30%)"
            if source_a in ("claude", "gemini")
            else "🔍 Score règles métier DEF (Claude indisponible)"
        )

    # ── Description brute — toujours affichée ─────────────────────────────────
    with st.expander("📄 Description brute du marché"):
        if t.description and t.description.strip():
            st.write(t.description)
        else:
            st.caption("Aucune description textuelle disponible dans la base pour ce marché.")
            st.markdown(f"**Titre complet :** {t.title or '—'}")
            if getattr(t, "source", None):
                st.markdown(f"**Source :** {t.source}")
            st.info("Consulter directement la plateforme source pour accéder au cahier des charges complet.")


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
        from sqlalchemy import or_
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


def save_status(tender_id: str, new_status: str) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.status = new_status
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


# ── sidebar ───────────────────────────────────────────────────────────────────

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

        if score >= 65:
            color_class = ""
            badge = f"🟢 GO — Score {score}/100"
        elif score >= 35:
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
    search_query = st.text_input("🔍 Rechercher", placeholder="Titre, source…", key="search_query")

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
    selected_status = st.selectbox(
        "Filtrer par statut",
        ["Tous", "À qualifier", "En cours", "Soumis", "Gagné", "Perdu"],
    )
    selected_decisions = st.multiselect(
        "Filtrer par décision",
        options=["🟢 GO", "🟡 Étudier", "🔴 Passer"],
        placeholder="Toutes les décisions",
    )
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
        cat_sources = [s for s in all_sources if s.category == cat and s.enabled]
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

    st.markdown("")
    if st.button("⚡ Collecter la sélection", use_container_width=True, type="primary",
                 disabled=len(selected_source_ids) == 0):
        _collect_selected_sources(selected_source_ids)

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
    col_nav1, col_nav2 = st.columns(2)
    with col_nav1:
        st.page_link("pages/parametres.py", label="⚙️ Paramètres", use_container_width=True)
    with col_nav2:
        st.page_link("pages/guide.py", label="📖 Guide", use_container_width=True)


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
    db_exp = new_db()
    try:
        excel_bytes = generate_executive_report(db_exp)
    finally:
        db_exp.close()

    st.download_button(
        label="📊  Télécharger le Rapport Direction (Excel)",
        data=excel_bytes,
        file_name=f"Rapport_Direction_DEF_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        type="primary",
    )

st.markdown("---")

# ── Nouveaux marchés post-collecte ────────────────────────────────────────────
_render_new_tenders_section()

# ── KPI metrics ───────────────────────────────────────────────────────────────

db_kpi = new_db()
try:
    from sqlalchemy import or_ as _or
    _pub = _or(Tender.secteur == "Public", Tender.secteur == None)
    total = db_kpi.query(Tender).filter(_pub).count()
    a_qualifier = db_kpi.query(Tender).filter(_pub, Tender.status == "À qualifier").count()
    en_cours = db_kpi.query(Tender).filter(_pub, Tender.status == "En cours").count()
    gagnes = db_kpi.query(Tender).filter(_pub, Tender.status == "Gagné").count()
    soumis = db_kpi.query(Tender).filter(_pub, Tender.status == "Soumis").count()
finally:
    db_kpi.close()

st.markdown(_kpi_row([
    ("Total marchés", total),
    ("À qualifier", a_qualifier),
    ("En cours", en_cours),
    ("Soumis", soumis),
    ("Gagnés 🏆", gagnes),
], colors=["", "orange", "blue", "purple", "green"]), unsafe_allow_html=True)

# KPI CA pipeline
db_ca = new_db()
try:
    def _sum_amount(statuts):
        from sqlalchemy import func, or_
        _pub = or_(Tender.secteur == "Public", Tender.secteur == None)
        res = db_ca.query(func.sum(Tender.amount)).filter(
            _pub, Tender.status.in_(statuts), Tender.amount != None
        ).scalar()
        return res or 0

    ca_en_cours = _sum_amount(["En cours"])
    ca_soumis = _sum_amount(["Soumis"])
    ca_gagne = _sum_amount(["Gagné"])
    ca_pipeline = ca_en_cours + ca_soumis
finally:
    db_ca.close()

if ca_pipeline > 0 or ca_gagne > 0:
    st.markdown('<p class="ca-label">CA Pipeline — montants renseignés</p>', unsafe_allow_html=True)
    st.markdown(_kpi_row([
        ("CA En cours", f"{ca_en_cours:,.0f} €".replace(",", " ")),
        ("CA Soumis", f"{ca_soumis:,.0f} €".replace(",", " ")),
        ("CA Gagné 🏆", f"{ca_gagne:,.0f} €".replace(",", " ")),
        ("CA Total pipeline", f"{ca_pipeline:,.0f} €".replace(",", " ")),
    ], colors=["blue", "orange", "green", ""]), unsafe_allow_html=True)

st.markdown("---")

# ── signaux privés KPI ────────────────────────────────────────────────────────

db_priv = new_db()
try:
    nb_permis = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.type_opportunite == "Permis Construire"
    ).count()
    nb_presse = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.type_opportunite == "Presse"
    ).count()
    nb_instit = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.type_opportunite == "Institution"
    ).count()
    nb_devbanks = db_priv.query(Tender).filter(
        Tender.type_opportunite == "Banque Dev."
    ).count()
    nb_qualif_priv = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.status == "À qualifier"
    ).count()
finally:
    db_priv.close()

st.markdown('<p class="ca-label">Signaux privés</p>', unsafe_allow_html=True)
st.markdown(_kpi_row([
    ("Permis construire", nb_permis),
    ("Articles presse", nb_presse),
    ("Institutions", nb_instit),
    ("Banques Dev.", nb_devbanks),
    ("Privé — À qualifier", nb_qualif_priv),
], colors=["teal", "blue", "purple", "orange", ""]), unsafe_allow_html=True)

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
        decision = _gonogo(score)

        tag = a.get("tag_pertinence") or decision
        if score >= 65:
            st.success(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
        elif score >= 35:
            st.warning(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")
        else:
            st.error(f"**{tag}** — Score {score}/100 · {domaine} · {territoire}")

        domaines = a.get("domaines_concernes", [])
        if domaines:
            chips = " · ".join([f"`{d}`" for d in domaines])
            st.markdown(f"**Domaines :** {chips}")

        if a.get("justification_score"):
            st.caption(f"💡 {a['justification_score']}")

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Type", a.get("type_marche") or t.type_opportunite or "—")
        m2.metric("Score DEF", f"{score} / 100")
        m3.metric("Concurrents", len(a.get("marques_concurrentes_citees", [])))
        m4.metric("Maintenance", "Oui" if t.is_maintenance else "Non")

        if a.get("marques_concurrentes_citees"):
            st.write("**Marques concurrentes citées :**", ", ".join(a["marques_concurrentes_citees"]))
        if a.get("risques_penalites"):
            st.warning(f"⚠️ Risques / Pénalités : {a['risques_penalites']}")

        source_a = a.get("_source", "local")
        if source_a in ("claude", "gemini"):
            st.caption("🤖 Analyse Claude (score combiné 70 % IA + 30 % règles métier)")
        else:
            st.caption("🔍 Analyse locale (règles métier DEF — Claude indisponible)")

        _render_strategic_analysis(t, a, domaine, territoire, score)
        st.markdown("---")
        if st.button("🤖 Réanalyser avec Claude", key=f"reanalyze_{key_suffix}_{tender_id}",
                     help="Relance l'analyse Claude pour affiner le score et la justification"):
            with st.spinner("Analyse Claude en cours…"):
                run_analysis(tender_id)
            st.cache_data.clear()
            st.rerun()
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

    df = pd.DataFrame(rows)

    # ── Tableau principal (clic pour sélectionner) ────────────────────────────
    st.caption("👆 Cliquez sur une ligne pour la sélectionner et afficher son analyse ci-dessous")
    view_event = st.dataframe(
        df.drop(columns=["ID", "Secteur"], errors="ignore"),
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

    title_to_id = {r["Titre"]: r["ID"] for r in rows}
    _titles = list(title_to_id.keys())
    _default = 0
    _sel_t = st.session_state.get(sel_title_key)
    if _sel_t and _sel_t in _titles:
        _default = _titles.index(_sel_t)
    chosen_title = st.selectbox(fiche_label, _titles, index=_default, key=sel_box_key)

    if chosen_title:
        _render_fiche(title_to_id[chosen_title], editor_key)

    st.markdown("---")


# ── Tableau Marchés Publics ───────────────────────────────────────────────────

rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_pub = [r for r in rows_pub if _sq in r["Titre"].lower() or _sq in r["Source"].lower()]
if terr_actifs:
    rows_pub = [r for r in rows_pub if any(terr in r["Territoire"] for terr in terr_actifs)]
if selected_domaines:
    rows_pub = [r for r in rows_pub if any(d in r["Domaine"] for d in selected_domaines)]
if selected_decisions:
    rows_pub = [r for r in rows_pub if r["Go/No-Go"] in selected_decisions]

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
    rows_priv = [r for r in rows_priv if _sq in r["Titre"].lower() or _sq in r["Source"].lower()]
if terr_actifs:
    rows_priv = [r for r in rows_priv if any(terr in r["Territoire"] for terr in terr_actifs)]
if selected_domaines:
    rows_priv = [r for r in rows_priv if any(d in r["Domaine"] for d in selected_domaines)]
if selected_decisions:
    rows_priv = [r for r in rows_priv if r["Go/No-Go"] in selected_decisions]

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
                import hashlib as _hl
                tid = "MANUAL-" + _hl.md5(f"{m_title}{m_url}{m_deadline}".encode()).hexdigest()[:10]
                db_m = new_db()
                try:
                    if db_m.query(Tender).filter(Tender.id == tid).first():
                        st.warning("Cette opportunité existe déjà.")
                    else:
                        from models import Tender as T
                        _url = m_url.strip()
                        analyse = analyze_tender(
                            f"{m_title.strip()} {m_desc.strip()}",
                            source_url=_url if _url.startswith("http") else None,
                        )
                        db_m.add(T(
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
            st.markdown(f"**{s.name}**")
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
