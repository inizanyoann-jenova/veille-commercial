from datetime import datetime

import pandas as pd
import streamlit as st

from database import SessionLocal, init_db
from export_excel import generate_executive_report
from llm_analyzer import analyze_tender, auto_analyze_pending
from source_registry import list_sources, add_source, remove_source, toggle_enabled
from models import Tender

# ── domaine detection ─────────────────────────────────────────────────────────

DOMAINES = {
    # SSI = systèmes électroniques de détection/alarme — PAS les extincteurs ni le génie civil
    "🔥 SSI / Détection incendie": [
        " ssi ", "ssi,", "(ssi)", "système de sécurité incendie",
        "systeme de securite incendie", "détection incendie", "detection incendie",
        "alarme incendie", "centrale incendie", "détecteur incendie",
        "detecteur incendie", "tableau de signalisation", "equipement d'alarme",
        "équipement d'alarme",
    ],
    "💨 CMSI / Désenfumage": [
        "cmsi", "désenfumage", "desenfumage", "désenfumer", "desenfumer",
        "extraction de fumée", "extraction de fumee", "évacuation de fumée",
        "evacuation de fumee", "volet de désenfumage", "volet de desenfumage",
    ],
    "📷 Vidéosurveillance / CCTV": [
        "vidéosurveillance", "videosurveillance", "cctv", "vidéo-surveillance",
        "video-surveillance", "vidéo protection", "video protection",
        "caméras de sécurité", "cameras de securite", "télésurveillance vidéo",
        "supervision vidéo",
    ],
    "⚡ Courants faibles": [
        "courants faibles", "contrôle d'accès", "controle d'acces",
        "interphonie", "gtb", "intrusion", "anti-intrusion",
    ],
}


def detect_domaine(title: str) -> str:
    t = f" {title.lower()} "
    found = []
    for label, keywords in DOMAINES.items():
        if any(kw in t for kw in keywords):
            found.append(label)
    return ", ".join(found) if found else "Autre"


# ── territoire detection ──────────────────────────────────────────────────────

TERRITOIRES = {
    "🏝️ La Réunion": [
        "la réunion", "la reunion", " 974 ", "(974)", "saint-denis", "saint-pierre",
        "saint-paul", "le port", "sainte-marie", "le tampon", "saint-benoît",
        "saint-benoit", "saint-joseph", "ile bourbon",
    ],
    "🏝️ Mayotte": [
        "mayotte", " 976 ", "(976)", "mamoudzou", "dzaoudzi", "koungou",
        "bandraboua", "petite terre",
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


def calc_score(title: str, domaine: str, territoire: str) -> int:
    """Score DEF automatique 0–100 sans GPT, basé sur domaine + territoire + mots-clés."""
    score = 0
    t = title.lower()

    # Pertinence métier (0–45)
    if "🔥 SSI" in domaine:      score += 45
    elif "💨 CMSI" in domaine:   score += 40
    elif "📷 Vidéo" in domaine:  score += 40
    elif "⚡ Courants" in domaine: score += 30
    else:                         score += 5

    # Proximité géographique (0–30)
    if "La Réunion" in territoire or "Mayotte" in territoire: score += 30
    elif "Madagascar" in territoire or "Maurice" in territoire: score += 22
    elif "Comores" in territoire:                              score += 18
    elif "France" in territoire:                              score += 10

    # Bonus mots-clés titre (0–15)
    for kw in ["ssi", "cmsi", "détection", "alarme incendie", "désenfumage",
               "vidéosurveillance", "cctv", "courants faibles"]:
        if kw in t:
            score += 15
            break

    # Bonus maintenance = client récurrent (0–10)
    if "maintenance" in t:
        score += 10

    return min(score, 100)

st.set_page_config(
    page_title="DEF OI — Veille Marchés",
    page_icon="🔥",
    layout="wide",
)

init_db()


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


# Auto-analyse au démarrage (une seule fois par session)
if "auto_analyzed" not in st.session_state:
    _run_auto_analysis()
    st.session_state["auto_analyzed"] = True


@st.cache_data(ttl=60)
def load_tenders(status_filter: str, maintenance_only: bool, annee_min: int, secteur: str = "Public") -> list[dict]:
    db = new_db()
    try:
        from sqlalchemy import or_, extract
        q = db.query(Tender)

        if secteur == "Public":
            q = q.filter(or_(Tender.secteur == "Public", Tender.secteur == None))
        elif secteur == "Privé":
            q = q.filter(Tender.secteur == "Privé")

        if status_filter != "Tous":
            q = q.filter(Tender.status == status_filter)
        if maintenance_only:
            q = q.filter(Tender.is_maintenance == True)
        if annee_min > 0:
            q = q.filter(or_(
                extract("year", Tender.publication_date) >= annee_min,
                extract("year", Tender.deadline) >= annee_min,
                Tender.publication_date == None,
            ))
        tenders = q.order_by(Tender.deadline).all()

        rows = []
        for t in tenders:
            a = t.llm_analysis or {}
            domaine = detect_domaine(t.title or "")
            territoire = detect_territoire(t.title or "", t.description or "")
            score = (
                t.relevance_score
                or a.get("score_pertinence", 0)
                or calc_score(t.title or "", domaine, territoire)
            )
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
                }
            )
        return rows
    finally:
        db.close()


def delete_tender(tender_id: str) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            db.delete(t)
            db.commit()
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


def run_analysis(tender_id: str) -> None:
    db = new_db()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if not t:
            return
        result = analyze_tender(f"{t.title or ''} {t.description or ''}")
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
                mod = importlib.import_module(source.scraper_module)
                func = getattr(mod, source.scraper_func)
                count = func()
                total += count
            except Exception as exc:
                errors.append(f"{source.name} : {exc}")

    _run_auto_analysis()
    st.cache_data.clear()
    if total:
        st.success(f"{total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée pour les sources sélectionnées.")
    for err in errors:
        st.warning(err)


with st.sidebar:
    st.markdown("## 🔥 DEF Océan Indien")
    st.markdown("**Veille Marchés Publics**")
    st.markdown("---")

    current_year = datetime.now().year
    periode_labels = {
        f"Depuis {current_year} (cette année)": current_year,
        f"Depuis {current_year - 1} (2 ans)": current_year - 1,
        f"Depuis {current_year - 2} (3 ans)": current_year - 2,
        "Tout afficher": 0,
    }
    selected_periode = st.selectbox(
        "Période",
        list(periode_labels.keys()),
        index=1,  # défaut : 2 ans
    )
    annee_min = periode_labels[selected_periode]

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
    selected_status = st.selectbox(
        "Filtrer par statut",
        ["Tous", "À qualifier", "En cours", "Soumis", "Gagné", "Perdu"],
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
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(
                        f"<span style='color:grey;font-size:0.9em'>☐ {s.name}</span>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    st.link_button("🔗", url=s.url, help=f"Ouvrir {s.url}")
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


# ── header + export ───────────────────────────────────────────────────────────

st.title("🔥 DEF Océan Indien — Veille Marchés Publics")
st.caption(
    "Périmètre : La Réunion (974) & Mayotte (976) · SSI · CMSI · Détection incendie · Vidéosurveillance"
)

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

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total", total)
c2.metric("À qualifier", a_qualifier)
c3.metric("En cours", en_cours)
c4.metric("Soumis", soumis)
c5.metric("Gagnés 🏆", gagnes)

st.markdown("---")

# ── interactive table ─────────────────────────────────────────────────────────

rows = load_tenders(selected_status, maintenance_only, annee_min, secteur="Public")

# Filtres territoire côté affichage
terr_actifs = selected_territoires[:]
if selected_groupe != "Tous":
    terr_actifs = list(set(terr_actifs + GROUPES[selected_groupe]))
if terr_actifs:
    rows = [r for r in rows if any(t in r["Territoire"] for t in terr_actifs)]
if selected_domaines:
    rows = [r for r in rows if any(d in r["Domaine"] for d in selected_domaines)]

if not rows:
    st.info(
        "Aucun marché trouvé. Lancez la collecte depuis le menu latéral, "
        "ou ajustez les filtres."
    )
else:
    st.subheader(f"📋 Marchés qualifiés ({len(rows)} résultats) — cochez pour supprimer")

    df = pd.DataFrame(rows)
    df.insert(0, "🗑️", False)
    status_options = ["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]

    edited = st.data_editor(
        df,
        column_config={
            "🗑️": st.column_config.CheckboxColumn("🗑️", width="small"),
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Go/No-Go": st.column_config.TextColumn("Décision", width="small", disabled=True),
            "Titre": st.column_config.TextColumn("Titre du Marché", width="large"),
            "Source": st.column_config.LinkColumn("Source", width="small"),
            "Territoire": st.column_config.TextColumn("Territoire", width="medium", disabled=True),
            "Domaine": st.column_config.TextColumn("Domaine", width="medium", disabled=True),
            "Score": st.column_config.NumberColumn(
                "Score DEF", min_value=0, max_value=100, width="small"
            ),
            "Date Limite": st.column_config.TextColumn("Date Limite", width="small"),
            "Publication": st.column_config.TextColumn("Publication", width="small"),
            "Statut": st.column_config.SelectboxColumn(
                "Statut", options=status_options, width="medium"
            ),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Maint.": st.column_config.TextColumn("Maint.", width="small", disabled=True),
            "Concurrents": st.column_config.TextColumn("Concurrents", width="medium"),
        },
        column_order=["🗑️", "Go/No-Go", "Titre", "Source", "Territoire", "Domaine", "Score", "Date Limite", "Publication", "Statut", "Type", "Maint.", "Concurrents", "ID"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="tenders_editor",
    )

    # Suppression des lignes cochées
    to_delete_pub = edited[edited["🗑️"] == True]["ID"].tolist()
    if to_delete_pub:
        if st.button(f"🗑️ Supprimer {len(to_delete_pub)} marché(s) sélectionné(s)", type="secondary"):
            for tid in to_delete_pub:
                delete_tender(tid)
            st.cache_data.clear()
            st.rerun()

    # Persist status changes
    editor_state = st.session_state.get("tenders_editor", {})
    for row_idx, changes in editor_state.get("edited_rows", {}).items():
        if "Statut" in changes:
            save_status(df.iloc[row_idx]["ID"], changes["Statut"])
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── per-tender AI analysis ─────────────────────────────────────────────────

    st.subheader("📋 Fiche commerciale")
    title_to_id = {r["Titre"]: r["ID"] for r in rows}
    chosen_title = st.selectbox("Sélectionner un marché", list(title_to_id.keys()))

    if chosen_title:
        chosen_id = title_to_id[chosen_title]
        db_det = new_db()
        try:
            t = db_det.query(Tender).filter(Tender.id == chosen_id).first()
            if t:
                a = t.llm_analysis or {}
                domaine = detect_domaine(t.title or "")
                territoire = detect_territoire(t.title or "", t.description or "")
                score = t.relevance_score or a.get("score_pertinence", 0) or calc_score(t.title or "", domaine, territoire)
                decision = _gonogo(score)

                # Bandeau Go/No-Go
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
                m1.metric("Type", a.get("type_marche", "—"))
                m2.metric("Score DEF", f"{score} / 100")
                m3.metric("Concurrents", len(a.get("marques_concurrentes_citees", [])))
                m4.metric("Maintenance", "Oui" if t.is_maintenance else "Non")

                if a.get("marques_concurrentes_citees"):
                    st.write("**Marques concurrentes citées :**", ", ".join(a["marques_concurrentes_citees"]))
                if a.get("risques_penalites"):
                    st.warning(f"⚠️ Risques / Pénalités : {a['risques_penalites']}")

                source = a.get("_source", "local")
                if source == "gemini":
                    st.caption("🤖 Analyse Gemini (score combiné 70 % IA + 30 % règles métier)")
                else:
                    st.caption("🔍 Analyse locale (règles métier DEF — Gemini indisponible ou quota dépassé)")

                if t.description:
                    with st.expander("Description complète du marché"):
                        st.write(t.description)
        finally:
            db_det.close()

st.markdown("---")

# ── section marché privé ──────────────────────────────────────────────────────

st.subheader("🏗️ Signaux & Opportunités Marché Privé")
st.caption("Sources : Permis de construire · Presse locale IO · Institutions · Banques de développement")

rows_priv = load_tenders(selected_status, maintenance_only, annee_min, secteur="Privé")

if terr_actifs:
    rows_priv = [r for r in rows_priv if any(t in r["Territoire"] for t in terr_actifs)]
if selected_domaines:
    rows_priv = [r for r in rows_priv if any(d in r["Domaine"] for d in selected_domaines)]

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
    nb_qualif = db_priv.query(Tender).filter(
        Tender.secteur == "Privé", Tender.status == "À qualifier"
    ).count()
finally:
    db_priv.close()

kp1, kp2, kp3, kp4, kp5 = st.columns(5)
kp1.metric("Permis construire", nb_permis)
kp2.metric("Articles presse", nb_presse)
kp3.metric("Institutions", nb_instit)
kp4.metric("Banques Dev.", nb_devbanks)
kp5.metric("À qualifier", nb_qualif)

if not rows_priv:
    st.info("Aucun signal privé. Lancez la collecte Permis / Presse / Banques Dev. depuis le menu latéral.")
else:
    st.caption(f"{len(rows_priv)} signal(s) affiché(s) — cochez pour supprimer")
    df_priv = pd.DataFrame(rows_priv)
    df_priv.insert(0, "🗑️", False)

    edited_priv = st.data_editor(
        df_priv,
        column_config={
            "🗑️": st.column_config.CheckboxColumn("🗑️", width="small"),
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
            "Go/No-Go": st.column_config.TextColumn("Décision", width="small", disabled=True),
            "Titre": st.column_config.TextColumn("Titre", width="large"),
            "Source": st.column_config.LinkColumn("Source", width="small"),
            "Territoire": st.column_config.TextColumn("Territoire", width="medium", disabled=True),
            "Domaine": st.column_config.TextColumn("Domaine", width="medium", disabled=True),
            "Score": st.column_config.NumberColumn("Score", min_value=0, max_value=100, width="small"),
            "Date Limite": st.column_config.TextColumn("Date Limite", width="small"),
            "Publication": st.column_config.TextColumn("Publication", width="small"),
            "Statut": st.column_config.SelectboxColumn(
                "Statut", options=["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"], width="medium"
            ),
            "Type": st.column_config.TextColumn("Type", width="small", disabled=True),
            "Maint.": st.column_config.TextColumn("Maint.", width="small", disabled=True),
            "Concurrents": st.column_config.TextColumn("Concurrents", width="medium"),
        },
        column_order=["🗑️", "Go/No-Go", "Titre", "Source", "Territoire", "Domaine", "Type", "Score", "Publication", "Statut", "Maint.", "Concurrents", "ID"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="priv_editor",
    )

    # Suppression des lignes cochées
    to_delete = edited_priv[edited_priv["🗑️"] == True]["ID"].tolist()
    if to_delete:
        if st.button(f"🗑️ Supprimer {len(to_delete)} signal(s) sélectionné(s)", type="secondary"):
            for tid in to_delete:
                delete_tender(tid)
            st.cache_data.clear()
            st.rerun()

    # Persistance des changements de statut
    editor_state_priv = st.session_state.get("priv_editor", {})
    for row_idx, changes in editor_state_priv.get("edited_rows", {}).items():
        if "Statut" in changes:
            save_status(df_priv.iloc[row_idx]["ID"], changes["Statut"])
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── fiche commerciale privé ────────────────────────────────────────────────
    st.subheader("📋 Fiche commerciale — Signal privé")
    title_to_id_priv = {r["Titre"]: r["ID"] for r in rows_priv}
    chosen_priv = st.selectbox("Sélectionner un signal", list(title_to_id_priv.keys()), key="sel_priv")

    if chosen_priv:
        chosen_priv_id = title_to_id_priv[chosen_priv]
        db_fp = new_db()
        try:
            t = db_fp.query(Tender).filter(Tender.id == chosen_priv_id).first()
            if t:
                a = t.llm_analysis or {}
                domaine = detect_domaine(t.title or "")
                territoire = detect_territoire(t.title or "", t.description or "")
                score = t.relevance_score or a.get("score_pertinence", 0) or calc_score(t.title or "", domaine, territoire)
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
                m1.metric("Type signal", a.get("type_marche") or t.type_opportunite or "—")
                m2.metric("Score DEF", f"{score} / 100")
                m3.metric("Concurrents", len(a.get("marques_concurrentes_citees", [])))
                m4.metric("Maintenance", "Oui" if t.is_maintenance else "Non")

                if a.get("marques_concurrentes_citees"):
                    st.write("**Marques concurrentes citées :**", ", ".join(a["marques_concurrentes_citees"]))
                if a.get("risques_penalites"):
                    st.warning(f"⚠️ Risques / Pénalités : {a['risques_penalites']}")

                if t.description:
                    with st.expander("Description complète du signal"):
                        st.write(t.description)
        finally:
            db_fp.close()

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
                import hashlib as _hl
                tid = "MANUAL-" + _hl.md5(f"{m_title}{m_url}{m_deadline}".encode()).hexdigest()[:10]
                db_m = new_db()
                try:
                    if db_m.query(Tender).filter(Tender.id == tid).first():
                        st.warning("Cette opportunité existe déjà.")
                    else:
                        from models import Tender as T
                        analyse = analyze_tender(f"{m_title.strip()} {m_desc.strip()}")
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
st.caption("DEF Océan Indien © 2025 · Outil de Veille Commerciale Interne")
