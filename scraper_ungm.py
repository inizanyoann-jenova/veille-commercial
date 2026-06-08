from datetime import timezone
"""
UNGM (United Nations Global Marketplace) — appels d'offres Océan Indien.
Source globale : filtrée par mots-clés SSI/incendie puis par pays OI.
Method: REST API POST (UNGM SearchNotices).
"""

import requests
from datetime import datetime, timezone

from scraper_utils import retry_post

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DEF-OI-Veille/1.0)",
    "Accept": "application/json, text/html, */*",
    "Content-Type": "application/json",
    "X-Requested-With": "XMLHttpRequest",
}

UNGM_SEARCH_URL = "https://www.ungm.org/Public/Notice/SearchNotices"

_UNGM_KEYWORDS = [
    "fire detection",
    "SSI",
    "fire alarm",
    "fire safety",
    "smoke detection",
    "CCTV",
    "surveillance",
    "access control",
]

# Pays OI : codes ISO + noms pour filtrer les résultats globaux UNGM
_COUNTRY_CODES_OI = ["MG", "MU", "KM", "RE", "YT", "FR", "DJ", "MZ", "TZ", "SC"]

PAYS_OI = [
    "madagascar",
    "mauritius",
    "île maurice",
    "ile maurice",
    "comoros",
    "comores",
    "réunion",
    "reunion",
    "mayotte",
    "djibouti",
    "mozambique",
    "tanzania",
    "seychelles",
    "indian ocean",
    "océan indien",
]


def _is_relevant_oi(title: str, description: str, country_code: str = "") -> bool:
    if country_code.upper() in _COUNTRY_CODES_OI:
        return True
    text = f"{title} {description}".lower()
    return any(p in text for p in PAYS_OI)


def _search_ungm(keyword: str) -> list[dict]:
    """POST one keyword search to UNGM API. Returns [] on failure."""
    payload = {
        "Title": keyword,
        "Description": "",
        "GoodsServices": "",
        "Deadline": None,
        "PublishedFrom": None,
        "CountryCodes": _COUNTRY_CODES_OI,
        "AgencyId": None,
        "Status": 0,
    }
    try:
        resp = retry_post(UNGM_SEARCH_URL, json=payload, headers=HEADERS, timeout=30)
        data = resp.json()
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("Notices", data.get("notices", data.get("results", [])))
    except requests.RequestException:
        pass
    return []


def fetch() -> list[dict]:
    """
    Returns UNGM tenders relevant to Indian Ocean countries.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []
    seen_ids = set()

    for keyword in _UNGM_KEYWORDS:
        notices = _search_ungm(keyword)

        for notice in notices:
            title = (
                notice.get("Title")
                or notice.get("title")
                or notice.get("NoticeTitle")
                or ""
            )
            description = (
                notice.get("Description")
                or notice.get("description")
                or notice.get("GoodsServices")
                or ""
            )
            country = notice.get("CountryCode") or notice.get("countryCode") or ""

            if not title.strip():
                continue
            if not _is_relevant_oi(title, description, country):
                continue

            uid = notice.get("Id") or notice.get("id") or notice.get("NoticeId") or ""
            if uid and uid in seen_ids:
                continue
            if uid:
                seen_ids.add(uid)

            results.append(_normalise(notice, title, description, uid))

    return results


def _normalise(notice: dict, title: str, description: str, uid: str) -> dict:
    """Convert raw UNGM notice to standard schema."""

    def _pick(*keys):
        for k in keys:
            v = notice.get(k)
            if v:
                return str(v)
        return ""

    def _to_iso(raw: str) -> str:
        if not raw:
            return ""
        try:
            return datetime.fromisoformat(raw[:10]).date().isoformat()
        except ValueError:
            return raw

    url = _pick("Url", "url") or (
        f"https://www.ungm.org/Public/Notice/{uid}" if uid else "https://www.ungm.org"
    )

    return {
        "name": title,
        "url": url,
        "source": "UNGM",
        "date_found": datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat(),
        "publication_date": _to_iso(
            _pick("PublishedOn", "publishedOn", "PublicationDate")
        ),
        "deadline": _to_iso(_pick("Deadline", "deadline", "SubmissionDeadline")),
        "description": description,
        "ungm_id": uid,
    }
