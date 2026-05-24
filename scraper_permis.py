"""
Permis de Construire — DiDo v1 (SDES).
Récupère les permis autorisés sur La Réunion (974) et Mayotte (976).
Method: REST API (DiDo — données statistiques développement durable).
"""

import os
import requests
from datetime import datetime, timedelta, timezone

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)",
}

DIDO_BASE = "https://data.statistiques.developpement-durable.gouv.fr/dido/api/v1"
_PAGE_SIZE = 100

DATAFILES = {
    "Locaux non résidentiels": "f8f0700f-806c-40a7-83b1-f21cf507e7c4",
    "Logements": "8b35affb-55fc-4c1f-915b-7750f974446a",
}

_DEST_LABELS = {
    "1": "Habitation",
    "2": "Exploitation agricole",
    "3": "Bureaux",
    "4": "Commerce et services",
    "5": "Industrie",
    "6": "Industrie",
    "7": "Entrepôt",
    "8": "Service public / ERP",
    "9": "Divers",
}

_DATASET_URL = (
    "https://www.statistiques.developpement-durable.gouv.fr"
    "/catalogue?page=datafile&datafileRid={}"
)


def _fetch_dataset(rid: str, label: str, date_from: str) -> list[dict]:
    """Paginate through one DiDo dataset and return normalised records."""
    results = []
    page = 1

    while True:
        params = {
            "pageSize": _PAGE_SIZE,
            "page": page,
            "DEP_CODE": "in:974,976",
            "DATE_REELLE_AUTORISATION": f"gte:{date_from}",
        }
        try:
            resp = requests.get(
                f"{DIDO_BASE}/datafiles/{rid}/rows",
                headers=HEADERS,
                params=params,
                timeout=15,
            )
        except requests.RequestException:
            break

        if resp.status_code != 200:
            break

        records = resp.json().get("data", [])
        if not records:
            break

        for rec in records:
            results.append(_normalise(rec, rid))

        if len(records) < _PAGE_SIZE:
            break
        page += 1

    return results


def fetch() -> list[dict]:
    """
    Returns building permits for La Réunion (974) and Mayotte (976).
    Each item: name, url, source, date_found + domain-specific fields.
    """
    days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "30"))
    date_from = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%d"
    )

    results = []
    for label, rid in DATAFILES.items():
        results.extend(_fetch_dataset(rid, label, date_from))

    return results


def _normalise(raw: dict, rid: str = "") -> dict:
    """Convert raw DiDo permit record to standard schema."""
    dep = raw.get("DEP_CODE") or ""
    comm = raw.get("ADR_LOCALITE_TER") or raw.get("COMM") or dep
    dest = _DEST_LABELS.get(str(raw.get("DESTINATION_PRINCIPALE") or ""), "Bâtiment")
    surf = (
        raw.get("SURF_LOC_CREEE")
        or raw.get("SURF_HAB_CREEE")
        or raw.get("SURF_PUB_CREEE")
        or raw.get("SURF_COM_CREEE")
        or 0
    )
    surf_txt = f" — {surf} m²" if surf else ""
    demandeur = raw.get("DENOM_DEM") or ""
    adresse = " ".join(
        filter(
            None,
            [
                raw.get("ADR_NUM_TER"),
                raw.get("ADR_LIBVOIE_TER"),
                comm,
                raw.get("ADR_CODPOST_TER"),
            ],
        )
    )

    raw_date = raw.get("DATE_REELLE_AUTORISATION") or raw.get("DR_DEPOT") or ""
    try:
        publication_date = (
            datetime.fromisoformat(raw_date[:10]).date().isoformat() if raw_date else ""
        )
    except ValueError:
        publication_date = raw_date

    description = (
        f"Permis de construire — Département {dep}\n"
        f"Nature : {dest}{surf_txt}\n"
        f"Adresse : {adresse or 'Non renseignée'}\n"
        + (f"Demandeur : {demandeur}\n" if demandeur else "")
        + f"Type DAU : {raw.get('TYPE_DAU') or 'PC'}"
    )

    return {
        "name": f"[PC] {dest}{surf_txt} — {comm} ({dep})",
        "url": _DATASET_URL.format(rid),
        "source": "Permis de Construire (DiDo)",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "departement": dep,
        "destination": dest,
        "surface_m2": surf,
        "adresse": adresse,
        "demandeur": demandeur,
        "num_dau": raw.get("NUM_DAU") or "",
        "description": description,
    }
