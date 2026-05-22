# Credentials Management UI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose a UI in the Paramètres page to manage email/password credentials for the 8 authenticated scraping sites, with Playwright connection testing and a standardized `CREDENTIALS_MISSING` error in collection runs.

**Architecture:** Four new FastAPI routes in `backend/main.py` read/write credentials via the existing `CredentialManager` (encrypted SQLite). A new `CredentialsSection` React component is added to `Parametres.jsx`. Three scrapers that already implement an early-return pattern get their error string standardized to `"CREDENTIALS_MISSING"` so the frontend can distinguish auth failures from other errors.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, `cryptography` (Fernet), Playwright (via `_test_login_worker.py`), React 18, TanStack Query v5, Tailwind CSS.

---

## File Map

| File | Change |
|---|---|
| `backend/main.py` | +imports, +`_LOGIN_CONFIG`, +`CredentialSave`, +4 routes |
| `tests/test_credentials_routes.py` | New — tests for the 4 routes |
| `tests/test_credentials_missing.py` | New — tests CREDENTIALS_MISSING in 3 scrapers |
| `frontend/src/services/api.js` | +4 API functions |
| `frontend/src/hooks/useTenders.js` | +4 React Query hooks |
| `frontend/src/pages/Parametres.jsx` | +`CredentialsSection`, update `CollectSection` |
| `scraper_marchessecurises.py` | 1-line error string change |
| `scraper_instao.py` | 1-line error string change |
| `scraper_tendersgo.py` | 1-line error string change |

---

## Task 1: Backend — Constants + `GET /api/credentials`

**Files:**
- Modify: `backend/main.py` (after imports block ~line 57, and after Pydantic models ~line 322)
- Create: `tests/test_credentials_routes.py`

- [ ] **Step 1.1: Write failing tests**

Create `tests/test_credentials_routes.py`:

```python
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'backend'))

from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
import main as _m

_client = TestClient(_m.app)


def _mock_db(rows=None):
    """Return a mock SessionLocal() that yields `rows` from .query().all()."""
    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = rows or []
    mock_db.close = MagicMock()
    return mock_db


def test_get_credentials_returns_8_sites():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    sites = {d['site'] for d in data}
    assert 'nukema' in sites
    assert 'vaao' in sites
    assert 'instao' in sites


def test_get_credentials_missing_status():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    assert resp.status_code == 200
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'missing'
    assert nukema['email'] is None
    assert nukema['has_login_url'] is True


def test_get_credentials_configured_status():
    from models import Credential
    mock_cred = MagicMock(spec=Credential)
    mock_cred.site = 'nukema'
    mock_cred.email = 'user@test.com'
    with patch.object(_m, 'SessionLocal', return_value=_mock_db([mock_cred])), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'configured'
    assert nukema['email'] == 'user@test.com'


def test_get_credentials_env_override():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {'NUKEMA_EMAIL': 'env@test.com'}, clear=False):
        resp = _client.get('/api/credentials')
    nukema = next(d for d in resp.json() if d['site'] == 'nukema')
    assert nukema['status'] == 'env_override'
    assert nukema['email'] == 'env@test.com'


def test_get_credentials_public_site_has_no_login_url():
    with patch.object(_m, 'SessionLocal', return_value=_mock_db()), \
         patch.dict('os.environ', {}, clear=False):
        resp = _client.get('/api/credentials')
    vaao = next(d for d in resp.json() if d['site'] == 'vaao')
    assert vaao['has_login_url'] is False
```

- [ ] **Step 1.2: Run tests — expect failure**

```
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
python -m pytest tests/test_credentials_routes.py -v 2>&1 | head -30
```

Expected: `AttributeError: module 'main' has no attribute '_ALL_CREDENTIAL_SITES'` or similar import errors.

- [ ] **Step 1.3: Add imports to `backend/main.py`**

After line 57 (after `from llm_analyzer import ...`), add:

```python
import json as _json
import subprocess as _subprocess
from credential_manager import CredentialManager as _CredMgr, _ENV_MAP as _CRED_ENV_MAP
```

- [ ] **Step 1.4: Add `_LOGIN_CONFIG` and site constants to `backend/main.py`**

After `class CollectResult(BaseModel):` block (~line 322), add:

```python
class CredentialSave(BaseModel):
    email: str
    password: str


# ── Credential site registry ──────────────────────────────────────────────────

_LOGIN_CONFIG: dict[str, dict] = {
    "nukema": {
        "label": "Nukema",
        "url": "https://www.actu.nukema.com/connexion",
        "selectors": {
            "email": "input[type='email']",
            "password": "input[type='password']",
            "submit": "button[type='submit']",
        },
    },
    "marcheonline": {
        "label": "Marché Online",
        "url": "https://www.marchesonline.com/connexion",
        "selectors": {
            "email": "#email-input",
            "password": "input[type='password'].modal_connexion_input",
            "submit": "button.primary-dark-btn",
        },
    },
    "instao": {
        "label": "Instao",
        "url": "https://www.instao.fr/connexion",
        "selectors": {
            "email": "input[type='email'], input[name='email'], #email",
            "password": "input[type='password'], input[name='password'], #password",
            "submit": "button[type='submit'], input[type='submit']",
        },
    },
    "marches_securises": {
        "label": "Marchés Sécurisés",
        "url": "https://www.marches-securises.fr/entreprise/?page=connexion",
        "selectors": {
            "email": "input[name='login'], input[type='email'], #login",
            "password": "input[name='pass'], input[type='password'], #password",
            "submit": "input[type='submit'], button[type='submit']",
        },
    },
    "tendersgo": {
        "label": "Tenders Go",
        "url": "https://app.tendersgo.com/login",
        "selectors": {
            "email": "input[type='email'], input[name='email'], #email",
            "password": "input[type='password'], input[name='password'], #password",
            "submit": "button[type='submit'], input[type='submit']",
        },
    },
}

_SITES_PUBLIC = {
    "vaao": "VAAO",
    "dept974": "Marchés Publics 974",
    "marchespublicsinfo": "Marchés Publics Info",
}

_ALL_CREDENTIAL_SITES: dict[str, str] = (
    {site: cfg["label"] for site, cfg in _LOGIN_CONFIG.items()} | _SITES_PUBLIC
)

_WORKER_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "_test_login_worker.py",
)
```

- [ ] **Step 1.5: Add `GET /api/credentials` route at end of `backend/main.py`**

```python
# ── GET /api/credentials ──────────────────────────────────────────────────────

@app.get("/api/credentials", summary="Liste les 8 sites protégés et leur statut d'auth")
def list_credentials():
    from models import Credential as _Cred
    db = SessionLocal()
    try:
        db_creds = {c.site: c for c in db.query(_Cred).all()}
    finally:
        db.close()
    result = []
    for site, label in sorted(_ALL_CREDENTIAL_SITES.items()):
        email_var, _ = _CRED_ENV_MAP.get(site, (f"{site.upper()}_EMAIL", ""))
        env_email = os.getenv(email_var)
        if env_email:
            status, email = "env_override", env_email
        elif site in db_creds:
            status, email = "configured", db_creds[site].email
        else:
            status, email = "missing", None
        result.append({
            "site": site,
            "label": label,
            "status": status,
            "email": email,
            "has_login_url": site in _LOGIN_CONFIG,
        })
    return result
```

- [ ] **Step 1.6: Run tests — expect pass**

```
python -m pytest tests/test_credentials_routes.py::test_get_credentials_returns_8_sites tests/test_credentials_routes.py::test_get_credentials_missing_status tests/test_credentials_routes.py::test_get_credentials_configured_status tests/test_credentials_routes.py::test_get_credentials_env_override tests/test_credentials_routes.py::test_get_credentials_public_site_has_no_login_url -v
```

Expected: `5 passed`.

- [ ] **Step 1.7: Commit**

```
git add backend/main.py tests/test_credentials_routes.py
git commit -m "feat(api): GET /credentials — liste les 8 sites avec statut auth"
```

---

## Task 2: Backend — `POST` + `DELETE /api/credentials/{site}`

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/test_credentials_routes.py`

- [ ] **Step 2.1: Add tests to `tests/test_credentials_routes.py`**

Append to the file:

```python
def test_save_credential_known_site():
    with patch.object(_m, '_CredMgr') as mock_cm:
        resp = _client.post('/api/credentials/nukema',
                            json={'email': 'u@u.com', 'password': 'secret'})
    assert resp.status_code == 200
    assert resp.json()['ok'] is True
    mock_cm.save.assert_called_once_with('nukema', 'u@u.com', 'secret')


def test_save_credential_unknown_site():
    resp = _client.post('/api/credentials/nonexistent_xyz',
                        json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 404


def test_delete_credential_known_site():
    with patch.object(_m, '_CredMgr') as mock_cm:
        resp = _client.delete('/api/credentials/instao')
    assert resp.status_code == 200
    assert resp.json()['ok'] is True
    mock_cm.delete.assert_called_once_with('instao')


def test_delete_credential_unknown_site():
    resp = _client.delete('/api/credentials/nonexistent_xyz')
    assert resp.status_code == 404
```

- [ ] **Step 2.2: Run new tests — expect failure**

```
python -m pytest tests/test_credentials_routes.py::test_save_credential_known_site tests/test_credentials_routes.py::test_delete_credential_known_site -v
```

Expected: `404 Not Found` (routes don't exist yet).

- [ ] **Step 2.3: Add routes to `backend/main.py`** (after `GET /api/credentials`)

```python
# ── POST /api/credentials/{site} ─────────────────────────────────────────────

@app.post("/api/credentials/{site}", summary="Sauvegarder les identifiants d'un site")
def save_credential(site: str, body: CredentialSave):
    if site not in _ALL_CREDENTIAL_SITES:
        raise HTTPException(status_code=404, detail=f"Site inconnu : {site}")
    _CredMgr.save(site, body.email, body.password)
    return {"ok": True}


# ── DELETE /api/credentials/{site} ───────────────────────────────────────────

@app.delete("/api/credentials/{site}", summary="Supprimer les identifiants d'un site")
def delete_credential(site: str):
    if site not in _ALL_CREDENTIAL_SITES:
        raise HTTPException(status_code=404, detail=f"Site inconnu : {site}")
    _CredMgr.delete(site)
    return {"ok": True}
```

- [ ] **Step 2.4: Run all credential tests — expect pass**

```
python -m pytest tests/test_credentials_routes.py -v
```

Expected: `9 passed`.

- [ ] **Step 2.5: Commit**

```
git add backend/main.py tests/test_credentials_routes.py
git commit -m "feat(api): POST + DELETE /credentials/{site} — CRUD identifiants"
```

---

## Task 3: Backend — `POST /api/credentials/{site}/test`

**Files:**
- Modify: `backend/main.py`
- Modify: `tests/test_credentials_routes.py`

- [ ] **Step 3.1: Add tests**

Append to `tests/test_credentials_routes.py`:

```python
def test_test_credential_public_site_skips_playwright():
    """Sites without login URL return ok=True immediately."""
    resp = _client.post('/api/credentials/vaao/test',
                        json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is True
    assert 'message' in body


def test_test_credential_playwright_success():
    import json as _json_mod
    mock_proc = MagicMock()
    mock_proc.stdout = _json_mod.dumps({'ok': True, 'url_finale': 'https://nukema.com/dashboard'})
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.return_value = mock_proc
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'correct'})
    assert resp.status_code == 200
    assert resp.json()['ok'] is True


def test_test_credential_playwright_wrong_password():
    import json as _json_mod
    mock_proc = MagicMock()
    mock_proc.stdout = _json_mod.dumps({'ok': False, 'erreur_page': 'Identifiants incorrects'})
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.return_value = mock_proc
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'wrong'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is False
    assert 'incorrects' in body['message']


def test_test_credential_playwright_timeout():
    with patch.object(_m, '_subprocess') as mock_sub:
        mock_sub.run.side_effect = TimeoutError()
        mock_sub.TimeoutExpired = TimeoutError
        resp = _client.post('/api/credentials/nukema/test',
                            json={'email': 'u@u.com', 'password': 'p'})
    assert resp.status_code == 200
    body = resp.json()
    assert body['ok'] is False
    assert 'expiré' in body['message']
```

- [ ] **Step 3.2: Run new tests — expect failure**

```
python -m pytest tests/test_credentials_routes.py::test_test_credential_playwright_success -v
```

Expected: `404 Not Found`.

- [ ] **Step 3.3: Add route to `backend/main.py`**

```python
# ── POST /api/credentials/{site}/test ────────────────────────────────────────

@app.post("/api/credentials/{site}/test", summary="Tester la connexion Playwright")
def test_credential(site: str, body: CredentialSave):
    if site not in _LOGIN_CONFIG:
        return {"ok": True, "message": "Accès public — aucun test disponible"}
    cfg = _LOGIN_CONFIG[site]
    payload = {
        "url": cfg["url"],
        "selectors": cfg["selectors"],
        "email": body.email,
        "password": body.password,
    }
    try:
        proc = _subprocess.run(
            [sys.executable, _WORKER_PATH],
            input=_json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=35,
        )
        result = _json.loads(proc.stdout)
        if result.get("ok"):
            return {"ok": True}
        msg = (
            result.get("erreur_page")
            or result.get("champ_manquant")
            or result.get("erreur_worker")
            or "Connexion refusée"
        )
        return {"ok": False, "message": msg}
    except _subprocess.TimeoutExpired:
        return {"ok": False, "message": "Test expiré — site trop lent ou inaccessible (>30s)"}
    except Exception as exc:
        return {"ok": False, "message": str(exc)}
```

- [ ] **Step 3.4: Run all credential tests — expect pass**

```
python -m pytest tests/test_credentials_routes.py -v
```

Expected: `13 passed`.

- [ ] **Step 3.5: Commit**

```
git add backend/main.py tests/test_credentials_routes.py
git commit -m "feat(api): POST /credentials/{site}/test — test Playwright en sous-processus"
```

---

## Task 4: Frontend — API functions + React Query hooks

**Files:**
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/hooks/useTenders.js`

No unit tests needed — these are thin wrappers exercised by Task 5's manual testing.

- [ ] **Step 4.1: Add API functions to `frontend/src/services/api.js`**

After the `getDuplicates` export (around line 92), add:

```js
// ── Credentials ───────────────────────────────────────────────────────────────

export const getCredentials = () =>
  api.get('/credentials').then((r) => r.data)

export const saveCredential = (site, email, password) =>
  api.post(`/credentials/${site}`, { email, password }).then((r) => r.data)

export const deleteCredential = (site) =>
  api.delete(`/credentials/${site}`).then((r) => r.data)

export const testCredential = (site, email, password) =>
  api.post(`/credentials/${site}/test`, { email, password }).then((r) => r.data)
```

- [ ] **Step 4.2: Add React Query hooks to `frontend/src/hooks/useTenders.js`**

Add the import of the 4 new functions at the top (inside the existing import block from `../services/api`):

```js
import {
  // … existing imports …
  getCredentials, saveCredential, deleteCredential, testCredential,
} from '../services/api'
```

Append the hooks at the bottom of the file:

```js
// ── Credentials ───────────────────────────────────────────────────────────────

export const useCredentials = () =>
  useQuery({ queryKey: ['credentials'], queryFn: getCredentials, staleTime: 30_000 })

export const useSaveCredential = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ site, email, password }) => saveCredential(site, email, password),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['credentials'] }),
  })
}

export const useDeleteCredential = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (site) => deleteCredential(site),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['credentials'] }),
  })
}

export const useTestCredential = () =>
  useMutation({
    mutationFn: ({ site, email, password }) => testCredential(site, email, password),
  })
```

- [ ] **Step 4.3: Verify no TypeScript/lint errors**

```
cd frontend && npm run lint 2>&1 | tail -20
```

Expected: no errors.

- [ ] **Step 4.4: Commit (2 files, 2 commits per CLAUDE.md rules)**

```
git add frontend/src/services/api.js
git commit -m "feat(frontend/api): getCredentials, saveCredential, deleteCredential, testCredential"
git add frontend/src/hooks/useTenders.js
git commit -m "feat(frontend/hooks): useCredentials + useSaveCredential + useDeleteCredential + useTestCredential"
```

---

## Task 5: Frontend — `CredentialsSection` in `Parametres.jsx`

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx`

- [ ] **Step 5.1: Add imports at top of `Parametres.jsx`**

The existing import of hooks is at line 1-13. Add to the hook imports:

```js
import {
  // … existing imports …
  useCredentials,
  useSaveCredential,
  useDeleteCredential,
  useTestCredential,
} from '../hooks/useTenders'
```

- [ ] **Step 5.2: Add `CredentialsSection` component before the `export default` line**

```jsx
function CredentialsSection() {
  const { data: credentials = [], isLoading, refetch } = useCredentials()
  const { mutate: saveMutation } = useSaveCredential()
  const { mutate: removeMutation } = useDeleteCredential()
  const { mutate: testMutation, isPending: testing } = useTestCredential()

  const [open, setOpen] = useState(null)
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPwd, setShowPwd] = useState(false)
  const [testResult, setTestResult] = useState(null)

  const openSite = (cred) => {
    setOpen(open === cred.site ? null : cred.site)
    setForm({ email: cred.email || '', password: '' })
    setTestResult(null)
  }

  const handleFormChange = (field, value) => {
    setForm((f) => ({ ...f, [field]: value }))
    setTestResult(null)
  }

  const handleTest = () => {
    setTestResult(null)
    testMutation(
      { site: open, email: form.email, password: form.password },
      {
        onSuccess: (data) => setTestResult(data),
        onError: () => setTestResult({ ok: false, message: 'Erreur réseau' }),
      },
    )
  }

  const handleSave = () => {
    saveMutation(
      { site: open, email: form.email, password: form.password },
      { onSuccess: () => { refetch(); setOpen(null) } },
    )
  }

  const handleDelete = (site) => {
    removeMutation(site, { onSuccess: () => refetch() })
  }

  const badge = (status) => {
    if (status === 'configured')
      return <span className="px-1.5 py-0.5 text-xs rounded bg-green-100 text-green-700">✓ Configuré</span>
    if (status === 'env_override')
      return <span className="px-1.5 py-0.5 text-xs rounded bg-blue-100 text-blue-700">ENV</span>
    return <span className="px-1.5 py-0.5 text-xs rounded bg-red-100 text-red-700">Manquant</span>
  }

  const saveDisabled = !form.email || !form.password ||
    (credentials.find((c) => c.site === open)?.has_login_url && testResult?.ok !== true)

  return (
    <div id="credentials" className="space-y-4">
      <SectionTitle>🔐 Identifiants sites protégés</SectionTitle>
      {isLoading && <p className="text-sm text-gray-400">Chargement…</p>}
      <div className="space-y-2">
        {credentials.map((cred) => (
          <div key={cred.site} className="border border-gray-200 rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                {badge(cred.status)}
                <span className="text-sm font-medium text-gray-800">{cred.label}</span>
                {cred.email && (
                  <span className="text-xs text-gray-400">{cred.email}</span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {cred.status === 'configured' && (
                  <button
                    onClick={() => handleDelete(cred.site)}
                    className="text-xs text-red-500 hover:text-red-700"
                  >
                    Supprimer
                  </button>
                )}
                {cred.status !== 'env_override' && (
                  <button
                    onClick={() => openSite(cred)}
                    className="text-xs text-indigo-600 hover:text-indigo-800"
                  >
                    {open === cred.site ? 'Fermer' : cred.status === 'configured' ? 'Modifier' : 'Configurer'}
                  </button>
                )}
              </div>
            </div>

            {open === cred.site && (
              <div className="px-4 pb-4 pt-3 space-y-3 border-t border-gray-100 bg-gray-50">
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="email"
                    placeholder="Email"
                    value={form.email}
                    onChange={(e) => handleFormChange('email', e.target.value)}
                    className="px-3 py-1.5 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-400"
                  />
                  <div className="relative">
                    <input
                      type={showPwd ? 'text' : 'password'}
                      placeholder="Mot de passe"
                      value={form.password}
                      onChange={(e) => handleFormChange('password', e.target.value)}
                      className="w-full px-3 py-1.5 pr-12 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-400"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPwd((v) => !v)}
                      className="absolute right-2 top-1.5 text-xs text-gray-400 hover:text-gray-600"
                    >
                      {showPwd ? 'Cacher' : 'Voir'}
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {cred.has_login_url && (
                    <button
                      onClick={handleTest}
                      disabled={testing || !form.email || !form.password}
                      className="px-3 py-1.5 text-sm bg-white border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50 transition-colors"
                    >
                      {testing ? 'Test en cours… (~15s)' : 'Tester la connexion'}
                    </button>
                  )}
                  <button
                    onClick={handleSave}
                    disabled={saveDisabled}
                    className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    Sauvegarder
                  </button>
                </div>
                {testResult?.ok === true && (
                  <p className="text-sm text-green-600">✓ Connexion réussie — vous pouvez sauvegarder</p>
                )}
                {testResult?.ok === false && (
                  <p className="text-sm text-red-600">✗ {testResult.message}</p>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 5.3: Add `CredentialsSection` to the `Parametres` export**

Find the `export default function Parametres()` block (around line 201) and add `<CredentialsSection />` after `<CollectSection />`:

```jsx
export default function Parametres() {
  return (
    <div className="p-5 space-y-10 max-w-4xl">
      <CollectSection />
      <CredentialsSection />
      <AnalyseSection />
      <DoublonsSection />
      <MaintenanceSection />
    </div>
  )
}
```

- [ ] **Step 5.4: Manual test — start the app and verify**

```
cd frontend && npm run dev
```

Open `http://localhost:5173`, navigate to **Paramètres**. Verify:
- "🔐 Identifiants sites protégés" section appears with 8 rows
- Each row shows a badge (Manquant / Configuré / ENV)
- Clicking "Configurer" opens the form with email + password fields + "Tester la connexion" + "Sauvegarder"
- Sites without login URL (VAAO, Marchés Publics 974, Marchés Publics Info) show no "Tester la connexion" button and Save is immediately enabled

- [ ] **Step 5.5: Commit**

```
git add frontend/src/pages/Parametres.jsx
git commit -m "feat(frontend): CredentialsSection — gestion des identifiants sites protégés"
```

---

## Task 6: Scrapers — standardize `CREDENTIALS_MISSING`

Three scrapers already have the early-return pattern but log the wrong error string. Change the string in each to `"CREDENTIALS_MISSING"` so the frontend can detect it.

**Files:**
- Modify: `scraper_marchessecurises.py:40`
- Modify: `scraper_instao.py:41`
- Modify: `scraper_tendersgo.py:40`
- Create: `tests/test_credentials_missing.py`

- [ ] **Step 6.1: Write failing tests**

Create `tests/test_credentials_missing.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock


def _run_with_no_creds(module_name, func_name, scraper_display_name):
    with patch(f'{module_name}.CredentialManager') as cm, \
         patch(f'{module_name}.init_db'), \
         patch(f'{module_name}.SessionLocal') as sl, \
         patch(f'{module_name}.start_scraper_run', return_value=42), \
         patch(f'{module_name}.finish_scraper_run') as finish_run:
        cm.get.return_value = None
        sl.return_value.close = MagicMock()
        import importlib
        mod = importlib.import_module(module_name)
        result = getattr(mod, func_name)()
    return result, finish_run


def test_marchessecurises_reports_credentials_missing():
    result, finish_run = _run_with_no_creds(
        'scraper_marchessecurises', 'fetch_marchessecurises_tenders', 'Marchés Sécurisés'
    )
    assert result == 0
    finish_run.assert_called_once()
    _, kwargs = finish_run.call_args
    assert kwargs['error'] == 'CREDENTIALS_MISSING'


def test_instao_reports_credentials_missing():
    result, finish_run = _run_with_no_creds(
        'scraper_instao', 'fetch_instao_tenders', 'Instao'
    )
    assert result == 0
    finish_run.assert_called_once()
    _, kwargs = finish_run.call_args
    assert kwargs['error'] == 'CREDENTIALS_MISSING'


def test_tendersgo_reports_credentials_missing():
    result, finish_run = _run_with_no_creds(
        'scraper_tendersgo', 'fetch_tendersgo_tenders', 'Tenders Go'
    )
    assert result == 0
    finish_run.assert_called_once()
    _, kwargs = finish_run.call_args
    assert kwargs['error'] == 'CREDENTIALS_MISSING'
```

- [ ] **Step 6.2: Run tests — expect failure**

```
python -m pytest tests/test_credentials_missing.py -v
```

Expected: `AssertionError` — `'Pas d'identifiants configurés' != 'CREDENTIALS_MISSING'`.

- [ ] **Step 6.3: Fix `scraper_marchessecurises.py`**

In `scraper_marchessecurises.py`, line 40, change:

```python
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Pas d'identifiants configurés")
```

to:

```python
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="CREDENTIALS_MISSING")
```

- [ ] **Step 6.4: Fix `scraper_instao.py`**

In `scraper_instao.py`, line 41, change:

```python
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Pas d'identifiants configurés")
```

to:

```python
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="CREDENTIALS_MISSING")
```

- [ ] **Step 6.5: Fix `scraper_tendersgo.py`**

In `scraper_tendersgo.py`, line 40, change:

```python
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="Pas d'identifiants configurés")
```

to:

```python
            finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error="CREDENTIALS_MISSING")
```

- [ ] **Step 6.6: Run tests — expect pass**

```
python -m pytest tests/test_credentials_missing.py -v
```

Expected: `3 passed`.

- [ ] **Step 6.7: Commit each file separately (per project rules)**

```
git add scraper_marchessecurises.py tests/test_credentials_missing.py
git commit -m "fix(scraper): marchessecurises — error CREDENTIALS_MISSING standardisé"

git add scraper_instao.py
git commit -m "fix(scraper): instao — error CREDENTIALS_MISSING standardisé"

git add scraper_tendersgo.py
git commit -m "fix(scraper): tendersgo — error CREDENTIALS_MISSING standardisé"
```

---

## Task 7: Frontend — `CollectSection` handles `CREDENTIALS_MISSING`

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx` (inside `CollectSection`)

- [ ] **Step 7.1: Find and update the error display in `CollectSection`**

In `Parametres.jsx`, the `CollectSection` currently shows (around line 77):

```jsx
{r.status === 'error' && <span className="text-red-500 text-xs">{r.error}</span>}
```

Replace that line with:

```jsx
{r.status === 'error' && (
  r.error === 'CREDENTIALS_MISSING' ? (
    <a
      href="#credentials"
      className="text-amber-600 text-xs hover:underline"
    >
      ⚠ Identifiants manquants — configurer ↗
    </a>
  ) : (
    <span className="text-red-500 text-xs">{r.error}</span>
  )
)}
```

- [ ] **Step 7.2: Manual test**

With the app running:
1. Go to Paramètres
2. Launch a collection including Instao, Marchés Sécurisés, or Tenders Go (without credentials configured)
3. Verify the collect result row shows "⚠ Identifiants manquants — configurer ↗" in amber
4. Clicking the link scrolls to the `#credentials` section

- [ ] **Step 7.3: Commit**

```
git add frontend/src/pages/Parametres.jsx
git commit -m "feat(frontend): CollectSection — lien vers credentials quand CREDENTIALS_MISSING"
```

---

## Self-Review

**Spec coverage:**
- ✓ 8 sites identifiés avec statut — `GET /api/credentials` + `_ALL_CREDENTIAL_SITES`
- ✓ Saisie email + mot de passe — formulaire inline `CredentialsSection`
- ✓ Test Playwright avant sauvegarde — `POST /test` + bouton "Tester la connexion"
- ✓ Sauvegarde chiffrée persistante — `CredentialManager.save()` + Fernet
- ✓ Suppression — `DELETE` route + bouton "Supprimer"
- ✓ Badge de statut (manquant/configuré/env_override) — `status` field in `GET /credentials`
- ✓ CREDENTIALS_MISSING visible dans les runs — 3 scrapers + `CollectSection` link
- ✓ Sites sans URL de login (vaao, dept974, marchespublicsinfo) — pas de bouton "Tester", Save immédiat
- ✓ Variables d'env ont priorité (env_override, lecture seule) — `GET /credentials` logic

**Placeholder scan:** None found.

**Type consistency:**
- `site` key is always the string key from `_ALL_CREDENTIAL_SITES` (e.g. `"marches_securises"` not `"marchessecurises"`)
- `testCredential(site, email, password)` → `POST /credentials/{site}/test` with body `{email, password}` — matches `CredentialSave` model
- `useSaveCredential` mutationFn destructures `{ site, email, password }` — matches `handleSave` call in the component
