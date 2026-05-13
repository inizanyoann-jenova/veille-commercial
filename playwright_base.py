import logging
from playwright.sync_api import Page

log = logging.getLogger(__name__)


class ScraperError(Exception):
    pass


def login(page: Page, url: str, email: str, password: str, selectors: dict) -> bool:
    try:
        page.goto(url, timeout=15000)
        page.wait_for_load_state("domcontentloaded", timeout=15000)
        initial_url = page.url
        page.fill(selectors["email"], email)
        page.fill(selectors["password"], password)
        # Essayer JS click d'abord (contourne les overlays), fallback sur Entrée
        submit_sel = selectors.get("submit", "")
        clicked = False
        if submit_sel:
            try:
                clicked = page.evaluate(
                    f"() => {{ const b = document.querySelector({repr(submit_sel)}); if (b) {{ b.click(); return true; }} return false; }}"
                )
            except Exception:
                pass
        if not clicked:
            page.press(selectors["password"], "Enter")
        page.wait_for_load_state("networkidle", timeout=15000)
        # Redirect after submit = successful login
        if page.url != initial_url:
            return True
        # Still on login page — check for visible error messages
        _error_sel = (
            ".error, .alert-danger, .alert-error, .login-error, "
            ".message-erreur, .erreur, [class*='error-msg'], "
            ".invalid-feedback, .form-error"
        )
        if page.query_selector(_error_sel):
            return False
        return True
    except Exception as exc:
        log.warning("Login failed on %s: %s", url, exc)
        return False


def extract_cards(page: Page, card_selector: str, field_map: dict) -> list[dict]:
    cards = page.query_selector_all(card_selector)
    results = []
    for card in cards:
        item = {}
        for field, selector in field_map.items():
            if "@" in selector:
                sel, attr = selector.rsplit("@", 1)
                el = card.query_selector(sel) if sel else card
                item[field] = el.get_attribute(attr).strip() if el else ""
            else:
                el = card.query_selector(selector)
                item[field] = el.inner_text().strip() if el else ""
        results.append(item)
    return results


def paginate(page: Page, next_selector: str) -> bool:
    """Click the next-page link once. Returns True if found and clicked, False if no more pages."""
    btn = page.query_selector(next_selector)
    if not btn or not btn.is_enabled():
        return False
    btn.click()
    page.wait_for_load_state("networkidle", timeout=15000)
    return True
