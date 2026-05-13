# Mots déclencheurs directs — équipements DEF OI
INCLUSION_KEYWORDS = [
    "ssi",
    "cmsi",
    "détection incendie",
    "désenfumage",
    "vidéosurveillance",
    "cctv",
    "caméras de sécurité",
    "courants faibles",
    "alarme incendie",
    "système incendie",
]

# Exclusions absolues — hors périmètre DEF OI
EXCLUSION_KEYWORDS = [
    "gardiennage",
    "agents de sécurité",
    "télésurveillance",
    "maître-chien",
    "ssiap",
    "sécurité civile",
    # Contenu scolaire/culturel sans lien avec la construction
    "livres scolaires",
    "manuels scolaires",
    "fournitures scolaires",
    "rentrée scolaire",
    "prix littéraire",
    "concours littéraire",
    # RH / social
    "offre d'emploi",
    "aide sociale",
    "allocation",
    "bourse scolaire",
]

# Indicateurs de projet de construction ou réhabilitation
# (condition NÉCESSAIRE pour les signaux presse/institution)
KEYWORDS_CONSTRUCTION = [
    "construction", "chantier", "travaux", "permis de construire",
    "réhabilitation", "rénovation", "extension", "restructuration",
    "aménagement", "programme immobilier", "promotion immobilière",
    "lotissement", "inauguration", "pose de la première pierre",
    "mise en service", "nouveau bâtiment", "nouvelle construction",
    "projet de construction", "maître d'ouvrage", "maîtrise d'ouvrage",
    "financement construction", "investissement immobilier",
    "bâtiment neuf", "immeuble neuf",
]

# Types d'ERP / bâtiments à obligation SSI
# (condition NÉCESSAIRE pour les signaux presse/institution)
KEYWORDS_ERP_CIBLES = [
    "hôpital", "hopital", "clinique", "ehpad", "maison de retraite",
    "hôtel", "hotel", "résidence hôtelière", "resort",
    "école", "ecole", "lycée", "lycee", "collège", "college",
    "université", "universite", "centre commercial", "mall",
    "galerie marchande", "salle de sport", "gymnase", "stade", "arena",
    "centre culturel", "théâtre", "theatre", "cinéma", "cinema",
    "immeuble de bureaux", "siège social", "entrepôt logistique",
    "entrepot", "usine", "résidence étudiante", "campus", "internat",
    "aéroport", "aeroport", "gare", "port maritime",
    "centre de données", "data center",
    "mairie", "préfecture", "tribunal", "commissariat", "centre médical",
    "dispensaire",
]


_WORD_BOUNDARY_KW = {"ssi", "cmsi", "cctv"}


def is_relevant_def(text: str) -> bool:
    import re
    text_lower = text.lower()
    for keyword in EXCLUSION_KEYWORDS:
        if keyword in text_lower:
            return False
    for keyword in INCLUSION_KEYWORDS:
        if keyword in _WORD_BOUNDARY_KW:
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
                return True
        elif keyword in text_lower:
            return True
    return False


def is_construction_relevant(text: str) -> bool:
    """Retourne True si le texte mentionne un projet de construction susceptible de nécessiter du SSI/CMSI."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)


def is_prive_relevant(text: str) -> bool:
    """Filtre marché privé DEF OI.

    Pertinent si :
    1. Mention directe d'un équipement DEF OI (SSI, CMSI, vidéosurveillance...), OU
    2. Article sur un projet de construction/réhabilitation d'un ERP ciblé.
       → Les DEUX conditions (indicateur de chantier + type d'ERP) doivent être réunies.
       Un article sur les livres scolaires mentionne "école" mais pas "chantier" → rejeté.
    """
    text_lower = text.lower()

    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False

    # Cas 1 : mention directe d'un équipement DEF OI
    if any(kw in text_lower for kw in INCLUSION_KEYWORDS):
        return True

    # Cas 2 : projet de construction d'un ERP (les deux ensemble obligatoire)
    has_projet = any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
    has_erp = any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)
    return has_projet and has_erp
