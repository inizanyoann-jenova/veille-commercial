import json
import logging
import os
import re
import time
from functools import lru_cache

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
    r"\bssi\b", r"\bcmsi\b", r"\bsmsi\b", r"\bsdi\b", r"\bdai\b",
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
    r"\btype 1\b", r"\btype 2\b", r"\btype 3\b", r"\btype 4\b",  # types d'alarme
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
    "porte coupe-feu", "porte coupe feu", r"\bcf\b",
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
    r"\bgta\b",  # gestion technique aéroport/avancée
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
    r"\bchu\b", "centre hospitalier", r"\behpad\b", "maison de retraite",
    "hôpital", "hopital", "clinique", "polyclinique",
    r"\bchu\b", r"\bchrs\b", r"\bchru\b",
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

@lru_cache(maxsize=128)
def _local_analyze(text: str) -> dict:
    t = f" {text.lower()} "

    # --- Type de marché ---
    score_maint = sum(1 for kw in _KW_MAINTENANCE if _match(kw, t))
    score_trav = sum(1 for kw in _KW_TRAVAUX if _match(kw, t))
    if score_maint > score_trav:
        type_marche = "Maintenance"
    elif score_trav > 0:
        type_marche = "Travaux"
    else:
        type_marche = "Inconnu"

    # --- Marques concurrentes ---
    marques = [m for m in _MARQUES_TOUTES if re.search(r'\b' + re.escape(m) + r'\b', t)]
    marques = list(dict.fromkeys(marques))

    # --- Risques / pénalités ---
    penalites_trouvees = [kw for kw in _KW_PENALITES if kw in t]
    if penalites_trouvees:
        match = re.search(
            r'(pénalité|penalite|retenue)[^.]{0,80}(\d[\d\s]*[€%])',
            text, re.IGNORECASE
        )
        risques = (f"Pénalités détectées : {match.group(0)[:120]}" if match
                   else f"Clauses de pénalités/garantie ({', '.join(penalites_trouvees[:3])})")
    else:
        risques = None

    # --- Comptage des signaux métier ---
    nb_ssi  = sum(1 for kw in _KW_SSI if _match(kw, t))
    nb_cmsi = sum(1 for kw in _KW_CMSI if _match(kw, t))
    nb_vid  = sum(1 for kw in _KW_VIDEO if _match(kw, t))
    nb_cf   = sum(1 for kw in _KW_COURANTS_FAIBLES if _match(kw, t))
    nb_qhse = sum(1 for kw in _KW_QHSE if _match(kw, t))
    nb_erp  = sum(1 for kw in _KW_ERP if _match(kw, t))
    nb_excl = sum(1 for kw in _KW_EXCLUSION if _match(kw, t))

    # Signal technique global (pour la pénalité d'exclusion)
    signal_technique = nb_ssi + nb_cmsi + nb_vid + nb_cf

    # --- Score de pertinence DEF ---
    score = 0

    # Bloc technique (0–55) : SSI/CMSI primaires, Vidéo/CF secondaires
    if nb_ssi >= 3:        score += 55
    elif nb_ssi == 2:      score += 50
    elif nb_ssi == 1:      score += 40
    if nb_cmsi >= 2:       score += 20   # peut s'additionner au SSI
    elif nb_cmsi == 1:     score += 12
    if nb_vid >= 2:        score += 35
    elif nb_vid == 1:      score += 28
    if nb_cf >= 1:         score += 20
    if nb_qhse >= 1:       score += 10
    score = min(score, 55)  # plafond technique

    # Bloc géographique (0–30)
    if any(_match(kw, t) for kw in _KW_TERRITOIRE_REUNION):  score += 30
    elif any(_match(kw, t) for kw in _KW_TERRITOIRE_MAYOTTE): score += 28
    elif any(_match(kw, t) for kw in _KW_TERRITOIRE_IO):      score += 15

    # Bonus ERP (0–10) : bâtiment à obligation réglementaire SSI
    if nb_erp > 0 and signal_technique > 0:
        score += min(nb_erp * 4, 10)

    # Bonus maintenance (0–10)
    if type_marche == "Maintenance":
        score += 10

    # Bonus marques concurrentes citées = DCE détaillé (0–5)
    if marques:
        score += min(len(marques) * 2, 5)

    score = min(score, 100)

    # Pénalité exclusion : si signaux hors périmètre ET signal technique faible
    if nb_excl > 0 and signal_technique < 2:
        malus = min(nb_excl * 12, 30)
        score = max(5, score - malus)

    # --- Domaines concernés ---
    domaines = []
    if nb_ssi > 0:   domaines.append("SSI")
    if nb_cmsi > 0:  domaines.append("CMSI")
    if nb_vid > 0:   domaines.append("Vidéosurveillance")
    if nb_cf > 0:    domaines.append("Courants faibles")
    if nb_qhse > 0:  domaines.append("QHSE")
    if nb_erp > 0:   domaines.append("ERP")
    if type_marche == "Maintenance": domaines.append("Maintenance")

    # --- Territoire local ---
    if any(_match(kw, t) for kw in _KW_TERRITOIRE_REUNION):
        territoire_ia = "La Réunion"
    elif any(_match(kw, t) for kw in _KW_TERRITOIRE_MAYOTTE):
        territoire_ia = "Mayotte"
    elif any(_match(kw, t) for kw in _KW_TERRITOIRE_IO):
        territoire_ia = "Océan Indien"
    else:
        territoire_ia = "Non précisé"

    # --- Justification enrichie DEF OI ---
    parts = []

    # Pertinence technique
    if nb_ssi >= 3:
        parts.append(f"Marché SSI fortement qualifié ({nb_ssi} références techniques détectées : centrale, détecteurs, déclencheurs, alarme) — cœur de métier DEF OI, offre à préparer")
    elif nb_ssi == 2:
        parts.append(f"Marché SSI bien identifié ({nb_ssi} indices techniques) — cœur de métier DEF OI")
    elif nb_ssi == 1:
        parts.append("Signal SSI/incendie présent — cœur de métier DEF OI, vérifier la profondeur dans le CCTP")
    if nb_cmsi >= 2:
        parts.append(f"CMSI/désenfumage clairement qualifié ({nb_cmsi} références) — compétence rare, peu de concurrents locaux qualifiés")
    elif nb_cmsi == 1:
        parts.append("CMSI/désenfumage mentionné — spécialité DEF OI, avantage concurrentiel local")
    if nb_vid >= 2:
        parts.append(f"Vidéosurveillance bien identifiée ({nb_vid} références : caméras IP, NVR, VMS) — dans le portefeuille DEF OI")
    elif nb_vid == 1:
        parts.append("Composante vidéosurveillance détectée — expertise DEF OI, souvent couplée au SSI sur les ERP")
    if nb_cf >= 1:
        parts.append(f"Courants faibles ({nb_cf} signal(s) : contrôle d'accès, interphonie, GTB) — prestation complémentaire du portefeuille DEF OI")
    if nb_qhse >= 1:
        parts.append("Signal QHSE/réglementaire incendie — opportunité d'accompagnement ERP (audit, formation, mise en conformité)")
    if nb_erp > 0 and signal_technique > 0:
        parts.append(f"Type de bâtiment ERP détecté ({nb_erp} indice(s)) — obligation réglementaire SSI catégorie A/B ; DEF OI a l'expertise et les certifications requises")
    elif nb_erp > 0 and signal_technique == 0:
        parts.append(f"Bâtiment ERP détecté mais aucun domaine technique DEF OI explicite — potentiel SSI latent, vérifier le CCTP")
    if signal_technique == 0 and nb_erp == 0:
        parts.append("Aucun domaine métier DEF OI (SSI/CMSI/Vidéo/Courants faibles) ni bâtiment ERP détecté dans le texte — pertinence technique faible")

    # Pénalités d'exclusion signalées
    if nb_excl > 0 and signal_technique < 2:
        excl_hits = [kw for kw in _KW_EXCLUSION if _match(kw, t)][:3]
        parts.append(f"Signaux hors périmètre DEF OI détectés ({', '.join(excl_hits)}) — risque de confusion avec gardiennage/génie civil/électricité générale ; score pénalisé")

    # Géographie
    if territoire_ia == "La Réunion":
        parts.append("La Réunion (974) : territoire principal DEF OI — présence locale, réseau établi, connaissance des donneurs d'ordre publics, avantage décisif sur les concurrents métropolitains")
    elif territoire_ia == "Mayotte":
        parts.append("Mayotte (976) : territoire principal DEF OI — marché peu concurrentiel, DEF OI parmi les rares opérateurs locaux qualifiés SSI/CMSI")
    elif territoire_ia == "Océan Indien":
        parts.append("Zone Océan Indien : axe de développement stratégique DEF OI — peu de concurrents locaux certifiés, opportunité de positionnement régional")
    else:
        parts.append("Territoire non localisé dans la zone Océan Indien — réduire la priorité ; confirmer le lien géographique avant d'engager des ressources")

    # Type de prestation
    if type_marche == "Maintenance":
        parts.append("Contrat de maintenance = CA récurrent et prévisible, taux de marge élevé, fidélisation client sur plusieurs années")
    elif type_marche == "Travaux":
        parts.append("Marché travaux (installation/rénovation) = revenus ponctuels mais ouvre la porte à un contrat de maintenance annuel si DEF OI remporte")

    # Marques concurrentes
    if marques:
        parts.append(f"Marques citées dans le DCE : {', '.join(marques[:4])} — étudier la compatibilité technique ou la possibilité de substitution agréée")

    justification = ". ".join(parts) + "."

    return {
        "type_marche": type_marche,
        "marques_concurrentes_citees": marques,
        "risques_penalites": risques,
        "score_pertinence": score,
        "tag_pertinence": _score_to_tag(score),
        "domaines_concernes": domaines,
        "territoire_ia": territoire_ia,
        "justification_score": justification,
        "_source": "local",
        # compteurs bruts — utilisés dans _render_strategic_analysis
        "_nb_ssi": nb_ssi,
        "_nb_cmsi": nb_cmsi,
        "_nb_vid": nb_vid,
        "_nb_cf": nb_cf,
        "_nb_erp": nb_erp,
        "_nb_excl": nb_excl,
    }


# ---------------------------------------------------------------------------
# Score combiné
# ---------------------------------------------------------------------------

def compute_combined_score(gemini_score: int, local_score: int,
                            gemini_available: bool) -> int:
    """Pondère : 70 % LLM + 30 % local si LLM disponible, sinon 100 % local."""
    if gemini_available:
        return round(gemini_score * 0.70 + local_score * 0.30)
    return local_score


# ---------------------------------------------------------------------------
# System Prompt Gemini (réécrit — contexte DEF OI complet + QHSE)
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

_client = None
_anthropic_client = None


def _get_client():
    global _client
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=api_key)
        except Exception:
            return None
    return _client


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


def _gemini_analyze(text: str) -> dict | None:
    """Tente une analyse via Gemini.

    Retourne None si la clé API est absente ou en cas d'erreur inattendue.
    Lève _LLMQuotaError si le quota API est atteint (429 / RESOURCE_EXHAUSTED).
    """
    client = _get_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Analyse ce marché :\n\n{text[:8000]}",
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.1,
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        result["_source"] = "gemini"
        return result
    except Exception as exc:
        msg = str(exc)
        if any(code in msg for code in ("429", "RESOURCE_EXHAUSTED", "quota")):
            # Tenter d'extraire le délai de retry suggéré par l'API
            m = re.search(r'"retryDelay"\s*:\s*"(\d+)s"', msg) or re.search(r'retry.*?(\d+)\s*s', msg, re.IGNORECASE)
            retry_after = int(m.group(1)) if m else None
            raise _LLMQuotaError(retry_after=retry_after)
        if any(code in msg for code in ("401", "403", "API_KEY")):
            _log.warning("Clé API Gemini invalide ou absente : %s", msg[:120])
            return None
        _log.warning("Gemini analyse échouée (erreur inattendue) : %s", msg[:200])
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
            max_tokens=2048,
            thinking={"type": "adaptive"},
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
                    "content": f"Analyse ce marché :\n\n{text[:8000]}",
                }
            ],
        )
        raw = next(block.text for block in response.content if block.type == "text")
        result = json.loads(raw)
        result["_source"] = "claude"
        return result
    except anthropic.RateLimitError as exc:
        retry_after = None
        try:
            retry_after = int(exc.response.headers.get("retry-after", 0)) or None
        except Exception:
            pass
        raise _LLMQuotaError(retry_after=retry_after)
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
        _log.warning("Clé API Claude invalide ou absente : %s", str(exc)[:120])
        return None
    except Exception as exc:
        _log.warning("Claude analyse échouée (erreur inattendue) : %s", str(exc)[:200])
        return None


# ---------------------------------------------------------------------------
# Récupération du contenu DCE depuis l'URL source (pages publiques uniquement)
# ---------------------------------------------------------------------------

_SKIP_DCE_DOMAINS = (
    "marchessecurises", "instao", "tendersgo", "aws-achat",
    "achatpublic", "boamp.fr",  # BOAMP retourne du JS dynamique peu utile
)


def fetch_dce_content(url: str) -> str | None:
    """
    Tente de récupérer le texte brut d'une page DCE publique.
    Retourne None si l'URL est vide, protégée par auth, ou si la requête échoue.
    Limite à 6 000 caractères pour rester dans le budget Gemini.
    """
    if not url or not url.startswith(("http://", "https://")):
        return None
    if any(d in url.lower() for d in _SKIP_DCE_DOMAINS):
        return None
    try:
        import html as _html
        import requests as _req

        resp = _req.get(
            url,
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DEF-OI-Veille/1.0)"},
            allow_redirects=True,
        )
        if resp.status_code != 200:
            return None
        raw = resp.text
        # Supprimer scripts et styles
        raw = re.sub(
            r"<(script|style)[^>]*>.*?</\1>", " ", raw,
            flags=re.IGNORECASE | re.DOTALL,
        )
        text = re.sub(r"<[^>]+>", " ", raw)
        text = _html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:6000] if len(text) > 150 else None
    except Exception:
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
    delay: float = 0.5,  # 0.5 s entre requêtes — Claude Enterprise a des limites très élevées
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
            Tender.is_blacklisted != True,
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

        try:
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
            # Erreur non-quota (réseau, JSON invalide…) : on saute ce marché
            continue

        combined_score = compute_combined_score(
            gemini_score=llm_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            gemini_available=True,
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
        db.commit()

    if progress_cb:
        progress_cb(len(pending), len(pending), "")

    return nb_done, -1


# Alias pour compatibilité ascendante
auto_analyze_gemini = auto_analyze_claude


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def analyze_tender(text: str, source_url: str | None = None) -> dict:
    """
    Analyse un appel d'offre. Si source_url est fourni et accessible publiquement,
    enrichit le texte avec le contenu de la page DCE avant l'analyse.
    Essaie Claude en premier (score combiné 70 % Claude + 30 % local).
    Fallback sur analyse locale si Claude indisponible.
    """
    if source_url:
        dce_content = fetch_dce_content(source_url)
        if dce_content:
            text = text + "\n\n[Contenu page DCE]\n" + dce_content

    local_result = _local_analyze(text)
    try:
        llm_result = _claude_analyze(text)
    except _LLMQuotaError:
        llm_result = None

    if llm_result is not None:
        combined_score = compute_combined_score(
            gemini_score=llm_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            gemini_available=True,
        )
        llm_result["score_pertinence"] = combined_score
        llm_result.setdefault("tag_pertinence", _score_to_tag(combined_score))
        llm_result.setdefault("domaines_concernes", local_result.get("domaines_concernes", []))
        llm_result.setdefault("justification_score", local_result.get("justification_score", ""))
        llm_result.setdefault("territoire_ia", local_result.get("territoire_ia", "Non précisé"))
        return llm_result

    return local_result
