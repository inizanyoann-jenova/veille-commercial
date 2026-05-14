# Fiche Marché — Refonte Layout Vertical Plat

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer les 6 blocs de colonnes imbriquées de la fiche marché par un layout vertical plat ordonné par priorité décisionnelle.

**Architecture:** Extraire la logique métier de `_render_strategic_analysis()` dans `fiche_logic.py` (pure, sans Streamlit, testable). `app.py` importe depuis `fiche_logic.py`. `_render_fiche()` est réécrite pour consommer cette logique et afficher les 6 blocs en vertical. `_render_strategic_analysis()` est supprimée.

**Tech Stack:** Python 3.11+, Streamlit, pytest (tests dans `tests/`)

---

## Fichiers touchés

| Fichier | Action | Détail |
|---|---|---|
| `fiche_logic.py` | Créer | `SCORE_GO`, `SCORE_ETUDE`, `_compute_fiche_data()` |
| `app.py` | Modifier | Importer depuis `fiche_logic`, supprimer `_render_strategic_analysis`, réécrire `_render_fiche` |
| `tests/test_fiche.py` | Créer | 34 tests de `_compute_fiche_data` |

---

### Task 1 : Créer `fiche_logic.py` avec `_compute_fiche_data()` (TDD)

**Files:**
- Create: `fiche_logic.py`
- Create: `tests/test_fiche.py`

---

- [ ] **Étape 1 — Écrire les tests dans `tests/test_fiche.py`**

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fiche_logic import _compute_fiche_data


# ── label_action & steps ─────────────────────────────────────────────────────

def test_go_deadline_passe():
    d = _compute_fiche_data(70, -3, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "⚠️ Date limite dépassée"
    assert len(d["steps"]) == 2

def test_go_delai_critique():
    d = _compute_fiche_data(70, 5, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🚨 Action immédiate — délai critique"
    assert len(d["steps"]) == 4

def test_go_priorite():
    d = _compute_fiche_data(70, 20, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🟢 Traiter en priorité"

def test_go_planifier():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🟢 Planifier la réponse"

def test_etude():
    d = _compute_fiche_data(50, 30, "Autre", "Non précisé", False, "", {})
    assert d["label_action"] == "🟡 À évaluer — décision requise"

def test_passer():
    d = _compute_fiche_data(10, None, "Autre", "Non précisé", False, "", {})
    assert d["label_action"] == "🔴 Hors périmètre DEF OI"


# ── sous-scores sm / sg / sk / smaint ────────────────────────────────────────

def test_sm_ssi():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "Non précisé", False, "", {})
    assert d["sm"] == 45

def test_sm_cmsi():
    d = _compute_fiche_data(70, None, "💨 CMSI / Désenfumage", "Non précisé", False, "", {})
    assert d["sm"] == 40

def test_sm_video():
    d = _compute_fiche_data(70, None, "📷 Vidéosurveillance / CCTV", "Non précisé", False, "", {})
    assert d["sm"] == 40

def test_sm_courants():
    d = _compute_fiche_data(70, None, "⚡ Courants faibles", "Non précisé", False, "", {})
    assert d["sm"] == 30

def test_sm_autre():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "", {})
    assert d["sm"] == 5

def test_sg_reunion():
    d = _compute_fiche_data(70, None, "Autre", "🏝️ La Réunion", False, "", {})
    assert d["sg"] == 30

def test_sg_mayotte():
    d = _compute_fiche_data(70, None, "Autre", "🏝️ Mayotte", False, "", {})
    assert d["sg"] == 30

def test_sg_madagascar():
    d = _compute_fiche_data(70, None, "Autre", "🌍 Madagascar", False, "", {})
    assert d["sg"] == 22

def test_sg_france():
    d = _compute_fiche_data(70, None, "Autre", "🇫🇷 France métropole", False, "", {})
    assert d["sg"] == 10

def test_sg_inconnu():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "", {})
    assert d["sg"] == 0

def test_sk_ssi_in_title():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Installation SSI bâtiment", {})
    assert d["sk"] == 15

def test_sk_cmsi_in_title():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Marché CMSI désenfumage", {})
    assert d["sk"] == 15

def test_sk_absent():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Nettoyage parkings", {})
    assert d["sk"] == 0

def test_smaint_true():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", True, "", {})
    assert d["smaint"] == 10

def test_smaint_false():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "", {})
    assert d["smaint"] == 0


# ── atouts ────────────────────────────────────────────────────────────────────

def test_atout_coeur_metier_ssi():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "Non précisé", False, "", {})
    assert any("Cœur de métier" in a for a in d["atouts"])

def test_atout_coeur_metier_video():
    d = _compute_fiche_data(70, None, "📷 Vidéosurveillance / CCTV", "Non précisé", False, "", {})
    assert any("Cœur de métier" in a for a in d["atouts"])

def test_atout_perimetre_courants():
    d = _compute_fiche_data(70, None, "⚡ Courants faibles", "Non précisé", False, "", {})
    assert any("Périmètre DEF OI" in a for a in d["atouts"])

def test_atout_presence_locale_974():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert any("974/976" in a for a in d["atouts"])

def test_atout_ocean_indien():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "🌍 Madagascar", False, "", {})
    assert any("Océan Indien" in a for a in d["atouts"])

def test_atout_maintenance():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "Non précisé", True, "", {})
    assert any("Maintenance" in a for a in d["atouts"])

def test_atout_signal_direct():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Mise en place SSI", {})
    assert any("Signal direct" in a for a in d["atouts"])

def test_atout_pertinence_limitee_si_aucun():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Nettoyage", {})
    assert any("Pertinence limitée" in a for a in d["atouts"])
    assert len(d["atouts"]) == 1


# ── risques ───────────────────────────────────────────────────────────────────

def test_risque_concurrent():
    a = {"marques_concurrentes_citees": ["Siemens", "Bosch"]}
    d = _compute_fiche_data(70, 30, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", a)
    assert any("Siemens" in r for r in d["risques"])

def test_risque_delai_court():
    d = _compute_fiche_data(70, 7, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert any("Délai très court" in r for r in d["risques"])

def test_risque_penalites():
    a = {"risques_penalites": "Pénalités de retard élevées"}
    d = _compute_fiche_data(70, 30, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", a)
    assert any("Pénalités" in r for r in d["risques"])

def test_risque_vide_si_tout_ok():
    d = _compute_fiche_data(70, 60, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["risques"] == []
```

- [ ] **Étape 2 — Vérifier que les tests échouent (module absent)**

```
pytest tests/test_fiche.py -v
```
Résultat attendu : `ModuleNotFoundError: No module named 'fiche_logic'`

- [ ] **Étape 3 — Créer `fiche_logic.py`**

```python
SCORE_GO = 65
SCORE_ETUDE = 35


def _compute_fiche_data(
    score: int,
    jours_restants: int | None,
    domaine: str,
    territoire: str,
    is_maintenance: bool,
    title: str,
    a: dict,
) -> dict:
    """Logique métier de la fiche marché — aucun appel Streamlit."""
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

    title_l = title.lower()
    sk = 15 if any(kw in title_l for kw in [
        "ssi", "cmsi", "détection", "alarme incendie", "désenfumage",
        "vidéosurveillance", "cctv", "courants faibles",
    ]) else 0
    smaint = 10 if is_maintenance else 0

    if score >= SCORE_GO:
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
    elif score >= SCORE_ETUDE:
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

    atouts: list[str] = []
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

    concurrents = a.get("marques_concurrentes_citees", [])
    risques: list[str] = []
    if concurrents:
        risques.append(f"⚠️ Concurrents nommés dans le DCE : {', '.join(concurrents[:4])}")
    if a.get("risques_penalites"):
        risques.append(f"⚠️ {a['risques_penalites']}")
    if jours_restants is not None and 0 <= jours_restants <= 14:
        risques.append("⚠️ Délai très court — risque de réponse technique insuffisante")

    return {
        "sm": sm, "sg": sg, "sk": sk, "smaint": smaint,
        "label_action": label_action, "steps": steps,
        "atouts": atouts, "risques": risques,
    }
```

- [ ] **Étape 4 — Vérifier que les tests passent**

```
pytest tests/test_fiche.py -v
```
Résultat attendu : 34 tests passent (aucun FAIL).

- [ ] **Étape 5 — Commit**

```bash
git add fiche_logic.py tests/test_fiche.py
git commit -m "feat: fiche_logic.py — _compute_fiche_data() pure function + 34 tests"
```

---

### Task 2 : Modifier `app.py` — importer depuis `fiche_logic`, supprimer `_render_strategic_analysis`, réécrire `_render_fiche`

**Files:**
- Modify: `app.py`

---

- [ ] **Étape 1 — Remplacer les constantes locales par l'import de `fiche_logic`**

Dans `app.py`, remplacer les lignes 30–31 :

```python
SCORE_GO = 65
SCORE_ETUDE = 35
```

par :

```python
from fiche_logic import SCORE_GO, SCORE_ETUDE, _compute_fiche_data
```

- [ ] **Étape 2 — Supprimer `_render_strategic_analysis()` (L395–636)**

Dans `app.py`, supprimer entièrement la fonction `_render_strategic_analysis` — depuis la ligne `def _render_strategic_analysis(t, a: dict, domaine: str, territoire: str, score: int) -> None:` jusqu'à la dernière ligne de son corps (la ligne `st.info("Consulter directement la plateforme source pour accéder au cahier des charges complet.")`).

Après suppression, la ligne immédiatement suivante doit être `# Auto-analyse au démarrage (une seule fois par session)`.

- [ ] **Étape 3 — Remplacer `_render_fiche()` par le nouveau corps**

Localiser la fonction `_render_fiche` (commence par `def _render_fiche(tender_id: str, key_suffix: str) -> None:`). Remplacer l'intégralité de la fonction par :

```python
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
    finally:
        db_det.close()
```

- [ ] **Étape 4 — Vérifier qu'aucun test existant n'est cassé**

```
pytest tests/ -v
```
Résultat attendu : tous les tests passent. Vérifier notamment que `tests/test_fiche.py` (34 tests) est inclus.

- [ ] **Étape 5 — Vérifier que `_render_strategic_analysis` n'est plus référencée dans `app.py`**

```
grep -n "_render_strategic_analysis" app.py
```
Résultat attendu : aucune ligne trouvée.

- [ ] **Étape 6 — Commit**

```bash
git add app.py
git commit -m "refactor: fiche marché layout vertical plat — supprime colonnes imbriquées"
```

---

## Résumé des changements

| Avant | Après |
|---|---|
| `_render_strategic_analysis()` — 240 lignes, 3 blocs de colonnes imbriquées | Supprimée |
| `_render_fiche()` — 67 lignes | Remplacée, absorbe toute la logique en 6 blocs verticaux |
| Logique plan d'action / atouts / risques embarquée dans le rendu UI | `fiche_logic._compute_fiche_data()` — 34 tests |
| `SCORE_GO / SCORE_ETUDE` dupliqués dans `app.py` et `analytics.py` | Source unique dans `fiche_logic.py`, `app.py` importe |
| Justification affichée 2 fois | Affichée 1 fois (caption Bloc 1) |
| Bouton Réanalyser après les notes | Bouton Réanalyser avant les notes |
