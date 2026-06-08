import re as _re

# Mots déclencheurs directs — équipements ATEXIA
INCLUSION_KEYWORDS = [
    # ── SSI — signaux directs ──────────────────────────────────────────────────
    "ssi",
    "système de sécurité incendie",
    "alarme incendie",
    "alarme anti-incendie",
    "système incendie",
    "sécurité incendie",
    "protection incendie",
    "centrale incendie",
    "tableau de signalisation",
    # Détecteurs
    "détection incendie",
    "détecteur de fumée",
    "détecteurs de fumée",
    "détecteur thermique",
    "détecteurs thermiques",
    "détecteur incendie",
    "détecteurs incendie",
    "tête de détection",
    "têtes de détection",
    # Déclencheurs / diffuseurs
    "déclencheur manuel",
    "déclencheurs manuels",
    "diffuseur sonore",
    "diffuseurs sonores",
    "flash lumineux",
    "flash incendie",
    # Extinction / compartimentage
    "extinction incendie",
    "extinction automatique",
    "sprinkler",
    "porte coupe-feu",
    "portes coupe-feu",
    "compartimentage",
    "compartimentage incendie",
    "évacuation incendie",
    # Équipements complémentaires SSI
    "ria",
    "robinet incendie arm",
    "robinets incendie arm",
    "baas",
    "bloc autonome alarme",
    "blocs autonomes alarme",
    # ── CMSI / Désenfumage ─────────────────────────────────────────────────────
    "cmsi",
    "désenfumage",
    "centrale de mise en sécurité",
    "mise en sécurité incendie",
    "volet de désenfumage",
    "volets de désenfumage",
    "trappe de désenfumage",
    "trappes de désenfumage",
    "exutoire de fumée",
    "exutoires de fumée",
    "extracteur de fumée",
    "extracteurs de fumée",
    "désenfumage naturel",
    "désenfumage mécanique",
    "denfc",
    "dmfc",
    # ── Vidéosurveillance / CCTV ───────────────────────────────────────────────
    "cctv",
    "vidéosurveillance",
    "vidéo surveillance",
    "vidéoprotection",
    "vidéo protection",
    "système de vidéosurveillance",
    "système de vidéoprotection",
    "caméras de sécurité",
    "caméra de surveillance",
    "caméras de surveillance",
    "caméra ip",
    "caméras ip",
    "caméra thermique",
    "caméras thermiques",
    "télésurveillance",
    "nvr",
    "dvr",
    # Contrôle d'accès
    "contrôle d'accès",
    "controle d'acces",
    "système de contrôle d'accès",
    "lecteur de badge",
    "lecteurs de badge",
    "badge d'accès",
    "interphonie",
    "interphone",
    "visiophone",
    "portier vidéo",
    "vidéo portier",
    "sûreté électronique",
    "sureté électronique",
    "sécurité électronique",
    # Intrusion
    "alarme intrusion",
    "détection intrusion",
    "anti-intrusion",
    "système anti-intrusion",
    "système d'alarme",
    # ── Courants faibles / GTB ─────────────────────────────────────────────────
    "courants faibles",
    "courant faible",
    "gtb",
    "gtc",
    "bms",
    "gestion technique bâtiment",
    "gestion technique du bâtiment",
    "building management",
    "câblage structuré",
    "cablage structure",
    "vdi",
    "voix données images",
    "réseau de communication",
    "domotique",
    "automatisme bâtiment",
    "tableau de communication",
    "armoire de brassage",
    "baie de brassage",
    # ── Courants forts / Génie électrique ────────────────────────────────────
    "courants forts",
    "génie électrique",
    "genie electrique",
    "installation électrique",
    "installations électriques",
    "travaux électriques",
    "tgbt",
    "tableau général basse tension",
    "armoire électrique",
    "armoires électriques",
    "distribution basse tension",
    "coffret électrique",
    "coffrets électriques",
    "tableau divisionnaire",
    "tableaux divisionnaires",
    "disjoncteur",
    "câblage électrique",
    "cablage electrique",
    # ── Continuité d'énergie ─────────────────────────────────────────────────
    "groupe électrogène",
    "groupes électrogènes",
    "onduleur",
    "onduleurs",
    "ups",
    "asi",
    "alimentation sans interruption",
    "continuité d'énergie",
    "secours électrique",
    "alimentation de secours",
    # ── Éclairage ────────────────────────────────────────────────────────────
    "relamping",
    "éclairage intérieur",
    "éclairage led",
    "mise aux normes électriques",
    "nf c 15-100",
    "nfc 15-100",
    "éclairage de sécurité",
    "balisage lumineux",
    "éclairage de balisage",
    # ── IRVE — bornes de recharge ────────────────────────────────────────────
    "irve",
    "borne de recharge",
    "bornes de recharge",
    "recharge véhicule électrique",
    "infrastructure de recharge",
    "point de charge",
    "station de recharge",
    # ── Énergie renouvelable / photovoltaïque ────────────────────────────────
    "photovoltaïque",
    "photovoltaique",
    "panneaux solaires",
    "panneau solaire",
    "centrale solaire",
    "autoconsommation",
    "stockage énergie",
    "batterie solaire",
    "ombrière photovoltaïque",
    "ombriere photovoltaique",
    "enr",
    # ── Efficacité énergétique / réglementaire ───────────────────────────────
    "décret tertiaire",
    "decret tertiaire",
    "operat",
    "performance énergétique",
    "audit énergétique",
    "audit energetique",
    "bilan énergétique",
    "rénovation énergétique",
    "efficacité énergétique",
    "cee",
    # ── Réseau / infrastructures numériques ──────────────────────────────────
    "fibre optique",
    "réseau informatique",
    "baie informatique",
    "réseau local",
    "lan",
    "câblage réseau",
    "infrastructure réseau",
    # ── Maintenance SSI / réglementaire ──────────────────────────────────────
    "mco ssi",
    "mco",
    "maintenance ssi",
    "contrat de maintenance ssi",
    "contrat de maintenance",
    "maintien en condition opérationnelle",
    "maintenance préventive",
    "maintenance corrective",
    "vérification annuelle",
    "vérification réglementaire",
    "vérification périodique",
    "vérification et maintenance",
    "maintenance et vérification",
    "télémaintenance",
    # Conformité réglementaire
    "mise en conformité",
    "dta",
    "dossier technique amiante",
]

# Exclusions absolues — hors périmètre ATEXIA
EXCLUSION_KEYWORDS = [
    "gardiennage",
    "agents de sécurité",
    "agent de sécurité",
    "agent de surveillance",
    "rondes de surveillance",
    "surveillance humaine",
    "maître-chien",
    "ssiap",
    "sécurité civile",
    "livres scolaires",
    "manuels scolaires",
    "fournitures scolaires",
    "rentrée scolaire",
    "prix littéraire",
    "concours littéraire",
    "offre d'emploi",
    "aide sociale",
    "allocation",
    "bourse scolaire",
    "espaces verts",
    "voirie",
    "assainissement",
    "eau potable",
    "collecte des déchets",
    "déchèterie",
]

KEYWORDS_CONSTRUCTION = [
    "construction",
    "chantier",
    "travaux",
    "permis de construire",
    "réhabilitation",
    "rénovation",
    "extension",
    "restructuration",
    "aménagement",
    "programme immobilier",
    "promotion immobilière",
    "lotissement",
    "inauguration",
    "pose de la première pierre",
    "mise en service",
    "nouveau bâtiment",
    "nouvelle construction",
    "projet de construction",
    "maître d'ouvrage",
    "maîtrise d'ouvrage",
    "financement construction",
    "investissement immobilier",
    "bâtiment neuf",
    "immeuble neuf",
    "opération immobilière",
    "programme de construction",
    "zac",
]

KEYWORDS_ERP_CIBLES = [
    "hôpital", "hopital", "clinique", "ehpad", "maison de retraite",
    "résidence seniors", "établissement de santé", "maison de santé",
    "centre de soins", "centre médical", "dispensaire",
    "hôtel", "hotel", "résidence hôtelière", "resort", "résidence de tourisme",
    "école", "ecole", "lycée", "lycee", "collège", "college",
    "université", "universite", "résidence étudiante", "campus",
    "internat", "crèche", "creche", "halte-garderie", "halte garderie",
    "centre commercial", "mall", "galerie marchande", "marché couvert",
    "entrepôt logistique", "entrepot", "usine",
    "salle de sport", "gymnase", "stade", "arena", "piscine",
    "centre aquatique", "base nautique",
    "centre culturel", "théâtre", "theatre", "cinéma", "cinema",
    "musée", "musee", "bibliothèque", "bibliotheque",
    "médiathèque", "mediatheque", "salle des fêtes", "salle polyvalente",
    "immeuble de bureaux", "siège social", "bâtiment administratif",
    "mairie", "préfecture", "sous-préfecture", "tribunal",
    "commissariat", "caserne", "foyer",
    "logement social", "hlm", "office hlm", "résidence sociale",
    "aéroport", "aeroport", "gare", "port maritime",
    "centre de données", "data center",
]

# Acteurs locaux La Réunion — renforcent le score géographique
_ACTEURS_LOCAUX_974 = [
    "shlmr", "sidr", "semader", "sedre", "chu réunion", "chu reunion",
    "chor", "cinor", "tco", "civis", "cirest",
]

_WORD_BOUNDARY_KW = {
    "ssi", "cmsi", "cctv", "ria", "gtb", "gtc", "bms", "mco", "vdi",
    "nvr", "dvr", "ups", "asi", "irve", "enr", "cee", "lan", "tgbt",
}

_COMPILED_BOUNDARY = {
    kw: _re.compile(r"\b" + _re.escape(kw) + r"\b") for kw in _WORD_BOUNDARY_KW
}


def classify_relevance(text: str) -> tuple[bool, list[str]]:
    """Retourne (pertinent, tags).

    tags contient ["Potentiel SSI implicite"] quand la capture est via
    la logique construction+ERP, sans mot-clé ATEXIA direct.
    """
    text_lower = text.lower()

    for kw in INCLUSION_KEYWORDS:
        if kw in _WORD_BOUNDARY_KW:
            if _COMPILED_BOUNDARY[kw].search(text_lower):
                return True, []
        elif kw in text_lower:
            return True, []

    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False, []

    has_chantier = any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
    has_erp = any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)
    has_acteur_local = any(kw in text_lower for kw in _ACTEURS_LOCAUX_974)

    if has_chantier:
        if has_erp:
            return True, ["Potentiel SSI implicite"]
        if (
            "974" in text_lower
            or "réunion" in text_lower
            or has_acteur_local
        ):
            return True, ["Potentiel SSI implicite"]

    return False, []


def is_relevant_def(text: str) -> bool:
    return classify_relevance(text)[0]


def is_construction_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)


def is_prive_relevant(text: str) -> bool:
    return classify_relevance(text)[0]
