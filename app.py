from datetime import datetime, timedelta, date as _date
import html as _html
import io as _io
import logging
import os
import re
import sys
import uuid as _uuid
import threading
from collections import Counter, defaultdict

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func as _func, or_

from database import SessionLocal, init_db, clean_obsolete_data
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
import health_check as _hc

# Configuration de la journalisation
def setup_logging():
    """Configure le système de journalisation avec un format standard."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

    # Configurer le logger pour capturer les exceptions non gérées
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        _log.critical("Exception non capturée", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

# Initialiser la journalisation
setup_logging()
_log = logging.getLogger(__name__)

TENDER_TAGS = [
    "Potentiel SSI implicite",
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
        "trois-bassins", "les avirons", "la possession", "l'île-en-bois",
        "saint-gilles", "l'hermitage", "la saline", "grand bois",
        "ile bourbon", "ile de la reunion",
        # Codes postaux Réunion
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
        "kani-kéli", "kani-keli", "mtsamboro", "m'tsangamouji", "ouangani",
        "sada", "tsingoni", "acoua", "petite-terre", "grande-terre",
        # Codes postaux Mayotte
        "97600", "97610", "97615", "97616", "97617", "97618", "97619",
        "97620", "97625", "97630", "97640", "97650", "97660", "97670",
        "97680",
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

@st.cache_resource
def _init_db_once():
    init_db()

_init_db_once()

# ── Archivage automatique au démarrage (une seule fois par session) ───────────
if "retention_done" not in st.session_state:
    _db_ret = SessionLocal()
    try:
        n = clean_obsolete_data(_db_ret, days=30)
        if n:
            st.toast(f"🗂️ {n} offre(s) archivée(s) automatiquement (> 30 jours)", icon="ℹ️")
    except Exception:
        _log.warning("clean_obsolete_data: échec au démarrage", exc_info=True)
    finally:
        _db_ret.close()
    st.session_state["retention_done"] = True

# ── Scheduler ré-validation hebdomadaire ──────────────────────────────────────

@st.cache_resource
def _start_background_services():
    """Démarre le scheduler et le catchup une seule fois par processus (pas par session)."""
    from source_registry import _run_weekly_ping as _rwp
    from datetime import datetime as _dts, timezone as _tz_bg

    def _maybe_run_catchup():
        """Exécute le catchup des sources validées qui n'ont pas été pingées depuis 8 jours."""
        from database import SessionLocal as _SL_c
        from source_registry import Source as _SrcC, _ping_source as _ps

        _db_c = None
        try:
            _db_c = _SL_c()
            _now_c = _dts.now(_tz_bg.utc).replace(tzinfo=None)

            # Récupère uniquement les sources validées
            stale_sources = _db_c.query(_SrcC).filter(_SrcC.is_validated == True).all()

            for source in stale_sources:
                try:
                    # Vérifie si le dernier ping date de plus de 8 jours ou n'a jamais été fait
                    if source.last_ping_at is None or (_now_c - source.last_ping_at.replace(tzinfo=None)).days >= 8:
                        _ps(_db_c, source)
                        _log.info(f"Catchup réussi pour la source: {source.name}")
                except Exception as e:
                    _log.error(f"Échec du catchup pour la source {source.name}: {str(e)}", exc_info=True)
                    continue

        except Exception as e:
            _log.error(f"Échec global du catchup: {str(e)}", exc_info=True)
        finally:
            if _db_c:
                _db_c.close()

    # Lance le catchup dans un thread séparé avec gestion d'erreurs
    catchup_thread = threading.Thread(target=_maybe_run_catchup, daemon=True)
    catchup_thread.start()

    try:
        # Initialisation du scheduler avec gestion d'erreurs
        _scheduler = _BgScheduler()

        # Configuration des jobs avec gestion d'erreurs spécifique
        try:
            _scheduler.add_job(
                _rwp,
                "interval",
                weeks=1,
                id="weekly_ping",
                max_instances=1,
                coalesce=True
            )
            _log.info("Job weekly_ping ajouté au scheduler")
        except Exception as e:
            _log.error(f"Échec de l'ajout du job weekly_ping: {str(e)}")
            raise

        # Job digest email quotidien (uniquement si SMTP configuré)
        _digest_hour = int(os.getenv("DIGEST_HOUR", "7"))
        if os.getenv("DIGEST_SMTP_HOST") and os.getenv("DIGEST_TO"):
            def _send_daily_digest():
                """Envoie le digest quotidien par email avec gestion d'erreurs complète."""
                try:
                    from email_digest import send_digest as _sd

                    # Validation des paramètres SMTP
                    required_params = [
                        "DIGEST_SMTP_HOST",
                        "DIGEST_SMTP_PORT",
                        "DIGEST_TO"
                    ]

                    missing_params = [param for param in required_params if not os.getenv(param)]
                    if missing_params:
                        _log.error(f"Paramètres SMTP manquants: {', '.join(missing_params)}")
                        return

                    _cfg = {
                        "host": os.getenv("DIGEST_SMTP_HOST"),
                        "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
                        "user": os.getenv("DIGEST_SMTP_USER"),
                        "password": os.getenv("DIGEST_SMTP_PASSWORD"),
                        "to": os.getenv("DIGEST_TO"),
                    }
                    _sd(_cfg)
                    _log.info("Digest quotidien envoyé avec succès")

                except TimeoutError:
                    _log.error("Timeout lors de l'envoi du digest email")
                except Exception as e:
                    _log.error(f"Échec de l'envoi du digest email: {str(e)}", exc_info=True)

            try:
                _scheduler.add_job(
                    _send_daily_digest,
                    "cron",
                    hour=_digest_hour,
                    minute=0,
                    id="daily_digest",
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=3600  # 1 heure de tolérance
                )
                _log.info(f"Job daily_digest ajouté au scheduler (à {_digest_hour}:00)")
            except Exception as e:
                _log.error(f"Échec de l'ajout du job daily_digest: {str(e)}")

        def _weekly_adaptive_scores():
            """Recalcule les scores adaptatifs hebdomadaires."""
            try:
                from score_adaptive import recompute_adaptive_scores as _r
                _log.info("Début du recalcul des scores adaptatifs")
                _r()
                _log.info("Recalcul des scores adaptatifs terminé")
            except Exception as e:
                _log.error(f"Échec du recalcul des scores adaptatifs: {str(e)}", exc_info=True)
                raise  # Re-lève l'exception pour que le scheduler puisse la gérer

        try:
            _scheduler.add_job(
                _weekly_adaptive_scores,
                "interval",
                weeks=1,
                id="weekly_adaptive_scores",
                max_instances=1,
                coalesce=True
            )
            _log.info("Job weekly_adaptive_scores ajouté au scheduler")
        except Exception as e:
            _log.error(f"Échec de l'ajout du job weekly_adaptive_scores: {str(e)}")

        # Configuration du scheduler pour une meilleure gestion des erreurs
        _scheduler.configure(
            job_defaults={
                'max_instances': 1,
                'coalesce': True
            }
        )

        # Démarrage du scheduler avec gestion d'erreurs
        _scheduler.start()
        _log.info("Scheduler démarré avec succès")

        return _scheduler

    except Exception as e:
        _log.error(f"Échec critique de l'initialisation du scheduler: {str(e)}", exc_info=True)
        # En cas d'échec critique, on tente de créer un scheduler minimal
        try:
            _fallback_scheduler = _BgScheduler()
            _fallback_scheduler.start()
            _log.warning("Scheduler de secours démarré avec des fonctionnalités limitées")
            return _fallback_scheduler
        except Exception as fallback_error:
            _log.critical(f"Impossible de démarrer même le scheduler de secours: {str(fallback_error)}")
            raise

_start_background_services()

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
    """Retourne une nouvelle session de base de données. L'appelant est responsable de db.close()."""
    return SessionLocal()

def _run_auto_analysis():
    """Lance l'analyse locale sur tous les marchés non encore analysés."""
    db = new_db()
    try:
        auto_analyze_pending(db)
    finally:
        db.close()

def _trigger_structured_analysis():
    """Analyse structurée des marchés sans llm_structured et score >= SCORE_ETUDE."""
    from llm_analyzer import analyze_tender_structured as _ats

    def _get_eligible_tenders(db_session):
        """Récupère les tenders éligibles pour l'analyse structurée."""
        try:
            return (
                db_session.query(Tender)
                .filter(
                    Tender.llm_structured == None,
                    Tender.relevance_score >= SCORE_ETUDE,
                    Tender.is_blacklisted == False,
                )
                .limit(20)
                .all()
            )
        except Exception as e:
            _log.error(f"Échec de la récupération des tenders éligibles: {str(e)}")
            return []

    def _analyze_and_update_tender(db_session, tender):
        """Analyse un tender et met à jour sa structure si succès."""
        if not tender.title and not tender.description:
            _log.warning(f"Tender {tender.id} sans titre ni description - analyse ignorée")
            return False

        try:
            result = _ats(tender.title or "", tender.description or "", tender.amount)
            if result:
                tender.llm_structured = result
                _log.info(f"Analyse structurée réussie pour le tender {tender.id}")
                return True
            else:
                _log.warning(f"Aucun résultat d'analyse pour le tender {tender.id}")
                return False
        except Exception as e:
            _log.error(f"Échec de l'analyse structurée pour le tender {tender.id}: {str(e)}")
            return False

    def _update_database(db_session, updated_count):
        """Met à jour la base de données si des modifications ont été apportées."""
        if updated_count > 0:
            try:
                db_session.commit()
                _log.info(f"Mise à jour de {updated_count} tender(s) avec analyse structurée")
            except Exception as e:
                db_session.rollback()
                _log.error(f"Échec de la mise à jour de la base de données: {str(e)}")
                raise

    # Exécution principale
    db_session = None
    try:
        db_session = new_db()
        tenders = _get_eligible_tenders(db_session)

        if not tenders:
            _log.info("Aucun tender éligible trouvé pour l'analyse structurée")
            return

        _log.info(f"Début de l'analyse structurée pour {len(tenders)} tender(s)")
        updated_count = 0

        for tender in tenders:
            if _analyze_and_update_tender(db_session, tender):
                updated_count += 1

        _update_database(db_session, updated_count)

    except Exception as e:
        _log.error(f"Échec critique dans _trigger_structured_analysis: {str(e)}", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
            except Exception:
                pass
    finally:
        if db_session:
            db_session.close()

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

@st.cache_data(ttl=3600)
def _get_health_status() -> dict:
    """Retourne le résultat du health check mis en cache 1h."""
    results = _hc.run_all_health_checks()
    _db = SessionLocal()
    try:
        _hc.persist_health_results(_db, results)
    except Exception:
        _log.warning("persist_health_results: échec de la persistance", exc_info=True)
    finally:
        _db.close()
    return {name: {"ok": r.ok, "error": r.error} for name, r in results.items()}

def _show_health_alerts():
    """Affiche une bannière si des sources sont dégradées."""
    try:
        statuses = _get_health_status()
    except Exception:
        return  # ne pas bloquer l'UI si le health check échoue
    degraded = [(name, info["error"]) for name, info in statuses.items() if not info["ok"]]
    if not degraded:
        return
    st.warning(
        f"⚠️ **{len(degraded)} source(s) dégradée(s)** — les données peuvent être incomplètes :\n"
        + "\n".join(f"- **{name}** : {err}" for name, err in degraded),
        icon="🔴",
    )

# Auto-analyse au démarrage (une seule fois par session)
if "auto_analyzed" not in st.session_state:
    _run_auto_analysis()
    threading.Thread(target=_trigger_structured_analysis, daemon=True).start()
    st.session_state["auto_analyzed"] = True
st.session_state.setdefault("new_tender_ids", set())

_show_health_alerts()

@st.cache_data(ttl=300)
def load_tenders(
    status_filter: str,
    maintenance_only: bool,
    date_from: datetime | None,
    strict_date: bool = False,
    secteur: str = "Public",
    only_recent: bool = False,
) -> list[dict]:
    if secteur not in ["Public", "Privé", "International"]:
        raise ValueError(f"Secteur invalide: {secteur}")
    if status_filter not in ["Tous", "À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]:
        raise ValueError(f"Statut invalide: {status_filter}")
    if date_from is not None and not isinstance(date_from, datetime):
        raise ValueError(f"date_from doit être un objet datetime, reçu: {type(date_from)}")

    db = new_db()
    try:
        q = db.query(Tender).filter(Tender.is_blacklisted == False)

        if secteur == "Public":
            q = q.filter(or_(Tender.secteur == "Public", Tender.secteur == None))
        elif secteur == "Privé":
            q = q.filter(Tender.secteur == "Privé")
        elif secteur == "International":
            q = q.filter(Tender.secteur == "International")

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
            deadline_str = t.deadline.strftime("%d/%m/%Y") if t.deadline else "—"
            pub_date_str = t.publication_date.strftime("%d/%m/%Y") if t.publication_date else "—"
            tags_list = t.tags if isinstance(t.tags, list) else []

            rows.append(
                {
                    "ID": t.id,
                    "Go/No-Go": _gonogo(score),
                    "Titre": t.title or "Sans titre",
                    "Source": t.source or "",
                    "Territoire": territoire,
                    "Domaine": domaine,
                    "Score": score,
                    "🧠 Adapt.": t.adaptive_score if t.adaptive_score is not None else "—",
                    "Date Limite": deadline_str,
                    "Publication": pub_date_str,
                    "Statut": t.status or "À qualifier",
                    "Type": a.get("type_marche") or t.type_opportunite or "—",
                    "Maint.": "✓" if t.is_maintenance else "",
                    "Concurrents": ", ".join(a.get("marques_concurrentes_citees", [])),
                    "Montant (€)": t.amount,
                    "⭐": bool(t.is_saved),
                    "Secteur": t.secteur or "Public",
                    "_deadline_dt": t.deadline,
                    "_pub_dt": t.publication_date,
                    "_desc": (t.description or "").lower(),
                    "_tags": tags_list,
                }
            )

        return rows

    except ValueError:
        raise
    except Exception as e:
        _log.error(f"Erreur critique dans load_tenders: {str(e)}", exc_info=True)
        return []
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

@st.cache_data(ttl=300)
def load_saved_tenders() -> list[dict]:
    db = new_db()
    try:
        tenders = (
            db.query(Tender)
            .filter(Tender.is_saved == True, Tender.is_blacklisted == False)
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
def load_chart_data(max_rows: int = 5000) -> list[dict]:
    """Charge les données pour les graphiques avec pagination pour optimiser les performances.

    Args:
        max_rows: Nombre maximum de résultats à retourner (par défaut: 5000)

    Returns:
        Liste de dictionnaires contenant les données pour les graphiques
    """
    db = new_db()
    try:
        # Utiliser une requête avec limite pour éviter de charger trop de données
        query = (
            db.query(
                Tender.publication_date,
                Tender.title,
                Tender.description,
                Tender.secteur,
            )
            .filter(Tender.is_blacklisted == False)
            .order_by(Tender.publication_date.desc())
            .limit(max_rows)  # Limiter le nombre de résultats
        )

        rows = query.all()
        return [
            {
                "pub": r.publication_date,
                "title": r.title or "",
                "desc": (r.description or "")[:200],  # Limiter la longueur de la description
                "secteur": r.secteur,
            }
            for r in rows
        ]
    except Exception as e:
        _log.error(f"Erreur dans load_chart_data: {str(e)}", exc_info=True)
        return []
    finally:
        db.close()

@st.cache_data(ttl=300)
def load_pipeline() -> dict[str, list[dict]]:
    """Retourne les marchés publics groupés par statut pour la vue pipeline."""
    db = new_db()
    try:
        tenders = (
            db.query(Tender)
            .filter(
                Tender.is_blacklisted == False,
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
        try:
            result = analyze_tender(
                f"{t.title or ''} {t.description or ''}",
                source_url=t.source if t.source and t.source.startswith("http") else None,
            )
        except Exception as exc:
            _log.warning("Analyse LLM échouée pour %s : %s", tender_id, type(exc).__name__)
            return
        if result:
            t.llm_analysis     = result
            t.relevance_score  = result.get("score_pertinence", 0)
            t.is_maintenance   = result.get("type_marche", "").lower() == "maintenance"
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def _naive_dt(dt):
    """Normalise un datetime en naïf (supprime tzinfo si présent)."""
    return dt.replace(tzinfo=None) if dt and dt.tzinfo is not None else dt

def _sort_rows(rows: list[dict], sort_by: str) -> list[dict]:
    if sort_by == "Score ↓":
        return sorted(rows, key=lambda r: -(r.get("Score") or 0))
    elif sort_by == "Score adaptatif ↓":
        return sorted(rows, key=lambda r: -(r.get("🧠 Adapt.") if isinstance(r.get("🧠 Adapt."), int) else 0))
    elif sort_by == "Publication ↓":
        return sorted(rows, key=lambda r: _naive_dt(r.get("_pub_dt")) or datetime.min, reverse=True)
    else:  # Date limite ↑ (défaut)
        return sorted(rows, key=lambda r: (
            r.get("_deadline_dt") is None,
            _naive_dt(r.get("_deadline_dt")) or datetime.max,
        ))

def _is_urgent(r: dict) -> bool:
    dl = r.get("_deadline_dt")
    if dl is None:
        return False
    try:
        d = dl.date() if hasattr(dl, "date") else dl
        return (d - _date.today()).days <= 14
    except Exception:
        return False

def _clear_tender_caches():
    load_tenders.clear()
    load_saved_tenders.clear()
    load_pipeline.clear()
    load_kpis_public.clear()
    load_kpis_ca.clear()
    load_kpis_priv.clear()
    load_chart_data.clear()
    _load_urgences_cached.clear()

def _apply_filters(
    rows: list[dict],
    search_query: str,
    urgent_only: bool,
    terr_actifs: list,
    selected_domaines: list,
    selected_decisions: list,
    selected_tags: list,
    sort_by: str,
    excluded_ids: set,
) -> list[dict]:
    if search_query:
        _sq = search_query.lower()
        rows = [r for r in rows if (
            _sq in r["Titre"].lower()
            or _sq in r["Territoire"].lower()
            or _sq in r["Domaine"].lower()
            or _sq in r["_desc"]
        )]
    if urgent_only:
        rows = [r for r in rows if _is_urgent(r)]
    if terr_actifs:
        rows = [r for r in rows if any(terr in r["Territoire"] for terr in terr_actifs)]
    if selected_domaines:
        rows = [r for r in rows if any(d in r["Domaine"] for d in selected_domaines)]
    if selected_decisions:
        rows = [r for r in rows if r["Go/No-Go"] in selected_decisions]
    if selected_tags:
        rows = [r for r in rows if any(tg in (r["_tags"] or []) for tg in selected_tags)]
    rows = _sort_rows(rows, sort_by)
    if excluded_ids:
        rows = [r for r in rows if r["ID"] not in excluded_ids]
    return rows

@st.cache_data(ttl=300)
def load_kpis_public() -> dict:
    db = new_db()
    try:
        pub_filter = or_(Tender.secteur == "Public", Tender.secteur == None)
        # Un seul GROUP BY remplace 5 COUNT séparés
        counts = dict(
            db.query(Tender.status, _func.count(Tender.id))
            .filter(Tender.is_blacklisted == False, pub_filter)
            .group_by(Tender.status)
            .all()
        )
        total = sum(counts.values())
        return {
            "total": total,
            "a_qualifier": counts.get("À qualifier", 0),
            "en_cours": counts.get("En cours", 0),
            "gagnes": counts.get("Gagné", 0),
            "soumis": counts.get("Soumis", 0),
        }
    finally:
        db.close()

@st.cache_data(ttl=300)
def load_kpis_ca() -> dict:
    db = new_db()
    try:
        pub = (Tender.is_blacklisted == False, or_(Tender.secteur == "Public", Tender.secteur == None))
        # Un seul GROUP BY remplace 3 SUM séparés
        sums = dict(
            db.query(Tender.status, _func.sum(Tender.amount))
            .filter(*pub, Tender.amount != None)
            .group_by(Tender.status)
            .all()
        )
        en_cours = sums.get("En cours") or 0
        soumis = sums.get("Soumis") or 0
        gagne = sums.get("Gagné") or 0
        return {"en_cours": en_cours, "soumis": soumis, "gagne": gagne, "pipeline": en_cours + soumis}
    finally:
        db.close()

@st.cache_data(ttl=300)
def load_kpis_priv() -> dict:
    db = new_db()
    try:
        priv = (Tender.is_blacklisted == False, Tender.secteur == "Privé")
        type_counts = dict(
            db.query(Tender.type_opportunite, _func.count(Tender.id))
            .filter(*priv)
            .group_by(Tender.type_opportunite)
            .all()
        )
        devbanks = db.query(_func.count(Tender.id)).filter(
            Tender.is_blacklisted == False, Tender.type_opportunite == "Banque Dev."
        ).scalar() or 0
        qualif_priv = db.query(_func.count(Tender.id)).filter(
            *priv, Tender.status == "À qualifier"
        ).scalar() or 0
        return {
            "permis": type_counts.get("Permis Construire", 0),
            "presse": type_counts.get("Presse", 0),
            "instit": type_counts.get("Institution", 0),
            "devbanks": devbanks,
            "qualif_priv": qualif_priv,
        }
    except Exception as e:
        _log.error(f"Erreur dans load_kpis_priv: {str(e)}", exc_info=True)
        return {"permis": 0, "presse": 0, "instit": 0, "devbanks": 0, "qualif_priv": 0}
    finally:
        db.close()

# ── sidebar ───────────────────────────────────────────────────────────────────

def _collect_all_enabled_sources() -> None:
    """Lance les scrapers de toutes les sources activées/validées et traite les résultats."""
    import importlib

    def _initialize_collection():
        """Initialise la collecte en récupérant les IDs existants et les sources."""
        _db_init = new_db()
        try:
            known_ids = {row.id for row in _db_init.query(Tender.id).all()}
            sources = list_sources(_db_init)
            return known_ids, sources
        finally:
            _db_init.close()

    def _process_source(source, known_ids):
        """Traite une source individuelle et retourne les résultats."""
        _src_error = None
        new_ids = set()

        if source.is_manual or not source.scraper_module:
            return new_ids, _src_error
        if not source.enabled or not source.is_validated:
            return new_ids, _src_error

        try:
            mod = importlib.import_module(source.scraper_module)
            func = getattr(mod, source.scraper_func)
            func()
        except Exception as exc:
            _src_error = str(exc)
            _cleanup_failed_scraper(source.name, str(exc))

        # Compare les IDs après le scraping
        new_ids = _get_new_ids_after_scraping(source.name, known_ids)
        return new_ids, _src_error

    def _cleanup_failed_scraper(source_name, error):
        """Nettoie les exécutions de scraper échouées."""
        try:
            from models import ScraperRun as _SR_cleanup
            from database import finish_scraper_run as _fsr
            _db_cleanup = new_db()
            try:
                _orphan = _db_cleanup.query(_SR_cleanup).filter(
                    _SR_cleanup.source_name == source_name,
                    _SR_cleanup.status == "running",
                ).order_by(_SR_cleanup.id.desc()).first()
                if _orphan:
                    _fsr(_db_cleanup, _orphan.id, nb_found=0, nb_new=0, error=error)
            finally:
                _db_cleanup.close()
        except Exception:
            _log.error(f"Échec du nettoyage pour {source_name}", exc_info=True)

    def _get_new_ids_after_scraping(source_name, known_ids):
        _db_post = new_db()
        try:
            # Filtre côté DB pour éviter de scanner toute la table
            return {
                row.id for row in
                _db_post.query(Tender.id).filter(~Tender.id.in_(known_ids)).all()
            }
        finally:
            _db_post.close()

    def _analyze_results(all_new_ids):
        """Analyse les nouveaux tenders et retourne les statistiques."""
        if not all_new_ids:
            return 0, 0, 0, 0

        _db_res = new_db()
        try:
            _new_tenders = _db_res.query(Tender).filter(
                Tender.id.in_(all_new_ids)
            ).all()

            def _get_score(t) -> int:
                return (t.llm_analysis or {}).get("score_pertinence", t.relevance_score or 0)

            go_count = sum(1 for t in _new_tenders if _get_score(t) >= SCORE_GO)
            etude_count = sum(1 for t in _new_tenders if SCORE_ETUDE <= _get_score(t) < SCORE_GO)
            pass_count = sum(1 for t in _new_tenders if _get_score(t) < SCORE_ETUDE)
            claude_ok = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("_source") in ("claude", "gemini"))

            return go_count, etude_count, pass_count, claude_ok
        finally:
            _db_res.close()

    def _update_session_state(per_source_new, per_source_status, all_new_ids):
        """Met à jour l'état de la session avec les résultats."""
        st.session_state["new_tender_ids"] = all_new_ids
        st.session_state["collection_results"] = per_source_new
        st.session_state["collection_source_ids"] = {src: ids for src, ids in per_source_new.items()}
        st.session_state["collection_status"] = per_source_status

        # Réinitialise les filtres source
        for k in [k for k in st.session_state if k.startswith("src_filter_")]:
            del st.session_state[k]
        for src in per_source_new:
            st.session_state[f"src_filter_{src}"] = True

    def _display_results(total, go_count, etude_count, pass_count, claude_ok, errors, new_ids):
        if total and new_ids:
            message = (
                f"✅ {total} nouveau(x) marché(s) importé(s) — "
                f"🟢 {go_count} GO · 🟡 {etude_count} À étudier · 🔴 {pass_count} Passer"
            )
            if claude_ok:
                message += f" · 🤖 {claude_ok} analysé(s) par IA"
            st.success(message)
        elif total:
            st.success(f"✅ {total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
        elif not errors:
            st.info("Aucune nouvelle offre trouvée.")

    # Exécution principale
    with st.spinner("Collecte en cours…"):
        # Initialisation
        known_ids, sources = _initialize_collection()
        per_source_new = {}
        per_source_status = []
        errors = []

        # Traitement des sources
        for source in sources:
            new_ids, src_error = _process_source(source, known_ids)
            if src_error:
                errors.append(f"{source.name} : {src_error}")
            if new_ids:
                per_source_new[source.name] = new_ids
                known_ids.update(new_ids)
            per_source_status.append({
                "name": source.name,
                "nb_new": len(new_ids),
                "error": src_error,
            })

        # Analyse des résultats
        all_new_ids = {tid for ids in per_source_new.values() for tid in ids}
        go_count, etude_count, pass_count, claude_ok = _analyze_results(all_new_ids)
        total = sum(len(ids) for ids in per_source_new.values())

        # Mise à jour de l'état et affichage
        _update_session_state(per_source_new, per_source_status, all_new_ids)
        _display_results(total, go_count, etude_count, pass_count, claude_ok, errors, all_new_ids)

    # Analyse automatique post-collecte (locale)
    _run_auto_analysis()

    # Analyse LLM automatique si de nouveaux marchés existent
    if all_new_ids:
        _nb_attempted = min(len(all_new_ids), 10)
        _llm_provider = os.getenv("LLM_PROVIDER", "mistral")
        _db_llm = new_db()
        try:
            _nb_done, _retry_after = auto_analyze_claude(_db_llm, max_per_run=10)
            st.session_state["llm_analysis_status"] = {
                "nb_done": _nb_done,
                "nb_failed": max(0, _nb_attempted - _nb_done),
                "retry_after": _retry_after,
                "provider": _llm_provider,
                "error": None,
            }
        except Exception as _exc:
            st.session_state["llm_analysis_status"] = {
                "nb_done": 0,
                "nb_failed": _nb_attempted,
                "retry_after": -1,
                "provider": _llm_provider,
                "error": str(_exc),
            }
        finally:
            _db_llm.close()

    _clear_tender_caches()

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
            .filter(Tender.id.in_(new_ids), Tender.is_blacklisted == False)
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
                _clear_tender_caches()
                st.rerun(scope="fragment")
        with col_qualify:
            if st.button("✅ Qualifier", key=f"new_qualify_{t.id}"):
                save_status(t.id, "En cours")
                _clear_tender_caches()
                st.rerun(scope="fragment")
        with col_src:
            if t.source and t.source.startswith("http"):
                st.link_button("🔗 Source", url=t.source)

    if total > 5:
        st.caption(f"+ {total - 5} autre(s) nouveau(x) marché(s) — consultez le tableau ci-dessous.")

    st.markdown("---")

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
    c3.metric("📋 Collectés", total_new)

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
                f"<span style='color:#f87171;font-weight:600;font-size:0.8rem;'>✗ {_html.escape(s['name'])}</span>"
                f"<br><span style='color:#64748b;font-size:0.72rem;font-style:italic;'>"
                f"{_html.escape(s['error'][:120])}</span></div>",
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
                f"<span style='color:{color};'>{icon} {_html.escape(s['name'])}</span>"
                f"<span style='color:#64748b;font-size:0.7rem;'>{detail}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

with st.sidebar:
    st.markdown("## 🔥 DEF Océan Indien")
    st.markdown("**Veille Marchés Publics**")
    st.markdown("---")

    _now = datetime.now()
    _cy = _now.year
    _today = _now.replace(hour=0, minute=0, second=0, microsecond=0)
    periode_labels = {
        "30 derniers jours": (_today - timedelta(days=30), True),
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
        ["Date limite ↑", "Score ↓", "Score adaptatif ↓", "Publication ↓"],
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

    _render_collection_status_sidebar()

    _col_results = st.session_state.get("collection_results", {})
    if _col_results:
        st.markdown("**Filtrer par source :**")
        for _src_name, _nb_new in sorted(_col_results.items()):
            st.checkbox(
                f"{_src_name} ({_nb_new})",
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
        _clear_tender_caches()

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

# ── header + export ───────────────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
  <div class="page-header-left">
    <h1>🔥 DEF Océan Indien — <em>Veille Marchés</em></h1>
    <p>Périmètre : La Réunion (974) & Mayotte (976) · SSI · CMSI · Détection incendie · Vidéosurveillance</p>
  </div>
  <div class="page-header-badge">Marchés Publics & Privés</div>
</div>
""", unsafe_allow_html=True)

# Export button — génère le rapport uniquement sur clic (pas au chargement de page)
_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    if st.button("📊  Générer le Rapport Direction (Excel)", use_container_width=True, type="primary"):
        with st.spinner("Génération du rapport en cours…"):
            _db_rpt = new_db()
            try:
                _report_bytes = generate_executive_report(_db_rpt)
            finally:
                _db_rpt.close()
        st.download_button(
            label="⬇️  Télécharger le Rapport Direction",
            data=_report_bytes,
            file_name=f"Rapport_Direction_DEF_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
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
                if r["pub"] and _naive_dt(r["pub"]) >= _cutoff:
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

def _get_tender_data(tender_id: str):
    """Récupère les données du tender depuis la base de données."""
    db = new_db()
    try:
        return db.query(Tender).filter(Tender.id == tender_id).first()
    finally:
        db.close()

def _calculate_tender_metrics(t, a):
    """Calcule les métriques et données dérivées pour un tender."""
    domaine = detect_domaine(t.title or "", t.description or "")
    territoire = detect_territoire(t.title or "", t.description or "")
    score = a.get("score_pertinence", t.relevance_score or 0)

    # Calcul du délai restant
    jours_restants = None
    if t.deadline:
        try:
            today = _date.today()
            dl = t.deadline.date() if hasattr(t.deadline, "date") else t.deadline
            jours_restants = (dl - today).days
        except Exception:
            pass

    return {
        "domaine": domaine,
        "territoire": territoire,
        "score": score,
        "jours_restants": jours_restants,
        "fiche_data": _compute_fiche_data(
            score, jours_restants, domaine, territoire,
            bool(t.is_maintenance), t.title or "", a,
        )
    }

def _render_decision_header(score, tag, domaine, territoire, justification):
    """Affiche l'en-tête de décision avec le score et le badge approprié."""
    header_line = f"**{tag}** — Score {score}/100 · {domaine} · {territoire}"
    if score >= SCORE_GO:
        st.success(header_line)
    elif score >= SCORE_ETUDE:
        st.warning(header_line)
    else:
        st.error(header_line)
    if justification:
        st.caption(f"💡 {justification}")

def _render_ssi_warning(tags):
    """Affiche un avertissement si le tag 'Potentiel SSI implicite' est présent."""
    if "Potentiel SSI implicite" in (tags if isinstance(tags, list) else []):
        st.info(
            "⚠️ **Potentiel SSI implicite** — capturé via type de bâtiment (ERP) "
            "sans mot-clé SSI direct. Confirmer lors de la qualification."
        )

def _render_metrics_row(t, a):
    """Affiche la rangée de métriques condensées."""
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    jours_restants = t.deadline.date() if hasattr(t.deadline, "date") else t.deadline if t.deadline else None

    if jours_restants is not None:
        m1.metric("Délai (j)", (jours_restants - _date.today()).days)
    else:
        m1.metric("Délai (j)", "—")
    m2.metric("Type", a.get("type_marche") or t.type_opportunite or "—")
    m3.metric("Maintenance", "Oui" if t.is_maintenance else "Non")
    m4.metric("Concurrents", len(a.get("marques_concurrentes_citees", [])))
    source_a = a.get("_source", "local")
    m5.metric("Analyse", "Claude IA" if source_a in ("claude", "gemini") else "Règles")
    _adap_val = t.adaptive_score if t.adaptive_score is not None else "—"
    m6.metric("🧠 Adapt.", _adap_val)

def _render_fiche(tender_id: str, key_suffix: str) -> None:
    """Affiche la fiche détaillée d'un tender avec une meilleure organisation."""
    t = _get_tender_data(tender_id)
    if not t:
        return

    a = t.llm_analysis or {}
    metrics = _calculate_tender_metrics(t, a)

    _render_fiche_header_section(t, a, metrics)
    _render_fiche_action_plan_section(metrics["fiche_data"])
    _render_fiche_technical_section(t, a, metrics["fiche_data"])
    _render_fiche_additional_analysis(t, key_suffix)
    _render_fiche_actions_and_notes(t, key_suffix)

def _render_fiche_header_section(t, a, metrics):
    """Affiche la section d'en-tête de la fiche."""
    _render_decision_header(
        metrics["score"],
        a.get("tag_pertinence") or _gonogo(metrics["score"]),
        metrics["domaine"],
        metrics["territoire"],
        a.get("justification_score")
    )

    _render_ssi_warning(t.tags)
    _render_metrics_row(t, a)

def _render_fiche_action_plan_section(fiche_data):
    """Affiche la section du plan d'action et des atouts."""
    # Plan d'action
    st.markdown(f"#### {fiche_data['label_action']}")
    for i, step in enumerate(fiche_data["steps"], 1):
        st.markdown(f"{i}. {step}")
    for risque in fiche_data["risques"]:
        st.warning(risque)

    # Atouts DEF OI
    st.markdown("#### Pourquoi c'est pertinent pour DEF OI")
    for atout in fiche_data["atouts"]:
        st.markdown(atout)

def _render_fiche_technical_section(t, a, fiche_data):
    """Affiche la section technique avec les détails du score."""
    with st.expander("📊 Détail du score & mots-clés"):
        _render_technical_details(t, a, fiche_data)

def _render_fiche_additional_analysis(t, key_suffix):
    """Affiche les sections d'analyse supplémentaire."""
    # Analyse structurée IA
    if t.llm_structured:
        _render_structured_analysis(t, key_suffix)

    # Historique marchés similaires
    _render_similar_history(t, key_suffix)

    st.markdown("---")

def _render_fiche_actions_and_notes(t, key_suffix):
    """Affiche les sections d'actions rapides et de notes."""
    # Actions rapides
    _render_quick_actions(t, key_suffix)

    # Notes internes
    _render_notes_section(t, key_suffix)

    # Tags
    _render_tags_section(t, key_suffix)

def _render_technical_details(t, a, fiche_data):
    """Affiche les détails techniques dans l'expander."""
    st.markdown("**Décomposition du score DEF**")
    source_a = a.get("_source", "local")
    if source_a in ("claude", "gemini"):
        st.caption("Estimation indicative — le score affiché est celui de l'IA, pas la somme ci-dessous.")
    for nom, val, maxval in [
        ("Pertinence métier", fiche_data["sm"], 45),
        ("Proximité géographique", fiche_data["sg"], 30),
        ("Mots-clés dans le titre", fiche_data["sk"], 15),
        ("Maintenance / Récurrence", fiche_data["smaint"], 10),
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
    territoire_ia = a.get("territoire_ia") or detect_territoire(t.title or "", t.description or "")
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

def _render_structured_analysis(t, key_suffix):
    """Affiche l'analyse structurée IA."""
    _s = t.llm_structured
    with st.expander("🤖 Analyse structurée IA", expanded=True):
        _c1, _c2 = st.columns(2)
        with _c1:
            st.markdown(f"**Budget estimé** {_s.get('budget_estime') or '—'}")
            st.markdown(f"**Type de travaux** {_s.get('type_travaux') or '—'}")
            st.markdown(f"**Acheteur** {_s.get('acheteur_type') or '—'}")
        with _c2:
            st.markdown(f"**Concurrence** {_s.get('niveau_concurrence') or '—'}")
            _conf = _s.get('score_confiance')
            st.markdown(f"**Confiance IA** {_conf} %" if _conf is not None else "**Confiance IA** —")
            _reco = _s.get('recommandation', '')
            _badge = "✅ GO" if _reco == "GO" else ("🔴 NON" if _reco == "NON" else "—")
            st.markdown(f"**Recommandation** {_badge}")
        _lots = _s.get('lots', [])
        if _lots:
            st.markdown(f"**Lots** {' · '.join(_lots)}")
        _justif = _s.get('justification', '')
        if _justif:
            st.caption(_justif)
        if st.button("🔄 Ré-analyser (LLM structuré)", key=f"rellm_{key_suffix}_{t.id}"):
            from llm_analyzer import analyze_tender_structured as _ats
            with st.spinner("Analyse en cours…"):
                _new = _ats(t.title or "", t.description or "", t.amount)
            if _new:
                _db_ra = new_db()
                try:
                    _t_ra = _db_ra.query(Tender).filter(Tender.id == t.id).first()
                    if _t_ra:
                        _t_ra.llm_structured = _new
                        _db_ra.commit()
                finally:
                    _db_ra.close()
                _clear_tender_caches()
                st.rerun()
            else:
                st.warning("Analyse impossible (description trop courte ou clé API manquante)")

def _render_similar_history(t, key_suffix):
    """Affiche l'historique des marchés similaires."""
    from fiche_logic import get_acheteur_history as _gah
    _db_hist = new_db()
    try:
        _hist = _gah(_db_hist, t)
    finally:
        _db_hist.close()
    if _hist.get('nb_total', 0) >= 2:
        with st.expander(f"📋 Historique marchés similaires ({_hist['nb_total']} trouvés)", expanded=False):
            _hc1, _hc2, _hc3 = st.columns(3)
            _hc1.metric("Marchés similaires", _hist['nb_total'])
            _hc2.metric("Dont GO (≥65)", _hist.get('nb_go', 0))
            _hc3.metric("Gagnés", _hist.get('nb_gagnes', 0))
            if _hist.get('montant_total_gagne'):
                st.caption(f"CA gagné : {_hist['montant_total_gagne']:,.0f} €")
            _derniers = _hist.get('derniers', [])
            if _derniers:
                st.markdown("**Derniers marchés similaires :**")
                for _d in _derniers:
                    _d_score = _d.relevance_score or 0
                    _d_badge = "🟢" if _d_score >= SCORE_GO else ("🟡" if _d_score >= SCORE_ETUDE else "🔴")
                    st.markdown(f"{_d_badge} {_d.title or '—'} — Score {_d_score}")

def _render_quick_actions(t, key_suffix):
    """Affiche les boutons d'actions rapides."""
    col_save, col_qualify, col_reanalyze, _ = st.columns([2, 2, 2, 4])
    with col_save:
        star = bool(t.is_saved)
        label_star = "⭐ Sauvegardé" if star else "⭐ Sauvegarder"
        if st.button(label_star, key=f"fiche_save_{key_suffix}_{t.id}"):
            toggle_saved(t.id, not star)
            _clear_tender_caches()
            st.rerun()
    with col_qualify:
        if t.status not in ("En cours", "Soumis", "Gagné", "Perdu"):
            if st.button("✅ Qualifier → En cours", key=f"fiche_qualify_{key_suffix}_{t.id}"):
                save_status(t.id, "En cours")
                _clear_tender_caches()
                st.rerun()
        else:
            st.caption(f"Statut : {t.status}")
    with col_reanalyze:
        if st.button("🤖 Réanalyser", key=f"reanalyze_{key_suffix}_{t.id}",
                     help="Relance l'analyse Claude pour affiner le score et la justification"):
            with st.spinner("Analyse Claude en cours…"):
                run_analysis(t.id)
            _clear_tender_caches()
            st.rerun()

def _render_notes_section(t, key_suffix):
    """Affiche la section des notes internes."""
    with st.expander("📝 Notes internes", expanded=bool(t.notes)):
        _notes_new = st.text_area(
            "Annotations commerciales (non exportées)",
            value=t.notes or "",
            height=80,
            key=f"notes_area_{key_suffix}_{t.id}",
        )
        if st.button("💾 Enregistrer", key=f"save_notes_{key_suffix}_{t.id}"):
            save_notes(t.id, _notes_new)
            st.success("Notes enregistrées.")

def _render_tags_section(t, key_suffix):
    """Affiche la section des tags."""
    with st.expander("🏷️ Tags", expanded=bool(t.tags)):
        _selected_tags = st.multiselect(
            "Étiquettes",
            options=TENDER_TAGS,
            default=[tg for tg in (t.tags if isinstance(t.tags, list) else []) if tg in TENDER_TAGS],
            key=f"tags_ms_{key_suffix}_{t.id}",
        )
        if st.button("💾 Sauvegarder les tags", key=f"save_tags_{key_suffix}_{t.id}"):
            save_tags(t.id, _selected_tags)
            _clear_tender_caches()
            st.success("Tags sauvegardés.")
            st.rerun()

def _render_editor_section(
    rows: list[dict],
    section_title: str,
    section_subtitle: str,
    fiche_title: str,
    editor_key: str,
    sel_all_key: str,
    del_btn_key: str,
) -> None:
    """Affiche la section d'édition avec séparation claire entre logique et rendu."""
    _render_editor_header(section_title, section_subtitle, rows)
    if not rows:
        return

    df = _prepare_editor_data(rows)
    _sel_id_key, _df_prev_row_key = _get_editor_keys(editor_key)

    _render_export_button(df, editor_key)
    _render_main_dataframe(df, editor_key, _sel_id_key, _df_prev_row_key)
    _render_quick_edit_section(df, editor_key, sel_all_key, del_btn_key)
    _render_selected_item_analysis(df, editor_key, _sel_id_key, _df_prev_row_key, fiche_title)

def _render_editor_header(section_title: str, section_subtitle: str, rows: list[dict]):
    """Affiche l'en-tête de la section d'édition."""
    st.markdown(_section_html(section_title, section_subtitle), unsafe_allow_html=True)

    if not rows:
        st.info("Aucun résultat. Lancez la collecte depuis le menu latéral ou ajustez les filtres.")

def _prepare_editor_data(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    return df

def _get_editor_keys(editor_key: str) -> tuple[str, str]:
    """Retourne les clés pour la gestion de l'état."""
    return f"_sel_id_{editor_key}", f"_df_prev_row_{editor_key}"

def _render_export_button(df: pd.DataFrame, editor_key: str):
    """Affiche le bouton d'export CSV."""
    _MAX_EXPORT_ROWS = 10_000
    if len(df) > _MAX_EXPORT_ROWS:
        st.warning(f"⚠️ Export limité aux {_MAX_EXPORT_ROWS} premières lignes (sur {len(df)} résultats). Affinez vos filtres pour exporter tout.")
        df_export = df.head(_MAX_EXPORT_ROWS)
    else:
        df_export = df

    _export_cols = [c for c in df_export.columns if not c.startswith("_") and c not in ("ID", "Secteur")]
    _csv_buf = _io.StringIO()
    df_export[_export_cols].to_csv(_csv_buf, index=False)
    st.download_button(
        "📥 Exporter vue filtrée (CSV)",
        data=_csv_buf.getvalue().encode("utf-8-sig"),
        file_name=f"DEF_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key=f"csv_{editor_key}",
    )

def _render_main_dataframe(df: pd.DataFrame, editor_key: str, sel_id_key: str, df_prev_row_key: str):
    """Affiche le tableau principal avec gestion de la sélection."""
    st.caption("👆 Cliquez sur une ligne pour la sélectionner et afficher son analyse ci-dessous")
    view_event = st.dataframe(
        df.drop(columns=["ID", "Secteur", "_deadline_dt", "_pub_dt", "_desc", "_tags"], errors="ignore"),
        column_config={
            "Go/No-Go": st.column_config.TextColumn("Décision", width="small"),
            "Titre": st.column_config.TextColumn("Titre du Marché", width="large"),
            "Source": st.column_config.LinkColumn("Source", width="small"),
            "Territoire": st.column_config.TextColumn("Territoire", width="medium"),
            "Domaine": st.column_config.TextColumn("Domaine", width="medium"),
            "Score": st.column_config.ProgressColumn("Score DEF", min_value=0, max_value=100, format="%d"),
            "🧠 Adapt.": st.column_config.TextColumn("Score Adapt.", width="small"),
            "Date Limite": st.column_config.TextColumn("Date Limite", width="small"),
            "Publication": st.column_config.TextColumn("Publication", width="small"),
            "Statut": st.column_config.TextColumn("Statut", width="small"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Montant (€)": st.column_config.NumberColumn("Montant (€)", format="%d €", width="small"),
            "⭐": st.column_config.CheckboxColumn("⭐", width="small"),
        },
        column_order=["Go/No-Go", "Titre", "Source", "Territoire", "Domaine", "Score", "🧠 Adapt.", "Montant (€)", "Date Limite", "Publication", "Statut", "Type", "⭐"],
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=f"{editor_key}_view",
    )

    _handle_row_selection(view_event, df, sel_id_key, df_prev_row_key)

def _handle_row_selection(view_event, df: pd.DataFrame, sel_id_key: str, df_prev_row_key: str):
    """Gère la sélection des lignes dans le tableau."""
    if view_event.selection.rows:
        selected_row_idx = view_event.selection.rows[0]
        if selected_row_idx < len(df):
            new_id = df.iloc[selected_row_idx]["ID"]
            if new_id != st.session_state.get(sel_id_key):
                st.session_state[df_prev_row_key] = selected_row_idx
                st.session_state[sel_id_key] = new_id

def _render_quick_edit_section(df: pd.DataFrame, editor_key: str, sel_all_key: str, del_btn_key: str):
    """Affiche la section d'édition rapide."""
    with st.expander("✏️ Modifier statut / montant / étoile / supprimer"):
        _all = st.session_state.get(sel_all_key, False)
        _, col_selall = st.columns([8, 1])
        with col_selall:
            if st.button("☑️ Tout" if not _all else "☐ Aucun", key=f"btn_{sel_all_key}"):
                st.session_state[sel_all_key] = not _all
                st.session_state.pop(editor_key, None)
                st.rerun()

        df_edit = _prepare_editable_dataframe(df, sel_all_key)
        edited = _render_editable_dataframe(df_edit, editor_key)

        _handle_bulk_deletion(edited, del_btn_key, sel_all_key)
        _handle_individual_edits(edited, df_edit, editor_key)

def _prepare_editable_dataframe(df: pd.DataFrame, sel_all_key: str) -> pd.DataFrame:
    """Prépare le DataFrame pour l'édition."""
    df_edit = df.copy()
    df_edit.insert(0, "🗑️", st.session_state.get(sel_all_key, False))
    return df_edit

def _render_editable_dataframe(df_edit: pd.DataFrame, editor_key: str):
    """Affiche le DataFrame éditable."""
    return st.data_editor(
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
            "🧠 Adapt.": st.column_config.TextColumn("Score Adapt.", width="small", disabled=True),
            "Date Limite": st.column_config.TextColumn("Date Limite", width="small", disabled=True),
            "Publication": st.column_config.TextColumn("Publication", width="small", disabled=True),
            "Statut": st.column_config.SelectboxColumn("Statut", options=status_options, width="medium"),
            "Type": st.column_config.TextColumn("Type", width="small", disabled=True),
            "Maint.": st.column_config.TextColumn("Maint.", width="small", disabled=True),
            "Concurrents": st.column_config.TextColumn("Concurrents", width="medium", disabled=True),
            "Montant (€)": st.column_config.NumberColumn("Montant (€)", min_value=0, step=1000, format="%d €", width="small"),
        },
        column_order=["🗑️", "⭐", "Go/No-Go", "Titre", "Source", "Territoire", "Domaine", "Score", "🧠 Adapt.", "Montant (€)", "Date Limite", "Publication", "Statut", "Type", "Maint.", "Concurrents", "ID"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key=editor_key,
    )

def _handle_bulk_deletion(edited: pd.DataFrame, del_btn_key: str, sel_all_key: str):
    """Gère la suppression en masse."""
    to_delete = edited[edited["🗑️"] == True]["ID"].tolist()
    if to_delete:
        if st.button(f"🗑️ Supprimer {len(to_delete)} élément(s) sélectionné(s)", key=del_btn_key, type="secondary"):
            for tid in to_delete:
                delete_tender(tid)
            st.session_state.pop(sel_all_key, None)
            _clear_tender_caches()
            st.rerun()

def _handle_individual_edits(edited: pd.DataFrame, df_edit: pd.DataFrame, editor_key: str):
    """Gère les modifications individuelles."""
    editor_state = st.session_state.get(editor_key, {})
    _needs_rerun = False

    for row_idx, changes in editor_state.get("edited_rows", {}).items():
        if "Statut" in changes:
            save_status(df_edit.iloc[row_idx]["ID"], changes["Statut"])
            _needs_rerun = True
        if "Montant (€)" in changes:
            save_amount(df_edit.iloc[row_idx]["ID"], changes["Montant (€)"])
            _needs_rerun = True
        if "⭐" in changes:
            toggle_saved(df_edit.iloc[row_idx]["ID"], changes["⭐"])
            _needs_rerun = True

    if _needs_rerun:
        _clear_tender_caches()
        st.rerun()

def _render_selected_item_analysis(df: pd.DataFrame, editor_key: str, sel_id_key: str, df_prev_row_key: str, fiche_title: str):
    """Affiche l'analyse de l'élément sélectionné."""
    st.markdown("---")
    st.markdown(_section_html(fiche_title, "Analyse détaillée de l'élément sélectionné"), unsafe_allow_html=True)

    _sel_id = st.session_state.get(sel_id_key)
    _prev_row = st.session_state.get(df_prev_row_key)

    if _sel_id:
        if _prev_row is None:
            st.caption("📌 Affichage depuis le pipeline — cliquez sur une ligne du tableau pour changer la sélection.")
        _render_fiche(_sel_id, editor_key)
    else:
        st.info("👆 Cliquez sur une ligne du tableau pour afficher son analyse.")

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
rows_pub = _apply_filters(rows_pub, search_query, urgent_only, terr_actifs, selected_domaines, selected_decisions, selected_tags, sort_by, _excluded_new_ids)

_render_editor_section(
    rows=rows_pub,
    section_title=f"📋 Marchés Publics — {len(rows_pub)} résultats",
    section_subtitle="Modifiez le statut, le montant ou l'étoile directement dans le tableau",
    fiche_title="📋 Fiche commerciale — Marché Public",
    editor_key="pub_editor",
    sel_all_key="_sel_all_pub",
    del_btn_key="del_pub",
)

# ── Tableau Signaux Privés ────────────────────────────────────────────────────

rows_priv = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Privé", only_recent=only_recent)
rows_priv = _apply_filters(rows_priv, search_query, urgent_only, terr_actifs, selected_domaines, selected_decisions, selected_tags, sort_by, _excluded_new_ids)

_render_editor_section(
    rows=rows_priv,
    section_title=f"🏗️ Signaux Privés — {len(rows_priv)} résultats",
    section_subtitle="Permis de construire, articles presse, institutions, banques de développement",
    fiche_title="🏗️ Fiche commerciale — Signal Privé",
    editor_key="priv_editor",
    sel_all_key="_sel_all_priv",
    del_btn_key="del_priv",
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
                st.session_state["_sel_id_pub_editor"] = _it["id"]
                st.session_state.pop("_df_prev_row_pub_editor", None)
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
            m_dept = st.selectbox("Territoire",
                ["974 — La Réunion", "976 — Mayotte",
                 "Madagascar", "Maurice", "Comores", "Autre / Non précisé"],
            )

        m_desc = st.text_area("Description / Objet", placeholder="Coller ici le descriptif du marché…", height=80)

        submitted = st.form_submit_button("Enregistrer l'opportunité", use_container_width=True, type="primary")

        if submitted:
            _url_raw = m_url.strip()
            _url_invalid = _url_raw and not _url_raw.startswith(("http://", "https://"))
            _deadline_past = m_deadline is not None and m_deadline < _date.today()
            if not m_title.strip():
                st.error("Le titre est obligatoire.")
            elif _url_invalid:
                st.error("L'URL doit commencer par http:// ou https://")
            elif _deadline_past:
                st.warning("⚠️ La date limite est dans le passé — l'opportunité sera enregistrée en archive.")
            if not m_title.strip() or _url_invalid:
                pass
            else:
                tid = "MANUAL-" + _uuid.uuid4().hex[:16]
                db_m = new_db()
                try:
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
                    _clear_tender_caches()
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
                _clear_tender_caches()
                st.rerun()
        with col_del:
            if s.scraper_module is None:  # uniquement les sources manuelles
                if st.button("🗑️", key=f"del_{s.id}", help="Supprimer cette source"):
                    db_d = new_db()
                    try:
                        remove_source(db_d, s.id)
                    finally:
                        db_d.close()
                    _clear_tender_caches()
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
                _clear_tender_caches()
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
            _clear_tender_caches()
            st.rerun()

st.markdown("---")
st.caption("DEF Océan Indien © 2025 · Outil de Veille Commerciale Interne")