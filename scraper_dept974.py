"""
Marchés Publics — Département de La Réunion (974).
Method: JS-rendered scraping via Playwright (plateforme e-marchespublics).
"""

from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_URL = "https://cg974.e-marchespublics.com/"
_BASE = "https://cg974.e-marchespublics.com"
_CARD = "tr.ligneMarche, .liste-marche tr, .avis-marche, li.marche"
_NEXT = "a.suivant, a[title='Page suivante'], .pagination-next a"
_MAX_PAGES = 5


def fetch() -> list[dict]:
    """
    Returns tenders from the Département 974 (La Réunion) public procurement platform.
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

    title = text("td.objet, .objet, h3, h2")
    description = text("td.organisme, .organisme, td.lieu")
    url = href("a")
    date = text("td.date, .date-publication, time")

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
        "source": "Département 974",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "description": raw.get("description", ""),
    }
