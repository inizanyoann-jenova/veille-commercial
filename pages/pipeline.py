from datetime import date

import streamlit as st

from database import SessionLocal, init_db, load_pipeline_data
from models import Tender

st.set_page_config(page_title="Pipeline — DEF OI", page_icon="📋", layout="wide")
init_db()

st.markdown("# 📋 Pipeline commercial")
st.caption("Vue Kanban des marchés en cours — transitions de statut en un clic")
st.markdown("---")


def _jours_badge(deadline) -> tuple[str, str]:
    if deadline is None:
        return "⚫ pas de deadline", "#f3f4f6"
    today = date.today()
    dl_date = deadline.date() if hasattr(deadline, "date") else deadline
    days = (dl_date - today).days
    if days < 0:
        return f"⚠️ {abs(days)}j dépassé", "#fef2f2"
    if days < 7:
        return f"🔴 {days}j", "#fef2f2"
    if days <= 30:
        return f"🟡 {days}j", "#fffbeb"
    return f"🟢 {days}j", "#f0fdf4"


def _set_status(tender_id: str, new_status: str):
    db = SessionLocal()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.status = new_status
            db.commit()
    finally:
        db.close()
    st.cache_data.clear()
    st.rerun()


def _card(t: Tender):
    import html as _html
    badge, bg = _jours_badge(t.deadline)
    title_short = _html.escape(t.title[:60]) + ("…" if len(t.title) > 60 else "")
    st.markdown(
        f'<div style="background:{bg};border:1px solid #e5e7eb;border-radius:8px;'
        f'padding:10px;margin-bottom:6px;font-size:0.82rem">'
        f'<strong>{title_short}</strong><br>'
        f'{badge} · Score : {t.relevance_score}</div>',
        unsafe_allow_html=True,
    )


db = SessionLocal()
try:
    data = load_pipeline_data(db)
finally:
    db.close()

col_go, col_soumis, col_results = st.columns(3)

with col_go:
    st.markdown(f"### ✅ GO ({len(data['go'])})")
    if not data["go"]:
        st.caption("Aucun marché GO en cours.")
    for t in data["go"]:
        _card(t)
        if st.button("Marquer Soumis", key=f"soumis_{t.id}"):
            _set_status(t.id, "Soumis")

with col_soumis:
    st.markdown(f"### 📤 Soumis ({len(data['soumis'])})")
    if not data["soumis"]:
        st.caption("Aucune offre soumise en cours.")
    for t in data["soumis"]:
        _card(t)
        c1, c2 = st.columns(2)
        if c1.button("Gagné 🏆", key=f"gagne_{t.id}"):
            _set_status(t.id, "Gagné")
        if c2.button("Perdu", key=f"perdu_{t.id}"):
            _set_status(t.id, "Perdu")

with col_results:
    st.markdown("### 🏆 Résultats")
    gagnes = [t for t in data["resultats"] if t.status == "Gagné"]
    perdus = [t for t in data["resultats"] if t.status == "Perdu"]
    if not gagnes and not perdus:
        st.caption("Aucun résultat enregistré.")
    if gagnes:
        st.markdown("**Gagné**")
        for t in gagnes:
            _card(t)
    if perdus:
        st.markdown("**Perdu**")
        for t in perdus:
            _card(t)

st.markdown("---")
st.page_link("app.py", label="← Retour à la veille marchés")
