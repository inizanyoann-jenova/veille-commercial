"""
Nukema — marchés publics La Réunion (974) et Mayotte (976).
Method: JS-rendered scraping via Playwright.
Credentials optionnels: NUKEMA_EMAIL et NUKEMA_PASSWORD.
Note: login sur actu.nukema.com, consultation sur marches-publics.nukema.com
      (cookies non partagés cross-subdomain — auth peut échouer silencieusement).
"""

from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_URLS = [
    "https://marches-publics.nukema.com/seo/consultation/departement?departement=974",
    "https://marches-publics.nukema.com/seo/consultation/departement?departement=976",
]
_LOGIN_URL = "https://www.actu.nukema.com/connexion"
_BASE = "https://marches-publics.nukema.com"
_CARD = ".consultation-card, .card, article.consultation, li.consultation"
_NEXT = "a[aria-label='Next'], .pagination-next a, a.next"
_MAX_PAGES = 5

_LOGIN_SELECTORS = {
    "email": "input[type='email']",
    "password": "input[type='password']",
    "submit": "button[type='submit']",
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
    Returns Nukema tenders for La Réunion (974) and Mayotte (976).
    Credentials optional. If cross-subdomain auth fails, collection continues unauthenticated.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    from credential_manager import CredentialManager
    creds = CredentialManager.get("nukema")
    email, password = (creds[0], creds[1]) if creds else ("", "")
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            try:
                if email and password:
                    _login(page, email, password)

                for base_url in _URLS:
                    try:
                        page.goto(base_url, timeout=30_000)
                        page.wait_for_load_state("networkidle", timeout=30_000)
                    except Exception:
                        continue

                    # Détection auth cross-subdomain : actu.nukema.com → marches-publics.nukema.com
                    # Les cookies ne sont pas partagés entre sous-domaines — on continue sans auth
                    if any(
                        k in page.url
                        for k in ("connexion", "login", "authentification")
                    ):
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

    title = text("h3, h2, .card-title, .consultation-title")
    description = text(".card-text, .description, .organisme")
    url = href("a")
    date = text(".date, .card-date, time")
    deadline = text(
        ".date-limite, .date-echeance, .deadline, .remise-offres, "
        ".card-deadline, .consultation-deadline, time[datetime]"
    )

    if url and not url.startswith("http"):
        url = f"{_BASE}{url}"

    return {
        "name": title,
        "description": description,
        "url": url or base_url,
        "raw_date": date,
        "raw_deadline": deadline,
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

    raw_deadline = raw.get("raw_deadline") or ""
    try:
        deadline = (
            datetime.fromisoformat(raw_deadline[:10]).date().isoformat()
            if raw_deadline
            else ""
        )
    except ValueError:
        deadline = raw_deadline

    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _BASE),
        "source": "Nukema",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "description": raw.get("description", ""),
    }
