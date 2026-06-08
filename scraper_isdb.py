from datetime import timezone
"""
IsDB (Islamic Development Bank) — appels d'offres projets Océan Indien.
Source globale : filtrée sur pays OI et secteurs pertinents DEF.
Method: JS-rendered scraping via Playwright.
"""

from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_URL = "https://www.isdb.org/project-procurement"
_BASE = "https://www.isdb.org"
_CARD = "tr.views-row, .views-row, article.tender, li.tender, .procurement-item, table tbody tr"
_NEXT = "a[title='Go to next page'], li.pager__item--next a, .pager-next a"
_MAX_PAGES = 5

PAYS_OI = [
    "madagascar",
    "mauritius",
    "comoros",
    "comores",
    "maldives",
    "mozambique",
    "tanzania",
    "kenya",
    "djibouti",
    "somalia",
    "indian ocean",
    "océan indien",
    "réunion",
    "reunion",
    "mayotte",
]

SECTEURS_PERTINENTS = [
    "health",
    "hospital",
    "santé",
    "education",
    "school",
    "university",
    "infrastructure",
    "transport",
    "water",
    "energy",
    "housing",
    "construction",
    "urban",
    "public",
    "fire",
    "safety",
    "security",
    "ssi",
    "surveillance",
    "electrical",
    "building",
]


def _is_relevant(title: str, description: str) -> bool:
    text = f"{title} {description}".lower()
    geo_ok = any(p in text for p in PAYS_OI)
    secteur_ok = any(s in text for s in SECTEURS_PERTINENTS)
    return geo_ok and secteur_ok


def fetch() -> list[dict]:
    """
    Returns IsDB procurement items relevant to Indian Ocean countries.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            try:
                page.goto(_URL, timeout=30_000)
                page.wait_for_load_state("networkidle", timeout=30_000)
            except Exception:
                return results

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

    title = text("td.views-field-title, .views-field-title, h3, h2, td:first-child")
    description = text(
        "td.views-field-body, .views-field-body, .description, td:nth-child(2)"
    )
    url = href("a")
    date = text("td.views-field-field-date, .date, time")

    if url and not url.startswith("http"):
        url = f"{_BASE}{url}"

    return {
        "name": title,
        "description": description,
        "url": url or _URL,
        "raw_date": date,
    }


def _normalise(raw: dict) -> dict:
    """Convert extracted card data to standard schema."""
    raw_date = raw.get("raw_date") or ""
    try:
        publication_date = (
            datetime.fromisoformat(raw_date[:10]).date().isoformat() if raw_date else ""
        )
    except ValueError:
        publication_date = raw_date

    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _URL),
        "source": "IsDB",
        "date_found": datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "description": raw.get("description", ""),
    }
