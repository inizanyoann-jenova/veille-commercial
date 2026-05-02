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


def is_relevant_def(text: str) -> bool:
    text_lower = text.lower()

    for keyword in EXCLUSION_KEYWORDS:
        if keyword in text_lower:
            return False

    for keyword in INCLUSION_KEYWORDS:
        if keyword in text_lower:
            return True

    return False
