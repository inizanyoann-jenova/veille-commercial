import re as _re

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

# Pré-compilation pour éviter de recompiler à chaque appel
_COMPILED_BOUNDARY = {
    kw: _re.compile(r"\b" + _re.escape(kw) + r"\b")
    for kw in _WORD_BOUNDARY_KW
}


def classify_relevance(text: str) -> tuple[bool, list[str]]:
    """Retourne (pertinent, tags).

    tags contient ["Potentiel SSI implicite"] quand la capture est via
    la logique construction+ERP, sans mot-clé DEF OI direct.
    """
    text_lower = text.lower()

    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False, []

    for kw in INCLUSION_KEYWORDS:
        if kw in _WORD_BOUNDARY_KW:
            if _COMPILED_BOUNDARY[kw].search(text_lower):
                return True, []
        elif kw in text_lower:
            return True, []

    has_chantier = any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
    has_erp = any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)
    if has_chantier and has_erp:
        return True, ["Potentiel SSI implicite"]

    return False, []


def is_relevant_def(text: str) -> bool:
    return classify_relevance(text)[0]


def is_construction_relevant(text: str) -> bool:
    """Retourne True si le texte mentionne un projet de construction susceptible de nécessiter du SSI/CMSI."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)


def is_prive_relevant(text: str) -> bool:
    return classify_relevance(text)[0]
