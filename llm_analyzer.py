import hashlib
import html
import json
import logging
import os
import re
import threading
import time

from dotenv import load_dotenv

_log = logging.getLogger(__name__)
load_dotenv()


class _LLMQuotaError(Exception):
    """Levée quand l'API LLM retourne une erreur de quota (429 / RESOURCE_EXHAUSTED)."""
    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after  # secondes avant de pouvoir réessayer, None si inconnu

# ---------------------------------------------------------------------------
# Listes de marques concurrentes
# ---------------------------------------------------------------------------

_MARQUES_SSI = [
    "notifier", "hochiki", "apollo", "cerberus", "esser", "edwards", "kidde",
    "aritech", "autronica", "fireclass", "finsecur", "morley", "advanced",
    "nittan", "mircom", "napco", "c-tec", "tyco", "siemens", "bosch",
    "honeywell", "johnson controls", "ge security", "est3",
    "cooper", "gewiss", "daitem", "legrand", "sorhea",
]
_MARQUES_VIDEO = [
    "axis", "hikvision", "dahua", "hanwha", "avigilon", "genetec", "milestone",
    "pelco", "vivotek", "mobotix", "verkada", "ubiquiti", "sony", "panasonic",
    "bosch", "flir", "i-pro", "uniview", "reolink",
]
_MARQUES_ACCES = [
    "hid", "lenel", "assa abloy", "dorma", "kaba", "paxton", "suprema",
    "zkteco", "came", "bft", "cdvi", "fermax", "urmet", "aiphone",
]
_MARQUES_TOUTES = _MARQUES_SSI + _MARQUES_VIDEO + _MARQUES_ACCES

# ---------------------------------------------------------------------------
# Mots-clés métier
# ---------------------------------------------------------------------------

_KW_MAINTENANCE = [
    "maintenance", "entretien", "vérification", "verification", "contrat de maintenance",
    "mco", "maintien en condition", "préventif", "correctif", "gmao",
    "télémaintenance", "telemaintenance", "dépannage", "depannage",
    "intervention sur site", "contrat de service", "vérification périodique",
    "verification periodique", "passage annuel", "contrat annuel",
    "visite de maintenance", "visite technique", "ronde technique",
    "télésurveillance", "telesurveillance", "astreinte",
]
_KW_TRAVAUX = [
    "installation", "fourniture et pose", "travaux", "mise en place",
    "réalisation", "construction", "extension", "rénovation", "renovation",
    "remplacement", "mise aux normes", "fourniture", "pose et raccordement",
    "déploiement", "deploiement", "mise en conformité", "mise en conformite",
    "création", "creation", "équipement", "equipement",
]
_KW_PENALITES = [
    "pénalité", "penalite", "pénalités de retard", "retenue de garantie",
    "dommages et intérêts", "pfa", "p.f.a.", "délai contractuel",
    "garantie décennale", "décennale", "responsabilité civile",
    "clause résolutoire", "défaillance",
]

# SSI — toute la chaîne technique : centrales, détecteurs, déclencheurs, SMSI, etc.
_KW_SSI = [
    r"\bssi\b", r"\bsmsi\b", r"\bsdi\b", r"\bdai\b",
    "détection incendie", "detection incendie",
    "alarme incendie", "désenfumage", "desenfumage",
    "évacuation incendie", "evacuation incendie",
    "centrale incendie", "tableau de signalisation incendie",
    "détecteur incendie", "detecteur incendie",
    "détecteur de fumée", "detecteur de fumee",
    "détecteur optique", "détecteur thermique", "détecteur de chaleur",
    "détecteur adressable", "detecteur adressable",
    "déclencheur manuel", "declencheur manuel", r"\bdmc\b",
    "diffuseur d'alarme", "diffuseur sonore", "sirène incendie",
    "système de sécurité incendie", "systeme de securite incendie",
    "système de mise en sécurité incendie", "systeme de mise en securite incendie",
    "boucle incendie", "ligne de détection", "report d'alarme incendie",
    "unité de signalisation", "équipement d'alarme", "equipement d'alarme",
    r"\bsprinkler\b", "extinction automatique", "nf s 61",
    r"\bcategorie a\b", r"\bcategorie b\b", r"\bcategorie c\b",
    "catégorie a", "catégorie b", "catégorie c",
    # types d'alarme — retirés car trop génériques
    "commission de sécurité incendie",
]

# CMSI / Désenfumage — extracteurs, volets, exutoires, etc.
_KW_CMSI = [
    r"\bcmsi\b", "désenfumage", "desenfumage", "désenfumer", "desenfumer",
    "extraction de fumée", "extraction de fumee",
    "évacuation de fumée", "evacuation de fumee",
    "volet de désenfumage", "volet de desenfumage",
    "exutoire", "extracteur de fumée", "extracteur de fumee",
    "désenfumage naturel", "desenfumage naturel",
    "désenfumage mécanique", "desenfumage mecanique",
    "amenée d'air", "amenee d'air", "balayage d'air",
    "commande de désenfumage", "commande de desenfumage",
    "volet coupe-feu", "volet coupe feu", "clapet coupe-feu",
    "porte coupe-feu", "porte coupe feu",
    "compartimentage", "compartimentage au feu",
]

# Vidéosurveillance — caméras, enregistreurs, VMS, analytics
_KW_VIDEO = [
    "vidéosurveillance", "videosurveillance", r"\bcctv\b",
    "caméras de sécurité", "cameras de securite",
    "vidéo protection", "video protection", "télésurveillance vidéo",
    "supervision vidéo", r"\bnvr\b", r"\bdvr\b", r"\bvms\b",
    "caméra ip", "camera ip", "enregistreur vidéo", "enregistreur video",
    r"\bptz\b", "caméra dôme", "camera dome", "caméra thermique",
    "analytics vidéo", "analyse vidéo", "gestion vidéo",
    "lecture de plaques", r"\blpr\b", "reconnaissance de plaques",
    "caméra grand angle", "caméra panoramique",
    "vidéo-protection", "vidéo-surveillance",
]

# Courants faibles — contrôle d'accès, interphonie, GTB, intrusion, badge
_KW_COURANTS_FAIBLES = [
    "courants faibles", "contrôle d'accès", "controle d'acces",
    r"\binterphonie\b", r"\bgtb\b", r"\bgtc\b", "anti-intrusion",
    r"\bbadge\b", "badgeuse", "lecteur de badge", "carte d'accès",
    "digicode", "visiophone", "portier vidéo", "portier video",
    "portier électronique", "portier electronique",
    "alarme intrusion", "détection intrusion", "detection intrusion",
    "gestion technique du bâtiment", "gestion technique du batiment",
    "supervision bâtiment", "supervision batiment",
    "câblage courants faibles", "cablage courants faibles",
    "gestion technique aéroport", "gestion technique avancée",  # remplace \bgta\b trop ambigu
    "télégestion", "telegestion",
]

# QHSE / réglementation ERP
_KW_QHSE = [
    "qhse", "qualité hygiène sécurité", "audit incendie",
    "formation sécurité incendie", "formation securite incendie",
    "document unique", "commission de sécurité",
    "registre de sécurité", "plan de prévention",
    "astreinte incendie", "exercice d'évacuation",
    "chef de sécurité incendie", "sécurité incendie réglementaire",
]

# ERP — bâtiments qui imposent légalement le SSI (Code de la construction)
_KW_ERP = [
    r"\berp\b", "établissement recevant du public", "etablissement recevant du public",
    r"\bchu\b", r"\bchrs\b", r"\bchru\b", "centre hospitalier", r"\behpad\b", "maison de retraite",
    "hôpital", "hopital", "clinique", "polyclinique",
    "école", "ecole", "collège", "college", "lycée", "lycee",
    "université", "universite", "campus universitaire",
    "mairie", "hôtel de ville", "hotel de ville",
    "préfecture", "prefecture", "sous-préfecture",
    "tribunal", "palais de justice",
    "musée", "musee", "bibliothèque", "bibliotheque",
    "médiathèque", "mediatheque",
    "centre commercial", "galerie marchande",
    r"\bhôtel\b", r"\bhotel\b", "résidence hôtelière", "auberge",
    "centre sportif", "gymnase", "piscine", r"\bstade\b",
    "salle polyvalente", "salle des fêtes", "salle de spectacle",
    "cinéma", "cinema", "théâtre", "theatre",
    "bâtiment public", "batiment public", "infrastructure publique",
    "immeuble de grande hauteur", r"\bigh\b",
    "résidence universitaire", "foyer de jeunes", r"\bfji\b",
    "centre pénitentiaire", "maison d'arrêt",
    "aéroport", "aeroport", "gare", "port",
]

# Exclusions — marchés clairement hors périmètre DEF OI
_KW_EXCLUSION = [
    "gardiennage", "agent de sécurité", "agents de sécurité",
    r"\bssiap\b", "surveillance humaine", "rondes de sécurité",
    "sécurité civile", r"\bpompiers\b", "sapeurs-pompiers",
    "génie civil", "genie civil", r"\bvrd\b",
    "terrassement", "fouille", "excavation",
    r"\bmaçonnerie\b", r"\bmaconnerie\b", "gros oeuvre",
    "charpente métallique", "charpente bois",
    "plomberie", "sanitaire", "réseau d'eau",
    r"\bchauffage\b", r"\bcvc\b",  # attention : ne pas exclure si CMSI présent
    r"\bhta\b", r"\bhtb\b", "haute tension",
    "poste de transformation", "transformateur électrique",
    "éclairage public", "eclairage public", "lampadaire",
    "voirie", "bitumage", "enrobé",
    "cuisines", "cuisine professionnelle", "équipement de cuisine",
    "blanchisserie", "pressing",
    "ascenseur", "monte-charge", "élévateur",  # sauf si avec courants faibles
]

_KW_TERRITOIRE_REUNION = [
    "réunion", "reunion", "974",
    # Communes
    "saint-denis", "saint-paul", "saint-pierre", "le tampon", "saint-louis",
    "le port", "sainte-marie", "saint-benoît", "saint-benoit", "saint-joseph",
    "saint-leu", "sainte-suzanne", "saint-andré", "saint-andre",
    "bras-panon", "cilaos", "entre-deux", "l'étang-salé", "étang-salé",
    "petite-île", "petite ile", "la plaine-des-palmistes",
    "saint-philippe", "sainte-rose", "salazie", "les trois-bassins",
    "trois bassins", "les avirons", "la possession", "l'île-en-bois",
    "saint-gilles", "l'hermitage", "la saline", "grand bois",
    "ile bourbon", "ile de la reunion",
    # Codes postaux Réunion
    "97400", "97410", "97411", "97412", "97413", "97414", "97416",
    "97417", "97418", "97419", "97420", "97421", "97422", "97423",
    "97424", "97425", "97426", "97427", "97428", "97429", "97430",
    "97431", "97432", "97433", "97434", "97436", "97437", "97438",
    "97439", "97440", "97441", "97442", "97450", "97460", "97470",
    "97480", "97490",
]
_KW_TERRITOIRE_MAYOTTE = [
    "mayotte", "976",
    # Communes
    "mamoudzou", "dzaoudzi", "pamandzi", "koungou", "bandraboua",
    "bouéni", "boueni", "chiconi", "chirongui", "dembéni", "dembeni",
    "kani-kéli", "kani-keli", "mtsamboro", "m'tsangamouji", "ouangani",
    "sada", "tsingoni", "acoua", "petite-terre", "grande-terre",
    # Codes postaux Mayotte
    "97600", "97610", "97615", "97616", "97617", "97618", "97619",
    "97620", "97625", "97630", "97640", "97650", "97660", "97670",
    "97680",
]
_KW_TERRITOIRE_IO = [
    "madagascar", "antananarivo", "tamatave", "toamasina",
    "maurice", "mauritius", "île maurice", "ile maurice", "port-louis",
    "comores", "comoros", "moroni", "anjouan", "mohéli", "moheli",
]


def _match(kw: str, text: str) -> bool:
    if kw.startswith(r"\b"):
        return bool(re.search(kw, text))
    return kw in text


def _score_to_tag(score: int) -> str:
    if score >= 65:
        return "Très pertinent"
    elif score >= 35:
        return "À évaluer"
    return "Hors périmètre"


# ---------------------------------------------------------------------------
# Analyse locale (règles métier — sans API, toujours disponible)
# ---------------------------------------------------------------------------

_local_cache: dict[str, tuple[dict, float]] = {}
_local_cache_lock = threading.Lock()
_LOCAL_CACHE_TTL = 3600  # 1 heure
_LOCAL_CACHE_MAX = 512


def _local_analyze(text: str) -> dict:
    # MD5 non-sécuritaire suffit pour une clé de cache (usedforsecurity=False)
    text_key = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
    now = time.time()
    with _local_cache_lock:
        entry = _local_cache.get(text_key)
        if entry is not None:
            result, ts = entry
            if now - ts < _LOCAL_CACHE_TTL:
                return result.copy()
    result = _local_analyze_impl(text[:6000])
    with _local_cache_lock:
        _local_cache[text_key] = (result, now)
        # Éviction O(N) remplacée : on purge toutes les entrées expirées en une passe,
        # et seulement si on dépasse le seuil après purge, on retire la plus ancienne.
        if len(_local_cache) > _LOCAL_CACHE_MAX:
            expired = [k for k, (_, ts) in _local_cache.items() if now - ts >= _LOCAL_CACHE_TTL]
            for k in expired:
                del _local_cache[k]
            if len(_local_cache) > _LOCAL_CACHE_MAX:
                oldest = min(_local_cache, key=lambda k: _local_cache[k][1])
                del _local_cache[oldest]
    return result.copy()


def _count_keyword_matches(text: str, keyword_list: list) -> int:
    """Compte le nombre de correspondances pour une liste de mots-clés."""
    t = f" {text.lower()} "
    return sum(1 for kw in keyword_list if _match(kw, t))

def _calculate_market_type(text: str) -> str:
    """Détermine le type de marché (Maintenance, Travaux, Inconnu)."""
    score_maint = _count_keyword_matches(text, _KW_MAINTENANCE)
    score_trav = _count_keyword_matches(text, _KW_TRAVAUX)

    if score_maint > score_trav:
        return "Maintenance"
    elif score_trav > 0:
        return "Travaux"
    else:
        return "Inconnu"

def _find_competitor_brands(text: str) -> list:
    """Identifie les marques concurrentes mentionnées dans le texte."""
    t = f" {text.lower()} "
    marques = [m for m in _MARQUES_TOUTES if re.search(r'\b' + re.escape(m) + r'\b', t)]
    return list(dict.fromkeys(marques))

def _detect_penalties(text: str) -> str | None:
    """Détecte les clauses de pénalités dans le texte."""
    t = f" {text.lower()} "
    penalites_trouvees = [kw for kw in _KW_PENALITES if kw in t]

    if penalites_trouvees:
        match = re.search(
            r'(pénalité|penalite|retenue)[^.]{0,80}(\d[\d\s]*[€%])',
            text, re.IGNORECASE
        )
        return (f"Pénalités détectées : {match.group(0)[:120]}" if match
                else f"Clauses de pénalités/garantie ({', '.join(penalites_trouvees[:3])})")
    return None

def _calculate_technical_scores(text: str) -> dict:
    """Calcule les scores techniques pour chaque domaine."""
    return {
        'ssi': _count_keyword_matches(text, _KW_SSI),
        'cmsi': _count_keyword_matches(text, _KW_CMSI),
        'vid': _count_keyword_matches(text, _KW_VIDEO),
        'cf': _count_keyword_matches(text, _KW_COURANTS_FAIBLES),
        'qhse': _count_keyword_matches(text, _KW_QHSE),
        'erp': _count_keyword_matches(text, _KW_ERP),
        'excl': _count_keyword_matches(text, _KW_EXCLUSION)
    }

def _calculate_technical_signal(scores: dict) -> int:
    """Calcule le signal technique global."""
    return scores['ssi'] + scores['cmsi'] + scores['vid'] + scores['cf']

def _calculate_relevance_score(scores: dict, technical_signal: int, market_type: str, brands: list, text: str) -> int:
    """Calcule le score de pertinence DEF OI."""
    score = 0

    # Bloc technique (0–55) : SSI/CMSI primaires, Vidéo/CF secondaires
    if scores['ssi'] >= 3:        score += 55
    elif scores['ssi'] == 2:      score += 50
    elif scores['ssi'] == 1:      score += 40
    if scores['cmsi'] >= 2:       score += 30   # CMSI signal primaire (si SSI absent)
    elif scores['cmsi'] == 1:     score += 20   # CMSI signal primaire (si SSI absent)
    if scores['vid'] >= 2:        score += 35
    elif scores['vid'] == 1:      score += 28
    if scores['cf'] >= 1:         score += 20
    if scores['qhse'] >= 1:       score += 10
    score = min(score, 55)  # plafond technique

    # Bloc géographique (0–30)
    t_lower = f" {text.lower()} "
    if any(_match(kw, t_lower) for kw in _KW_TERRITOIRE_REUNION):  score += 30
    elif any(_match(kw, t_lower) for kw in _KW_TERRITOIRE_MAYOTTE): score += 28
    elif any(_match(kw, t_lower) for kw in _KW_TERRITOIRE_IO):      score += 15

    # Bonus ERP (0–10) : bâtiment à obligation réglementaire SSI
    if scores['erp'] > 0 and technical_signal > 0:
        score += min(scores['erp'] * 4, 10)

    # Bonus maintenance (0–10)
    if market_type == "Maintenance":
        score += 10

    # Bonus marques concurrentes citées = DCE détaillé (0–5)
    if brands:
        score += min(len(brands) * 2, 5)

    # Pénalité exclusion : si signaux hors périmètre ET signal technique faible
    if scores['excl'] > 0 and technical_signal < 2:
        malus = min(scores['excl'] * 12, 30)
        score = max(5, score - malus)

    return min(score, 100)

def _determine_territory(text: str) -> str:
    """Détermine le territoire local."""
    t = f" {text.lower()} "
    if any(_match(kw, t) for kw in _KW_TERRITOIRE_REUNION):
        return "La Réunion"
    elif any(_match(kw, t) for kw in _KW_TERRITOIRE_MAYOTTE):
        return "Mayotte"
    elif any(_match(kw, t) for kw in _KW_TERRITOIRE_IO):
        return "Océan Indien"
    else:
        return "Non précisé"

def _generate_technical_justification(scores: dict, technical_signal: int) -> list:
    """Génère la justification technique."""
    parts = []

    # SSI
    if scores['ssi'] >= 3:
        parts.append(f"Marché SSI fortement qualifié ({scores['ssi']} références techniques détectées : centrale, détecteurs, déclencheurs, alarme) — cœur de métier DEF OI, offre à préparer")
    elif scores['ssi'] == 2:
        parts.append(f"Marché SSI bien identifié ({scores['ssi']} indices techniques) — cœur de métier DEF OI")
    elif scores['ssi'] == 1:
        parts.append("Signal SSI/incendie présent — cœur de métier DEF OI, vérifier la profondeur dans le CCTP")

    # CMSI
    if scores['cmsi'] >= 2:
        parts.append(f"CMSI/désenfumage clairement qualifié ({scores['cmsi']} références) — compétence rare, peu de concurrents locaux qualifiés")
    elif scores['cmsi'] == 1:
        parts.append("CMSI/désenfumage mentionné — spécialité DEF OI, avantage concurrentiel local")

    # Vidéo
    if scores['vid'] >= 2:
        parts.append(f"Vidéosurveillance bien identifiée ({scores['vid']} références : caméras IP, NVR, VMS) — dans le portefeuille DEF OI")
    elif scores['vid'] == 1:
        parts.append("Composante vidéosurveillance détectée — expertise DEF OI, souvent couplée au SSI sur les ERP")

    # Courants faibles
    if scores['cf'] >= 1:
        parts.append(f"Courants faibles ({scores['cf']} signal(s) : contrôle d'accès, interphonie, GTB) — prestation complémentaire du portefeuille DEF OI")

    # QHSE
    if scores['qhse'] >= 1:
        parts.append("Signal QHSE/réglementaire incendie — opportunité d'accompagnement ERP (audit, formation, mise en conformité)")

    # ERP
    if scores['erp'] > 0 and technical_signal > 0:
        parts.append(f"Type de bâtiment ERP détecté ({scores['erp']} indice(s)) — obligation réglementaire SSI catégorie A/B ; DEF OI a l'expertise et les certifications requises")
    elif scores['erp'] > 0 and technical_signal == 0:
        parts.append(f"Bâtiment ERP détecté mais aucun domaine technique DEF OI explicite — potentiel SSI latent, vérifier le CCTP")

    if technical_signal == 0 and scores['erp'] == 0:
        parts.append("Aucun domaine métier DEF OI (SSI/CMSI/Vidéo/Courants faibles) ni bâtiment ERP détecté dans le texte — pertinence technique faible")

    return parts

def _generate_exclusion_justification(scores: dict, technical_signal: int, text: str) -> list:
    """Génère la justification pour les pénalités d'exclusion."""
    parts = []
    if scores['excl'] > 0 and technical_signal < 2:
        t = f" {text.lower()} "
        excl_hits = [kw for kw in _KW_EXCLUSION if _match(kw, t)][:3]
        parts.append(f"Signaux hors périmètre DEF OI détectés ({', '.join(excl_hits)}) — risque de confusion avec gardiennage/génie civil/électricité générale ; score pénalisé")
    return parts

def _generate_geographical_justification(territory: str) -> list:
    """Génère la justification géographique."""
    parts = []
    if territory == "La Réunion":
        parts.append("La Réunion (974) : territoire principal DEF OI — présence locale, réseau établi, connaissance des donneurs d'ordre publics, avantage décisif sur les concurrents métropolitains")
    elif territory == "Mayotte":
        parts.append("Mayotte (976) : territoire principal DEF OI — marché peu concurrentiel, DEF OI parmi les rares opérateurs locaux qualifiés SSI/CMSI")
    elif territory == "Océan Indien":
        parts.append("Zone Océan Indien : axe de développement stratégique DEF OI — peu de concurrents locaux certifiés, opportunité de positionnement régional")
    else:
        parts.append("Territoire non localisé dans la zone Océan Indien — réduire la priorité ; confirmer le lien géographique avant d'engager des ressources")
    return parts

def _generate_market_type_justification(market_type: str) -> list:
    """Génère la justification pour le type de marché."""
    parts = []
    if market_type == "Maintenance":
        parts.append("Contrat de maintenance = CA récurrent et prévisible, taux de marge élevé, fidélisation client sur plusieurs années")
    elif market_type == "Travaux":
        parts.append("Marché travaux (installation/rénovation) = revenus ponctuels mais ouvre la porte à un contrat de maintenance annuel si DEF OI remporte")
    return parts

def _generate_brands_justification(brands: list) -> list:
    """Génère la justification pour les marques concurrentes."""
    parts = []
    if brands:
        parts.append(f"Marques citées dans le DCE : {', '.join(brands[:4])} — étudier la compatibilité technique ou la possibilité de substitution agréée")
    return parts

def _local_analyze_impl(text: str) -> dict:
    """Analyse locale optimisée du texte pour déterminer la pertinence DEF OI."""
    # Calculs initiaux
    market_type = _calculate_market_type(text)
    brands = _find_competitor_brands(text)
    penalties = _detect_penalties(text)
    technical_scores = _calculate_technical_scores(text)
    technical_signal = _calculate_technical_signal(technical_scores)
    relevance_score = _calculate_relevance_score(technical_scores, technical_signal, market_type, brands, text)
    territory = _determine_territory(text)

    # Génération des justifications
    justification_parts = []

    # Justification technique
    justification_parts.extend(_generate_technical_justification(technical_scores, technical_signal))

    # Justification d'exclusion
    justification_parts.extend(_generate_exclusion_justification(technical_scores, technical_signal, text))

    # Justification géographique
    justification_parts.extend(_generate_geographical_justification(territory))

    # Justification type de marché
    justification_parts.extend(_generate_market_type_justification(market_type))

    # Justification marques
    justification_parts.extend(_generate_brands_justification(brands))

    # Construction du résultat
    return {
        "type_marche": market_type,
        "marques_concurrentes_citees": brands,
        "risques_penalites": penalties,
        "score_pertinence": relevance_score,
        "tag_pertinence": _score_to_tag(relevance_score),
        "domaines_concernes": _build_domains_list(technical_scores, market_type),
        "territoire_ia": territory,
        "justification_score": ". ".join(justification_parts) + ".",
        "_source": "local",
        # compteurs bruts — utilisés dans _render_strategic_analysis
        "_nb_ssi": technical_scores['ssi'],
        "_nb_cmsi": technical_scores['cmsi'],
        "_nb_vid": technical_scores['vid'],
        "_nb_cf": technical_scores['cf'],
        "_nb_erp": technical_scores['erp'],
        "_nb_excl": technical_scores['excl'],
    }

def _build_domains_list(scores: dict, market_type: str) -> list:
    """Construire la liste des domaines concernés."""
    domaines = []
    if scores['ssi'] > 0:   domaines.append("SSI")
    if scores['cmsi'] > 0:  domaines.append("CMSI")
    if scores['vid'] > 0:   domaines.append("Vidéosurveillance")
    if scores['cf'] > 0:    domaines.append("Courants faibles")
    if scores['qhse'] > 0:  domaines.append("QHSE")
    if scores['erp'] > 0:   domaines.append("ERP")
    if market_type == "Maintenance": domaines.append("Maintenance")
    return domaines


# ---------------------------------------------------------------------------
# Score combiné
# ---------------------------------------------------------------------------

def compute_combined_score(llm_score: int, local_score: int,
                            llm_available: bool) -> int:
    """Pondère : 70 % LLM + 30 % local si LLM disponible, sinon 100 % local."""
    if llm_available:
        return round(llm_score * 0.70 + local_score * 0.30)
    return local_score


# ---------------------------------------------------------------------------
# System Prompt Claude (contexte DEF OI complet + QHSE)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Tu es un analyste commercial expert pour DEF Océan Indien, société spécialisée \
en systèmes de sécurité incendie (SSI/CMSI), vidéosurveillance, courants faibles \
et QHSE. Ton rôle : évaluer précisément si un appel d'offres représente une \
opportunité commerciale réelle pour DEF OI.

ZONE PRIORITAIRE : La Réunion (974) et Mayotte (976) — présence locale, \
certifications, réseau établi.
ZONE SECONDAIRE : Madagascar, Maurice, Comores — axe de développement stratégique.
HORS ZONE : France métropole et international = score plafonné à 50 sauf \
composante technique SSI/CMSI très forte.

CŒUR DE MÉTIER DEF OI (domaines où DEF OI peut répondre) :
1. SSI complet : centrales incendie (Notifier, Hochiki, Apollo…), détecteurs \
adressables/conventionnels, déclencheurs manuels (DMC), SMSI, tableaux de \
signalisation (TSI), équipements d'alarme type 1-4, boucles incendie
2. CMSI / Désenfumage : volets coupe-feu, exutoires, extracteurs de fumée, \
amenées d'air, commandes manuelles centralisées, désenfumage naturel ou mécanique
3. Vidéosurveillance / CCTV : caméras IP/PTZ/dôme/thermiques, NVR/DVR, VMS, \
analytics, LPR (lecture de plaques)
4. Courants faibles : contrôle d'accès (badges, biométrie), interphonie, \
visiophone, GTC/GTB, anti-intrusion, télégestion
5. Maintenance réglementaire : vérifications annuelles SSI/CMSI (NF S 61-933), \
MCO, GMAO, astreinte, dépannage, contrats de service
6. QHSE / ERP : audits de sécurité incendie, formations SSIAP/évacuation, \
accompagnement commissions de sécurité, mise en conformité ERP

SIGNAL ERP (bâtiments à obligation réglementaire SSI) : \
hôpital/CHU/EHPAD, école/lycée/université, mairie/préfecture, \
hôtel/résidence, centre commercial, gymnase/piscine/stade, musée/bibliothèque, \
IGH (immeuble grande hauteur). Si un ERP est mentionné + contexte sécurité = \
probabilité forte de SSI obligatoire.

EXCLURE IMPÉRATIVEMENT — score ≤ 15 si aucun signal SSI/Vidéo/CF :
- Gardiennage, agents de sécurité, SSIAP pur, rondes, surveillance humaine
- Génie civil pur, VRD, terrassement, maçonnerie, charpente, gros œuvre
- Électricité HT/BT seule, éclairage public, postes de transformation
- Plomberie, chauffage/CVC pur (sauf CMSI), menuiserie, serrurerie
- Extincteurs seuls (sans SSI), fourniture de matériel de lutte incendie
- Sécurité civile, pompiers, secours

Réponds UNIQUEMENT en JSON valide, sans commentaire :
{
  "score_pertinence": <entier 0-100>,
  "tag_pertinence": "Très pertinent" | "À évaluer" | "Hors périmètre",
  "type_marche": "Travaux" | "Maintenance" | "Fourniture" | "Mixte" | "Inconnu",
  "domaines_concernes": ["SSI", "CMSI", "Vidéosurveillance", "Courants faibles", \
"QHSE", "ERP", "Maintenance"],
  "territoire": "La Réunion" | "Mayotte" | "Océan Indien" | "France métropole" | \
"International" | "Non précisé",
  "marques_concurrentes_citees": ["marque1", "marque2"],
  "risques_penalites": "texte court décrivant pénalités/retenues ou null",
  "justification_score": "3 phrases : (1) quels domaines métier DEF OI sont présents et avec quelle intensité dans le texte (SSI/CMSI/Vidéo/CF — citer les indices concrets), (2) pourquoi ce territoire est ou non stratégique pour DEF OI (avantage local 974/976, développement OI, ou hors zone), (3) type de prestation et impact commercial direct (maintenance = récurrent + marge, travaux = déclenche futur MCO, ERP = obligation réglementaire). Si hors périmètre, nommer précisément ce qui exclut (ex: gardiennage, génie civil, électricité HT)."
}

BARÈME DE SCORING :
85-100 : SSI/CMSI/Vidéo direct + La Réunion ou Mayotte (974/976)
65-84  : domaine DEF OI présent + territoire prioritaire, OU SSI fort + zone OI
45-64  : signal ERP avec contexte sécurité + territoire OI, OU courants faibles 974/976
25-44  : signal faible ou territoire secondaire seulement, mérite vérification DCE
5-24   : hors périmètre DEF OI ou signaux exclusion dominants\
"""

_anthropic_client = None


def _get_anthropic_client():
    global _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return None
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(api_key=api_key)
        except Exception:
            return None
    return _anthropic_client


_mistral_client = None


def _get_mistral_client():
    global _mistral_client
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        return None
    if _mistral_client is None:
        try:
            from mistralai.client import Mistral
            _mistral_client = Mistral(api_key=api_key)
        except Exception:
            return None
    return _mistral_client


def _mistral_analyze(text: str) -> dict | None:
    """Analyse via l'API Mistral (mistral-large-latest).

    Retourne None si la clé API est absente ou en cas d'erreur inattendue.
    Lève _LLMQuotaError si le quota API est atteint (429).
    """
    client = _get_mistral_client()
    if client is None:
        return None
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Analyse ce marché :\n\n"
                        "<MARCHE_CONTENT>\n"
                        f"{text[:8000]}\n"
                        "</MARCHE_CONTENT>"
                    ),
                },
            ],
        )
        raw = response.choices[0].message.content
        if not raw:
            _log.warning("Mistral : réponse vide")
            return None
        raw_clean = raw.strip()
        raw_clean = re.sub(r"^```(?:json)?\s*", "", raw_clean)
        raw_clean = re.sub(r"\s*```$", "", raw_clean).strip()
        try:
            result = json.loads(raw_clean)
        except json.JSONDecodeError:
            _log.warning("Mistral : réponse non-JSON — fallback analyse locale")
            return None
        result["_source"] = "mistral"
        return result
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status == 429:
            retry_after = None
            try:
                retry_after = int(getattr(exc, "headers", {}).get("retry-after", 0)) or None
            except Exception:
                pass
            raise _LLMQuotaError(retry_after=retry_after)
        if status in (401, 403):
            _log.warning("Clé API Mistral invalide ou permissions insuffisantes")
            return None
        _log.warning("Mistral analyse échouée (erreur inattendue) : %s", str(exc)[:200])
        return None


def _claude_analyze(text: str) -> dict | None:
    """Tente une analyse via l'API Claude (Anthropic).

    Retourne None si la clé API est absente ou en cas d'erreur inattendue.
    Lève _LLMQuotaError si le quota API est atteint (429).
    """
    client = _get_anthropic_client()
    if client is None:
        return None
    try:
        import anthropic
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=16000,
            thinking={"type": "enabled", "budget_tokens": 10000},
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Analyse ce marché :\n\n"
                        "<MARCHE_CONTENT>\n"
                        f"{text[:8000]}\n"
                        "</MARCHE_CONTENT>"
                    ),
                }
            ],
        )
        raw = next((block.text for block in response.content if block.type == "text"), None)
        if raw is None:
            _log.warning("Claude : aucun bloc texte dans la réponse")
            return None
        # Supprimer les éventuels code fences markdown (```json ... ```)
        raw_clean = raw.strip()
        raw_clean = re.sub(r"^```(?:json)?\s*", "", raw_clean)
        raw_clean = re.sub(r"\s*```$", "", raw_clean).strip()
        try:
            result = json.loads(raw_clean)
        except json.JSONDecodeError:
            _log.warning("Claude : réponse non-JSON — fallback analyse locale")
            return None
        result["_source"] = "claude"
        return result
    except anthropic.RateLimitError as exc:
        retry_after = None
        try:
            retry_after = int(exc.response.headers.get("retry-after", 0)) or None
        except Exception:
            pass
        raise _LLMQuotaError(retry_after=retry_after)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
        # Ne pas logger str(exc) — peut contenir des fragments de la clé API
        _log.warning("Clé API Claude invalide ou permissions insuffisantes (AuthenticationError)")
        return None
    except Exception as exc:
        _log.warning("Claude analyse échouée (erreur inattendue) : %s", str(exc)[:200])
        return None


# ---------------------------------------------------------------------------
# Récupération du contenu DCE depuis l'URL source (pages publiques uniquement)
# ---------------------------------------------------------------------------

# Whitelist de domaines autorisés pour fetch_dce_content
_ALLOWED_DCE_DOMAINS = {
    "boamp.fr", "marchessecurises.com", "tendersgo.com",
    "instao.com", "aws-achat.com", "achatpublic.com",
    "marcheonline.fr", "marchespublicsinfo.fr"
}

# Domains à ignorer (retournent du contenu non utile ou dynamique)
_SKIP_DCE_DOMAINS = {
    "marchessecurises.com", "instao.com", "tendersgo.com", "aws-achat.com",
    "achatpublic.com", "boamp.fr"  # BOAMP retourne du JS dynamique peu utile
}

def fetch_dce_content(url: str) -> str | None:
    """
    Tente de récupérer le texte brut d'une page DCE publique avec validation de sécurité.

    Sécurité :
    - Validation stricte du format URL et du domaine
    - Liste blanche de domaines autorisés
    - Liste noire de domaines à ignorer
    - Timeout court (8s) pour éviter les blocages
    - Limite de taille stricte (2MB)
    - Vérification du Content-Type
    - Lecture chunk par chunk pour éviter les débordements mémoire
    - Suppression des scripts et styles pour éviter les attaques XSS

    Retourne None si :
    - URL invalide ou malformée
    - Domaine non autorisé ou dans la liste noire
    - Erreur HTTP (status != 200)
    - Content-Type non HTML
    - Taille dépassant 2MB
    - Exception lors de la requête
    - Contenu trop court (< 150 caractères)
    """
    if not url or not isinstance(url, str):
        _log.debug("fetch_dce_content: URL vide ou non-string")
        return None

    # Validation du format URL
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            _log.debug("fetch_dce_content: URL malformée (%s)", url)
            return None

        # Vérifier le schéma HTTP/HTTPS
        if parsed.scheme not in ("http", "https"):
            _log.debug("fetch_dce_content: Schéma non supporté (%s)", parsed.scheme)
            return None

        # Extraire le domaine principal
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        # Vérifier contre la liste noire
        if domain in _SKIP_DCE_DOMAINS:
            _log.debug("fetch_dce_content: Domaine dans la liste noire (%s)", domain)
            return None

        # Vérifier contre la liste blanche (pour les domaines non dans la liste noire)
        domain_allowed = any(
            domain == allowed or domain.endswith(f".{allowed}")
            for allowed in _ALLOWED_DCE_DOMAINS
        )
        if not domain_allowed:
            _log.debug("fetch_dce_content: Domaine non autorisé (%s)", domain)
            return None

    except Exception as e:
        _log.warning("fetch_dce_content: Erreur de validation URL (%s): %s", url, str(e))
        return None

    try:
        import requests as _req

        _MAX_DCE_BYTES = 2_000_000  # 2 MB max avant lecture
        _MAX_URL_LENGTH = 2048     # Limite de longueur pour l'URL

        # Vérifier la longueur de l'URL
        if len(url) > _MAX_URL_LENGTH:
            _log.debug("fetch_dce_content: URL trop longue (%d caractères)", len(url))
            return None

        _log.debug("fetch_dce_content: Récupération de %s", url)
        with _req.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DEF-OI-Veille/1.0)"},
            allow_redirects=True,
            stream=True,
        ) as resp:
            if resp.status_code != 200:
                _log.debug("fetch_dce_content: Status HTTP %d pour %s", resp.status_code, url)
                return None

            ct = resp.headers.get("content-type", "").lower()
            if not any(t in ct for t in ("text/html", "text/plain", "application/xhtml")):
                _log.debug("fetch_dce_content: Content-Type non HTML (%s) — skipped", ct[:60])
                return None

            content_length = int(resp.headers.get("content-length", 0) or 0)
            if content_length > _MAX_DCE_BYTES:
                _log.debug("fetch_dce_content: Content-Length trop grand (%d bytes) — skipped", content_length)
                return None

            # Lecture chunk par chunk pour respecter la limite même sans Content-Length
            chunks: list[bytes] = []
            size = 0
            for chunk in resp.iter_content(chunk_size=65536):
                size += len(chunk)
                if size > _MAX_DCE_BYTES:
                    _log.debug("fetch_dce_content: corps > %d bytes — lecture interrompue", _MAX_DCE_BYTES)
                    return None
                chunks.append(chunk)

            encoding = resp.encoding or "utf-8"
            raw = b"".join(chunks).decode(encoding, errors="replace")

        # Supprimer scripts et styles pour éviter les attaques XSS
        raw = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", " ",
            raw,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r"<[^>]+>", " ", raw)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()

        # Vérifier que le texte extrait est suffisamment long
        if len(text) <= 150:
            _log.debug("fetch_dce_content: Contenu trop court (%d caractères)", len(text))
            return None

        result = text[:6000]
        _log.debug("fetch_dce_content: Succès - %d caractères extraits", len(result))
        return result

    except Exception as e:
        _log.warning("fetch_dce_content: Exception lors de la récupération de %s: %s", url, str(e))
        return None


# ---------------------------------------------------------------------------
# Analyse automatique en masse (local uniquement — sans quota)
# ---------------------------------------------------------------------------

def auto_analyze_pending(db) -> int:
    """Analyse tous les marchés sans llm_analysis. Moteur local uniquement."""
    from sqlalchemy import text as _text
    from models import Tender
    # SQLite stocke parfois 'null' (JSON null) au lieu de SQL NULL — on filtre les deux
    pending = db.query(Tender).filter(
        _text("llm_analysis IS NULL OR llm_analysis = 'null'")
    ).all()
    for t in pending:
        result = _local_analyze(f"{t.title or ''} {t.description or ''}")
        t.llm_analysis = result
        t.relevance_score = result.get("score_pertinence", 0)
        t.is_maintenance = result.get("type_marche", "").lower() == "maintenance"
    if pending:
        db.commit()
    return len(pending)


def auto_analyze_claude(
    db,
    max_per_run: int = 10,
    delay: float = 1.0,  # 1s entre requêtes — respecte les limites de l'API
    progress_cb=None,
) -> tuple[int, int]:
    """Analyse en masse via Claude (Anthropic) avec débit contrôlé.

    Cible les marchés analysés localement uniquement (source='local').
    Priorise les scores locaux les plus élevés en premier.
    Retourne (nb_analysés, retry_after_seconds) :
      - retry_after_seconds = -1  → pas d'erreur quota
      - retry_after_seconds >= 0  → quota atteint, nombre de secondes suggérées avant retry
    """
    from sqlalchemy import text as _text
    from models import Tender

    pending = (
        db.query(Tender)
        .filter(
            Tender.is_blacklisted == False,
            _text(
                "llm_analysis IS NULL OR llm_analysis = 'null' "
                "OR json_extract(llm_analysis, '$._source') = 'local'"
            ),
        )
        .order_by(Tender.relevance_score.desc())
        .limit(max_per_run)
        .all()
    )

    if not pending:
        if progress_cb:
            progress_cb(0, 0, "")
        return 0, -1

    nb_done = 0

    for i, t in enumerate(pending):
        if progress_cb:
            progress_cb(i, len(pending), t.title or "—")

        text = f"{t.title or ''} {t.description or ''}"
        local_result = _local_analyze(text)

        provider = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
        try:
            if provider == "mistral":
                llm_result = _mistral_analyze(text)
            else:
                llm_result = _claude_analyze(text)
        except _LLMQuotaError as qe:
            # Quota atteint : on sauvegarde ce qui est fait et on arrête immédiatement
            if nb_done > 0:
                db.commit()
            if progress_cb:
                progress_cb(len(pending), len(pending), "")
            retry = qe.retry_after if qe.retry_after is not None else 60
            return nb_done, retry

        if llm_result is None:
            _log.warning(
                "auto_analyze_claude: marché '%s' — %s a retourné None (clé absente, JSON invalide ou erreur réseau)",
                (t.title or t.id)[:60], provider,
            )
            if i < len(pending) - 1:
                time.sleep(delay)
            continue

        combined_score = compute_combined_score(
            llm_score=llm_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            llm_available=True,
        )
        llm_result["score_pertinence"] = combined_score
        llm_result.setdefault("tag_pertinence", _score_to_tag(combined_score))
        llm_result.setdefault("domaines_concernes", local_result.get("domaines_concernes", []))
        llm_result.setdefault("justification_score", local_result.get("justification_score", ""))
        llm_result.setdefault("territoire_ia", local_result.get("territoire_ia", "Non précisé"))

        t.llm_analysis = llm_result
        t.relevance_score = combined_score
        t.is_maintenance = llm_result.get("type_marche", "").lower() == "maintenance"
        nb_done += 1

        if i < len(pending) - 1:
            time.sleep(delay)

    if nb_done > 0:
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

    if progress_cb:
        progress_cb(len(pending), len(pending), "")

    return nb_done, -1


auto_analyze_gemini = auto_analyze_claude  # alias rétrocompat


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def analyze_tender(text: str, source_url: str | None = None) -> dict:
    """
    Analyse un appel d'offre. Si source_url est fourni et accessible publiquement,
    enrichit le texte avec le contenu de la page DCE avant l'analyse.
    Route vers Claude ou Mistral selon LLM_PROVIDER (.env). Fallback analyse locale.
    """
    if source_url:
        dce_content = fetch_dce_content(source_url)
        if dce_content:
            text = text + "\n\n[Contenu page DCE]\n" + dce_content

    local_result = _local_analyze(text)

    provider = os.getenv("LLM_PROVIDER", "mistral").strip().lower()
    try:
        if provider == "mistral":
            llm_result = _mistral_analyze(text)
        else:
            llm_result = _claude_analyze(text)
    except _LLMQuotaError:
        llm_result = None

    if llm_result is not None:
        combined_score = compute_combined_score(
            llm_score=llm_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            llm_available=True,
        )
        llm_result["score_pertinence"] = combined_score
        llm_result.setdefault("tag_pertinence", _score_to_tag(combined_score))
        llm_result.setdefault("domaines_concernes", local_result.get("domaines_concernes", []))
        llm_result.setdefault("justification_score", local_result.get("justification_score", ""))
        llm_result.setdefault("territoire_ia", local_result.get("territoire_ia", "Non précisé"))
        return llm_result

    return local_result


_STRUCTURED_SYSTEM = (
    "Tu es un expert en marchés publics SSI, CMSI, désenfumage, vidéosurveillance "
    "et courants faibles pour les DOM (La Réunion 974, Mayotte 976). "
    "Tu retournes UNIQUEMENT un objet JSON valide, sans texte avant ni après."
)

_STRUCTURED_USER_TPL = """Analyse ce marché et retourne ce JSON strict :

{{
  "budget_estime": "<montant en euro ou null>",
  "type_travaux": "Installation neuve" | "Rénovation" | "Maintenance" | "Étude" | "Mixte" | "Inconnu",
  "lots": ["Lot 1 — ...", "..."],
  "keywords_techniques": ["ERP type J", "SSI catégorie A", "..."],
  "acheteur_type": "Commune" | "Établissement scolaire" | "Hôpital" | "Administration" | "Privé" | "Autre",
  "niveau_concurrence": "Faible" | "Moyen" | "Élevé",
  "recommandation": "GO" | "NON",
  "score_confiance": <entier 0-100>,
  "justification": "<1-2 phrases>"
}}

--- MARCHÉ ---
Titre : {title}
Description : {description}
Montant estimé : {amount}
"""


def analyze_tender_structured(
    title: str,
    description: str,
    amount: int | None = None,
) -> dict | None:
    """
    Analyse structurée LLM d'un marché. Retourne un dict JSON ou None si :
    - description trop courte (< 50 chars)
    - clé API absente
    - réponse non-JSON
    - quota / erreur réseau
    """
    if not description or len(description.strip()) < 50:
        return None

    client = _get_mistral_client()
    if client is None:
        return None

    amount_str = f"{amount:,} €".replace(",", " ") if amount else "Non renseigné"
    prompt = _STRUCTURED_USER_TPL.format(
        title=title or "",
        description=description[:3000],
        amount=amount_str,
    )

    try:
        response = client.chat.complete(
            model="mistral-small-latest",
            messages=[
                {"role": "system", "content": _STRUCTURED_SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.choices[0].message.content.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        return json.loads(raw[start:end])
    except Exception:
        return None
