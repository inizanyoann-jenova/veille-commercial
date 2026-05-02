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


def is_construction_relevant(text: str) -> bool:
    """Retourne True si le texte mentionne un projet de construction susceptible de nécessiter du SSI/CMSI."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
