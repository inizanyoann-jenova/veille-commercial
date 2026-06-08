from datetime import timezone
"""
MarchésPublics.info (AW Solutions) — appels d'offres en cours
La Réunion (974) et Mayotte (976).

Formulaire POST → /Annonces/lister.
Chaque avis est dans un div#entity :
  - .affiche_date_avis  → date publication + deadline
  - h2.h2-avis          → organisme / acheteur
  - #titre_box          → objet du marché
  - a[href*='Annonces'] → lien detail
Pagination : GET /Annonces/lister?pager_t=N
"""

import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_SEARCH_URL = "https://www.marches-publics.info/Annonces/rechercher"
_LIST_URL = "https://www.marches-publics.info/Annonces/lister"
_BASE = "https://www.marches-publics.info"
_DEPTS = [("974", "974"), ("976", "976")]
_MAX_PAGES = 5


def fetch() -> list[dict]:
    results = []
    seen_urls: set[str] = set()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            for dept_value, dept_label in _DEPTS:
                results.extend(_search_dept(browser, dept_value, seen_urls))
        finally:
            browser.close()

    return results


def _search_dept(browser, dept_value: str, seen_urls: set) -> list[dict]:
    results = []
    page = browser.new_page()
    try:
        try:
            page.goto(_SEARCH_URL, timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=20_000)
        except Exception:
            return results

        try:
            page.select_option('select[name="IDR"]', value=dept_value)
            page.click("#sub")
            page.wait_for_load_state("networkidle", timeout=25_000)
        except Exception:
            return results

        for page_num in range(1, _MAX_PAGES + 1):
            if page_num > 1:
                try:
                    page.goto(f"{_LIST_URL}?pager_t={page_num}", timeout=20_000)
                    page.wait_for_load_state("networkidle", timeout=20_000)
                except Exception:
                    break

            entities = page.query_selector_all("div#entity")
            if not entities:
                break

            for entity in entities:
                item = _extract_entity(entity)
                url = item.get("url", "")
                if item.get("name") and url not in seen_urls:
                    seen_urls.add(url)
                    results.append(_normalise(item))

            # S'arrêter si pas de page suivante
            has_next = page.query_selector(f'a[href*="pager_t={page_num + 1}"]')
            if not has_next:
                break

    finally:
        page.close()

    return results


def _extract_entity(entity) -> dict:
    def text(sel: str) -> str:
        el = entity.query_selector(sel)
        return el.inner_text().strip() if el else ""

    def href(sel: str) -> str:
        el = entity.query_selector(sel)
        return (el.get_attribute("href") or "") if el else ""

    date_text = text(".affiche_date_avis")
    organisme = text("h2.h2-avis")
    url = href("a[href*='Annonces']")

    # Titre : contenu textuel de #titre_box sans le sous-élément .ref-acheteur
    titre_box = entity.query_selector("#titre_box")
    title = ""
    if titre_box:
        ref_el = titre_box.query_selector(".ref-acheteur")
        if ref_el:
            ref_el.evaluate("el => el.remove()")
        title = titre_box.inner_text().strip()
    if not title:
        title = organisme  # fallback

    if url and not url.startswith("http"):
        url = f"{_BASE}{url}"

    return {
        "name": title,
        "organisme": organisme,
        "url": url or _LIST_URL,
        "date_text": date_text,
    }


def _parse_date_fr(text: str, pattern: str) -> str:
    """Extrait une date DD/MM/YY ou DD/MM/YYYY depuis un texte."""
    m = re.search(pattern, text)
    if not m:
        return ""
    d, mo, y = m.group(1), m.group(2), m.group(3)
    if len(y) == 2:
        y = "20" + y
    try:
        return datetime.strptime(f"{d}/{mo}/{y}", "%d/%m/%Y").date().isoformat()
    except ValueError:
        return ""


def _normalise(raw: dict) -> dict:
    date_text = raw.get("date_text", "")
    publication_date = _parse_date_fr(date_text, r"Publi[ée] le\s+(\d{2})/(\d{2})/(\d{2,4})")
    deadline = _parse_date_fr(date_text, r"Date limite\s*:.*?(\d{2})/(\d{2})/(\d{2,4})")

    return {
        "name": raw.get("name", ""),
        "url": raw.get("url", _LIST_URL),
        "source": "Marchés-Publics.info",
        "date_found": datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat(),
        "publication_date": publication_date,
        "deadline": deadline,
        "description": raw.get("organisme", ""),
    }
