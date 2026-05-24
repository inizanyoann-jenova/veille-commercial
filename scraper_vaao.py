"""
VAAO — appels d'offres La Réunion et Mayotte.
Method: JS-rendered scraping via Playwright.
"""

from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_URLS = [
    "https://www.vaao.fr/departement/la-reunion",
    "https://www.vaao.fr/departement/mayotte",
]
_BASE = "https://www.vaao.fr"
_CARD = ".views-row, article.node--type-appel-offre, .appel-offre-item, article"
_NEXT = "a[rel='next'], li.pager__item--next > a, .pager-next a"
_MAX_PAGES = 5


def fetch() -> list[dict]:
    """
    Returns VAAO tenders for La Réunion and Mayotte.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for base_url in _URLS:
                page = browser.new_page()
                try:
                    try:
                        page.goto(base_url, timeout=30_000)
                        page.wait_for_load_state("networkidle", timeout=30_000)
                    except Exception:
                        continue

                    for _ in range(_MAX_PAGES):
                        cards = page.query_selector_all(_CARD)
                        for card in cards:
                            raw = _extract_card(card, base_url)
                            if raw.get("name"):
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


def _extract_card(card, base_url: str = "") -> dict:
    """Extract raw fields from a Playwright element handle."""

    def text(selector):
        el = card.query_selector(selector)
        return el.inner_text().strip() if el else ""

    def href(selector):
        el = card.query_selector(selector)
        return el.get_attribute("href") or "" if el else ""

    title = text("h3, h2, .node__title, .title")
    description = text(".field--name-body, .description, .body")
    url = href("a")
    date = text("time, .date, .field--name-field-date")

    if url and not url.startswith("http"):
        url = f"{_BASE}{url}"

    return {
        "name": title,
        "description": description,
        "url": url or base_url,
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
        "url": raw.get("url", _BASE),
        "source": "VAAO",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "description": raw.get("description", ""),
    }
