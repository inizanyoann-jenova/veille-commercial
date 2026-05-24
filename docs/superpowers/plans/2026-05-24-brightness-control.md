# Brightness Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un slider de luminosité ajustable dans Paramètres > Apparence, avec live preview et persistance localStorage.

**Architecture:** Variable CSS `--app-brightness` posée sur `:root`, appliquée via `filter: brightness()` sur le `<main>` de Layout. Le système de thème existant (`theme.js`) est étendu avec `applyBrightness` / `loadSavedBrightness`. Le slider vit dans `ApparenceTab` de `Parametres.jsx` et partage les boutons "Appliquer"/"Réinitialiser" existants.

**Tech Stack:** React 19, Vite, Tailwind CSS, Vitest + Testing Library, localStorage

---

## Fichiers concernés

| Fichier | Action |
|---|---|
| `frontend/src/utils/theme.js` | Modifier — ajouter `BRIGHTNESS_KEY`, `DEFAULT_BRIGHTNESS`, `applyBrightness`, `loadSavedBrightness` |
| `frontend/src/utils/theme.test.js` | Modifier — ajouter tests pour les deux nouvelles fonctions |
| `frontend/src/index.css` | Modifier — ajouter `--app-brightness: 1` au `:root` |
| `frontend/src/components/Layout.jsx` | Modifier — `useEffect` + `style` filter sur `<main>` |
| `frontend/src/pages/Parametres.apparence.test.jsx` | Modifier — mettre à jour les mocks + ajouter tests slider |
| `frontend/src/pages/Parametres.jsx` | Modifier — slider dans `ApparenceTab` |

---

## Task 1 : Tests pour les nouvelles fonctions de theme.js

**Files:**
- Modify: `frontend/src/utils/theme.test.js`

- [ ] **Step 1 : Ajouter les imports manquants en tête de fichier**

Ouvrir `frontend/src/utils/theme.test.js`. La ligne 2 importe actuellement :
```js
import { hexToRgbString, applyTheme, loadSavedTheme, DEFAULTS, THEME_KEY } from './theme'
```
Remplacer par :
```js
import {
  hexToRgbString, applyTheme, loadSavedTheme, DEFAULTS, THEME_KEY,
  applyBrightness, loadSavedBrightness, BRIGHTNESS_KEY, DEFAULT_BRIGHTNESS,
} from './theme'
```

- [ ] **Step 2 : Ajouter les blocs de tests à la fin du fichier**

Ajouter après la dernière accolade fermante du fichier :

```js
describe('applyBrightness', () => {
  beforeEach(() => {
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })
  afterEach(() => vi.restoreAllMocks())

  it('définit --app-brightness sur documentElement', () => {
    applyBrightness(1.5)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1.5')
  })

  it('accepte la valeur minimale 0.5', () => {
    applyBrightness(0.5)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '0.5')
  })

  it('accepte la valeur maximale 2.0', () => {
    applyBrightness(2)
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '2')
  })
})

describe('loadSavedBrightness', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.spyOn(document.documentElement.style, 'setProperty').mockImplementation(() => {})
  })
  afterEach(() => vi.restoreAllMocks())

  it('applique DEFAULT_BRIGHTNESS si rien en localStorage', () => {
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1')
  })

  it('applique la valeur sauvegardée depuis localStorage', () => {
    localStorage.setItem(BRIGHTNESS_KEY, '1.5')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1.5')
  })

  it('clamp à 2 les valeurs trop élevées', () => {
    localStorage.setItem(BRIGHTNESS_KEY, '5')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '2')
  })

  it('clamp à 0.5 les valeurs trop basses', () => {
    localStorage.setItem(BRIGHTNESS_KEY, '0.1')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '0.5')
  })

  it('ignore une valeur non-numérique et utilise le défaut', () => {
    localStorage.setItem(BRIGHTNESS_KEY, 'not-a-number')
    loadSavedBrightness()
    expect(document.documentElement.style.setProperty).toHaveBeenCalledWith('--app-brightness', '1')
  })
})
```

- [ ] **Step 3 : Vérifier que les tests échouent**

```
cd frontend && npm test -- --run utils/theme.test.js
```
Résultat attendu : **FAIL** — `applyBrightness is not a function` (ou similaire).

- [ ] **Step 4 : Commit du fichier test**

```
git add frontend/src/utils/theme.test.js
git commit -m "test(theme): add tests for applyBrightness and loadSavedBrightness"
```

---

## Task 2 : Implémenter applyBrightness et loadSavedBrightness dans theme.js

**Files:**
- Modify: `frontend/src/utils/theme.js`

- [ ] **Step 1 : Ajouter les exports à la fin de theme.js**

Ajouter après la dernière fonction `loadSavedTheme` :

```js
export const BRIGHTNESS_KEY = 'app-brightness'
export const DEFAULT_BRIGHTNESS = 1.0

export function applyBrightness(value) {
  document.documentElement.style.setProperty('--app-brightness', String(value))
}

export function loadSavedBrightness() {
  const saved = parseFloat(localStorage.getItem(BRIGHTNESS_KEY))
  const value = isNaN(saved) ? DEFAULT_BRIGHTNESS : Math.min(2.0, Math.max(0.5, saved))
  applyBrightness(value)
}
```

- [ ] **Step 2 : Vérifier que les tests passent**

```
cd frontend && npm test -- --run utils/theme.test.js
```
Résultat attendu : **PASS** — tous les tests du fichier verts.

- [ ] **Step 3 : Commit**

```
git add frontend/src/utils/theme.js
git commit -m "feat(theme): add applyBrightness and loadSavedBrightness"
```

---

## Task 3 : Ajouter la variable CSS dans index.css

**Files:**
- Modify: `frontend/src/index.css`

- [ ] **Step 1 : Ajouter --app-brightness au :root**

Ouvrir `frontend/src/index.css`. Le bloc `:root` actuel est :
```css
:root {
  --color-ocean-deep:  4 13 26;
  --color-ocean-cyan:  0 200 255;
  --color-ocean-coral: 255 107 107;
  --color-ocean-text:  221 238 255;
}
```
Remplacer par :
```css
:root {
  --color-ocean-deep:  4 13 26;
  --color-ocean-cyan:  0 200 255;
  --color-ocean-coral: 255 107 107;
  --color-ocean-text:  221 238 255;
  --app-brightness:    1;
}
```

- [ ] **Step 2 : Commit**

```
git add frontend/src/index.css
git commit -m "style: add --app-brightness CSS variable to :root"
```

---

## Task 4 : Appliquer le filtre de luminosité dans Layout.jsx

**Files:**
- Modify: `frontend/src/components/Layout.jsx`

- [ ] **Step 1 : Modifier Layout.jsx**

Le fichier actuel (`frontend/src/components/Layout.jsx`) n'importe rien depuis React. Remplacer le contenu entier par :

```jsx
import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import { loadSavedBrightness } from '../utils/theme'

const PAGE_TITLES = {
  '/': 'Pipeline',
  '/analytics': 'Analytics',
  '/direction': 'Direction',
  '/urgences': 'Urgences',
  '/parametres': 'Paramètres',
  '/guide': 'Guide',
}

export default function Layout() {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'DEF OI'
  const today = new Date().toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric',
  })

  useEffect(() => { loadSavedBrightness() }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-ocean-deep">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="h-[52px] bg-ocean-navy border-b border-ocean-border flex items-center px-6 flex-shrink-0">
          <span className="font-serif text-xl font-bold text-ocean-text">{title}</span>
          <span className="ml-auto font-mono text-xs text-ocean-muted">{today}</span>
        </header>
        <main
          className="flex-1 overflow-auto bg-ocean-deep"
          style={{ filter: 'brightness(var(--app-brightness, 1))' }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2 : Vérifier que les tests Layout existants passent toujours**

```
cd frontend && npm test -- --run components/Layout.test.jsx
```
Résultat attendu : **PASS** — les 2 tests existants toujours verts.

- [ ] **Step 3 : Commit**

```
git add frontend/src/components/Layout.jsx
git commit -m "feat(layout): apply brightness filter on main content area"
```

---

## Task 5 : Mettre à jour les mocks et ajouter les tests du slider

**Files:**
- Modify: `frontend/src/pages/Parametres.apparence.test.jsx`

- [ ] **Step 1 : Remplacer le contenu entier du fichier**

```jsx
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Parametres from './Parametres'
import { applyTheme, applyBrightness } from '../utils/theme'

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
  useSaveMistralKey: () => ({ mutate: vi.fn(), isPending: false, isSuccess: false, isError: false, error: null, reset: vi.fn() }),
  useMistralStatus: () => ({ data: undefined }),
}))

vi.mock('../utils/theme', () => ({
  THEME_KEY: 'theme-colors',
  BRIGHTNESS_KEY: 'app-brightness',
  DEFAULTS: { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' },
  DEFAULT_BRIGHTNESS: 1.0,
  hexToRgbString: (hex) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return `${r} ${g} ${b}`
  },
  applyTheme: vi.fn(),
  loadSavedTheme: vi.fn(),
  applyBrightness: vi.fn(),
  loadSavedBrightness: vi.fn(),
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

  it('sauvegarde les couleurs dans localStorage au clic sur Appliquer', () => {
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
    expect(applyTheme).toHaveBeenCalledWith({ deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' })
  })

  it('affiche le slider de luminosité', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByRole('slider', { name: /luminosité/i })).toBeInTheDocument()
  })

  it('appelle applyBrightness quand le slider change', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    const slider = screen.getByRole('slider', { name: /luminosité/i })
    fireEvent.change(slider, { target: { value: '1.5' } })
    expect(applyBrightness).toHaveBeenCalledWith(1.5)
  })

  it('sauvegarde brightness dans localStorage au clic sur Appliquer', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    const slider = screen.getByRole('slider', { name: /luminosité/i })
    fireEvent.change(slider, { target: { value: '1.5' } })
    fireEvent.click(screen.getByRole('button', { name: /appliquer/i }))
    expect(localStorage.getItem('app-brightness')).toBe('1.5')
  })

  it('supprime brightness de localStorage au clic sur Réinitialiser', () => {
    localStorage.setItem('app-brightness', '1.5')
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    fireEvent.click(screen.getByRole('button', { name: /réinitialiser/i }))
    expect(localStorage.getItem('app-brightness')).toBeNull()
    expect(applyBrightness).toHaveBeenCalledWith(1.0)
  })

  it('affiche la valeur en % à côté du slider', () => {
    render(<Parametres />, { wrapper: Wrapper })
    fireEvent.click(screen.getByText(/Apparence/i))
    expect(screen.getByText('100%')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2 : Vérifier que les nouveaux tests échouent**

```
cd frontend && npm test -- --run pages/Parametres.apparence.test.jsx
```
Résultat attendu : **FAIL** — les tests `slider` échouent (slider inexistant dans le DOM).

- [ ] **Step 3 : Commit**

```
git add frontend/src/pages/Parametres.apparence.test.jsx
git commit -m "test(parametres): add brightness slider tests and fix useTenders mock"
```

---

## Task 6 : Ajouter le slider de luminosité dans Parametres.jsx

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx`

- [ ] **Step 1 : Mettre à jour l'import de theme.js**

Ligne 3 actuelle :
```js
import { THEME_KEY, DEFAULTS, hexToRgbString, applyTheme } from '../utils/theme'
```
Remplacer par :
```js
import { THEME_KEY, DEFAULTS, hexToRgbString, applyTheme, BRIGHTNESS_KEY, DEFAULT_BRIGHTNESS, applyBrightness } from '../utils/theme'
```

- [ ] **Step 2 : Remplacer la fonction ApparenceTab entière**

Localiser la fonction `ApparenceTab` (lignes ~414–491) et la remplacer entièrement par :

```jsx
function ApparenceTab() {
  const [colors, setColors] = useState(() => {
    const saved = JSON.parse(localStorage.getItem(THEME_KEY) || 'null') ?? DEFAULTS
    return {
      deep:  saved.deep  ?? DEFAULTS.deep,
      cyan:  saved.cyan  ?? DEFAULTS.cyan,
      coral: saved.coral ?? DEFAULTS.coral,
      text:  saved.text  ?? DEFAULTS.text,
    }
  })

  const [brightness, setBrightness] = useState(() => {
    const saved = parseFloat(localStorage.getItem(BRIGHTNESS_KEY))
    return isNaN(saved) ? DEFAULT_BRIGHTNESS : Math.min(2.0, Math.max(0.5, saved))
  })

  const handleChange = (key, hex) => {
    const rgb = hexToRgbString(hex)
    if (rgb === null) return
    setColors((prev) => ({ ...prev, [key]: rgb }))
    applyTheme({ [key]: rgb })
  }

  const handleBrightnessChange = (e) => {
    const value = parseFloat(e.target.value)
    setBrightness(value)
    applyBrightness(value)
  }

  const handleApply = () => {
    localStorage.setItem(THEME_KEY, JSON.stringify(colors))
    localStorage.setItem(BRIGHTNESS_KEY, String(brightness))
  }

  const handleReset = () => {
    setColors({ ...DEFAULTS })
    applyTheme(DEFAULTS)
    localStorage.removeItem(THEME_KEY)
    setBrightness(DEFAULT_BRIGHTNESS)
    applyBrightness(DEFAULT_BRIGHTNESS)
    localStorage.removeItem(BRIGHTNESS_KEY)
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

      <div className="p-3 bg-ocean-panel border border-ocean-border rounded-lg space-y-2">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-sans text-sm font-medium text-ocean-text">Luminosité</div>
            <div className="font-sans text-xs text-ocean-muted">Ajustez l'éclat global de l'interface</div>
          </div>
          <span className="font-mono text-sm text-ocean-cyan">{Math.round(brightness * 100)}%</span>
        </div>
        <input
          type="range"
          min="0.5"
          max="2.0"
          step="0.05"
          value={brightness}
          onChange={handleBrightnessChange}
          aria-label="Luminosité"
          className="w-full accent-ocean-cyan"
        />
        <div className="flex justify-between font-mono text-xs text-ocean-muted">
          <span>50%</span>
          <span>100%</span>
          <span>200%</span>
        </div>
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

- [ ] **Step 3 : Vérifier que tous les tests Parametres passent**

```
cd frontend && npm test -- --run pages/Parametres.apparence.test.jsx
```
Résultat attendu : **PASS** — tous les tests verts.

- [ ] **Step 4 : Lancer la suite complète pour détecter les régressions**

```
cd frontend && npm test -- --run
```
Résultat attendu : **PASS** — aucun test cassé.

- [ ] **Step 5 : Commit**

```
git add frontend/src/pages/Parametres.jsx
git commit -m "feat(parametres): add brightness slider in Apparence tab"
```
