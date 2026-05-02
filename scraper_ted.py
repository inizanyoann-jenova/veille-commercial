import hashlib
from datetime import datetime

import requests

from database import SessionLocal, init_db
from filters import is_relevant_def
from models import Tender

TED_API_URL = "https://api.ted.europa.eu/v3/notices/search"

_METIERS = (
    "FT~SSI OR FT~CMSI OR FT~incendie OR FT~desenfumage"
    " OR FT~videosurveillance OR FT~camera OR FT~CCTV"
)

# Une requête par zone géographique pour rester précis
QUERIES = {
    "La Réunion":  f"FT~974 AND ({_METIERS})",
    "Mayotte":     f"FT~Mayotte AND ({_METIERS})",
    "Madagascar":  f"FT~Madagascar AND ({_METIERS})",
    "Maurice":     f"FT~Mauritius AND ({_METIERS})",
    "Comores":     f"FT~Comoros AND ({_METIERS})",
}

_FIELDS = [
    "notice-title",
    "publication-number",
    "deadline-receipt-tender-date-lot",
    "description-glo",
]


def _extract_fr(field_value) -> str:
    """Extrait la valeur française d'un champ multilingue TED (dict ou list)."""
    if not field_value:
        return ""
    if isinstance(field_value, list):
        return " ".join(
            _extract_fr(item) for item in field_value if item
        ).strip()
    if isinstance(field_value, dict):
        return (field_value.get("fra") or field_value.get("eng")
                or next(iter(field_value.values()), "")) or ""
    return str(field_value)


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return None
    s = str(value)[:19]
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s[:len(fmt)], fmt)
        except ValueError:
            continue
    return None


def _fetch_query(db, query: str, inserted_ids: set) -> int:
    inserted = 0
    page = 1
    limit = 100

    while True:
        payload = {"query": query, "fields": _FIELDS, "page": page, "limit": limit}

        try:
            r = requests.post(TED_API_URL, json=payload, timeout=30)
            r.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"TED API inaccessible : {exc}") from exc

        notices = r.json().get("notices", [])
        if not notices:
            break

        for notice in notices:
            pub_num = notice.get("publication-number") or ""
            title = _extract_fr(notice.get("notice-title"))
            description = _extract_fr(notice.get("description-glo"))

            if not is_relevant_def(f"{title} {description}"):
                continue

            tender_id = (f"TED-{pub_num}" if pub_num
                         else f"TED-{hashlib.md5(title.encode()).hexdigest()[:12]}")

            if tender_id in inserted_ids:
                continue
            if db.query(Tender).filter(Tender.id == tender_id).first():
                inserted_ids.add(tender_id)
                continue

            links = notice.get("links", {})
            url_fr = ((links.get("html") or {}).get("FRA")
                      or f"https://ted.europa.eu/fr/notice/{pub_num}/html")

            db.add(Tender(
                id=tender_id,
                title=title or f"Avis TED {pub_num}",
                description=description,
                source=url_fr,
                publication_date=None,
                deadline=_parse_date(notice.get("deadline-receipt-tender-date-lot")),
                status="À qualifier",
                relevance_score=0,
                is_maintenance=False,
                llm_analysis=None,
            ))
            inserted_ids.add(tender_id)
            inserted += 1

        db.commit()
        if len(notices) < limit:
            break
        page += 1

    return inserted


def fetch_ted_tenders(zones: list[str] | None = None) -> int:
    """
    zones : liste de clés de QUERIES à collecter.
            Si None, collecte toutes les zones.
    """
    init_db()
    db = SessionLocal()
    inserted_ids: set = set()
    total = 0

    selected = {k: v for k, v in QUERIES.items() if zones is None or k in zones}

    try:
        for zone, query in selected.items():
            total += _fetch_query(db, query, inserted_ids)
    finally:
        db.close()

    return total


if __name__ == "__main__":
    print("Collecte TED (La Réunion & Mayotte)…")
    count = fetch_ted_tenders()
    print(f"Terminé — {count} nouveau(x) marché(s) TED inséré(s).")
