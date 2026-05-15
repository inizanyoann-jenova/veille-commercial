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
        if page.url != initial_url:
            return True
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
            try:
                if "@" in selector:
                    sel, attr = selector.rsplit("@", 1)
                    el = card.query_selector(sel) if sel else card
                    val = el.get_attribute(attr) if el else None
                    item[field] = (val or "").strip()
                else:
                    el = card.query_selector(selector)
                    item[field] = el.inner_text().strip() if el else ""
            except Exception:
                item[field] = ""
        results.append(item)
    return results


def paginate(page: Page, next_selector: str) -> bool:
    """Click the next-page link. Returns True si trouvé et cliqué, False sinon."""
    try:
        btn = page.query_selector(next_selector)
        if not btn or not btn.is_enabled():
            return False
        btn.click()
        page.wait_for_load_state("networkidle", timeout=15000)
        return True
    except Exception:
        return False
