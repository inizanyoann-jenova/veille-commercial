from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
from sqlalchemy import func
import streamlit as st

from database import SessionLocal, init_db
from fiche_logic import SCORE_GO
from models import Tender


# ── Fonctions de données pures (testables sans Streamlit) ─────────────────────

def _load_direction_kpis_data(db) -> dict:
    nb_actifs = db.query(Tender).filter(
        Tender.is_blacklisted == False,
        Tender.relevance_score >= SCORE_GO,
        Tender.status.notin_(["Gagné", "Perdu"]),
    ).count()

    ca_prev = db.query(func.sum(Tender.amount)).filter(
        Tender.is_blacklisted == False,
        Tender.status.in_(["Soumis", "En cours"]),
        Tender.amount != None,
    ).scalar() or 0

    ca_gagne = db.query(func.sum(Tender.amount)).filter(
        Tender.is_blacklisted == False,
        Tender.status == "Gagné",
        Tender.amount != None,
    ).scalar() or 0

    nb_soumis = db.query(Tender).filter(
        Tender.is_blacklisted == False, Tender.status == "Soumis"
    ).count()
    nb_gagne = db.query(Tender).filter(
        Tender.is_blacklisted == False, Tender.status == "Gagné"
    ).count()
    taux = round(nb_gagne / nb_soumis * 100) if nb_soumis > 0 else None

    return {
        "nb_actifs": nb_actifs,
        "ca_previsionnel": ca_prev,
        "ca_gagne": ca_gagne,
        "taux_conversion": taux,
    }


def _load_activity_90d_data(db) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=90)
    rows = db.query(Tender.publication_date, Tender.status).filter(
        Tender.is_blacklisted == False,
        Tender.publication_date >= cutoff,
        Tender.publication_date != None,
    ).all()

    buckets: dict[str, int] = {}
    for pub, status in rows:
        week = pub.strftime("%Y-W%W")
        buckets[week] = buckets.get(week, 0) + 1

    return [{"semaine": w, "count": c} for w, c in sorted(buckets.items())]


def _load_pipeline_direction_data(db) -> list:
    return (
        db.query(Tender)
        .filter(
            Tender.is_blacklisted == False,
            Tender.relevance_score >= SCORE_GO,
            Tender.status.notin_(["Gagné", "Perdu"]),
        )
        .order_by(Tender.deadline.asc().nullslast())
        .all()
    )
