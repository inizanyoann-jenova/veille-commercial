"""
FastAPI backend — DEF OI Veille Marchés
Reproduit exactement la logique de récupération de données de app.py.
"""

from __future__ import annotations

import importlib
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import func as _func, or_
from sqlalchemy.orm import Session

# Le backend tourne depuis le dossier backend/ — on remonte d'un niveau pour
# trouver les modules du projet (database, models, llm_analyzer, …)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import (  # noqa: E402
    SessionLocal,
    clean_obsolete_data,
    detect_duplicates,
    get_db,
    init_db,
    load_pipeline_data,
    load_urgences,
    reset_tenders_db,
    start_scraper_run,
    finish_scraper_run,
)
from models import DuplicateCandidate, ScraperRun, Tender  # noqa: E402
from source_registry import list_sources  # noqa: E402
from fiche_logic import _compute_fiche_data  # noqa: E402

# ── Domaine / territoire (répliqués depuis app.py) ────────────────────────────

from llm_analyzer import (  # noqa: E402
    _KW_SSI,
    _KW_CMSI,
    _KW_VIDEO,
    _KW_COURANTS_FAIBLES,
    _match,
    analyze_tender,
    auto_analyze_claude,
    auto_analyze_pending,
)

_log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Constantes métier ─────────────────────────────────────────────────────────

SCORE_GO = 65
SCORE_ETUDE = 35

DOMAINES: dict[str, list] = {
    "🔥 SSI / Détection incendie": _KW_SSI,
    "💨 CMSI / Désenfumage": _KW_CMSI,
    "📷 Vidéosurveillance / CCTV": _KW_VIDEO,
    "⚡ Courants faibles": _KW_COURANTS_FAIBLES,
}

TERRITOIRES: dict[str, list[str]] = {
    "La Réunion": [
        "la réunion", "la reunion", " 974 ", "(974)", "ile bourbon",
        "ile de la reunion", "saint-denis", "saint-pierre", "saint-paul",
        "le tampon", "saint-louis", "le port", "sainte-marie",
        "saint-benoît", "saint-benoit", "saint-joseph", "saint-leu",
        "sainte-suzanne", "saint-andré", "saint-andre", "bras-panon",
        "cilaos", "entre-deux", "étang-salé", "etang-sale", "petite-île",
        "la plaine-des-palmistes", "saint-philippe", "sainte-rose",
        "salazie", "les trois-bassins", "trois-bassins", "les avirons",
        "la possession", "saint-gilles", "l'hermitage", "la saline",
        "grand bois", "97400", "97410", "97411", "97412", "97413",
        "97414", "97416", "97417", "97418", "97419", "97420", "97421",
        "97422", "97423", "97424", "97425", "97426", "97427", "97428",
        "97429", "97430", "97431", "97432", "97433", "97434", "97436",
        "97437", "97438", "97439", "97440", "97441", "97442", "97450",
        "97460", "97470", "97480", "97490",
    ],
    "Mayotte": [
        "mayotte", " 976 ", "(976)", "petite-terre", "grande-terre",
        "mamoudzou", "dzaoudzi", "pamandzi", "koungou", "bandraboua",
        "bouéni", "boueni", "chiconi", "chirongui", "dembéni", "dembeni",
        "kani-kéli", "kani-keli", "mtsamboro", "m'tsangamouji", "ouangani",
        "sada", "tsingoni", "acoua",
        "97600", "97610", "97615", "97616", "97617", "97618", "97619",
        "97620", "97625", "97630", "97640", "97650", "97660", "97670",
        "97680",
    ],
    "France métropole": [
        "france", "paris", "lyon", "marseille", "bordeaux", "nantes",
        "toulouse", "lille", "strasbourg", "rennes", "nice", "montpellier",
    ],
    "Madagascar": [
        "madagascar", "antananarivo", "tamatave", "toamasina",
        "mahajanga", "fianarantsoa", "toliara",
    ],
    "Maurice": [
        "mauritius", "île maurice", "ile maurice", "port-louis",
        "port louis", "beau bassin", "curepipe", "vacoas",
    ],
    "Comores": [
        "comores", "comoros", "moroni", "anjouan", "mohéli", "moheli",
        "grande comore",
    ],
}


def _detect_domaine(title: str, description: str = "") -> str:
    t = f" {(title + ' ' + description).lower()} "
    found = [label for label, kws in DOMAINES.items() if any(_match(kw, t) for kw in kws)]
    return ", ".join(found) if found else "Autre"


def _detect_territoire(title: str, description: str = "") -> str:
    t = f" {(title + ' ' + description).lower()} "
    found = [label for label, kws in TERRITOIRES.items() if any(kw in t for kw in kws)]
    return ", ".join(found) if found else "Non précisé"


def _gonogo(score: int) -> str:
    if score >= SCORE_GO:
        return "GO"
    if score >= SCORE_ETUDE:
        return "Étudier"
    return "Passer"


def _ser_dt(dt) -> Optional[str]:
    """Sérialise un datetime en ISO-8601 ou None."""
    if dt is None:
        return None
    if hasattr(dt, "replace"):
        return dt.replace(tzinfo=None).isoformat()
    return str(dt)


def _tender_to_dict(t: Tender) -> dict:
    a = t.llm_analysis or {}
    score = a.get("score_pertinence", t.relevance_score or 0)
    domaine = _detect_domaine(t.title or "", t.description or "")
    territoire = _detect_territoire(t.title or "", t.description or "")
    jours_restants = (t.deadline - datetime.now(timezone.utc).replace(tzinfo=None)).days if t.deadline else None
    fiche_data = _compute_fiche_data(
        score, jours_restants, domaine, territoire,
        bool(t.is_maintenance), t.title or "", a
    )
    return {
        "id": t.id,
        "title": t.title or "Sans titre",
        "description": t.description or "",
        "source": t.source or "",
        "publication_date": _ser_dt(t.publication_date),
        "date_extraction": _ser_dt(t.date_extraction),
        "deadline": _ser_dt(t.deadline),
        "status": t.status or "À qualifier",
        "relevance_score": score,
        "gonogo": _gonogo(score),
        "adaptive_score": t.adaptive_score,
        "is_maintenance": bool(t.is_maintenance),
        "secteur": t.secteur or "Public",
        "type_opportunite": t.type_opportunite or "Marché Public",
        "amount": t.amount,
        "is_blacklisted": bool(t.is_blacklisted),
        "is_saved": bool(t.is_saved),
        "notes": t.notes,
        "tags": t.tags if isinstance(t.tags, list) else [],
        "domaine": domaine,
        "territoire": territoire,
        "type_marche": a.get("type_marche") or t.type_opportunite or "",
        "concurrents": ", ".join(a.get("marques_concurrentes_citees", [])),
        "llm_structured": t.llm_structured,
        "jours_restants": jours_restants,
        "fiche_data": fiche_data,
    }


# ── Scheduler jobs ───────────────────────────────────────────────────────────

def _send_daily_digest() -> None:
    """Job APScheduler — envoi digest email quotidien."""
    try:
        from email_digest import send_digest as _sd
        required = ["DIGEST_SMTP_HOST", "DIGEST_SMTP_PORT", "DIGEST_TO"]
        missing = [p for p in required if not os.getenv(p)]
        if missing:
            _log.error("Digest email: paramètres SMTP manquants: %s", missing)
            return
        cfg = {
            "host": os.getenv("DIGEST_SMTP_HOST"),
            "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
            "user": os.getenv("DIGEST_SMTP_USER"),
            "password": os.getenv("DIGEST_SMTP_PASSWORD"),
            "to": os.getenv("DIGEST_TO"),
        }
        _sd(cfg)
        _log.info("Digest quotidien envoyé")
    except Exception as exc:
        _log.error("Échec envoi digest email : %s", exc, exc_info=True)


def _weekly_adaptive_scores() -> None:
    """Job APScheduler — recalcul hebdomadaire des scores adaptatifs."""
    try:
        from score_adaptive import recompute_adaptive_scores as _r
        _r()
        _log.info("Scores adaptatifs recalculés")
    except Exception as exc:
        _log.error("Échec recalcul scores adaptatifs : %s", exc, exc_info=True)


def _weekly_source_ping() -> None:
    """Job APScheduler — ping hebdomadaire des sources."""
    try:
        from source_registry import _run_weekly_ping as _rwp
        _rwp()
    except Exception as exc:
        _log.error("Échec weekly_ping : %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────
    init_db()
    db = SessionLocal()
    try:
        n = clean_obsolete_data(db, days=30)
        if n:
            _log.info("Startup: %d tenders archivés (>30 jours)", n)
    except Exception:
        _log.warning("clean_obsolete_data échoué au démarrage", exc_info=True)
    finally:
        db.close()

    scheduler = BackgroundScheduler(
        job_defaults={"max_instances": 1, "coalesce": True}
    )
    scheduler.add_job(_weekly_source_ping, "interval", weeks=1, id="weekly_ping")
    scheduler.add_job(
        _weekly_adaptive_scores, "interval", weeks=1, id="weekly_adaptive_scores"
    )
    digest_hour = int(os.getenv("DIGEST_HOUR", "7"))
    if os.getenv("DIGEST_SMTP_HOST") and os.getenv("DIGEST_TO"):
        scheduler.add_job(
            _send_daily_digest, "cron", hour=digest_hour, minute=0, id="daily_digest"
        )
    scheduler.start()
    _log.info("Scheduler APScheduler démarré (%d jobs)", len(scheduler.get_jobs()))

    yield  # ── Application en cours ──────────────────────────────────────

    # ── Shutdown ──────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    _log.info("Scheduler APScheduler arrêté")


# ── Application ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="DEF OI — Veille Marchés API",
    description="API REST pour la veille marchés DEF Océan Indien",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Schémas Pydantic ──────────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: str

class NotesUpdate(BaseModel):
    notes: Optional[str] = None

class TagsUpdate(BaseModel):
    tags: list[str]

class AmountUpdate(BaseModel):
    amount: Optional[int] = None

class SavedUpdate(BaseModel):
    is_saved: bool

class CollectRequest(BaseModel):
    source_names: Optional[list[str]] = None  # None = toutes les sources activées


# ── GET /api/tenders ──────────────────────────────────────────────────────────

_VALID_STATUS = {"Tous", "À qualifier", "En cours", "Soumis", "Gagné", "Perdu"}
_VALID_SECTEURS = {"Public", "Privé", "International"}


@app.get("/api/tenders", summary="Liste des marchés avec filtres")
def get_tenders(
    status: str = Query("Tous", description="Filtre statut"),
    secteur: str = Query("Public", description="Public | Privé | International"),
    maintenance_only: bool = Query(False),
    date_from: Optional[str] = Query(None, description="ISO date (YYYY-MM-DD)"),
    strict_date: bool = Query(False),
    only_recent: bool = Query(False, description="Publiés dans les dernières 24h"),
    db: Session = Depends(get_db),
):
    if status not in _VALID_STATUS:
        raise HTTPException(422, f"Statut invalide : {status}")
    if secteur not in _VALID_SECTEURS:
        raise HTTPException(422, f"Secteur invalide : {secteur}")

    dt_from: Optional[datetime] = None
    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
        except ValueError:
            raise HTTPException(422, "date_from doit être au format ISO (YYYY-MM-DD)")

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

    if status != "Tous":
        q = q.filter(Tender.status == status)

    if maintenance_only:
        q = q.filter(Tender.is_maintenance == True)

    if dt_from is not None:
        if strict_date:
            q = q.filter(Tender.publication_date >= dt_from)
        else:
            q = q.filter(or_(
                Tender.publication_date >= dt_from,
                Tender.deadline >= dt_from,
                Tender.publication_date == None,
            ))

    tenders = q.order_by(Tender.deadline).all()
    return [_tender_to_dict(t) for t in tenders]


@app.get("/api/tenders/saved", summary="Marchés sauvegardés (étoile)")
def get_saved_tenders(db: Session = Depends(get_db)):
    tenders = (
        db.query(Tender)
        .filter(Tender.is_saved == True, Tender.is_blacklisted == False)
        .order_by(Tender.publication_date.desc())
        .all()
    )
    return [_tender_to_dict(t) for t in tenders]


@app.get("/api/tenders/{tender_id}", summary="Détail d'un marché")
def get_tender(tender_id: str, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    return _tender_to_dict(t)


# ── GET /api/kpis/* ───────────────────────────────────────────────────────────

@app.get("/api/kpis/public", summary="KPIs marchés publics (compteurs par statut)")
def get_kpis_public(db: Session = Depends(get_db)):
    pub_filter = or_(Tender.secteur == "Public", Tender.secteur == None)
    counts = dict(
        db.query(Tender.status, _func.count(Tender.id))
        .filter(Tender.is_blacklisted == False, pub_filter)
        .group_by(Tender.status)
        .all()
    )
    a_qualifier = counts.get("À qualifier", 0) + counts.get(None, 0)
    en_cours = counts.get("En cours", 0)
    soumis = counts.get("Soumis", 0)
    gagnes = counts.get("Gagné", 0)
    total = a_qualifier + en_cours + soumis + gagnes
    return {
        "total": total,
        "a_qualifier": a_qualifier,
        "en_cours": en_cours,
        "gagnes": gagnes,
        "soumis": soumis,
    }


@app.get("/api/kpis/ca", summary="KPIs CA pipeline (sommes montants)")
def get_kpis_ca(db: Session = Depends(get_db)):
    pub = (Tender.is_blacklisted == False, or_(Tender.secteur == "Public", Tender.secteur == None))
    sums = dict(
        db.query(Tender.status, _func.sum(Tender.amount))
        .filter(*pub, Tender.amount != None)
        .group_by(Tender.status)
        .all()
    )
    en_cours = sums.get("En cours") or 0
    soumis = sums.get("Soumis") or 0
    gagne = sums.get("Gagné") or 0
    return {
        "en_cours": en_cours,
        "soumis": soumis,
        "gagne": gagne,
        "pipeline": en_cours + soumis,
    }


@app.get("/api/kpis/priv", summary="KPIs signaux privés (compteurs par type)")
def get_kpis_priv(db: Session = Depends(get_db)):
    try:
        priv = (Tender.is_blacklisted == False, Tender.secteur == "Privé")
        type_counts = dict(
            db.query(Tender.type_opportunite, _func.count(Tender.id))
            .filter(*priv)
            .group_by(Tender.type_opportunite)
            .all()
        )
        devbanks = db.query(_func.count(Tender.id)).filter(
            *priv, Tender.type_opportunite == "Banque Dev."
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
    except Exception as exc:
        _log.error("Erreur dans /api/kpis/priv : %s", exc, exc_info=True)
        return {"permis": 0, "presse": 0, "instit": 0, "devbanks": 0, "qualif_priv": 0}


# ── GET /api/pipeline ─────────────────────────────────────────────────────────

@app.get("/api/pipeline", summary="Marchés publics groupés par statut (pipeline)")
def get_pipeline(db: Session = Depends(get_db)):
    data = load_pipeline_data(db, score_go=SCORE_GO)
    return {
        key: [
            {
                "id": t.id,
                "title": t.title or "Sans titre",
                "amount": t.amount,
                "deadline": _ser_dt(t.deadline),
                "score": t.relevance_score or 0,
            }
            for t in tenders
        ]
        for key, tenders in data.items()
    }


# ── GET /api/urgences ─────────────────────────────────────────────────────────

@app.get("/api/urgences", summary="Marchés GO avec délai imminent (<30j)")
def get_urgences(
    score_go: int = Query(SCORE_GO),
    days_ahead: int = Query(30),
    db: Session = Depends(get_db),
):
    return load_urgences(db, score_go=score_go, days_ahead=days_ahead)


# ── GET /api/chart-data ───────────────────────────────────────────────────────

@app.get("/api/chart-data", summary="Données brutes pour graphiques (publication / domaine)")
def get_chart_data(
    max_rows: int = Query(5000, le=10000),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(
            Tender.publication_date,
            Tender.title,
            Tender.description,
            Tender.secteur,
        )
        .filter(Tender.is_blacklisted == False)
        .order_by(Tender.publication_date.desc())
        .limit(max_rows)
        .all()
    )
    return [
        {
            "publication_date": _ser_dt(r.publication_date),
            "title": r.title or "",
            "description": (r.description or "")[:200],
            "secteur": r.secteur,
            "domaine": _detect_domaine(r.title or "", r.description or ""),
            "territoire": _detect_territoire(r.title or "", r.description or ""),
        }
        for r in rows
    ]


# ── GET /api/duplicates ───────────────────────────────────────────────────────

@app.get("/api/duplicates", summary="Candidats doublons non résolus")
def get_duplicates(db: Session = Depends(get_db)):
    pairs = (
        db.query(DuplicateCandidate)
        .filter(DuplicateCandidate.resolved == False)
        .order_by(DuplicateCandidate.similarity_score.desc())
        .all()
    )
    result = []
    for p in pairs:
        ta = db.query(Tender).filter(Tender.id == p.tender_id_a).first()
        tb = db.query(Tender).filter(Tender.id == p.tender_id_b).first()
        result.append({
            "id": p.id,
            "similarity_score": p.similarity_score,
            "detected_at": _ser_dt(p.detected_at),
            "tender_a": _tender_to_dict(ta) if ta else None,
            "tender_b": _tender_to_dict(tb) if tb else None,
        })
    return result


# ── GET /api/scraper-runs ─────────────────────────────────────────────────────

@app.get("/api/scraper-runs", summary="Historique des exécutions de scrapers")
def get_scraper_runs(
    limit: int = Query(50, le=500),
    db: Session = Depends(get_db),
):
    runs = (
        db.query(ScraperRun)
        .order_by(ScraperRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "source_name": r.source_name,
            "started_at": _ser_dt(r.started_at),
            "finished_at": _ser_dt(r.finished_at),
            "nb_found": r.nb_found,
            "nb_new": r.nb_new,
            "status": r.status,
            "error": r.error,
        }
        for r in runs
    ]


# ── GET /api/sources ──────────────────────────────────────────────────────────

@app.get("/api/sources", summary="Liste des sources de collecte")
def get_sources(db: Session = Depends(get_db)):
    sources = list_sources(db)
    return [
        {
            "id": s.id,
            "name": s.name,
            "url": s.url,
            "category": s.category,
            "enabled": s.enabled,
            "is_manual": s.is_manual,
            "is_validated": s.is_validated,
            "scraper_module": s.scraper_module,
            "scraper_func": s.scraper_func,
            "notes": s.notes,
            "display_order": s.display_order,
            "last_ping_at": _ser_dt(s.last_ping_at),
            "ping_failures_count": s.ping_failures_count,
        }
        for s in sources
    ]


# ── POST /api/tenders/{id}/status ────────────────────────────────────────────

_VALID_STATUSES = {"À qualifier", "En cours", "Soumis", "Gagné", "Perdu", "Archivé"}


@app.post("/api/tenders/{tender_id}/status", summary="Changer le statut d'un marché")
def update_status(
    tender_id: str,
    body: StatusUpdate,
    db: Session = Depends(get_db),
):
    if body.status not in _VALID_STATUSES:
        raise HTTPException(422, f"Statut invalide : {body.status}")
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    t.status = body.status
    db.commit()
    return {"id": tender_id, "status": t.status}


@app.post("/api/tenders/{tender_id}/notes", summary="Mettre à jour les notes")
def update_notes(tender_id: str, body: NotesUpdate, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    t.notes = body.notes or None
    db.commit()
    return {"id": tender_id, "notes": t.notes}


@app.post("/api/tenders/{tender_id}/tags", summary="Mettre à jour les tags")
def update_tags(tender_id: str, body: TagsUpdate, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    t.tags = body.tags
    db.commit()
    return {"id": tender_id, "tags": t.tags}


@app.post("/api/tenders/{tender_id}/amount", summary="Mettre à jour le montant estimé")
def update_amount(tender_id: str, body: AmountUpdate, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    t.amount = body.amount
    db.commit()
    return {"id": tender_id, "amount": t.amount}


@app.post("/api/tenders/{tender_id}/saved", summary="Basculer l'étoile (sauvegarde)")
def update_saved(tender_id: str, body: SavedUpdate, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    t.is_saved = body.is_saved
    db.commit()
    return {"id": tender_id, "is_saved": t.is_saved}


@app.delete("/api/tenders/{tender_id}", summary="Suppression douce (blacklist)")
def delete_tender(tender_id: str, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    t.is_blacklisted = True
    db.commit()
    return {"id": tender_id, "is_blacklisted": True}


# ── POST /api/tenders/{id}/analyze ───────────────────────────────────────────

@app.post("/api/tenders/{tender_id}/analyze", summary="Déclencher l'analyse LLM d'un marché")
def analyze_one(tender_id: str, db: Session = Depends(get_db)):
    t = db.query(Tender).filter(Tender.id == tender_id).first()
    if not t:
        raise HTTPException(404, "Marché introuvable")
    try:
        result = analyze_tender(
            f"{t.title or ''} {t.description or ''}",
            source_url=t.source if t.source and t.source.startswith("http") else None,
        )
    except Exception as exc:
        _log.warning("Analyse LLM échouée pour %s : %s", tender_id, type(exc).__name__)
        raise HTTPException(502, f"Analyse LLM échouée : {exc}")
    if result:
        t.llm_analysis = result
        t.relevance_score = result.get("score_pertinence", 0)
        t.is_maintenance = result.get("type_marche", "").lower() == "maintenance"
        db.commit()
    return _tender_to_dict(t)


# ── POST /api/collect ─────────────────────────────────────────────────────────

@app.post("/api/collect", summary="Lancer la collecte (toutes sources ou liste)")
def collect(body: CollectRequest, background_tasks: BackgroundTasks):
    """
    Lance les scrapers en tâche de fond et retourne immédiatement un job_id.
    Le frontend peut ensuite interroger GET /api/scraper-runs pour suivre l'avancement.
    """
    def _run_collection(source_names: Optional[list[str]]):
        db = SessionLocal()
        try:
            sources = list_sources(db)
            if source_names:
                sources = [s for s in sources if s.name in source_names]

            known_ids = {row.id for row in db.query(Tender.id).all()}
            db.close()

            for source in sources:
                if source.is_manual or not source.scraper_module:
                    continue
                if not source.enabled or not source.is_validated:
                    continue
                run_db = SessionLocal()
                run_id = start_scraper_run(run_db, source.name)
                run_db.close()
                try:
                    mod = importlib.import_module(source.scraper_module)
                    func = getattr(mod, source.scraper_func)
                    func()
                    post_db = SessionLocal()
                    try:
                        new_count = post_db.query(Tender).filter(
                            ~Tender.id.in_(known_ids)
                        ).count()
                        finish_scraper_run(post_db, run_id, nb_found=new_count, nb_new=new_count)
                    finally:
                        post_db.close()
                except Exception as exc:
                    err_db = SessionLocal()
                    finish_scraper_run(err_db, run_id, nb_found=0, nb_new=0, error=str(exc))
                    err_db.close()
                    _log.error("Erreur scraper %s : %s", source.name, exc, exc_info=True)

            # Analyse automatique post-collecte
            analysis_db = SessionLocal()
            try:
                auto_analyze_pending(analysis_db)
                auto_analyze_claude(analysis_db, max_per_run=10)
            except Exception as exc:
                _log.warning("Analyse post-collecte échouée : %s", exc, exc_info=True)
            finally:
                analysis_db.close()

        except Exception as exc:
            _log.error("Erreur globale _run_collection : %s", exc, exc_info=True)

    background_tasks.add_task(_run_collection, body.source_names)
    return {"status": "started", "message": "Collecte lancée en arrière-plan"}


# ── POST /api/analyze-pending ─────────────────────────────────────────────────

@app.post("/api/analyze-pending", summary="Analyser tous les marchés en attente (LLM)")
def analyze_pending(background_tasks: BackgroundTasks):
    def _run():
        db = SessionLocal()
        try:
            auto_analyze_pending(db)
            auto_analyze_claude(db, max_per_run=20)
        finally:
            db.close()

    background_tasks.add_task(_run)
    return {"status": "started", "message": "Analyse LLM lancée en arrière-plan"}


# ── POST /api/detect-duplicates ───────────────────────────────────────────────

@app.post("/api/detect-duplicates", summary="Détecter les doublons")
def run_detect_duplicates(db: Session = Depends(get_db)):
    n = detect_duplicates(db)
    return {"new_pairs": n}


# ── POST /api/admin/reset-db ──────────────────────────────────────────────────

@app.post("/api/admin/reset-db", summary="[DANGER] Vider tenders/runs/doublons")
def admin_reset_db(db: Session = Depends(get_db)):
    n = reset_tenders_db(db)
    return {"deleted_tenders": n, "message": "Base vidée (sources et credentials préservés)"}


# ── POST /api/admin/archive-old ───────────────────────────────────────────────

@app.post("/api/admin/archive-old", summary="Archiver les tenders À qualifier > N jours")
def admin_archive_old(days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db)):
    n = clean_obsolete_data(db, days=days)
    return {"archived": n}
