# Frontend React Scaffold — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Scaffolder le frontend React (Vite + Tailwind + React Router + Axios + React Query) avec le Layout sidebar DEF OI et le service API complet.

**Architecture:** SPA React 18 avec sidebar fixe (#16213e) et routing React Router v6. Les appels API passent par un proxy Vite vers le backend FastAPI (localhost:8000). React Query gère le cache et le polling côté client.

**Tech Stack:** React 18, Vite 5, Tailwind CSS v3, React Router DOM v6, Axios, TanStack React Query v5, Vitest + Testing Library

---

## File Map

| Fichier | Rôle |
|---|---|
| `frontend/vite.config.js` | Config Vite + proxy `/api → localhost:8000` |
| `frontend/tailwind.config.js` | Contenu scanné + extensions couleurs |
| `frontend/src/index.css` | Directives Tailwind |
| `frontend/src/main.jsx` | Point d'entrée : QueryClientProvider + BrowserRouter |
| `frontend/src/App.jsx` | Routes React Router avec Layout comme wrapper |
| `frontend/src/services/api.js` | Instance Axios + toutes les fonctions par endpoint |
| `frontend/src/hooks/useTenders.js` | Hooks React Query (useQuery/useMutation) |
| `frontend/src/components/Sidebar.jsx` | Sidebar #16213e, nav items, badge urgences |
| `frontend/src/components/Layout.jsx` | Wrapper flex : Sidebar + topbar + `<Outlet/>` |
| `frontend/src/pages/Pipeline.jsx` | Stub page |
| `frontend/src/pages/Analytics.jsx` | Stub page |
| `frontend/src/pages/Direction.jsx` | Stub page |
| `frontend/src/pages/Urgences.jsx` | Stub page |
| `frontend/src/pages/Parametres.jsx` | Stub page |
| `frontend/src/pages/Guide.jsx` | Stub page |
| `frontend/src/services/api.test.js` | Tests Vitest pour le service API |
| `frontend/src/components/Sidebar.test.jsx` | Tests Vitest pour la Sidebar |

---

## Task 1 : Initialiser le projet Vite + React

**Files:**
- Create: `frontend/` (répertoire généré par Vite)

- [ ] **Step 1: Créer le projet**

Depuis la racine du repo (`commercial et opportunité def OI/`), exécuter :

```powershell
npm create vite@latest frontend -- --template react
```

Répondre aux prompts si nécessaire (normalement silencieux avec `--template react`).

- [ ] **Step 2: Installer les dépendances de base**

```powershell
cd frontend
npm install
```

- [ ] **Step 3: Installer les dépendances métier**

```powershell
npm install react-router-dom axios @tanstack/react-query
```

- [ ] **Step 4: Installer Tailwind CSS et ses pairs**

```powershell
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Attendu : création de `tailwind.config.js` et `postcss.config.js`.

- [ ] **Step 5: Installer Vitest et Testing Library**

```powershell
npm install -D vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 6: Vérifier l'installation**

```powershell
npm run dev
```

Attendu : le serveur démarre sur `http://localhost:5173` sans erreur. Couper avec Ctrl+C.

- [ ] **Step 7: Commit**

```powershell
cd ..
git add frontend/package.json frontend/package-lock.json frontend/index.html frontend/public frontend/src/main.jsx frontend/src/App.jsx frontend/src/App.css frontend/src/index.css frontend/vite.config.js frontend/tailwind.config.js frontend/postcss.config.js
git commit -m "chore: init frontend — Vite React + Tailwind + React Query + Router"
```

---

## Task 2 : Configurer Vite, Tailwind et le point d'entrée

**Files:**
- Modify: `frontend/vite.config.js`
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/main.jsx`

- [ ] **Step 1: Configurer le proxy Vite**

Remplacer le contenu de `frontend/vite.config.js` par :

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test-setup.js',
  },
})
```

- [ ] **Step 2: Configurer Tailwind**

Remplacer le contenu de `frontend/tailwind.config.js` par :

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#16213e',
        accent: '#e94560',
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: Remplacer index.css**

Remplacer tout le contenu de `frontend/src/index.css` par :

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* {
  box-sizing: border-box;
}
```

- [ ] **Step 4: Créer le fichier setup Vitest**

Créer `frontend/src/test-setup.js` :

```js
import '@testing-library/jest-dom'
```

- [ ] **Step 5: Réécrire main.jsx**

Remplacer `frontend/src/main.jsx` par :

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

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

- [ ] **Step 6: Supprimer les fichiers générés inutiles**

```powershell
Remove-Item frontend/src/App.css -ErrorAction SilentlyContinue
Remove-Item frontend/src/assets/react.svg -ErrorAction SilentlyContinue
Remove-Item frontend/public/vite.svg -ErrorAction SilentlyContinue
```

- [ ] **Step 7: Commit**

```powershell
git add frontend/vite.config.js frontend/tailwind.config.js frontend/src/index.css frontend/src/main.jsx frontend/src/test-setup.js
git commit -m "chore: configure Vite proxy, Tailwind, Vitest and entry point"
```

---

## Task 3 : Service API (services/api.js)

**Files:**
- Create: `frontend/src/services/api.js`
- Create: `frontend/src/services/api.test.js`

- [ ] **Step 1: Écrire le test en premier**

Créer `frontend/src/services/api.test.js` :

```js
import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      delete: vi.fn(),
      defaults: {},
      interceptors: { request: { use: vi.fn() }, response: { use: vi.fn() } },
    })),
  },
}))

describe('api service', () => {
  it('exports getTenders as a function', async () => {
    const { getTenders } = await import('./api.js')
    expect(typeof getTenders).toBe('function')
  })

  it('exports getKpisPublic as a function', async () => {
    const { getKpisPublic } = await import('./api.js')
    expect(typeof getKpisPublic).toBe('function')
  })

  it('exports collect as a function', async () => {
    const { collect } = await import('./api.js')
    expect(typeof collect).toBe('function')
  })

  it('exports updateStatus as a function', async () => {
    const { updateStatus } = await import('./api.js')
    expect(typeof updateStatus).toBe('function')
  })
})
```

- [ ] **Step 2: Vérifier que le test échoue**

```powershell
cd frontend && npx vitest run src/services/api.test.js
```

Attendu : FAIL — `Cannot find module './api.js'`

- [ ] **Step 3: Créer le service API**

Créer `frontend/src/services/api.js` :

```js
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// ── Tenders ───────────────────────────────────────────────────────────────────

export const getTenders = (params) =>
  api.get('/tenders', { params }).then((r) => r.data)

export const getTender = (id) =>
  api.get(`/tenders/${id}`).then((r) => r.data)

export const updateStatus = (id, status) =>
  api.post(`/tenders/${id}/status`, { status }).then((r) => r.data)

export const updateNotes = (id, notes) =>
  api.post(`/tenders/${id}/notes`, { notes }).then((r) => r.data)

export const updateTags = (id, tags) =>
  api.post(`/tenders/${id}/tags`, { tags }).then((r) => r.data)

export const updateAmount = (id, amount) =>
  api.post(`/tenders/${id}/amount`, { amount }).then((r) => r.data)

export const updateSaved = (id, is_saved) =>
  api.post(`/tenders/${id}/saved`, { is_saved }).then((r) => r.data)

export const deleteTender = (id) =>
  api.delete(`/tenders/${id}`).then((r) => r.data)

export const analyzeTender = (id) =>
  api.post(`/tenders/${id}/analyze`).then((r) => r.data)

// ── KPIs ──────────────────────────────────────────────────────────────────────

export const getKpisPublic = () =>
  api.get('/kpis/public').then((r) => r.data)

export const getKpisCa = () =>
  api.get('/kpis/ca').then((r) => r.data)

export const getKpisPriv = () =>
  api.get('/kpis/priv').then((r) => r.data)

// ── Pipeline & Urgences ───────────────────────────────────────────────────────

export const getPipeline = () =>
  api.get('/pipeline').then((r) => r.data)

export const getUrgences = (params) =>
  api.get('/urgences', { params }).then((r) => r.data)

// ── Collecte & analyse ────────────────────────────────────────────────────────

export const collect = (source_names = null) =>
  api.post('/collect', { source_names }).then((r) => r.data)

export const analyzePending = () =>
  api.post('/analyze-pending').then((r) => r.data)

export const detectDuplicates = () =>
  api.post('/detect-duplicates').then((r) => r.data)

// ── Scraper runs ──────────────────────────────────────────────────────────────

export const getScraperRuns = (limit = 50) =>
  api.get('/scraper-runs', { params: { limit } }).then((r) => r.data)

// ── Sources ───────────────────────────────────────────────────────────────────

export const getSources = () =>
  api.get('/sources').then((r) => r.data)

// ── Charts ────────────────────────────────────────────────────────────────────

export const getChartData = (max_rows = 5000) =>
  api.get('/chart-data', { params: { max_rows } }).then((r) => r.data)

// ── Admin ─────────────────────────────────────────────────────────────────────

export const resetDb = () =>
  api.post('/admin/reset-db').then((r) => r.data)

export const archiveOld = (days = 30) =>
  api.post(`/admin/archive-old?days=${days}`).then((r) => r.data)

export default api
```

- [ ] **Step 4: Vérifier que les tests passent**

```powershell
npx vitest run src/services/api.test.js
```

Attendu : PASS — 4 tests ✓

- [ ] **Step 5: Commit**

```powershell
cd ..
git add frontend/src/services/api.js frontend/src/services/api.test.js
git commit -m "feat: add API service layer with axios (api.js)"
```

---

## Task 4 : Hooks React Query (hooks/useTenders.js)

**Files:**
- Create: `frontend/src/hooks/useTenders.js`

- [ ] **Step 1: Créer le fichier de hooks**

Créer `frontend/src/hooks/useTenders.js` :

```js
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTenders,
  getTender,
  getKpisPublic,
  getKpisCa,
  getKpisPriv,
  getPipeline,
  getUrgences,
  getScraperRuns,
  getSources,
  getChartData,
  collect,
  analyzePending,
  updateStatus,
  updateSaved,
  updateNotes,
  updateTags,
  updateAmount,
  deleteTender,
  analyzeTender,
} from '../services/api'

export const useTenders = (params) =>
  useQuery({
    queryKey: ['tenders', params],
    queryFn: () => getTenders(params),
    staleTime: 30_000,
  })

export const useTender = (id) =>
  useQuery({
    queryKey: ['tender', id],
    queryFn: () => getTender(id),
    enabled: Boolean(id),
  })

export const useKpisPublic = () =>
  useQuery({ queryKey: ['kpis', 'public'], queryFn: getKpisPublic, staleTime: 30_000 })

export const useKpisCa = () =>
  useQuery({ queryKey: ['kpis', 'ca'], queryFn: getKpisCa, staleTime: 30_000 })

export const useKpisPriv = () =>
  useQuery({ queryKey: ['kpis', 'priv'], queryFn: getKpisPriv, staleTime: 30_000 })

export const usePipeline = () =>
  useQuery({ queryKey: ['pipeline'], queryFn: getPipeline, staleTime: 30_000 })

export const useUrgences = () =>
  useQuery({
    queryKey: ['urgences'],
    queryFn: getUrgences,
    staleTime: 60_000,
    refetchInterval: 120_000,
  })

export const useScraperRuns = () =>
  useQuery({
    queryKey: ['scraper-runs'],
    queryFn: getScraperRuns,
    staleTime: 10_000,
    refetchInterval: 30_000,
  })

export const useSources = () =>
  useQuery({ queryKey: ['sources'], queryFn: getSources, staleTime: 60_000 })

export const useChartData = () =>
  useQuery({ queryKey: ['chart-data'], queryFn: getChartData, staleTime: 120_000 })

// ── Mutations ─────────────────────────────────────────────────────────────────

export const useCollectMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: collect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scraper-runs'] }),
  })
}

export const useUpdateStatus = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }) => updateStatus(id, status),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenders'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
      qc.invalidateQueries({ queryKey: ['pipeline'] })
    },
  })
}

export const useUpdateSaved = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, is_saved }) => updateSaved(id, is_saved),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}

export const useUpdateNotes = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, notes }) => updateNotes(id, notes),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}

export const useUpdateTags = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, tags }) => updateTags(id, tags),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}

export const useUpdateAmount = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, amount }) => updateAmount(id, amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenders'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
    },
  })
}

export const useDeleteTender = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteTender,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}

export const useAnalyzeTender = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: analyzeTender,
    onSuccess: (_, id) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}

export const useAnalyzePending = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: analyzePending,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/src/hooks/useTenders.js
git commit -m "feat: add React Query hooks (useTenders.js)"
```

---

## Task 5 : Pages stub (6 pages)

**Files:**
- Create: `frontend/src/pages/Pipeline.jsx`
- Create: `frontend/src/pages/Analytics.jsx`
- Create: `frontend/src/pages/Direction.jsx`
- Create: `frontend/src/pages/Urgences.jsx`
- Create: `frontend/src/pages/Parametres.jsx`
- Create: `frontend/src/pages/Guide.jsx`

- [ ] **Step 1: Créer les 6 pages stub**

Créer `frontend/src/pages/Pipeline.jsx` :

```jsx
export default function Pipeline() {
  return <div className="p-4 text-gray-700">Page Pipeline — à implémenter</div>
}
```

Créer `frontend/src/pages/Analytics.jsx` :

```jsx
export default function Analytics() {
  return <div className="p-4 text-gray-700">Page Analytics — à implémenter</div>
}
```

Créer `frontend/src/pages/Direction.jsx` :

```jsx
export default function Direction() {
  return <div className="p-4 text-gray-700">Page Direction — à implémenter</div>
}
```

Créer `frontend/src/pages/Urgences.jsx` :

```jsx
export default function Urgences() {
  return <div className="p-4 text-gray-700">Page Urgences — à implémenter</div>
}
```

Créer `frontend/src/pages/Parametres.jsx` :

```jsx
export default function Parametres() {
  return <div className="p-4 text-gray-700">Page Paramètres — à implémenter</div>
}
```

Créer `frontend/src/pages/Guide.jsx` :

```jsx
export default function Guide() {
  return <div className="p-4 text-gray-700">Page Guide — à implémenter</div>
}
```

- [ ] **Step 2: Commit**

```powershell
git add frontend/src/pages/
git commit -m "feat: add 6 stub pages (Pipeline, Analytics, Direction, Urgences, Parametres, Guide)"
```

---

## Task 6 : Composant Sidebar

**Files:**
- Create: `frontend/src/components/Sidebar.jsx`
- Create: `frontend/src/components/Sidebar.test.jsx`

- [ ] **Step 1: Écrire le test Sidebar**

Créer `frontend/src/components/Sidebar.test.jsx` :

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Sidebar from './Sidebar'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('Sidebar', () => {
  it('affiche le logo DEF OI', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('DEF Océan Indien')).toBeInTheDocument()
  })

  it('affiche tous les items de navigation', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText('Pipeline')).toBeInTheDocument()
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Direction')).toBeInTheDocument()
    expect(screen.getByText('Urgences')).toBeInTheDocument()
    expect(screen.getByText('Guide')).toBeInTheDocument()
    expect(screen.getByText('Paramètres')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Vérifier que le test échoue**

```powershell
cd frontend && npx vitest run src/components/Sidebar.test.jsx
```

Attendu : FAIL — `Cannot find module './Sidebar'`

- [ ] **Step 3: Créer le composant Sidebar**

Créer `frontend/src/components/Sidebar.jsx` :

```jsx
import { NavLink } from 'react-router-dom'
import { useUrgences } from '../hooks/useTenders'

const NAV_ITEMS = [
  { to: '/', icon: '📋', label: 'Pipeline', end: true },
  { to: '/analytics', icon: '📊', label: 'Analytics' },
  { to: '/direction', icon: '🎯', label: 'Direction' },
  { to: '/urgences', icon: '🔔', label: 'Urgences', badge: true },
  { to: '/guide', icon: '📖', label: 'Guide' },
]

function NavItem({ to, icon, label, badge, urgenceCount, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 py-2 text-sm transition-colors',
          isActive
            ? 'bg-red-500/15 border-l-[3px] border-red-500 pl-[13px] text-white font-semibold'
            : 'pl-[17px] text-[#5a6e8a] hover:text-white',
        ].join(' ')
      }
    >
      <span className="text-base leading-none">{icon}</span>
      <span>{label}</span>
      {badge && urgenceCount > 0 && (
        <span className="ml-auto mr-3 bg-red-500 text-white text-[10px] font-bold rounded-full px-1.5 py-px">
          {urgenceCount}
        </span>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { data: urgences = [] } = useUrgences()

  return (
    <aside className="w-52 bg-[#16213e] flex flex-col flex-shrink-0 h-screen">
      {/* Logo */}
      <div className="px-4 py-4 border-b border-white/[0.07]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-red-500 rounded-lg flex items-center justify-center text-white font-extrabold text-xs flex-shrink-0">
            OI
          </div>
          <div>
            <p className="text-white text-[10px] font-bold leading-tight">DEF Océan Indien</p>
            <p className="text-[#4a5a72] text-[9px] mt-0.5">Veille Marchés</p>
          </div>
        </div>
      </div>

      {/* Navigation principale */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} urgenceCount={urgences.length} />
        ))}
      </nav>

      {/* Paramètres épinglés en bas */}
      <div className="border-t border-white/[0.07] py-2">
        <NavItem to="/parametres" icon="⚙️" label="Paramètres" />
      </div>
    </aside>
  )
}
```

- [ ] **Step 4: Vérifier que les tests passent**

```powershell
npx vitest run src/components/Sidebar.test.jsx
```

Attendu : PASS — 2 tests ✓

- [ ] **Step 5: Commit**

```powershell
cd ..
git add frontend/src/components/Sidebar.jsx frontend/src/components/Sidebar.test.jsx
git commit -m "feat: add Sidebar component with nav items and urgences badge"
```

---

## Task 7 : Composant Layout

**Files:**
- Create: `frontend/src/components/Layout.jsx`
- Create: `frontend/src/components/Layout.test.jsx`

- [ ] **Step 1: Écrire le test Layout**

Créer `frontend/src/components/Layout.test.jsx` :

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './Layout'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function Wrapper({ children }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

describe('Layout', () => {
  it('affiche la Sidebar et le contenu de la page courante', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<div>Contenu Pipeline</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('DEF Océan Indien')).toBeInTheDocument()
    expect(screen.getByText('Contenu Pipeline')).toBeInTheDocument()
  })

  it('affiche le titre dans la topbar selon la route', () => {
    render(
      <MemoryRouter initialEntries={['/analytics']}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route path="analytics" element={<div>Analytics content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
      { wrapper: Wrapper }
    )
    expect(screen.getByText('Analytics')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Vérifier que le test échoue**

```powershell
cd frontend && npx vitest run src/components/Layout.test.jsx
```

Attendu : FAIL — `Cannot find module './Layout'`

- [ ] **Step 3: Créer le composant Layout**

Créer `frontend/src/components/Layout.jsx` :

```jsx
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

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

  return (
    <div className="flex h-screen overflow-hidden bg-gray-100">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="h-11 bg-white border-b border-gray-200 flex items-center px-5 flex-shrink-0">
          <span className="text-sm font-bold text-gray-900">{title}</span>
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Vérifier que les tests passent**

```powershell
npx vitest run src/components/Layout.test.jsx
```

Attendu : PASS — 2 tests ✓

- [ ] **Step 5: Commit**

```powershell
cd ..
git add frontend/src/components/Layout.jsx frontend/src/components/Layout.test.jsx
git commit -m "feat: add Layout component (sidebar + topbar + Outlet)"
```

---

## Task 8 : Câblage App.jsx et vérification finale

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Réécrire App.jsx avec les routes**

Remplacer `frontend/src/App.jsx` par :

```jsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Pipeline from './pages/Pipeline'
import Analytics from './pages/Analytics'
import Direction from './pages/Direction'
import Urgences from './pages/Urgences'
import Parametres from './pages/Parametres'
import Guide from './pages/Guide'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Pipeline />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="direction" element={<Direction />} />
        <Route path="urgences" element={<Urgences />} />
        <Route path="parametres" element={<Parametres />} />
        <Route path="guide" element={<Guide />} />
      </Route>
    </Routes>
  )
}
```

- [ ] **Step 2: Lancer tous les tests**

```powershell
cd frontend && npx vitest run
```

Attendu : PASS — tous les tests ✓ (api.test.js, Sidebar.test.jsx, Layout.test.jsx)

- [ ] **Step 3: Lancer le dev server et vérifier visuellement**

```powershell
npm run dev
```

Ouvrir `http://localhost:5173` dans le navigateur et vérifier :
- La sidebar #16213e s'affiche à gauche avec le logo "OI" rouge
- Les 6 items de navigation sont présents
- "Paramètres" est épinglé en bas
- Cliquer sur chaque lien change le titre dans la topbar
- L'item actif a la barre rouge sur le côté gauche

Couper avec Ctrl+C.

- [ ] **Step 4: Commit final**

```powershell
cd ..
git add frontend/src/App.jsx
git commit -m "feat: wire up React Router routes in App.jsx — scaffold complete"
```

---

## Récapitulatif des commandes de démarrage

Pour lancer l'environnement de développement complet :

```powershell
# Terminal 1 — Backend FastAPI
cd "commercial et opportunité def OI/backend"
uvicorn main:app --reload

# Terminal 2 — Frontend React
cd "commercial et opportunité def OI/frontend"
npm run dev
```

Frontend disponible sur `http://localhost:5173`, proxifié vers le backend sur `http://localhost:8000`.
