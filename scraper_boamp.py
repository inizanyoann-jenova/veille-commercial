"""
BOAMP (Bulletin Officiel des Annonces des Marchés Publics) — appels d'offres
ciblés La Réunion (974) et Mayotte (976) : SSI, incendie, construction, ERP.
Method: REST API (OpenData BOAMP v2.1)
"""

import os
from datetime import datetime, timedelta, timezone

from scraper_utils import retry_get

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}

BOAMP_API_URL = (
    "https://boamp-datadila.opendatasoft.com/api/explore/v2.1"
    "/catalog/datasets/boamp/records"
)

DEPARTMENTS = ["974", "976"]

_KEYWORD_FILTER = (
    "objet like '%SSI%'"
    " OR objet like '%CMSI%'"
    " OR objet like '%incendie%'"
    " OR objet like '%désenfumage%'"
    " OR objet like '%desenfumage%'"
    " OR objet like '%vidéosurveillance%'"
    " OR objet like '%videosurveillance%'"
    " OR objet like '%caméra%'"
    " OR objet like '%camera%'"
    " OR objet like '%CCTV%'"
    " OR objet like '%courants faibles%'"
)

_CONSTRUCTION_FILTER = (
    "objet like '%construction%'"
    " OR objet like '%chantier%'"
    " OR objet like '%travaux%'"
    " OR objet like '%réhabilitation%'"
    " OR objet like '%rehabilitation%'"
    " OR objet like '%rénovation%'"
    " OR objet like '%renovation%'"
    " OR objet like '%extension%'"
    " OR objet like '%restructuration%'"
    " OR objet like '%aménagement%'"
    " OR objet like '%amenagement%'"
)

_ERP_FILTER = (
    "objet like '%hôpital%'"
    " OR objet like '%hopital%'"
    " OR objet like '%clinique%'"
    " OR objet like '%ehpad%'"
    " OR objet like '%hôtel%'"
    " OR objet like '%hotel%'"
    " OR objet like '%école%'"
    " OR objet like '%ecole%'"
    " OR objet like '%lycée%'"
    " OR objet like '%lycee%'"
    " OR objet like '%collège%'"
    " OR objet like '%college%'"
    " OR objet like '%université%'"
    " OR objet like '%universite%'"
    " OR objet like '%centre commercial%'"
    " OR objet like '%gymnase%'"
    " OR objet like '%stade%'"
    " OR objet like '%mairie%'"
    " OR objet like '%tribunal%'"
    " OR objet like '%aéroport%'"
    " OR objet like '%aeroport%'"
    " OR objet like '%gare%'"
)

_SEARCH_FILTER = f"({_KEYWORD_FILTER}) OR ({_CONSTRUCTION_FILTER}) OR ({_ERP_FILTER})"


def fetch() -> list[dict]:
    """
    Returns BOAMP tenders for La Réunion (974) and Mayotte (976).
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []
    days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
    date_min = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%d"
    )

    for dept in DEPARTMENTS:
        offset = 0
        limit = 100

        while True:
            params = {
                "where": (
                    f"code_departement='{dept}'"
                    f" AND ({_SEARCH_FILTER})"
                    f" AND dateparution >= '{date_min}'"
                ),
                "limit": limit,
                "offset": offset,
                "order_by": "dateparution DESC",
                # Champs enrichis : nature, procédure, acheteur pour améliorer l'analyse LLM
                "select": (
                    "idweb,url_avis,objet,dateparution,datelimitereponse,"
                    "descripteur_libelle,famille_libelle,nature_libelle,"
                    "procedure_libelle,nomacheteur,code_departement"
                ),
            }

            try:
                resp = retry_get(
                    BOAMP_API_URL, headers=HEADERS, params=params, timeout=15
                )
            except Exception:
                break

            records = resp.json().get("results", [])
            if not records:
                break

            for rec in records:
                results.append(_normalise(rec, dept))

            if len(records) < limit:
                break
            offset += limit

    return results


def _normalise(raw: dict, dept: str = "") -> dict:
    """Convert raw BOAMP API record to standard schema."""
    idweb = raw.get("idweb") or ""
    url = raw.get("url_avis") or (
        f"https://www.boamp.fr/aides-a-la-recherche/detail/{idweb}"
        if idweb
        else "https://www.boamp.fr"
    )

    descripteurs = raw.get("descripteur_libelle") or []
    cpv = (
        ", ".join(descripteurs)
        if isinstance(descripteurs, list)
        else str(descripteurs or "")
    )

    # Description enrichie : CPV + métadonnées BOAMP pour améliorer l'analyse LLM
    desc_parts = []
    if isinstance(descripteurs, list) and descripteurs:
        desc_parts.append("CPV : " + ", ".join(descripteurs))
    for field, label in (
        ("nature_libelle", "Nature"),
        ("famille_libelle", "Type"),
        ("procedure_libelle", "Procédure"),
        ("nomacheteur", "Acheteur"),
    ):
        val = raw.get(field) or ""
        if val:
            desc_parts.append(f"{label} : {val}")
    description = " | ".join(desc_parts) if desc_parts else cpv

    # publication_date en ISO pour lecture IA
    raw_date = raw.get("dateparution") or ""
    try:
        publication_date = (
            datetime.fromisoformat(raw_date[:10]).date().isoformat() if raw_date else ""
        )
    except ValueError:
        publication_date = raw_date

    raw_deadline = raw.get("datelimitereponse") or ""
    try:
        deadline = (
            datetime.fromisoformat(raw_deadline[:10]).date().isoformat()
            if raw_deadline
            else ""
        )
    except ValueError:
        deadline = raw_deadline

    return {
        "name": raw.get("objet") or f"Marché BOAMP {idweb}",
        "url": url,
        "source": "BOAMP",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "departement": dept,
        "description": description,
        "boamp_id": idweb,
        "cpv": cpv,
    }
