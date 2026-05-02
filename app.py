from datetime import datetime

import pandas as pd
import streamlit as st

from database import SessionLocal, init_db
from export_excel import generate_executive_report
from llm_analyzer import analyze_tender
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


@st.cache_data(ttl=60)
def load_tenders(status_filter: str, maintenance_only: bool, annee_min: int) -> list[dict]:
    db = new_db()
    try:
        from sqlalchemy import or_, extract
        q = db.query(Tender)
        if status_filter != "Tous":
            q = q.filter(Tender.status == status_filter)
        if maintenance_only:
            q = q.filter(Tender.is_maintenance == True)
        # Filtre année : publication_date OU deadline dans la période
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
                    "Type": a.get("type_marche", "—"),
                    "Maint.": "✓" if t.is_maintenance else "",
                    "Concurrents": ", ".join(a.get("marques_concurrentes_citees", [])),
                }
            )
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
    st.markdown("### Sources de données")

    st.markdown("**BOAMP** — Journal Officiel")
    if st.button("🔄 Collecter BOAMP (974 & 976)", use_container_width=True):
        with st.spinner("Interrogation BOAMP…"):
            try:
                from scraper_boamp import fetch_boamp_tenders
                count = fetch_boamp_tenders()
                st.cache_data.clear()
                st.success(f"BOAMP : {count} nouveau(x) marché(s).")
            except Exception as exc:
                st.error(f"Erreur BOAMP : {exc}")

    st.markdown("**TED** — Appels d'offres européens")
    if st.button("🇪🇺 Collecter TED (EU)", use_container_width=True):
        with st.spinner("Interrogation TED Europe…"):
            try:
                from scraper_ted import fetch_ted_tenders
                count = fetch_ted_tenders()
                st.cache_data.clear()
                st.success(f"TED : {count} nouveau(x) marché(s).")
            except Exception as exc:
                st.error(f"Erreur TED : {exc}")

    st.markdown("**AFD** — Projets Agence Française de Développement")
    if st.button("🏗️ Collecter AFD (Océan Indien)", use_container_width=True):
        with st.spinner("Interrogation AFD OpenData…"):
            try:
                from scraper_afd import fetch_afd_projects
                count = fetch_afd_projects()
                st.cache_data.clear()
                st.success(f"AFD : {count} projet(s) importé(s).")
            except Exception as exc:
                st.error(f"Erreur AFD : {exc}")

    st.markdown("**Banque Mondiale** — Projets actifs")
    if st.button("🌐 Collecter Banque Mondiale", use_container_width=True):
        with st.spinner("Interrogation World Bank…"):
            try:
                from scraper_worldbank import fetch_worldbank_projects
                count = fetch_worldbank_projects()
                st.cache_data.clear()
                st.success(f"Banque Mondiale : {count} projet(s) importé(s).")
            except Exception as exc:
                st.error(f"Erreur BM : {exc}")

    st.markdown("**Tout collecter**")
    if st.button("⚡ Toutes les sources", use_container_width=True, type="primary"):
        with st.spinner("Collecte BOAMP + TED…"):
            total = 0
            errors = []
            for name, func_path in [
                ("BOAMP", "scraper_boamp.fetch_boamp_tenders"),
                ("TED", "scraper_ted.fetch_ted_tenders"),
                ("AFD", "scraper_afd.fetch_afd_projects"),
                ("Banque Mondiale", "scraper_worldbank.fetch_worldbank_projects"),
            ]:
                try:
                    module_name, func_name = func_path.rsplit(".", 1)
                    import importlib
                    mod = importlib.import_module(module_name)
                    total += getattr(mod, func_name)()
                except Exception as exc:
                    errors.append(f"{name} : {exc}")
            st.cache_data.clear()
            if total:
                st.success(f"{total} nouveau(x) marché(s) importé(s).")
            for err in errors:
                st.warning(err)


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
    total = db_kpi.query(Tender).count()
    a_qualifier = db_kpi.query(Tender).filter(Tender.status == "À qualifier").count()
    en_cours = db_kpi.query(Tender).filter(Tender.status == "En cours").count()
    gagnes = db_kpi.query(Tender).filter(Tender.status == "Gagné").count()
    soumis = db_kpi.query(Tender).filter(Tender.status == "Soumis").count()
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

rows = load_tenders(selected_status, maintenance_only, annee_min)

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
    st.subheader(f"📋 Marchés qualifiés ({len(rows)} résultats)")

    df = pd.DataFrame(rows)
    status_options = ["À qualifier", "En cours", "Soumis", "Gagné", "Perdu"]

    edited = st.data_editor(
        df,
        column_config={
            "ID": st.column_config.TextColumn("ID", disabled=True, width="small"),
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
        column_order=["Titre", "Source", "Territoire", "Domaine", "Score", "Date Limite", "Publication", "Statut", "Type", "Maint.", "Concurrents", "ID"],
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        key="tenders_editor",
    )

    # Persist status changes
    editor_state = st.session_state.get("tenders_editor", {})
    for row_idx, changes in editor_state.get("edited_rows", {}).items():
        if "Statut" in changes:
            save_status(df.iloc[row_idx]["ID"], changes["Statut"])
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── per-tender AI analysis ─────────────────────────────────────────────────

    st.subheader("🤖 Analyse IA d'un Marché")
    title_to_id = {r["Titre"]: r["ID"] for r in rows}
    chosen_title = st.selectbox("Sélectionner un marché", list(title_to_id.keys()))

    if chosen_title:
        chosen_id = title_to_id[chosen_title]

        if st.button("▶ Lancer l'analyse GPT", use_container_width=False):
            with st.spinner("Analyse en cours…"):
                run_analysis(chosen_id)
                st.cache_data.clear()
            st.success("Analyse enregistrée.")
            st.rerun()

        db_det = new_db()
        try:
            t = db_det.query(Tender).filter(Tender.id == chosen_id).first()
            if t and t.llm_analysis:
                a = t.llm_analysis
                m1, m2, m3 = st.columns(3)
                m1.metric("Type de marché", a.get("type_marche", "—"))
                m2.metric("Score pertinence", f"{a.get('score_pertinence', 0)} / 100")
                m3.metric("Concurrents détectés", len(a.get("marques_concurrentes_citees", [])))

                if a.get("marques_concurrentes_citees"):
                    st.write(
                        "**Marques citées :**",
                        ", ".join(a["marques_concurrentes_citees"]),
                    )
                if a.get("risques_penalites"):
                    st.warning(f"⚠️ Risques / Pénalités : {a['risques_penalites']}")
                if a.get("error"):
                    st.error(f"Erreur LLM : {a['error']}")

                if t.description:
                    with st.expander("Description complète du marché"):
                        st.write(t.description)
            elif t:
                st.info("Ce marché n'a pas encore été analysé par l'IA.")
        finally:
            db_det.close()

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
                        db_m.add(T(
                            id=tid,
                            title=m_title.strip(),
                            description=m_desc.strip(),
                            source=m_url.strip() or m_source_name,
                            publication_date=datetime.combine(m_pub_date, datetime.min.time()) if m_pub_date else None,
                            deadline=datetime.combine(m_deadline, datetime.min.time()) if m_deadline else None,
                            status="À qualifier",
                            relevance_score=0,
                            is_maintenance=False,
                            llm_analysis=None,
                        ))
                        db_m.commit()
                        st.cache_data.clear()
                        st.success(f"✅ « {m_title} » ajouté.")
                finally:
                    db_m.close()

st.markdown("---")
st.caption("DEF Océan Indien © 2025 · Outil de Veille Commerciale Interne")
