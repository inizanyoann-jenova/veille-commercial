"""
TED (Tenders Electronic Daily — Journal Officiel UE) — appels d'offres
Océan Indien : La Réunion, Mayotte, Madagascar, Maurice, Comores.
Method: REST API POST avec pagination par token (TED v3).
"""

import os
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
    "Content-Type": "application/json",
}

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"

_METIERS = (
    "FT~SSI OR FT~CMSI OR FT~incendie OR FT~desenfumage"
    " OR FT~videosurveillance OR FT~camera OR FT~CCTV"
)
_CONSTRUCTION = (
    "FT~construction OR FT~chantier OR FT~travaux OR FT~rehabilitation"
    " OR FT~renovation OR FT~extension OR FT~restructuration OR FT~amenagement"
)
_ERP = (
    "FT~hopital OR FT~clinique OR FT~ehpad OR FT~hotel OR FT~ecole"
    " OR FT~lycee OR FT~college OR FT~universite OR FT~gymnase"
    " OR FT~stade OR FT~mairie OR FT~tribunal OR FT~aeroport OR FT~gare"
)
# Codes CPV SSI : alarme incendie, matériel, maintenance, anti-intrusion, contrôle accès
_CPV = (
    "PC=45312100 OR PC=35111300 OR PC=50610000"
    " OR PC=45312200 OR PC=42961000 OR PC=35111000"
)
_IMPLICITE_ERP = f"(({_CONSTRUCTION}) AND ({_ERP}))"
_PUBLIC_SEARCH = f"({_METIERS}) OR ({_IMPLICITE_ERP}) OR ({_CPV})"

# Variantes géographiques Mayotte — villes et gentilé pour meilleure couverture TED
_MAYOTTE_GEO = (
    "FT~Mayotte OR FT~Mahorais OR FT~Mamoudzou"
    " OR FT~Kaweni OR FT~Dzaoudzi OR FT~Koungou OR FT~Bandraboua"
)

QUERIES = {
    # ND (NUTS code) cible précisément La Réunion (FRY1) — évite les faux positifs
    # sur tout document contenant "974" dans un champ quelconque
    "La Réunion": f"ND=FRY1 AND ({_PUBLIC_SEARCH})",
    # FRY5 = Mayotte (NUTS 2021) + variantes textuelles pour couverture maximale
    "Mayotte": f"(ND=FRY5 OR ({_MAYOTTE_GEO})) AND ({_PUBLIC_SEARCH})",
    "Madagascar": f"FT~Madagascar AND ({_PUBLIC_SEARCH})",
    "Maurice": f"FT~Mauritius AND ({_PUBLIC_SEARCH})",
    "Comores": f"FT~Comoros AND ({_PUBLIC_SEARCH})",
}

_FIELDS = [
    "notice-title",
    "publication-number",
    "publication-date",
    "deadline-receipt-tender-date-lot",
    "description-glo",
]


def _extract_fr(field_value) -> str:
    """Extract French text from multilingual TED field (fallback to English)."""
    if not field_value:
        return ""
    if isinstance(field_value, list):
        return " ".join(_extract_fr(item) for item in field_value if item).strip()
    if isinstance(field_value, dict):
        return (
            field_value.get("fra")
            or field_value.get("eng")
            or next(iter(field_value.values()), "")
        ) or ""
    return str(field_value)


def _parse_ted_date(raw) -> str:
    """Parse TED date field to ISO string."""
    if not raw:
        return ""
    val = raw if isinstance(raw, str) else str(raw)
    try:
        return datetime.fromisoformat(val[:10]).date().isoformat()
    except ValueError:
        return val


def _fetch_zone(query: str, date_from: str) -> list[dict]:
    """Paginate TED API for one zone query and return normalised results."""
    results = []
    limit = 100
    token: str | None = None

    # TED PD>= exige YYYYMMDD sans tirets
    full_query = f"({query}) AND PD>={date_from}"

    while True:
        payload: dict = {
            "query": full_query,
            "fields": _FIELDS,
            "limit": limit,
            "paginationMode": "ITERATION",
            "scope": "ACTIVE",
        }
        if token:
            payload["iterationNextToken"] = token

        try:
            resp = requests.post(TED_API_URL, headers=HEADERS, json=payload, timeout=30)
        except requests.RequestException:
            break

        if resp.status_code != 200:
            break

        data = resp.json()
        notices = data.get("notices", [])
        if not notices:
            break

        for notice in notices:
            results.append(_normalise(notice))

        token = data.get("iterationNextToken")
        if not token or len(notices) < limit:
            break

    return results


def fetch() -> list[dict]:
    """
    Returns TED EU tenders for Indian Ocean zones.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    window_days = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
    # TED date format : YYYYMMDD sans tirets
    date_from = (datetime.now(timezone.utc) - timedelta(days=window_days)).strftime(
        "%Y%m%d"
    )

    results = []
    for zone, query in QUERIES.items():
        zone_results = _fetch_zone(query, date_from)
        for item in zone_results:
            item["zone"] = zone
        results.extend(zone_results)

    return results


def _normalise(notice: dict) -> dict:
    """Convert raw TED notice to standard schema."""
    pub_num = notice.get("publication-number") or ""
    title = _extract_fr(notice.get("notice-title")) or f"Avis TED {pub_num}"
    description = _extract_fr(notice.get("description-glo"))

    links = notice.get("links", {})
    url_fr = (links.get("html") or {}).get("FRA") or (
        f"https://ted.europa.eu/fr/notice/{pub_num}/html"
        if pub_num
        else "https://ted.europa.eu"
    )

    deadline = _parse_ted_date(notice.get("deadline-receipt-tender-date-lot"))

    return {
        "name": title,
        "url": url_fr,
        "source": "TED Europe",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": _parse_ted_date(notice.get("publication-date")),
        "deadline": deadline,
        "description": description,
        "ted_id": pub_num,
        "zone": "",  # renseigné par fetch()
    }
