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


# ── Génération PDF ────────────────────────────────────────────────────────────

def generate_direction_pdf(kpis: dict, activity_data: list, pipeline: list) -> bytes:
    """Génère le rapport Direction en PDF. Retourne les bytes du fichier."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # En-tête
    story.append(Paragraph("DEF Océan Indien", styles["Title"]))
    story.append(Paragraph("Rapport Direction — Pipeline Commercial", styles["Heading2"]))
    story.append(Paragraph(datetime.now().strftime("Généré le %d/%m/%Y"), styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    # KPIs
    kpi_table_data = [
        ["Opportunités actives", "CA prévisionnel", "CA gagné", "Taux conversion"],
        [
            str(kpis.get("nb_actifs", "—")),
            f"{kpis.get('ca_previsionnel', 0):,.0f} €".replace(",", " ") if kpis.get("ca_previsionnel") else "—",
            f"{kpis.get('ca_gagne', 0):,.0f} €".replace(",", " ") if kpis.get("ca_gagne") else "—",
            f"{kpis.get('taux_conversion')} %" if kpis.get("taux_conversion") is not None else "—",
        ],
    ]
    kpi_t = Table(kpi_table_data, colWidths=[4.2 * cm] * 4)
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cc2222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 0.5 * cm))

    # Graphique activité (si kaleido disponible)
    if activity_data:
        try:
            import plotly.express as px
            import plotly.io as pio
            from io import BytesIO as _BytesIO
            from reportlab.platypus import Image as _RLImage
            import pandas as pd
            import threading

            _df = pd.DataFrame(activity_data)
            _fig = px.bar(_df, x="semaine", y="count", color_discrete_sequence=["#cc2222"])
            _fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=0, r=0))
            # Thread daemon avec timeout pour kaleido (évite les blocages)
            _result: list = []
            _err: list = []

            def _render():
                try:
                    _result.append(pio.to_image(_fig, format="png", width=700, height=220))
                except Exception as e:
                    _err.append(e)

            _t = threading.Thread(target=_render, daemon=True)
            _t.start()
            _t.join(timeout=20)
            if _result:
                story.append(_RLImage(_BytesIO(_result[0]), width=16 * cm, height=5 * cm))
                story.append(Spacer(1, 0.3 * cm))
            # si timeout ou erreur → on saute le graphique silencieusement
        except Exception:
            pass  # kaleido absent ou erreur inattendue → on saute le graphique

    # Tableau pipeline
    if pipeline:
        story.append(Paragraph("Pipeline en cours", styles["Heading3"]))
        pipe_data = [["Titre", "Statut", "Deadline", "Montant"]]
        for t in pipeline[:20]:
            pipe_data.append([
                (t.title or "")[:55],
                t.status,
                t.deadline.strftime("%d/%m/%Y") if t.deadline else "—",
                f"{t.amount:,} €".replace(",", " ") if t.amount else "—",
            ])
        pipe_t = Table(pipe_data, colWidths=[9 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        pipe_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(pipe_t)

    doc.build(story)
    return buffer.getvalue()


# ── Page Streamlit ────────────────────────────────────────────────────────────

st.set_page_config(page_title="Direction — DEF OI", page_icon="📊", layout="wide")

@st.cache_resource
def _ensure_db_init():
    init_db()

_ensure_db_init()

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

st.markdown("# 📊 Direction — DEF OI")
st.caption("Vue exécutive — Pipeline commercial")
st.markdown("---")


@st.cache_data(ttl=120)
def _load_direction_kpis():
    db = SessionLocal()
    try:
        return _load_direction_kpis_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_activity_90d():
    db = SessionLocal()
    try:
        return _load_activity_90d_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_pipeline_direction():
    db = SessionLocal()
    try:
        return _load_pipeline_direction_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Bloc 1 : KPIs ─────────────────────────────────────────────────────────────

_kpis = _load_direction_kpis()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Opportunités actives", _kpis["nb_actifs"])
k2.metric("CA prévisionnel", f"{_kpis['ca_previsionnel']:,.0f} €".replace(",", " ") if _kpis["ca_previsionnel"] else "—")
k3.metric("CA Gagné 🏆", f"{_kpis['ca_gagne']:,.0f} €".replace(",", " ") if _kpis["ca_gagne"] else "—")
k4.metric("Taux conversion", f"{_kpis['taux_conversion']} %" if _kpis["taux_conversion"] is not None else "—")

st.markdown("---")

# ── Bloc 2 : Activité 90 jours ────────────────────────────────────────────────

st.markdown("### 📅 Activité — 90 derniers jours")
_activity = _load_activity_90d()
if _activity:
    _df_act = pd.DataFrame(_activity)
    _fig = px.bar(
        _df_act, x="semaine", y="count",
        labels={"semaine": "Semaine", "count": "Marchés collectés"},
        color_discrete_sequence=["#cc2222"],
    )
    _fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=0, r=0), height=250)
    st.plotly_chart(_fig, use_container_width=True)
else:
    st.caption("Aucune donnée d'activité sur 90 jours.")

st.markdown("---")

# ── Bloc 3 : Tableau pipeline ─────────────────────────────────────────────────

st.markdown("### 📋 Pipeline en cours")
_pipeline = _load_pipeline_direction()
if _pipeline:
    _df_pipe = pd.DataFrame([{
        "Titre": (t.title or "")[:60],
        "Statut": t.status,
        "Deadline": t.deadline.strftime("%d/%m/%Y") if t.deadline else "—",
        "Montant estimé": f"{t.amount:,} €".replace(",", " ") if t.amount else "—",
        "Source": t.source or "—",
    } for t in _pipeline])
    st.dataframe(_df_pipe, use_container_width=True, hide_index=True)
else:
    st.caption("Aucun marché GO ou Soumis en cours.")

st.markdown("---")

# ── Bloc 4 : Export PDF ───────────────────────────────────────────────────────

if st.button("📄 Télécharger le rapport PDF"):
    with st.spinner("Génération du PDF…"):
        _pdf = generate_direction_pdf(_kpis, _activity, _pipeline)
    _date = datetime.now().strftime("%Y%m%d")
    st.download_button(
        label="⬇️ Télécharger",
        data=_pdf,
        file_name=f"Rapport_Direction_DEF_{_date}.pdf",
        mime="application/pdf",
    )

st.page_link("app.py", label="← Retour à la veille marchés")
