"""
DECP (Données Essentielles de la Commande Publique) — marchés notifiés
La Réunion (974) et Mayotte (976) : SSI, CPV sécurité, construction, ERP.
Method: REST API (data.economie.gouv.fr v2.1)
"""

import os
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp_augmente/records"
)

_DEPT_FILTER = 'codedepartementexecution in ("974", "976")'

_KEYWORD_FILTER = (
    'search(objetmarche, "SSI")'
    ' OR search(objetmarche, "CMSI")'
    ' OR search(objetmarche, "incendie")'
    ' OR search(objetmarche, "desenfumage")'
    ' OR search(objetmarche, "videosurveillance")'
    ' OR search(objetmarche, "camera")'
    ' OR search(objetmarche, "CCTV")'
    ' OR search(objetmarche, "courants faibles")'
)

# Codes CPV SSI — si trop de faux positifs, basculer sur égalité directe : codecpv = "45312100"
_CPV_FILTER = (
    'search(codecpv, "45312100")'
    ' OR search(codecpv, "35111300")'
    ' OR search(codecpv, "50610000")'
    ' OR search(codecpv, "45312200")'
    ' OR search(codecpv, "42961000")'
    ' OR search(codecpv, "35111000")'
)

_CONSTRUCTION_FILTER = (
    'search(objetmarche, "construction")'
    ' OR search(objetmarche, "chantier")'
    ' OR search(objetmarche, "travaux")'
    ' OR search(objetmarche, "réhabilitation")'
    ' OR search(objetmarche, "rehabilitation")'
    ' OR search(objetmarche, "rénovation")'
    ' OR search(objetmarche, "renovation")'
    ' OR search(objetmarche, "extension")'
    ' OR search(objetmarche, "restructuration")'
    ' OR search(objetmarche, "aménagement")'
    ' OR search(objetmarche, "amenagement")'
)

_ERP_FILTER = (
    'search(objetmarche, "hôpital")'
    ' OR search(objetmarche, "hopital")'
    ' OR search(objetmarche, "clinique")'
    ' OR search(objetmarche, "ehpad")'
    ' OR search(objetmarche, "école")'
    ' OR search(objetmarche, "ecole")'
    ' OR search(objetmarche, "lycée")'
    ' OR search(objetmarche, "lycee")'
    ' OR search(objetmarche, "collège")'
    ' OR search(objetmarche, "college")'
    ' OR search(objetmarche, "université")'
    ' OR search(objetmarche, "universite")'
    ' OR search(objetmarche, "centre commercial")'
    ' OR search(objetmarche, "gymnase")'
    ' OR search(objetmarche, "stade")'
    ' OR search(objetmarche, "mairie")'
    ' OR search(objetmarche, "tribunal")'
    ' OR search(objetmarche, "aéroport")'
    ' OR search(objetmarche, "aeroport")'
    ' OR search(objetmarche, "gare")'
)

_SEARCH_FILTER = f"({_KEYWORD_FILTER}) OR ({_CPV_FILTER}) OR ({_CONSTRUCTION_FILTER}) OR ({_ERP_FILTER})"


def fetch() -> list[dict]:
    """
    Returns DECP tenders for La Réunion (974) and Mayotte (976).
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []
    days_back = int(os.getenv("DECP_WINDOW_DAYS", "30"))
    date_min = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%d"
    )
    where = (
        f"({_DEPT_FILTER})"
        f" AND ({_SEARCH_FILTER})"
        f' AND (datenotification >= "{date_min}")'
    )

    offset = 0
    limit = 100

    while True:
        params = {
            "where": where,
            "limit": limit,
            "offset": offset,
            "order_by": "datenotification DESC",
        }

        try:
            resp = requests.get(DECP_API, headers=HEADERS, params=params, timeout=15)
        except requests.RequestException:
            break

        if resp.status_code != 200:
            break

        records = resp.json().get("results", [])
        if not records:
            break

        for rec in records:
            results.append(_normalise(rec))

        if len(records) < limit:
            break
        offset += limit

    return results


def _normalise(raw: dict) -> dict:
    """Convert raw DECP API record to standard schema."""
    uid = raw.get("id") or ""
    objet = raw.get("objetmarche") or f"Marché DECP {uid}"
    acheteur = raw.get("nomacheteur") or ""
    dept = raw.get("codedepartementexecution") or ""
    cpv = raw.get("codecpv") or ""

    raw_date = raw.get("datenotification") or ""
    try:
        publication_date = (
            datetime.fromisoformat(raw_date[:10]).date().isoformat() if raw_date else ""
        )
    except ValueError:
        publication_date = raw_date

    return {
        "name": objet,
        "url": f"https://data.economie.gouv.fr/explore/dataset/decp_augmente/table/?q={uid}"
        if uid
        else "https://data.economie.gouv.fr",
        "source": "DECP",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "acheteur": acheteur,
        "departement": dept,
        "cpv": cpv,
        "decp_id": uid,
    }
