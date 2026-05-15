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
    # Validation défensive des paramètres
    score = int(score) if score is not None else 0
    score = max(0, min(100, score))
    domaine    = str(domaine or "")
    territoire = str(territoire or "")
    title      = str(title or "")
    a          = a if isinstance(a, dict) else {}
    if jours_restants is not None:
        jours_restants = int(jours_restants)

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
    _KW_TITRE = [
        "ssi", "cmsi", "détection", "alarme incendie", "désenfumage",
        "vidéosurveillance", "cctv", "courants faibles",
    ]
    _hits_titre = sum(1 for kw in _KW_TITRE if kw in title_l)
    if _hits_titre >= 3:
        sk = 15
    elif _hits_titre == 2:
        sk = 10
    elif _hits_titre == 1:
        sk = 6
    else:
        sk = 0
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

    atouts: list = []
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
    risques: list = []
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
