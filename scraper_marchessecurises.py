"""
Marchés Sécurisés — appels d'offres La Réunion (974) et Mayotte (976).
Method: JS-rendered scraping via Playwright avec authentification.
Credentials: MARCHESSECURISES_LOGIN et MARCHESSECURISES_PASSWORD.
"""

import os
from datetime import datetime, timezone

from scraper_utils import parse_date as _parse_date

from playwright.sync_api import sync_playwright

_LOGIN_URL = "https://www.marches-securises.fr/entreprise/?page=connexion"
_SEARCH_URL = (
    "https://www.marches-securises.fr/entreprise/?page=entreprise_dce_recherche"
)
_BASE = "https://www.marches-securises.fr"
_CARD = "table.tableau tr.ligneMarche, .liste-dce tr, tr[class*='ligne']"
_NEXT = "a.suivant, a[title='Suivant'], .page-suivante"
_MAX_PAGES = 5

_LOGIN_SELECTORS = {
    "email": "input[name='login'], input[type='email'], #login",
    "password": "input[name='pass'], input[type='password'], #password",
    "submit": "input[type='submit'], button[type='submit']",
}

# Filtre DEF OI appliqué post-extraction (URL de recherche générique sans filtre géo)
PAYS_OI = [
    "réunion",
    "reunion",
    "974",
    "mayotte",
    "976",
    "madagascar",
    "comores",
    "comoros",
    "maurice",
    "mauritius",
    "océan indien",
    "ocean indien",
]

SECTEURS_PERTINENTS = [
    "ssi",
    "cmsi",
    "incendie",
    "désenfumage",
    "desenfumage",
    "vidéosurveillance",
    "videosurveillance",
    "caméra",
    "camera",
    "cctv",
    "courants faibles",
    "construction",
    "travaux",
    "réhabilitation",
    "rehabilitation",
    "rénovation",
    "renovation",
    "extension",
    "aménagement",
    "amenagement",
    "hôpital",
    "hopital",
    "clinique",
    "école",
    "ecole",
    "lycée",
    "lycee",
    "mairie",
    "infrastructure",
]


def _is_relevant(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    geo_ok = any(p in text for p in PAYS_OI)
    secteur_ok = any(s in text for s in SECTEURS_PERTINENTS)
    return geo_ok or secteur_ok


def _login(page, login: str, password: str) -> bool:
    try:
        page.goto(_LOGIN_URL, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.fill(_LOGIN_SELECTORS["email"], login)
        page.fill(_LOGIN_SELECTORS["password"], password)
        page.click(_LOGIN_SELECTORS["submit"])
        page.wait_for_load_state("networkidle", timeout=20_000)
        return _LOGIN_URL not in page.url
    except Exception:
        return False


def fetch() -> list[dict]:
    """
    Returns Marchés Sécurisés tenders relevant to La Réunion and Mayotte.
    Requires MARCHESSECURISES_LOGIN and MARCHESSECURISES_PASSWORD environment variables.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    login_val = os.getenv("MARCHESSECURISES_LOGIN", "")
    password = os.getenv("MARCHESSECURISES_PASSWORD", "")

    if not login_val or not password:
        return []

    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            try:
                if not _login(page, login_val, password):
                    return results

                page.goto(_SEARCH_URL, timeout=30_000)
                page.wait_for_load_state("networkidle", timeout=30_000)

                for _ in range(_MAX_PAGES):
                    cards = page.query_selector_all(_CARD)
                    for card in cards:
                        raw = _extract_card(card)
                        if raw.get("name") and _is_relevant(
                            raw["name"], raw.get("description", "")
                        ):
                            results.append(_normalise(raw))

                    next_btn = page.query_selector(_NEXT)
                    if not next_btn:
                        break
                    next_btn.click()
                    try:
                        page.wait_for_load_state("networkidle", timeout=15_000)
                    except Exception:
                        break

            finally:
                page.close()
        finally:
            browser.close()

    return results


def _extract_card(card) -> dict:
    """Extract raw fields from a Playwright element handle."""

    def text(selector):
        el = card.query_selector(selector)
        return el.inner_text().strip() if el else ""

    def href(selector):
        el = card.query_selector(selector)
        return el.get_attribute("href") or "" if el else ""

    title = text("td.objet, .objet, td:nth-child(2)")
    description = text("td.pa, .organisme-acheteur, td:nth-child(3)")
    url = href("a")
    date = text("td.date-publication, td.date, td:nth-child(4)")
    deadline = text("td.date-limite, .date-limite, td:last-child")

    if url and not url.startswith("http"):
        url = f"{_BASE}{url}"

    return {
        "name": title,
        "description": description,
        "url": url or _SEARCH_URL,
        "raw_date": date,
        "raw_deadline": deadline,
    }


def _normalise(raw: dict) -> dict:
    """Convert extracted card data to standard schema."""
    pub_dt = _parse_date(raw.get("raw_date") or "")
    publication_date = pub_dt.date().isoformat() if pub_dt else ""

    dl_dt = _parse_date(raw.get("raw_deadline") or "")
    deadline = dl_dt.date().isoformat() if dl_dt else ""

    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _SEARCH_URL),
        "source": "Marchés Sécurisés",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "description": raw.get("description", ""),
    }
