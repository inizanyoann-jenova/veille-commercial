INCLUSION_KEYWORDS = [
    "ssi",
    "cmsi",
    "détection incendie",
    "désenfumage",
    "vidéosurveillance",
    "cctv",
    "caméras",
    "courants faibles",
]

EXCLUSION_KEYWORDS = [
    "gardiennage",
    "agents de sécurité",
    "télésurveillance",
    "maître-chien",
    "ssiap",
    "sécurité civile",
]

KEYWORDS_CONSTRUCTION = [
    "construction", "chantier", "permis de construire", "projet immobilier",
    "immeuble", "résidence", "hôtel", "hôpital", "clinique", "ehpad",
    "école", "lycée", "université", "centre commercial", "mall",
    "entrepôt", "usine", "réhabilitation", "rénovation", "extension",
    "bâtiment", "programme immobilier", "logements", "infrastructure",
    "complexe", "siège social", "campus", "promotion immobilière",
    "lotissement", "résidence étudiante", "résidence sénior",
]


def is_relevant_def(text: str) -> bool:
    text_lower = text.lower()
    for keyword in EXCLUSION_KEYWORDS:
        if keyword in text_lower:
            return False
    for keyword in INCLUSION_KEYWORDS:
        if keyword in text_lower:
            return True
    return False


# ERP et bâtiments à forte obligation SSI — signal ciblé pour DEF OI
KEYWORDS_ERP_CIBLES = [
    "hôpital", "hopital", "clinique", "ehpad", "maison de retraite",
    "hôtel", "hotel", "résidence hôtelière", "resort",
    "école", "ecole", "lycée", "lycee", "collège", "college", "université", "universite",
    "centre commercial", "mall", "galerie marchande",
    "salle de sport", "gymnase", "stade", "arena",
    "centre culturel", "théâtre", "theatre", "cinéma", "cinema",
    "immeuble de bureaux", "siège social", "siège",
    "entrepôt logistique", "entrepot", "usine",
    "résidence étudiante", "campus", "internat",
    "aéroport", "aeroport", "gare", "port maritime", "port de pêche", "port de commerce",
    "centre de données", "data center",
    "mairie", "préfecture", "tribunal", "commissariat",
]


def is_construction_relevant(text: str) -> bool:
    """Retourne True si le texte mentionne un projet de construction susceptible de nécessiter du SSI/CMSI."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)


def is_prive_relevant(text: str) -> bool:
    """Filtre marché privé DEF OI : article sur SSI/CMSI/vidéo OU projet ERP à fort potentiel SSI."""
    text_lower = text.lower()
    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False
    if any(kw in text_lower for kw in INCLUSION_KEYWORDS):
        return True
    return any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)
