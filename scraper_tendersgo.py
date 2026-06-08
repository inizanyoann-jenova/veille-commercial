from datetime import timezone
"""
TendersGo — appels d'offres SSI/incendie/CMSI/vidéosurveillance France (La Réunion + Mayotte).
Method: JS-rendered scraping via Playwright avec authentification.
Credentials: TENDERSGO_EMAIL et TENDERSGO_PASSWORD.
"""

from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_LOGIN_URL = "https://app.tendersgo.com/login"
_SEARCH_URL = "https://app.tendersgo.com/tenders?country=FR&keywords=SSI+incendie+videosurveillance+CCTV+CMSI"
_BASE = "https://app.tendersgo.com"
_CARD = ".tender-card, .tender-item, article.tender, li.tender, tr.tender-row"
_NEXT = "a[aria-label='Next page'], .pagination-next a, button.next-page"
_MAX_PAGES = 5

_LOGIN_SELECTORS = {
    "email": "input[type='email'], input[name='email'], #email",
    "password": "input[type='password'], input[name='password'], #password",
    "submit": "button[type='submit'], input[type='submit']",
}


def _login(page, email: str, password: str) -> bool:
    try:
        page.goto(_LOGIN_URL, timeout=30_000)
        page.wait_for_load_state("networkidle", timeout=30_000)
        page.fill(_LOGIN_SELECTORS["email"], email)
        page.fill(_LOGIN_SELECTORS["password"], password)
        page.click(_LOGIN_SELECTORS["submit"])
        page.wait_for_load_state("networkidle", timeout=20_000)
        return _LOGIN_URL not in page.url
    except Exception:
        return False


def fetch() -> list[dict]:
    """
    Returns TendersGo tenders for France (La Réunion + Mayotte) filtered on SSI/incendie keywords.
    Requires TENDERSGO_EMAIL and TENDERSGO_PASSWORD environment variables.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    from credential_manager import CredentialManager
    creds = CredentialManager.get("tendersgo")
    if not creds:
        return []
    email, password = creds

    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            try:
                if not _login(page, email, password):
                    return results

                page.goto(_SEARCH_URL, timeout=30_000)
                page.wait_for_load_state("networkidle", timeout=30_000)

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

    title = text("h3, h2, .tender-title, .title")
    description = text(".tender-description, .description, .country")
    url = href("a")
    date = text(".tender-date, .date, time")

    if url and not url.startswith("http"):
        url = f"{_BASE}{url}"

    return {
        "name": title,
        "description": description,
        "url": url or _SEARCH_URL,
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
        "url": raw.get("url", _SEARCH_URL),
        "source": "TendersGo",
        "date_found": datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat(),
        "publication_date": publication_date,
        "deadline": "",
        "description": raw.get("description", ""),
    }
