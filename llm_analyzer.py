import json
import os
import re

from dotenv import load_dotenv

load_dotenv()

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
    "intervention sur site", "contrat de service",
]
_KW_TRAVAUX = [
    "installation", "fourniture et pose", "travaux", "mise en place",
    "réalisation", "construction", "extension", "rénovation", "renovation",
    "remplacement", "mise aux normes", "fourniture", "pose et raccordement",
    "déploiement", "deploiement",
]
_KW_PENALITES = [
    "pénalité", "penalite", "pénalités de retard", "retenue de garantie",
    "dommages et intérêts", "pfa", "p.f.a.", "délai contractuel",
    "garantie décennale", "décennale", "responsabilité civile",
    "clause résolutoire", "défaillance",
]
_KW_SSI = [
    r"\bssi\b", r"\bcmsi\b", "détection incendie", "detection incendie",
    "alarme incendie", "désenfumage", "desenfumage", "évacuation incendie",
    "centrale incendie", "détecteur incendie", r"\bsprinkler\b", "extinction automatique",
    "système de sécurité incendie", "systeme de securite incendie",
]
_KW_VIDEO = [
    "vidéosurveillance", "videosurveillance", r"\bcctv\b", "caméras de sécurité",
    "cameras de securite", "vidéo protection", "video protection", "télésurveillance vidéo",
]
_KW_COURANTS_FAIBLES = [
    "courants faibles", "contrôle d'accès", "controle d'acces",
    r"\binterphonie\b", r"\bgtb\b", "anti-intrusion",
]
_KW_QHSE = [
    "qhse", "qualité hygiène sécurité", "audit incendie", "formation sécurité incendie",
    "document unique", "erp", "commission de sécurité",
]
_KW_TERRITOIRE_REUNION = [
    "réunion", "reunion", "974", "saint-denis", "saint-pierre", "saint-paul",
    "le port", "sainte-marie", "le tampon",
]
_KW_TERRITOIRE_MAYOTTE = [
    "mayotte", "976", "mamoudzou", "dzaoudzi", "koungou",
]
_KW_TERRITOIRE_IO = [
    "madagascar", "maurice", "mauritius", "comores", "comoros", "moroni",
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

    # --- Score de pertinence DEF ---
    score = 0
    nb_ssi = sum(1 for kw in _KW_SSI if _match(kw, t))
    nb_vid = sum(1 for kw in _KW_VIDEO if _match(kw, t))
    nb_cf = sum(1 for kw in _KW_COURANTS_FAIBLES if _match(kw, t))
    nb_qhse = sum(1 for kw in _KW_QHSE if _match(kw, t))

    if nb_ssi >= 2:      score += 50
    elif nb_ssi == 1:    score += 40
    if nb_vid >= 1:      score += 35
    if nb_cf >= 1:       score += 25
    if nb_qhse >= 1:     score += 15
    score = min(score, 50)

    if any(kw in t for kw in _KW_TERRITOIRE_REUNION):  score += 30
    elif any(kw in t for kw in _KW_TERRITOIRE_MAYOTTE): score += 28
    elif any(kw in t for kw in _KW_TERRITOIRE_IO):      score += 15

    if type_marche == "Maintenance":    score += 10
    if marques:                          score += min(len(marques) * 3, 10)
    score = min(score, 100)

    # --- Domaines concernés ---
    domaines = []
    if nb_ssi > 0:  domaines.append("SSI")
    if any(_match(kw, t) for kw in [r"\bcmsi\b", "désenfumage", "desenfumage"]): domaines.append("CMSI")
    if nb_vid > 0:  domaines.append("Vidéosurveillance")
    if nb_cf > 0:   domaines.append("Courants faibles")
    if nb_qhse > 0: domaines.append("QHSE")
    if type_marche == "Maintenance": domaines.append("Maintenance")

    # --- Territoire local ---
    if any(kw in t for kw in _KW_TERRITOIRE_REUNION):
        territoire_ia = "La Réunion"
    elif any(kw in t for kw in _KW_TERRITOIRE_MAYOTTE):
        territoire_ia = "Mayotte"
    elif any(kw in t for kw in _KW_TERRITOIRE_IO):
        territoire_ia = "Océan Indien"
    else:
        territoire_ia = "Non précisé"

    # --- Justification ---
    dom_str = ", ".join(domaines) if domaines else "aucun domaine métier détecté"
    justification = f"Analyse locale : {dom_str}. Territoire : {territoire_ia}."

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
    }


# ---------------------------------------------------------------------------
# Score combiné
# ---------------------------------------------------------------------------

def compute_combined_score(gemini_score: int, local_score: int,
                            gemini_available: bool) -> int:
    """Pondère : 70 % Gemini + 30 % local si Gemini disponible, sinon 100 % local."""
    if gemini_available:
        return round(gemini_score * 0.70 + local_score * 0.30)
    return local_score


# ---------------------------------------------------------------------------
# System Prompt Gemini (réécrit — contexte DEF OI complet + QHSE)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Tu es un analyste commercial expert pour DEF Océan Indien, entreprise \
spécialisée en systèmes de sécurité incendie (SSI/CMSI), vidéosurveillance, \
courants faibles, et problématiques QHSE (Qualité, Hygiène, Sécurité, \
Environnement).

Zone prioritaire : La Réunion (974) et Mayotte (976).
Zone secondaire : Madagascar, Maurice, Comores, France métropole, International.

Cœur de métier DEF OI :
1. SSI : centrales incendie, détecteurs, déclencheurs manuels, CMSI, équipements \
d'alarme de type 1 à 4, tableaux de signalisation
2. Désenfumage / CMSI : volets de désenfumage, extracteurs de fumée, commandes \
manuelles centralisées
3. Vidéosurveillance / CCTV : caméras IP, enregistreurs NVR/DVR, VMS, analytics
4. Courants faibles : contrôle d'accès, interphonie, GTC/GTB, anti-intrusion
5. Maintenance réglementaire : vérifications annuelles SSI, MCO, contrats de \
service, GMAO
6. QHSE : audits incendie, formations sécurité incendie, accompagnement \
réglementaire ERP

EXCLURE impérativement (ne pas scorer > 20) :
- Gardiennage, agents de sécurité, SSIAP, rondes de sécurité
- Sécurité civile, pompiers, secours
- Génie civil pur, VRD, extincteurs seuls (sans composante SSI)
- Électricité générale (HT/BT) sans courants faibles

Réponds UNIQUEMENT en JSON valide :
{
  "score_pertinence": <entier 0-100>,
  "tag_pertinence": "Très pertinent" | "À évaluer" | "Hors périmètre",
  "type_marche": "Travaux" | "Maintenance" | "Fourniture" | "Mixte" | "Inconnu",
  "domaines_concernes": ["SSI", "CMSI", "Vidéosurveillance", "Courants faibles", \
"QHSE", "Maintenance"],
  "territoire": "La Réunion" | "Mayotte" | "Océan Indien" | "France métropole" | \
"International" | "Non précisé",
  "marques_concurrentes_citees": [],
  "risques_penalites": "texte court ou null",
  "justification_score": "1-2 phrases expliquant le score"
}

Barème : 80-100 = SSI/CMSI/vidéo direct sur 974/976 ; 60-79 = domaine présent \
+ territoire secondaire OU courants faibles/QHSE sur 974/976 ; 40-59 = signal \
ERP potentiel SSI ; 20-39 = faiblement pertinent ; 0-19 = hors périmètre.\
"""

_client = None


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


def _gemini_analyze(text: str) -> dict | None:
    """Tente une analyse via Gemini. Retourne None si indisponible ou quota dépassé."""
    client = _get_client()
    if client is None:
        return None
    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=f"Analyse ce marché :\n\n{text[:3000]}",
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
        if any(code in msg for code in ("429", "RESOURCE_EXHAUSTED", "quota", "401", "403", "API_KEY")):
            return None
        return None


# ---------------------------------------------------------------------------
# Analyse automatique en masse (local uniquement — sans quota)
# ---------------------------------------------------------------------------

def auto_analyze_pending(db) -> int:
    """Analyse tous les marchés sans llm_analysis. Moteur local uniquement."""
    from models import Tender
    pending = db.query(Tender).filter(Tender.llm_analysis == None).all()  # noqa: E711
    for t in pending:
        result = _local_analyze(f"{t.title or ''} {t.description or ''}")
        t.llm_analysis = result
        t.relevance_score = result.get("score_pertinence", 0)
        t.is_maintenance = result.get("type_marche", "").lower() == "maintenance"
    if pending:
        db.commit()
    return len(pending)


# ---------------------------------------------------------------------------
# Point d'entrée public
# ---------------------------------------------------------------------------

def analyze_tender(text: str) -> dict:
    """
    Analyse un appel d'offre. Essaie Gemini en premier, calcule un score combiné
    70 % Gemini + 30 % local. Fallback sur analyse locale si Gemini indisponible.
    """
    local_result = _local_analyze(text)
    gemini_result = _gemini_analyze(text)

    if gemini_result is not None:
        combined_score = compute_combined_score(
            gemini_score=gemini_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            gemini_available=True,
        )
        gemini_result["score_pertinence"] = combined_score
        gemini_result.setdefault("tag_pertinence", _score_to_tag(combined_score))
        gemini_result.setdefault("domaines_concernes", local_result.get("domaines_concernes", []))
        gemini_result.setdefault("justification_score", local_result.get("justification_score", ""))
        gemini_result.setdefault("territoire_ia", local_result.get("territoire_ia", "Non précisé"))
        return gemini_result

    return local_result
