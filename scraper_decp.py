"""
DECP (Données Essentielles de la Commande Publique) — marchés notifiés
La Réunion (974) et Mayotte (976) : SSI, CPV sécurité, construction, ERP.
Method: REST API (data.economie.gouv.fr v2.1 — dataset decp-2022-marches-valides)
"""

import os
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}

DECP_API = (
    "https://data.economie.gouv.fr/api/explore/v2.1"
    "/catalog/datasets/decp-2022-marches-valides/records"
)

_DEPT_FILTER = 'lieuexecution_code like "974%" OR lieuexecution_code like "976%"'

_KEYWORD_FILTER = (
    'search(objet, "SSI")'
    ' OR search(objet, "CMSI")'
    ' OR search(objet, "incendie")'
    ' OR search(objet, "desenfumage")'
    ' OR search(objet, "videosurveillance")'
    ' OR search(objet, "camera")'
    ' OR search(objet, "CCTV")'
    ' OR search(objet, "courants faibles")'
)

_CPV_FILTER = (
    'search(codecpv, "45312100")'
    ' OR search(codecpv, "35111300")'
    ' OR search(codecpv, "50610000")'
    ' OR search(codecpv, "45312200")'
    ' OR search(codecpv, "42961000")'
    ' OR search(codecpv, "35111000")'
)

_CONSTRUCTION_FILTER = (
    'search(objet, "construction")'
    ' OR search(objet, "chantier")'
    ' OR search(objet, "travaux")'
    ' OR search(objet, "rehabilitation")'
    ' OR search(objet, "renovation")'
    ' OR search(objet, "extension")'
    ' OR search(objet, "restructuration")'
    ' OR search(objet, "amenagement")'
)

_ERP_FILTER = (
    'search(objet, "hopital")'
    ' OR search(objet, "clinique")'
    ' OR search(objet, "ehpad")'
    ' OR search(objet, "ecole")'
    ' OR search(objet, "lycee")'
    ' OR search(objet, "college")'
    ' OR search(objet, "universite")'
    ' OR search(objet, "gymnase")'
    ' OR search(objet, "stade")'
    ' OR search(objet, "mairie")'
    ' OR search(objet, "tribunal")'
    ' OR search(objet, "aeroport")'
    ' OR search(objet, "gare")'
)

_SEARCH_FILTER = f"({_KEYWORD_FILTER}) OR ({_CPV_FILTER}) OR ({_CONSTRUCTION_FILTER}) OR ({_ERP_FILTER})"


def fetch() -> list[dict]:
    """
    Returns DECP tenders for La Réunion (974) and Mayotte (976).
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []
    # Dataset publication lag ~6 weeks — use 90 days minimum to avoid missing recent data
    days_back = int(os.getenv("DECP_WINDOW_DAYS", "90"))
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
    objet = raw.get("objet") or f"Marché DECP {uid}"
    acheteur = raw.get("acheteur_id") or ""
    lieu_code = raw.get("lieuexecution_code") or ""
    cpv = raw.get("codecpv") or ""
    montant = raw.get("montant")

    raw_date = raw.get("datenotification") or ""
    try:
        publication_date = (
            datetime.fromisoformat(str(raw_date)[:10]).date().isoformat() if raw_date else ""
        )
    except ValueError:
        publication_date = str(raw_date)

    return {
        "name": objet,
        "url": (
            f"https://data.economie.gouv.fr/explore/dataset/decp-2022-marches-valides/table/?q={uid}"
            if uid
            else "https://data.economie.gouv.fr"
        ),
        "source": "DECP",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "acheteur": acheteur,
        "departement": lieu_code,
        "cpv": cpv,
        "decp_id": uid,
        "amount": montant,
    }
