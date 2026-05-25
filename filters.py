import re as _re

# Mots déclencheurs directs — équipements DEF OI
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
    "robinet incendie arm",  # préfixe : couvre armé / armés
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
    # Contrôle d'accès (souvent bundlé avec CCTV)
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
    # Intrusion (souvent couplé)
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
    # ── Maintenance SSI / réglementaire ───────────────────────────────────────
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
    # Conformité réglementaire (déclencheurs d'obligation SSI)
    "mise en conformité",
    "dta",
    "dossier technique amiante",
]

# Exclusions absolues — hors périmètre DEF OI
EXCLUSION_KEYWORDS = [
    # Sécurité humaine (gardiens, agents)
    "gardiennage",
    "agents de sécurité",
    "agent de sécurité",
    "agent de surveillance",
    "rondes de surveillance",
    "surveillance humaine",
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
    # Environnement / voirie (sans lien avec bâtiment)
    "espaces verts",
    "voirie",
    "assainissement",
    "eau potable",
    "collecte des déchets",
    "déchèterie",
]

# Indicateurs de projet de construction ou réhabilitation
# (condition NÉCESSAIRE pour les signaux presse/institution)
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

# Types d'ERP / bâtiments à obligation SSI
# (condition NÉCESSAIRE pour les signaux presse/institution)
KEYWORDS_ERP_CIBLES = [
    # Santé
    "hôpital",
    "hopital",
    "clinique",
    "ehpad",
    "maison de retraite",
    "résidence seniors",
    "établissement de santé",
    "maison de santé",
    "centre de soins",
    "centre médical",
    "dispensaire",
    # Hébergement / hôtellerie
    "hôtel",
    "hotel",
    "résidence hôtelière",
    "resort",
    "résidence de tourisme",
    # Enseignement
    "école",
    "ecole",
    "lycée",
    "lycee",
    "collège",
    "college",
    "université",
    "universite",
    "résidence étudiante",
    "campus",
    "internat",
    "crèche",
    "creche",
    "halte-garderie",
    "halte garderie",
    # Commerce / logistique
    "centre commercial",
    "mall",
    "galerie marchande",
    "marché couvert",
    "entrepôt logistique",
    "entrepot",
    "usine",
    # Sport / loisirs
    "salle de sport",
    "gymnase",
    "stade",
    "arena",
    "piscine",
    "centre aquatique",
    "base nautique",
    # Culture
    "centre culturel",
    "théâtre",
    "theatre",
    "cinéma",
    "cinema",
    "musée",
    "musee",
    "bibliothèque",
    "bibliotheque",
    "médiathèque",
    "mediatheque",
    "salle des fêtes",
    "salle polyvalente",
    # Bureaux / administration
    "immeuble de bureaux",
    "siège social",
    "bâtiment administratif",
    "mairie",
    "préfecture",
    "sous-préfecture",
    "tribunal",
    "commissariat",
    "caserne",
    "foyer",
    # Logement social
    "logement social",
    "hlm",
    "office hlm",
    "résidence sociale",
    # Transport / data
    "aéroport",
    "aeroport",
    "gare",
    "port maritime",
    "centre de données",
    "data center",
]


_WORD_BOUNDARY_KW = {"ssi", "cmsi", "cctv", "ria", "gtb", "gtc", "bms", "mco", "vdi", "nvr", "dvr"}

# Pré-compilation pour éviter de recompiler à chaque appel
_COMPILED_BOUNDARY = {
    kw: _re.compile(r"\b" + _re.escape(kw) + r"\b") for kw in _WORD_BOUNDARY_KW
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

    # Logique assouplie : construction seule = potentiel SSI pour ERP publics
    if has_chantier:
        if has_erp:
            return True, ["Potentiel SSI implicite"]
        # Ajout : tout projet de construction dans 974/976 est potentiellement pertinent
        if (
            "974" in text_lower
            or "976" in text_lower
            or "réunion" in text_lower
            or "mayotte" in text_lower
        ):
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
