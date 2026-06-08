from datetime import timezone
# scraper_factory.py
"""
Génère automatiquement un scraper Python pour un site donné via Mistral AI.
"""

import ast
import concurrent.futures
import importlib
import logging
import os
import re
import sys
import traceback
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup

_log = logging.getLogger(__name__)

from llm_analyzer import _get_mistral_client
from source_registry import add_auto_source

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Two short examples shown to Mistral as reference ─────────────────────────

_EXAMPLE_PLAYWRIGHT = '''\
# Exemple — scraper Playwright (sites dynamiques / JS)
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

def fetch() -> list[dict]:
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto("https://exemple.fr/appels-offres", timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=30_000)
            for card in page.query_selector_all("article"):
                title_el = card.query_selector("h2, h3")
                link_el = card.query_selector("a")
                if not title_el:
                    continue
                url = link_el.get_attribute("href") if link_el else "https://exemple.fr/appels-offres"
                if url and not url.startswith("http"):
                    url = "https://exemple.fr" + url
                results.append({
                    "name": title_el.inner_text().strip(),
                    "url": url,
                    "source": "Exemple Site",
                    "date_found": datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat(),
                    "publication_date": "",
                    "deadline": "",
                    "description": "",
                })
        finally:
            browser.close()
    return results
'''

_EXAMPLE_REQUESTS = '''\
# Exemple — scraper requests + BeautifulSoup (sites HTML statiques)
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone

def fetch() -> list[dict]:
    results = []
    try:
        resp = requests.get(
            "https://exemple2.fr/marches",
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        soup = BeautifulSoup(resp.text, "html.parser")
        for row in soup.select("table.appels-offres tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            link = cells[0].find("a")
            results.append({
                "name": cells[0].get_text(strip=True),
                "url": link["href"] if link else "https://exemple2.fr/marches",
                "source": "Exemple Site 2",
                "date_found": datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat(),
                "publication_date": cells[1].get_text(strip=True),
                "deadline": "",
                "description": "",
            })
    except Exception:
        pass
    return results
'''


# ── Public interface ──────────────────────────────────────────────────────────

@dataclass
class GenerationResult:
    status: str  # "ok" | "failed"
    scraper_module: str = ""
    nb_results: int = 0
    preview: list = field(default_factory=list)
    reason: str = ""


def generate(url: str, source_name: str, category: str, db) -> GenerationResult:
    """
    Full pipeline: fetch HTML → prompt Mistral → extract code → validate →
    save file → test → register source in DB.
    Returns GenerationResult with status "ok" or "failed".
    """
    client = _get_mistral_client()
    if client is None:
        return GenerationResult(
            status="failed",
            reason="Clé Mistral manquante — configurez-la dans Paramètres > Intégrations",
        )

    try:
        html = _fetch_html(url)
    except ValueError as exc:
        return GenerationResult(status="failed", reason=str(exc))

    prompt = _build_prompt(url, html)
    try:
        llm_response = _call_mistral(client, prompt)
    except Exception as exc:
        return GenerationResult(status="failed", reason=f"Erreur Mistral : {exc}")

    code = _extract_code(llm_response)
    if not code:
        return GenerationResult(
            status="failed",
            reason="Code non extractible — reformulez ou essayez une autre URL",
        )

    if not _validate_syntax(code):
        return GenerationResult(status="failed", reason="Code généré syntaxiquement invalide")

    domain = re.sub(r"^https?://", "", url).split("/")[0]
    slug = re.sub(r"[^a-z0-9]", "_", domain.lower()).strip("_")
    module_name = f"scraper_custom_{slug}"
    filepath = os.path.join(ROOT_DIR, f"{module_name}.py")

    if os.path.exists(filepath):
        return GenerationResult(
            status="failed",
            reason=f"Un scraper existe déjà pour ce domaine ({module_name}.py) — supprimez-le d'abord",
        )

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code)
    except OSError as exc:
        return GenerationResult(status="failed", reason=f"Impossible d'écrire le fichier : {exc}")

    try:
        results = _test_scraper_module(module_name)
    except TimeoutError:
        _cleanup(filepath, module_name)
        return GenerationResult(status="failed", reason="Timeout — le scraper a mis plus de 30s")
    except Exception as exc:
        tb = traceback.format_exc()[-600:]
        _cleanup(filepath, module_name)
        return GenerationResult(status="failed", reason=f"Erreur lors du test : {tb}")

    if not results or not results[0].get("name"):
        _cleanup(filepath, module_name)
        return GenerationResult(
            status="failed",
            reason="Scraper testé mais 0 résultats — page peut-être dynamique ou structure non reconnue",
        )

    add_auto_source(db, source_name, url, category, module_name)

    return GenerationResult(
        status="ok",
        scraper_module=module_name,
        nb_results=len(results),
        preview=results[:5],
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _fetch_html(url: str) -> str:
    try:
        resp = requests.get(
            url,
            timeout=15,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DEF-OI-Scraper/1.0)"},
        )
        resp.raise_for_status()
        html = resp.text
    except Exception as exc:
        raise ValueError(f"Impossible de télécharger la page : {exc}")

    if len(html.strip()) < 500:
        try:
            html = _fetch_html_playwright(url)
        except Exception:
            _log.warning("Playwright fallback échoué pour %s, HTML court utilisé", url)

    return html[:32_000]


def _fetch_html_playwright(url: str) -> str:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=30_000)
            page.wait_for_load_state("networkidle", timeout=20_000)
            return page.content()
        finally:
            browser.close()


def _build_prompt(url: str, html: str) -> str:
    try:
        from bs4 import BeautifulSoup as _BS
        html = _BS(html, "html.parser").get_text(separator=" ", strip=True)[:32_000]
    except Exception:
        pass
    return f"""Tu es un expert Python en web scraping de marchés publics.
Génère un scraper Python complet pour le site : {url}

CONTRAINTES STRICTES :
1. Expose UNE SEULE fonction `fetch() -> list[dict]`
2. Chaque dict DOIT avoir exactement ces clés :
   - name: str  (titre de l'appel d'offres, jamais vide)
   - url: str   (lien absolu vers l'annonce)
   - source: str (nom court du site)
   - date_found: str  (date ISO via datetime.now(timezone.utc).replace(tzinfo=None).date().isoformat())
   - publication_date: str  (date ISO "YYYY-MM-DD" ou "" si inconnue)
   - deadline: str  (date ISO "YYYY-MM-DD" ou "" si inconnue)
   - description: str  (description courte ou "")
3. Retourne [] si aucune annonce trouvée ou en cas d'erreur
4. Utilise playwright si le site nécessite JavaScript, sinon requests + BeautifulSoup
5. Retourne UNIQUEMENT le code Python, sans markdown, sans explication

EXEMPLES DE SCRAPERS EXISTANTS :
{_EXAMPLE_PLAYWRIGHT}

{_EXAMPLE_REQUESTS}

HTML DE LA PAGE CIBLE (tronqué) :
{html}

Génère le scraper Python complet pour {url} :"""


def _call_mistral(client, prompt: str) -> str:
    response = client.chat.complete(
        model="mistral-large-latest",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def _extract_code(text: str) -> str:
    m = re.search(r"```python\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"((?:import |from |def fetch).*)", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return ""


def _validate_syntax(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def _test_scraper_module(module_name: str, timeout: int = 30) -> list:
    sys.modules.pop(module_name, None)
    if ROOT_DIR not in sys.path:
        sys.path.insert(0, ROOT_DIR)
    mod = importlib.import_module(module_name)
    func = getattr(mod, "fetch")
    if not callable(func):
        raise ValueError("Le module ne contient pas de fonction fetch() appelable")
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError(f"Scraper timeout après {timeout}s")


def _cleanup(filepath: str, module_name: str) -> None:
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass
    sys.modules.pop(module_name, None)
