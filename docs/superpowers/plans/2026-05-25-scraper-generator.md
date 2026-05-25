# Scraper Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow a user to paste a URL in Paramètres → Sources, have Mistral AI generate a complete Python scraper, auto-test it, and activate it as a new collection source.

**Architecture:** A new root-level module `scraper_factory.py` orchestrates: fetch HTML → prompt Mistral → extract + validate code → save `scraper_custom_*.py` → run with 30s timeout → if ≥1 result, register in DB. Two new FastAPI endpoints wire this into the backend. A new `SourceGenerator.jsx` component + Sources tab in Paramètres surfaces it in the UI.

**Tech Stack:** Python 3.11, FastAPI, mistralai SDK (already installed), SQLAlchemy, concurrent.futures (stdlib), React 19, TanStack Query, Tailwind (Ocean Deep theme)

---

## File Map

| Action | File | Responsibility |
| --- | --- | --- |
| CREATE | `scraper_factory.py` | Full generation logic: fetch HTML, call Mistral, extract/validate code, save file, test, register source |
| CREATE | `tests/test_scraper_factory.py` | Unit tests for scraper_factory |
| MODIFY | `source_registry.py` | Add `add_auto_source()` + `remove_auto_source()` |
| MODIFY | `backend/main.py` | Add `POST /api/sources/generate` + `DELETE /api/sources/{id}` endpoints |
| MODIFY | `frontend/src/services/api.js` | Add `generateScraper()` + `deleteSource()` |
| MODIFY | `frontend/src/hooks/useTenders.js` | Add `useGenerateScraper` + `useDeleteSource` |
| CREATE | `frontend/src/components/SourceGenerator.jsx` | Form + status + list of custom sources |
| MODIFY | `frontend/src/pages/Parametres.jsx` | Import + wire Sources tab |

---

## Task 1 — Tests for `scraper_factory.py` helpers

**Files:**
- Create: `tests/test_scraper_factory.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_scraper_factory.py
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
import pytest
from scraper_factory import _extract_code, _validate_syntax, generate, GenerationResult


def test_extract_code_from_backtick_block():
    text = "Voici le code :\n```python\ndef fetch() -> list:\n    return []\n```\nFin."
    result = _extract_code(text)
    assert "def fetch" in result


def test_extract_code_from_bare_backtick_block():
    text = "```\ndef fetch():\n    return []\n```"
    result = _extract_code(text)
    assert "def fetch" in result


def test_extract_code_without_backticks():
    text = "Explication.\ndef fetch() -> list[dict]:\n    return []\n"
    result = _extract_code(text)
    assert "def fetch" in result


def test_extract_code_empty_response():
    result = _extract_code("Pas de code ici.")
    assert result == ""


def test_validate_syntax_valid():
    code = "from datetime import datetime\ndef fetch():\n    return []\n"
    assert _validate_syntax(code) is True


def test_validate_syntax_invalid():
    code = "def fetch(\n    broken syntax here"
    assert _validate_syntax(code) is False


def test_generate_no_mistral_client():
    with patch("scraper_factory._get_mistral_client", return_value=None):
        result = generate("https://example.com", "Test Site", "Public", db=None)
    assert result.status == "failed"
    assert "Mistral" in result.reason


def test_generate_site_unreachable():
    with patch("scraper_factory._get_mistral_client", return_value=MagicMock()), \
         patch("scraper_factory._fetch_html", side_effect=ValueError("Impossible de télécharger")):
        result = generate("https://unreachable.example", "Test", "Public", db=None)
    assert result.status == "failed"
    assert "télécharger" in result.reason


def test_generate_zero_results(tmp_path):
    mock_client = MagicMock()
    mock_client.chat.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="def fetch():\n    return []\n"))]
    )
    with patch("scraper_factory._get_mistral_client", return_value=mock_client), \
         patch("scraper_factory._fetch_html", return_value="<html><body>test</body></html>"), \
         patch("scraper_factory._test_scraper_module", return_value=[]), \
         patch("scraper_factory.ROOT_DIR", str(tmp_path)):
        result = generate("https://example.com", "Test", "Public", db=None)
    assert result.status == "failed"
    assert "0 résultats" in result.reason
    assert list(tmp_path.glob("*.py")) == []


def test_generate_success(tmp_path):
    preview_item = {
        "name": "Marché test",
        "url": "https://example.com/ao/1",
        "source": "Test",
        "date_found": "2026-05-25",
        "publication_date": "",
        "deadline": "",
        "description": "",
    }
    mock_client = MagicMock()
    mock_client.chat.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="def fetch():\n    return []\n"))]
    )
    with patch("scraper_factory._get_mistral_client", return_value=mock_client), \
         patch("scraper_factory._fetch_html", return_value="<html><body>test</body></html>"), \
         patch("scraper_factory._test_scraper_module", return_value=[preview_item]), \
         patch("scraper_factory.add_auto_source", return_value=MagicMock()), \
         patch("scraper_factory.ROOT_DIR", str(tmp_path)):
        result = generate("https://example.com", "Test Site", "Public", db=MagicMock())
    assert result.status == "ok"
    assert result.nb_results == 1
    assert result.preview[0]["name"] == "Marché test"
    saved = list(tmp_path.glob("scraper_custom_*.py"))
    assert len(saved) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```powershell
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
pytest tests/test_scraper_factory.py -v
```

Expected: `ModuleNotFoundError: No module named 'scraper_factory'`

- [ ] **Step 3: Commit the failing tests**

```powershell
git add tests/test_scraper_factory.py
git commit -m "test(scraper_factory): tests unitaires pour générateur de scrapers IA"
```

---

## Task 2 — Create `scraper_factory.py`

**Files:**
- Create: `scraper_factory.py`

- [ ] **Step 1: Write the module**

```python
# scraper_factory.py
"""
Génère automatiquement un scraper Python pour un site donné via Mistral AI.
"""

import ast
import concurrent.futures
import importlib
import os
import re
import sys
from dataclasses import dataclass, field

import requests

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
                    "date_found": datetime.now(timezone.utc).date().isoformat(),
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
                "date_found": datetime.now(timezone.utc).date().isoformat(),
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
        import traceback
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
            pass

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
    return f"""Tu es un expert Python en web scraping de marchés publics.
Génère un scraper Python complet pour le site : {url}

CONTRAINTES STRICTES :
1. Expose UNE SEULE fonction `fetch() -> list[dict]`
2. Chaque dict DOIT avoir exactement ces clés :
   - name: str  (titre de l'appel d'offres, jamais vide)
   - url: str   (lien absolu vers l'annonce)
   - source: str (nom court du site)
   - date_found: str  (date ISO via datetime.now(timezone.utc).date().isoformat())
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
    mod = importlib.import_module(module_name)
    func = getattr(mod, "fetch")
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
```

- [ ] **Step 2: Run the tests**

```powershell
pytest tests/test_scraper_factory.py -v
```

Expected: all 10 tests PASS

- [ ] **Step 3: Commit**

```powershell
git add scraper_factory.py
git commit -m "feat(scraper_factory): générateur de scrapers Python via Mistral AI"
```

---

## Task 3 — Extend `source_registry.py`

**Files:**
- Modify: `source_registry.py`

- [ ] **Step 1: Add `add_auto_source` and `remove_auto_source` after the existing `add_source` function (line ~386)**

In `source_registry.py`, after the `add_source` function, add:

```python
def add_auto_source(
    db, name: str, url: str, category: str, scraper_module: str
):
    """Ajoute une source avec scraper généré automatiquement (is_manual=False, is_validated=True)."""
    s = Source(
        name=name,
        url=url,
        category=category,
        is_manual=False,
        enabled=True,
        is_validated=True,
        scraper_module=scraper_module,
        scraper_func="fetch",
        display_order=90,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def remove_auto_source(db, source_id: int):
    """
    Supprime une source générée automatiquement (scraper_module startswith 'scraper_custom_').
    Returns: scraper_module str on success, None if not found, False if not a custom source.
    """
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s:
        return None
    if not s.scraper_module or not s.scraper_module.startswith("scraper_custom_"):
        return False
    module_name = s.scraper_module
    db.delete(s)
    db.commit()
    return module_name
```

- [ ] **Step 2: Run existing tests to verify no regression**

```powershell
pytest tests/ -v --ignore=tests/test_scraper_factory.py
```

Expected: all existing tests PASS

- [ ] **Step 3: Commit**

```powershell
git add source_registry.py
git commit -m "feat(source_registry): add_auto_source et remove_auto_source pour scrapers générés"
```

---

## Task 4 — Add endpoints to `backend/main.py`

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Add the Pydantic request model**

In `backend/main.py`, find the section where other Pydantic models are defined (search for `class CollectRequest`). Add after it:

```python
class GenerateScraperRequest(BaseModel):
    url: str
    name: str
    category: str

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in {"Public", "Privé", "International"}:
            raise ValueError("Catégorie invalide")
        return v

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL invalide — doit commencer par http:// ou https://")
        return v
```

- [ ] **Step 2: Add the two endpoints**

At the end of `backend/main.py`, before the last closing line, add:

```python
# ── POST /api/sources/generate ───────────────────────────────────────────────


@app.post("/api/sources/generate", summary="Générer un scraper via IA pour un nouveau site")
def generate_scraper(body: GenerateScraperRequest, db: Session = Depends(get_db)):
    from scraper_factory import generate as _generate

    result = _generate(body.url, body.name, body.category, db)
    if result.status == "failed":
        raise HTTPException(status_code=422, detail=result.reason)
    return {
        "status": "ok",
        "scraper_module": result.scraper_module,
        "nb_results": result.nb_results,
        "preview": result.preview,
    }


# ── DELETE /api/sources/{source_id} ─────────────────────────────────────────


@app.delete("/api/sources/{source_id}", summary="Supprimer une source personnalisée")
def delete_source_endpoint(source_id: int, db: Session = Depends(get_db)):
    from source_registry import remove_auto_source

    result = remove_auto_source(db, source_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Source introuvable")
    if result is False:
        raise HTTPException(
            status_code=403, detail="Seules les sources générées automatiquement peuvent être supprimées"
        )
    # result is the module_name string — delete the file and evict from sys.modules
    import sys as _sys

    _sys.modules.pop(result, None)
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    filepath = os.path.join(root_dir, f"{result}.py")
    try:
        os.remove(filepath)
    except FileNotFoundError:
        pass
    return {"deleted": True}
```

- [ ] **Step 3: Verify the backend starts without error**

```powershell
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI\backend"
python -c "import main; print('OK')"
```

Expected: `OK` with no errors

- [ ] **Step 4: Commit**

```powershell
git add backend/main.py
git commit -m "feat(api): endpoints POST /api/sources/generate et DELETE /api/sources/{id}"
```

---

## Task 5 — Extend `frontend/src/services/api.js`

**Files:**
- Modify: `frontend/src/services/api.js`

- [ ] **Step 1: Add the two API functions**

In `frontend/src/services/api.js`, after the `getSources` export (around line 75), add:

```js
export const generateScraper = (body) =>
  api.post('/sources/generate', body).then((r) => r.data)

export const deleteSource = (id) =>
  api.delete(`/sources/${id}`).then((r) => r.data)
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/src/services/api.js
git commit -m "feat(api.js): generateScraper et deleteSource"
```

---

## Task 6 — Extend `frontend/src/hooks/useTenders.js`

**Files:**
- Modify: `frontend/src/hooks/useTenders.js`

- [ ] **Step 1: Import the new API functions**

In `frontend/src/hooks/useTenders.js`, find the import block at the top. Add `generateScraper` and `deleteSource` to the existing named imports from `'../services/api'`.

The import block currently ends around line 10. Change it so `generateScraper` and `deleteSource` appear in the import list:

```js
import {
  getTenders, getTender, getKpisPublic, getKpisCa, getKpisPriv,
  getPipeline, getUrgences, getScraperRuns, getSources, getChartData,
  collect, analyzePending, updateStatus, updateSaved, updateNotes,
  updateTags, updateAmount, deleteTender, analyzeTender,
  getDuplicates, resolveDuplicate, detectDuplicates, archiveOld, resetDb,
  getCredentials, saveCredential, deleteCredential, testCredential,
  saveMistralKey,
  getMistralStatus,
  generateScraper,
  deleteSource,
} from '../services/api'
```

- [ ] **Step 2: Add the two hooks at the end of the file**

```js
export const useGenerateScraper = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: generateScraper,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}

export const useDeleteSource = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteSource,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sources'] }),
  })
}
```

- [ ] **Step 3: Commit**

```powershell
git add frontend/src/hooks/useTenders.js
git commit -m "feat(useTenders): useGenerateScraper et useDeleteSource"
```

---

## Task 7 — Create `frontend/src/components/SourceGenerator.jsx`

**Files:**
- Create: `frontend/src/components/SourceGenerator.jsx`

- [ ] **Step 1: Write the component**

```jsx
// frontend/src/components/SourceGenerator.jsx
import { useState } from 'react'
import { useGenerateScraper, useDeleteSource, useSources } from '../hooks/useTenders'

export default function SourceGenerator() {
  const [form, setForm] = useState({ name: '', url: '', category: 'Public' })
  const {
    mutate: generate,
    isPending,
    isSuccess,
    isError,
    error,
    data,
    reset,
  } = useGenerateScraper()
  const { mutate: removeSource } = useDeleteSource()
  const { data: sources = [] } = useSources()

  const customSources = sources.filter((s) =>
    s.scraper_module?.startsWith('scraper_custom_')
  )

  const handleSubmit = () => {
    reset()
    generate({ url: form.url, name: form.name, category: form.category })
  }

  const canSubmit = form.name.trim() && form.url.trim() && !isPending

  return (
    <div className="space-y-6">
      <div className="p-4 bg-ocean-panel border border-ocean-border rounded-lg space-y-4">
        <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest">
          ➕ Ajouter un site de veille
        </h3>
        <p className="font-sans text-sm text-ocean-muted">
          Collez l'URL d'une page listant des appels d'offres. Mistral AI analyse la page et génère
          automatiquement le scraper.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">
              Nom du site
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              placeholder="Ex: CHU Réunion — Appels d'offres"
              className="w-full px-3 py-2 font-sans text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text placeholder:text-ocean-muted focus:outline-none focus:border-ocean-cyan/30"
            />
          </div>

          <div>
            <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">
              URL
            </label>
            <input
              type="url"
              value={form.url}
              onChange={(e) => setForm((p) => ({ ...p, url: e.target.value }))}
              placeholder="https://..."
              className="w-full px-3 py-2 font-mono text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text placeholder:text-ocean-muted focus:outline-none focus:border-ocean-cyan/30"
            />
          </div>

          <div>
            <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">
              Catégorie
            </label>
            <select
              value={form.category}
              onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
              className="w-full px-3 py-2 font-sans text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text focus:outline-none focus:border-ocean-cyan/30"
            >
              <option value="Public">Public</option>
              <option value="Privé">Privé</option>
              <option value="International">International</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="px-4 py-2 bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
        >
          {isPending ? '⏳ Génération en cours…' : '🤖 Générer le scraper'}
        </button>

        {isPending && (
          <p className="font-sans text-xs text-ocean-muted animate-pulse">
            Analyse de la page, génération du code et test en cours — cela peut prendre 30–60 secondes…
          </p>
        )}

        {isSuccess && (
          <div className="space-y-2">
            <p className="font-mono text-xs text-ocean-teal">
              ✅ Scraper actif — {data.nb_results} annonces trouvées
            </p>
            {data.preview?.length > 0 && (
              <div className="border border-ocean-border rounded-md overflow-hidden">
                <table className="w-full text-xs font-sans">
                  <thead>
                    <tr className="bg-ocean-panel/50">
                      <th className="px-3 py-2 text-left text-ocean-muted font-medium">Titre</th>
                      <th className="px-3 py-2 text-left text-ocean-muted font-medium hidden sm:table-cell">
                        Date
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.preview.map((item, i) => (
                      <tr key={i} className="border-t border-ocean-border">
                        <td className="px-3 py-2 text-ocean-text truncate max-w-xs">{item.name}</td>
                        <td className="px-3 py-2 text-ocean-muted hidden sm:table-cell">
                          {item.publication_date || item.date_found}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {isError && (
          <p className="font-mono text-xs text-ocean-coral">
            ✗ {error?.response?.data?.detail ?? 'Erreur lors de la génération'}
          </p>
        )}
      </div>

      {customSources.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest">
            Sites personnalisés ({customSources.length})
          </h3>
          <div className="space-y-2">
            {customSources.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between p-3 bg-ocean-panel border border-ocean-border rounded-lg"
              >
                <div className="min-w-0 flex-1 mr-3">
                  <div className="font-sans text-sm font-medium text-ocean-text truncate">
                    {s.name}
                  </div>
                  <div className="font-mono text-xs text-ocean-muted truncate">{s.url}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="font-mono text-xs text-ocean-teal bg-ocean-teal/10 px-2 py-0.5 rounded-full">
                    actif
                  </span>
                  <button
                    onClick={() => removeSource(s.id)}
                    className="px-2 py-1 text-ocean-coral font-sans text-xs rounded border border-ocean-coral/20 hover:bg-ocean-coral/10 transition-colors"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/src/components/SourceGenerator.jsx
git commit -m "feat(SourceGenerator): composant formulaire + liste des sources personnalisées"
```

---

## Task 8 — Wire Sources tab in `frontend/src/pages/Parametres.jsx`

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx`

- [ ] **Step 1: Add the import at the top of the file**

In `frontend/src/pages/Parametres.jsx`, after the last existing import (after line 17), add:

```js
import SourceGenerator from '../components/SourceGenerator'
```

- [ ] **Step 2: Add the tab to the TABS array**

Find the `TABS` constant (around line 608):

```js
const TABS = [
  { id: 'connexion',     label: '🔐 Connexion' },
  { id: 'analyse',       label: '🤖 Analyse' },
  { id: 'maintenance',   label: '🛠️ Maintenance' },
  { id: 'intégrations',  label: '🔑 Intégrations' },
  { id: 'apparence',     label: '🎨 Apparence' },
]
```

Replace with:

```js
const TABS = [
  { id: 'connexion',     label: '🔐 Connexion' },
  { id: 'analyse',       label: '🤖 Analyse' },
  { id: 'maintenance',   label: '🛠️ Maintenance' },
  { id: 'sources',       label: '➕ Sources' },
  { id: 'intégrations',  label: '🔑 Intégrations' },
  { id: 'apparence',     label: '🎨 Apparence' },
]
```

- [ ] **Step 3: Add the conditional render**

Find the `<div>` block that renders tabs (around line 641):

```js
      <div>
        {activeTab === 'connexion' && <ConnexionTab />}
        {activeTab === 'analyse' && <AnalyseTab />}
        {activeTab === 'maintenance' && <MaintenanceTab />}
        {activeTab === 'intégrations' && <IntegrationsTab />}
        {activeTab === 'apparence' && <ApparenceTab />}
      </div>
```

Replace with:

```js
      <div>
        {activeTab === 'connexion' && <ConnexionTab />}
        {activeTab === 'analyse' && <AnalyseTab />}
        {activeTab === 'maintenance' && <MaintenanceTab />}
        {activeTab === 'sources' && <SourceGenerator />}
        {activeTab === 'intégrations' && <IntegrationsTab />}
        {activeTab === 'apparence' && <ApparenceTab />}
      </div>
```

- [ ] **Step 4: Verify the frontend compiles without errors**

```powershell
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI\frontend"
npm run build
```

Expected: build succeeds with no errors (warnings about unused vars are acceptable)

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/pages/Parametres.jsx
git commit -m "feat(Parametres): onglet Sources avec SourceGenerator"
```

---

## Self-Review Checklist

- [x] **Spec coverage:**
  - ✅ URL → Mistral → scraper_custom_*.py → test → DB source: Task 2
  - ✅ `add_auto_source` / `remove_auto_source`: Task 3
  - ✅ `POST /api/sources/generate` + `DELETE /api/sources/{id}`: Task 4
  - ✅ `generateScraper` / `deleteSource` API functions: Task 5
  - ✅ `useGenerateScraper` / `useDeleteSource` hooks: Task 6
  - ✅ SourceGenerator component (form + states + list): Task 7
  - ✅ Paramètres → Sources tab: Task 8
  - ✅ All error cases (no Mistral key, unreachable site, 0 results): Tasks 2+4
- [x] **No placeholders:** all steps have real code
- [x] **Type consistency:** `GenerationResult.status` is "ok"/"failed" in Task 2 and checked in Task 4; `module_name` string returned by `remove_auto_source` in Task 3 and used in Task 4
- [x] **One commit per file** respected throughout
