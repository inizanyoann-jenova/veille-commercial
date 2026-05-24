# Personnalisation des couleurs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un onglet "Apparence" dans Paramètres permettant de modifier 4 couleurs de l'interface via des sélecteurs natifs, avec persistance en localStorage.

**Architecture:** Les couleurs sont stockées comme variables CSS (`--color-ocean-*`) sur `document.documentElement`. Tailwind les référence via le format `rgb(var(--color-X) / <alpha-value>)` pour conserver le support des modificateurs d'opacité. Les valeurs sont sauvegardées en localStorage et rechargées avant le premier rendu React dans `main.jsx`.

**Tech Stack:** React 18, Tailwind CSS v3, Vitest, @testing-library/react, localStorage (navigateur)

---

## File Map

| Fichier | Action | Rôle |
|---|---|---|
| `frontend/src/index.css` | Modifier | Ajouter les variables CSS par défaut dans `:root` |
| `frontend/tailwind.config.js` | Modifier | Référencer les 4 couleurs configurables via CSS vars |
| `frontend/src/utils/theme.js` | Créer | Fonctions pures : conversion hex→RGB, apply, load |
| `frontend/src/utils/theme.test.js` | Créer | Tests unitaires des fonctions utilitaires |
| `frontend/src/main.jsx` | Modifier | Appeler `loadSavedTheme()` avant le rendu |
| `frontend/src/pages/Parametres.jsx` | Modifier | Ajouter `ApparenceTab` et l'onglet dans `TABS` |

---

## Task 1 : Infrastructure CSS

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1 : Ajouter les variables CSS dans index.css**

Ouvrir `frontend/src/index.css`. Remplacer le contenu entier par :

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
}

:root {
  --color-ocean-deep:  4 13 26;
  --color-ocean-cyan:  0 200 255;
  --color-ocean-coral: 255 107 107;
  --color-ocean-text:  221 238 255;
}
```

- [ ] **Step 2 : Mettre à jour tailwind.config.js**

Ouvrir `frontend/tailwind.config.js`. Remplacer le bloc `ocean:` par :

```js
ocean: {
  deep:   'rgb(var(--color-ocean-deep) / <alpha-value>)',
  navy:   '#071428',
  panel:  '#0a1c35',
  border: 'rgba(0,200,255,0.08)',
  glow:   'rgba(0,200,255,0.15)',
  cyan:   'rgb(var(--color-ocean-cyan) / <alpha-value>)',
  teal:   '#00e5c0',
  coral:  'rgb(var(--color-ocean-coral) / <alpha-value>)',
  gold:   '#ffd700',
  text:   'rgb(var(--color-ocean-text) / <alpha-value>)',
  muted:  'rgba(150,200,240,0.4)',
},
```

- [ ] **Step 3 : Vérifier que le build ne casse pas**

```bash
cd frontend && npm run build
```

Expected : build réussi sans erreur. Si des classes Tailwind cassent (ex: `text-ocean-muted/50`), c'est parce que `muted` est déjà une valeur `rgba()` — elle n'est pas convertie, pas de problème.

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/index.css frontend/tailwind.config.js
git commit -m "feat(theme): add CSS variables for runtime color customization"
```

---

## Task 2 : Fonctions utilitaires de thème

**Files:**
- Create: `frontend/src/utils/theme.js`
- Create: `frontend/src/utils/theme.test.js`

- [ ] **Step 1 : Écrire les tests d'abord**

Créer `frontend/src/utils/theme.test.js` :

```js
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { hexToRgbString, applyTheme, loadSavedTheme, DEFAULTS, THEME_KEY } from './theme'

describe('hexToRgbString', () => {
  it('convertit un hex sombre en chaîne RGB', () => {
    expect(hexToRgbString('#040d1a')).toBe('4 13 26')
  })

  it('convertit un hex cyan en chaîne RGB', () => {
    expect(hexToRgbString('#00c8ff')).toBe('0 200 255')
  })

  it('convertit un hex coral en chaîne RGB', () => {
    expect(hexToRgbString('#ff6b6b')).toBe('255 107 107')
  })

  it('convertit un hex texte en chaîne RGB', () => {
    expect(hexToRgbString('#ddeeff')).toBe('221 238 255')
  })
})

describe('applyTheme', () => {
  beforeEach(() => {
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  it('applique les 4 variables CSS sur documentElement', () => {
    const colors = { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' }
    applyTheme(colors)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', '4 13 26')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '0 200 255')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-coral', '255 107 107')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-text', '221 238 255')
  })
})

describe('loadSavedTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })

  it('applique DEFAULTS si rien en localStorage', () => {
    loadSavedTheme()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', DEFAULTS.deep)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', DEFAULTS.cyan)
  })

  it('applique les couleurs sauvegardées depuis localStorage', () => {
    const saved = { deep: '10 20 30', cyan: '100 150 200', coral: '200 50 50', text: '240 240 240' }
    localStorage.setItem(THEME_KEY, JSON.stringify(saved))
    loadSavedTheme()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-deep', '10 20 30')
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--color-ocean-cyan', '100 150 200')
  })
})
```

- [ ] **Step 2 : Lancer les tests (doivent échouer)**

```bash
cd frontend && npx vitest run src/utils/theme.test.js
```

Expected : FAIL — `Cannot find module './theme'`

- [ ] **Step 3 : Créer le module theme.js**

Créer `frontend/src/utils/theme.js` :

```js
export const THEME_KEY = 'theme-colors'

export const DEFAULTS = {
  deep:  '4 13 26',
  cyan:  '0 200 255',
  coral: '255 107 107',
  text:  '221 238 255',
}

export function hexToRgbString(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r} ${g} ${b}`
}

export function applyTheme(colors) {
  for (const [key, val] of Object.entries(colors)) {
    document.documentElement.style.setProperty(`--color-ocean-${key}`, val)
  }
}

export function loadSavedTheme() {
  const saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null')
  applyTheme(saved ?? DEFAULTS)
}
```

- [ ] **Step 4 : Relancer les tests (doivent passer)**

```bash
cd frontend && npx vitest run src/utils/theme.test.js
```

Expected : tous les tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/utils/theme.js frontend/src/utils/theme.test.js
git commit -m "feat(theme): add hexToRgbString, applyTheme, loadSavedTheme utilities"
```

---

## Task 3 : Chargement du thème au démarrage

**Files:**
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1 : Modifier main.jsx**

Ouvrir `frontend/src/main.jsx`. Ajouter l'import et l'appel **avant** `ReactDOM.createRoot` :

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'
import { loadSavedTheme } from './utils/theme'

loadSavedTheme()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
```

- [ ] **Step 2 : Vérifier dans le navigateur**

Lancer le dev server :
```bash
cd frontend && npm run dev
```

Ouvrir l'app. L'apparence doit être identique à avant (variables CSS appliquées avec les valeurs par défaut).

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/main.jsx
git commit -m "feat(theme): load saved theme colors from localStorage on startup"
```

---

## Task 4 : Onglet Apparence dans Paramètres

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx`

- [ ] **Step 1 : Écrire les tests du composant ApparenceTab**

Créer `frontend/src/pages/Parametres.apparence.test.jsx` :

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Parametres from './Parametres'

// Mock des hooks API pour isoler le test
vi.mock('../hooks/useTenders', () => ({
  useCredentials: () => ({ data: [], refetch: vi.fn(), isError: false }),
  useSaveCredential: () => ({ mutate: vi.fn(), isPending: false }),
  useDeleteCredential: () => ({ mutate: vi.fn(), isPending: false }),
  useTestCredential: () => ({ mutate: vi.fn(), isPending: false }),
  useAnalyzePending: () => ({ mutate: vi.fn(), isPending: false }),
  useDuplicates: () => ({ data: [], isLoading: false }),
  useDetectDuplicates: () => ({ mutate: vi.fn(), isPending: false }),
  useResolveDuplicate: () => ({ mutate: vi.fn() }),
  useArchiveOld: () => ({ mutate: vi.fn(), isPending: false }),
  useResetDb: () => ({ mutate: vi.fn(), isPending: false }),
}))

// Mock des fonctions utilitaires thème
vi.mock('../utils/theme', () => ({
  THEME_KEY: 'theme-colors',
  DEFAULTS: { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' },
  hexToRgbString: (hex) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `${r} ${g} ${b}`
  },
  applyTheme: vi.fn(),
  loadSavedTheme: vi.fn(),
}))

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Parametres — onglet Apparence', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('affiche l\'onglet Apparence dans la liste des onglets', () => {
    render(<Parametres />, { wrapper: Wrapper })
    expect(screen.getByText(/Apparence/i)).toBeInTheDocument()
  })

  it('affiche les 4 sélecteurs de couleur quand l\'onglet est actif', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByText('Fond')).toBeInTheDocument()
    expect(screen.getByText('Couleur principale')).toBeInTheDocument()
    expect(screen.getByText('Alerte')).toBeInTheDocument()
    expect(screen.getByText('Texte')).toBeInTheDocument()
  })

  it('affiche les boutons Appliquer et Réinitialiser', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByRole('button', { name: /appliquer/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /réinitialiser/i })).toBeInTheDocument()
  })

  it('sauvegarde dans localStorage au clic sur Appliquer', async () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /appliquer/i }))
    const saved = localStorage.getItem('theme-colors')
    expect(saved).not.toBeNull()
    const parsed = JSON.parse(saved)
    expect(parsed).toHaveProperty('deep')
    expect(parsed).toHaveProperty('cyan')
    expect(parsed).toHaveProperty('coral')
    expect(parsed).toHaveProperty('text')
  })

  it('efface localStorage et réinitialise au clic sur Réinitialiser', () => {
    localStorage.setItem('theme-colors', JSON.stringify({ deep: '10 20 30', cyan: '100 100 100', coral: '200 50 50', text: '240 240 240' }))
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /réinitialiser/i }))
    expect(localStorage.getItem('theme-colors')).toBeNull()
  })
})
```

- [ ] **Step 2 : Lancer les tests (doivent échouer)**

```bash
cd frontend && npx vitest run src/pages/Parametres.apparence.test.jsx
```

Expected : FAIL — onglet "Apparence" non trouvé.

- [ ] **Step 3 : Ajouter ApparenceTab et l'onglet dans Parametres.jsx**

Ouvrir `frontend/src/pages/Parametres.jsx`.

**a) Ajouter l'import en haut du fichier** (après les imports existants) :

```jsx
import { THEME_KEY, DEFAULTS, hexToRgbString, applyTheme } from '../utils/theme'
```

> Note : `useState` est déjà importé dans le fichier — pas besoin de le réimporter.

**b) Ajouter le composant `ApparenceTab`** avant `// ── Page principale` :

```jsx
// ── Onglet Apparence ──────────────────────────────────────────────────────────

const COLOR_FIELDS = [
  { key: 'deep',  label: 'Fond',              desc: 'Arrière-plan principal de l\'app', hex: '#040d1a' },
  { key: 'cyan',  label: 'Couleur principale', desc: 'Liens, boutons, éléments actifs',  hex: '#00c8ff' },
  { key: 'coral', label: 'Alerte',             desc: 'Erreurs, dangers, badges urgents', hex: '#ff6b6b' },
  { key: 'text',  label: 'Texte',              desc: 'Couleur du texte principal',       hex: '#ddeeff' },
]

function rgbStringToHex(rgb) {
  return '#' + rgb.split(' ').map((n) => parseInt(n).toString(16).padStart(2, '0')).join('')
}

function ApparenceTab() {
  const saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null') ?? DEFAULTS
  const [colors, setColors] = useState({
    deep:  saved.deep,
    cyan:  saved.cyan,
    coral: saved.coral,
    text:  saved.text,
  })

  const handleChange = (key, hex) => {
    const rgb = hexToRgbString(hex)
    setColors((prev) => ({ ...prev, [key]: rgb }))
    applyTheme({ [key]: rgb })
  }

  const handleApply = () => {
    localStorage.setItem(THEME_KEY, JSON.stringify(colors))
  }

  const handleReset = () => {
    setColors({ ...DEFAULTS })
    applyTheme(DEFAULTS)
    localStorage.removeItem(THEME_KEY)
  }

  return (
    <div className="space-y-6">
      <p className="font-sans text-sm text-ocean-muted">
        Personnalisez les couleurs de l'interface. Les changements sont appliqués immédiatement.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {COLOR_FIELDS.map(({ key, label, desc }) => (
          <div key={key} className="flex items-center gap-3 p-3 bg-ocean-panel border border-ocean-border rounded-lg">
            <label
              className="w-10 h-10 rounded-lg border-2 border-white/15 flex-shrink-0 cursor-pointer overflow-hidden relative"
              style={{ background: rgbStringToHex(colors[key]) }}
            >
              <input
                type="color"
                value={rgbStringToHex(colors[key])}
                onChange={(e) => handleChange(key, e.target.value)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
            </label>
            <div className="min-w-0">
              <div className="font-sans text-sm font-medium text-ocean-text">{label}</div>
              <div className="font-sans text-xs text-ocean-muted">{desc}</div>
              <div className="font-mono text-xs text-ocean-muted mt-0.5">{rgbStringToHex(colors[key])}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 pt-4 border-t border-ocean-border">
        <button
          onClick={handleApply}
          className="px-4 py-2 bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 transition-colors"
        >
          💾 Appliquer
        </button>
        <button
          onClick={handleReset}
          className="px-4 py-2 bg-ocean-panel border border-ocean-border text-ocean-muted font-sans text-sm rounded-lg hover:bg-ocean-cyan/4 transition-colors"
        >
          Réinitialiser
        </button>
      </div>

      <p className="font-sans text-xs text-ocean-muted italic">
        Cliquez sur "Appliquer" pour sauvegarder vos choix entre les sessions.
      </p>
    </div>
  )
}
```

**c) Ajouter l'onglet dans le tableau `TABS`** :

```jsx
const TABS = [
  { id: 'connexion',  label: '🔐 Connexion' },
  { id: 'analyse',    label: '🤖 Analyse' },
  { id: 'maintenance', label: '🛠️ Maintenance' },
  { id: 'apparence',  label: '🎨 Apparence' },
]
```

**d) Ajouter le rendu de l'onglet** dans le return de `Parametres()`, après la ligne `{activeTab === 'maintenance' && <MaintenanceTab />}` :

```jsx
{activeTab === 'apparence' && <ApparenceTab />}
```

- [ ] **Step 4 : Relancer les tests (doivent passer)**

```bash
cd frontend && npx vitest run src/pages/Parametres.apparence.test.jsx
```

Expected : tous les tests PASS.

- [ ] **Step 5 : Lancer la suite complète pour vérifier les régressions**

```bash
cd frontend && npx vitest run
```

Expected : tous les tests PASS (aucune régression).

- [ ] **Step 6 : Vérifier dans le navigateur**

Ouvrir l'app, aller dans Paramètres → onglet Apparence. Vérifier :
- Les 4 sélecteurs s'affichent avec les bonnes couleurs actuelles
- Cliquer sur un sélecteur ouvre le color picker natif du navigateur
- Changer une couleur → l'interface change immédiatement
- Clic "Appliquer" → recharger la page → les couleurs sont conservées
- Clic "Réinitialiser" → retour au thème Océan Profond original

- [ ] **Step 7 : Commit**

```bash
git add frontend/src/pages/Parametres.jsx frontend/src/pages/Parametres.apparence.test.jsx
git commit -m "feat(parametres): add Apparence tab with 4 live color pickers"
```
