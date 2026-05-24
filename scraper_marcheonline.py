"""
MarchesOnline — appels d'offres La Réunion (D101) et Mayotte (D976).
Method: Playwright avec parsing HTML commentaires (rendu non-premium).
Credentials optionnels: MARCHEONLINE_EMAIL et MARCHEONLINE_PASSWORD.
"""

import os
import re
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

_LOGIN_URL = "https://www.marchesonline.com/connexion"
_LOGIN_SELECTORS = {
    "email": "#email-input",
    "password": "input[type='password'].modal_connexion_input",
    "submit": "button.primary-dark-btn",
}
_URLS = [
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101",
    "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/mayotte-D976",
]
_BASE = "https://www.marchesonline.com"
_MAX_PAGES = 10

_DETAIL_PATTERNS = [
    r'itemprop=["\']description["\'][^>]*>(.*?)</(?:p|div|span|article)>',
    r'class=["\']ao-objet["\'][^>]*>(.*?)</(?:p|div|span)>',
    r'class=["\']objet-marche["\'][^>]*>(.*?)</(?:p|div|span)>',
    r'class=["\']description-lot["\'][^>]*>(.*?)</(?:p|div|span)>',
    r'class=["\']ao-description["\'][^>]*>(.*?)</(?:p|div|span)>',
]


def _strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


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


def _extract_from_comments(html: str) -> list[dict]:
    """MarchesOnline cache les fiches AO dans des commentaires HTML (rendu non-premium)."""
    comments = re.findall(r"<!--(.*?)-->", html, re.DOTALL)
    results = []
    for block in comments:
        if "blockNotice" not in block:
            continue
        href_m = re.search(r'href="(/appels-offres/avis/[^"]+)"', block)
        url_m = href_m if href_m and "blockContentResults" in block else None
        title_m = re.search(
            r'<h2[^>]*itemprop="about"[^>]*>(.*?)</h2>', block, re.DOTALL
        )
        pub_m = re.search(
            r'<span[^>]*itemprop="publisher"[^>]*>(.*?)</span>', block, re.DOTALL
        )
        date_pub_m = re.search(r'itemprop="datePublished" content="([^"]+)"', block)
        date_ans_m = re.search(
            r'class="answerDate"[^>]*>.*?<span[^>]*class="dateColor"[^>]*>(.*?)</span>',
            block,
            re.DOTALL,
        )
        loc_m = re.search(
            r'class="location"[^>]*>.*?<span>(97[46])</span>', block, re.DOTALL
        )
        dept = loc_m.group(1) if loc_m else ""
        publisher = _strip_tags(pub_m.group(1)) if pub_m else ""
        description = f"{dept} — {publisher}" if dept else publisher
        results.append(
            {
                "url": f"{_BASE}{url_m.group(1)}" if url_m else "",
                "title": _strip_tags(title_m.group(1)) if title_m else "",
                "description": description,
                "date": date_pub_m.group(1) if date_pub_m else "",
                "deadline": date_ans_m.group(1).strip() if date_ans_m else "",
            }
        )
    return results


def _get_next_url(html: str) -> str | None:
    m = re.search(
        r'<a[^>]+href="([^"]+)"[^>]*(?:rel="next"|class="[^"]*next[^"]*")', html
    )
    if not m:
        next_m = re.search(
            r'<li[^>]*class="[^"]*active[^"]*"[^>]*>.*?</li>\s*<li[^>]*>\s*<a[^>]+href="([^"]+)"',
            html,
            re.DOTALL,
        )
        if next_m:
            href = next_m.group(1)
            return f"{_BASE}{href}" if href.startswith("/") else href
        return None
    href = m.group(1)
    return f"{_BASE}{href}" if href.startswith("/") else href


def _parse_detail_html(html: str) -> str:
    for pattern in _DETAIL_PATTERNS:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if m:
            text = _strip_tags(m.group(1)).strip()
            if len(text) > 10:
                return text
    return ""


def _extract_detail(page, url: str) -> str:
    if not url:
        return ""
    try:
        page.goto(url, timeout=20_000)
        page.wait_for_load_state("domcontentloaded", timeout=20_000)
        return _parse_detail_html(page.content())
    except Exception:
        return ""


def _to_iso(raw_date: str) -> str:
    if not raw_date:
        return ""
    try:
        return datetime.fromisoformat(raw_date[:10]).date().isoformat()
    except ValueError:
        return raw_date


def fetch() -> list[dict]:
    """
    Returns MarchesOnline tenders for La Réunion and Mayotte.
    Phase 1: collect candidates from list pages (HTML comment parsing).
    Phase 2: enrich each candidate with detail page description.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    email = os.getenv("MARCHEONLINE_EMAIL", "")
    password = os.getenv("MARCHEONLINE_PASSWORD", "")
    results = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            try:
                if email and password:
                    _login(page, email, password)

                # Phase 1 : collecte des candidats depuis les pages de liste
                candidates = []
                for base_url in _URLS:
                    current_url = base_url
                    for _ in range(_MAX_PAGES):
                        try:
                            page.goto(current_url, timeout=30_000)
                            page.wait_for_load_state("networkidle", timeout=30_000)
                        except Exception:
                            break
                        html = page.content()
                        for card in _extract_from_comments(html):
                            if card.get("title", "").strip():
                                candidates.append(card)
                        next_url = _get_next_url(html)
                        if not next_url or next_url == current_url:
                            break
                        current_url = next_url

                # Phase 2 : enrichissement fiche détail
                for card in candidates:
                    detail_desc = _extract_detail(page, card.get("url", ""))
                    desc = detail_desc or card.get("description", "").strip()
                    results.append(_normalise(card, desc))

            finally:
                page.close()
        finally:
            browser.close()

    return results


def _normalise(card: dict, description: str = "") -> dict:
    """Convert collected card data to standard schema."""
    return {
        "name": card.get("title", ""),
        "url": card.get("url", _BASE),
        "source": "MarchesOnline",
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": _to_iso(card.get("date", "")),
        "deadline": _to_iso(card.get("deadline", "")),
        "description": description,
    }
