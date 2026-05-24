# Dashboard — KpiGrid + TendersTable Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter la page Dashboard principale avec une grille KPI et un tableau de marchés filtrable, remplaçant le placeholder Pipeline à la route index `/`.

**Architecture:** Dashboard.jsx orchestre l'état des filtres (status, secteur, searchText) et compose deux sous-composants indépendants — KpiGrid (auto-fetch KPIs publics) et TendersTable (fetch marchés avec filtres serveur + filtre texte client). App.jsx est mis à jour pour pointer l'index route vers Dashboard.

**Tech Stack:** React 18, Vite, TailwindCSS v3, @tanstack/react-query v5, Vitest + @testing-library/react, React Router v6.

---

## File Map

| Action | Chemin | Responsabilité |
|--------|--------|----------------|
| Modify | `frontend/src/App.jsx` | Pointer index route → Dashboard |
| Create | `frontend/src/components/KpiGrid.jsx` | 5 cartes KPI colorées |
| Create | `frontend/src/components/KpiGrid.test.jsx` | Tests KpiGrid |
| Create | `frontend/src/components/TendersTable.jsx` | Tableau marchés + filtres |
| Create | `frontend/src/components/TendersTable.test.jsx` | Tests TendersTable |
| Create | `frontend/src/pages/Dashboard.jsx` | Page principale, orchestre filtres |
| Create | `frontend/src/pages/Dashboard.test.jsx` | Tests Dashboard |

---

## Task 1 : Mettre à jour App.jsx pour pointer vers Dashboard

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1 : Remplacer l'import Pipeline par Dashboard**

Ouvrir `frontend/src/App.jsx` et appliquer les modifications suivantes :

```jsx
import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Analytics from './pages/Analytics'
import Direction from './pages/Direction'
import Urgences from './pages/Urgences'
import Parametres from './pages/Parametres'
import Guide from './pages/Guide'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
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

- [ ] **Step 2 : Créer un stub Dashboard.jsx pour que l'app compile**

Créer `frontend/src/pages/Dashboard.jsx` avec le contenu minimal :

```jsx
export default function Dashboard() {
  return <div className="p-4 text-gray-700">Dashboard — en cours d'implémentation</div>
}
```

- [ ] **Step 3 : Vérifier que les tests existants passent toujours**

```bash
cd frontend && npx vitest run
```

Résultat attendu : tous les tests existants (Layout, Sidebar, api) passent — aucun nouveau test introduit ici.

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/App.jsx frontend/src/pages/Dashboard.jsx
git commit -m "feat: wire index route to Dashboard (stub)"
```

---

## Task 2 : KpiGrid — test puis implémentation

**Files:**
- Create: `frontend/src/components/KpiGrid.jsx`
- Create: `frontend/src/components/KpiGrid.test.jsx`

### 2a — Écrire les tests en premier

- [ ] **Step 1 : Créer KpiGrid.test.jsx**

```jsx
// frontend/src/components/KpiGrid.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import KpiGrid from './KpiGrid'

vi.mock('../hooks/useTenders', () => ({
  useKpisPublic: vi.fn(),
}))

import { useKpisPublic } from '../hooks/useTenders'

describe('KpiGrid', () => {
  it('affiche 5 skeletons en état loading', () => {
    useKpisPublic.mockReturnValue({ data: null, isLoading: true, isError: false })
    const { container } = render(<KpiGrid />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(5)
  })

  it("affiche un message d'erreur si isError", () => {
    useKpisPublic.mockReturnValue({ data: null, isLoading: false, isError: true })
    render(<KpiGrid />)
    expect(screen.getByText(/impossible de charger les kpis/i)).toBeInTheDocument()
  })

  it('affiche les 5 compteurs KPI avec les bonnes valeurs', () => {
    useKpisPublic.mockReturnValue({
      data: { total: 42, a_qualifier: 10, en_cours: 5, soumis: 3, gagnes: 2 },
      isLoading: false,
      isError: false,
    })
    render(<KpiGrid />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('affiche les labels des 5 cartes', () => {
    useKpisPublic.mockReturnValue({
      data: { total: 0, a_qualifier: 0, en_cours: 0, soumis: 0, gagnes: 0 },
      isLoading: false,
      isError: false,
    })
    render(<KpiGrid />)
    expect(screen.getByText(/total marchés/i)).toBeInTheDocument()
    expect(screen.getByText(/à qualifier/i)).toBeInTheDocument()
    expect(screen.getByText(/en cours/i)).toBeInTheDocument()
    expect(screen.getByText(/soumis/i)).toBeInTheDocument()
    expect(screen.getByText(/gagnés/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2 : Vérifier que les tests échouent (KpiGrid.jsx n'existe pas encore)**

```bash
cd frontend && npx vitest run src/components/KpiGrid.test.jsx
```

Résultat attendu : FAIL — "Cannot find module './KpiGrid'"

### 2b — Implémenter KpiGrid.jsx

- [ ] **Step 3 : Créer KpiGrid.jsx**

```jsx
// frontend/src/components/KpiGrid.jsx
import { useKpisPublic } from '../hooks/useTenders'

const KPI_CARDS = [
  { key: 'total',       label: 'Total marchés', icon: '📋', colorClass: 'bg-blue-50 border-blue-200 text-blue-700'   },
  { key: 'a_qualifier', label: 'À qualifier',   icon: '🔍', colorClass: 'bg-slate-50 border-slate-200 text-slate-700'  },
  { key: 'en_cours',   label: 'En cours',       icon: '⚙️', colorClass: 'bg-indigo-50 border-indigo-200 text-indigo-700' },
  { key: 'soumis',     label: 'Soumis',         icon: '📤', colorClass: 'bg-amber-50 border-amber-200 text-amber-700'  },
  { key: 'gagnes',     label: 'Gagnés',         icon: '✅', colorClass: 'bg-green-50 border-green-200 text-green-700'  },
]

export default function KpiGrid() {
  const { data, isLoading, isError } = useKpisPublic()

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-20 rounded-lg border bg-gray-100 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="text-red-600 text-sm">Impossible de charger les KPIs.</p>
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {KPI_CARDS.map(({ key, label, icon, colorClass }) => (
        <div key={key} className={`rounded-lg border p-4 flex flex-col gap-1 ${colorClass}`}>
          <span className="text-xs font-medium uppercase tracking-wide opacity-70">
            {icon} {label}
          </span>
          <span className="text-3xl font-bold">{data?.[key] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd frontend && npx vitest run src/components/KpiGrid.test.jsx
```

Résultat attendu : 4 tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/KpiGrid.jsx frontend/src/components/KpiGrid.test.jsx
git commit -m "feat: add KpiGrid component with loading/error/data states"
```

---

## Task 3 : TendersTable — test puis implémentation

**Files:**
- Create: `frontend/src/components/TendersTable.jsx`
- Create: `frontend/src/components/TendersTable.test.jsx`

### 3a — Écrire les tests en premier

- [ ] **Step 1 : Créer TendersTable.test.jsx**

```jsx
// frontend/src/components/TendersTable.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import TendersTable from './TendersTable'

vi.mock('../hooks/useTenders', () => ({
  useTenders: vi.fn(),
}))

import { useTenders } from '../hooks/useTenders'

const MOCK_TENDERS = [
  {
    id: '1',
    title: 'Marché SSI Réunion',
    domaine: 'SSI / Détection incendie',
    territoire: 'La Réunion',
    deadline: '2026-06-30T00:00:00',
    relevance_score: 75,
    gonogo: 'GO',
    status: 'En cours',
    source: 'DECP',
  },
  {
    id: '2',
    title: 'Vidéosurveillance Mayotte',
    domaine: 'Vidéosurveillance / CCTV',
    territoire: 'Mayotte',
    deadline: null,
    relevance_score: 45,
    gonogo: 'Étudier',
    status: 'À qualifier',
    source: 'AFD',
  },
  {
    id: '3',
    title: 'Maintenance alarme',
    domaine: 'Autre',
    territoire: 'Non précisé',
    deadline: '2026-07-15T00:00:00',
    relevance_score: 20,
    gonogo: 'Passer',
    status: 'À qualifier',
    source: 'DECP',
  },
]

const DEFAULT_PROPS = {
  status: 'Tous',
  secteur: 'Public',
  searchText: '',
  onStatusChange: vi.fn(),
  onSecteurChange: vi.fn(),
  onSearchChange: vi.fn(),
}

describe('TendersTable', () => {
  it('affiche le filtre statut avec aria-label', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('combobox', { name: /statut/i })).toBeInTheDocument()
  })

  it('affiche le filtre secteur avec aria-label', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('combobox', { name: /secteur/i })).toBeInTheDocument()
  })

  it('affiche le champ de recherche textuelle', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByRole('textbox', { name: /rechercher/i })).toBeInTheDocument()
  })

  it('affiche un message si aucun marché trouvé', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/aucun marché trouvé/i)).toBeInTheDocument()
  })

  it('affiche un message erreur si isError', () => {
    useTenders.mockReturnValue({ data: [], isLoading: false, isError: true })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/impossible de charger les marchés/i)).toBeInTheDocument()
  })

  it('affiche les lignes du tableau avec les titres', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText('Marché SSI Réunion')).toBeInTheDocument()
    expect(screen.getByText('Vidéosurveillance Mayotte')).toBeInTheDocument()
    expect(screen.getByText('Maintenance alarme')).toBeInTheDocument()
  })

  it('affiche le badge 🟢 GO', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/🟢 GO/)).toBeInTheDocument()
  })

  it('affiche le badge 🟡 Étudier', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/🟡 Étudier/)).toBeInTheDocument()
  })

  it('affiche le badge 🔴 Passer', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText(/🔴 Passer/)).toBeInTheDocument()
  })

  it('filtre par searchText sur le titre', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} searchText="SSI" />)
    expect(screen.getByText('Marché SSI Réunion')).toBeInTheDocument()
    expect(screen.queryByText('Vidéosurveillance Mayotte')).not.toBeInTheDocument()
  })

  it('filtre par searchText sur le domaine', () => {
    useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} searchText="CCTV" />)
    expect(screen.getByText('Vidéosurveillance Mayotte')).toBeInTheDocument()
    expect(screen.queryByText('Marché SSI Réunion')).not.toBeInTheDocument()
  })

  it('affiche — pour une deadline nulle', () => {
    useTenders.mockReturnValue({ data: [MOCK_TENDERS[1]], isLoading: false, isError: false })
    render(<TendersTable {...DEFAULT_PROPS} />)
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('affiche 5 skeletons en état loading', () => {
    useTenders.mockReturnValue({ data: [], isLoading: true, isError: false })
    const { container } = render(<TendersTable {...DEFAULT_PROPS} />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(5)
  })
})
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd frontend && npx vitest run src/components/TendersTable.test.jsx
```

Résultat attendu : FAIL — "Cannot find module './TendersTable'"

### 3b — Implémenter TendersTable.jsx

- [ ] **Step 3 : Créer TendersTable.jsx**

```jsx
// frontend/src/components/TendersTable.jsx
import { useMemo } from 'react'
import { useTenders } from '../hooks/useTenders'

const STATUTS = ['Tous', 'À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']
const SECTEURS = ['Public', 'Privé', 'International']

function GonogoBadge({ gonogo }) {
  if (gonogo === 'GO')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
        🟢 GO
      </span>
    )
  if (gonogo === 'Étudier')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800">
        🟡 Étudier
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">
      🔴 Passer
    </span>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

export default function TendersTable({
  status,
  secteur,
  searchText,
  onStatusChange,
  onSecteurChange,
  onSearchChange,
}) {
  const { data: tenders = [], isLoading, isError } = useTenders({ status, secteur })

  const filtered = useMemo(() => {
    if (!searchText) return tenders
    const q = searchText.toLowerCase()
    return tenders.filter((t) =>
      `${t.title} ${t.domaine} ${t.territoire}`.toLowerCase().includes(q)
    )
  }, [tenders, searchText])

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Filtres */}
      <div className="flex flex-wrap gap-3 items-center p-4 border-b border-gray-100 bg-gray-50">
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filtrer par statut"
          className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white"
        >
          {STATUTS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          value={secteur}
          onChange={(e) => onSecteurChange(e.target.value)}
          aria-label="Filtrer par secteur"
          className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white"
        >
          {SECTEURS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <input
          type="text"
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Rechercher un marché…"
          aria-label="Rechercher un marché"
          className="text-sm border border-gray-300 rounded px-2 py-1.5 flex-1 min-w-[200px]"
        />
      </div>

      {/* Corps */}
      {isLoading && (
        <div className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <p className="p-4 text-red-600 text-sm">Impossible de charger les marchés.</p>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <p className="p-8 text-center text-gray-400 text-sm">Aucun marché trouvé.</p>
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs uppercase text-gray-500 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium">Titre</th>
                <th className="text-left px-4 py-3 font-medium">Domaine</th>
                <th className="text-left px-4 py-3 font-medium">Territoire</th>
                <th className="text-left px-4 py-3 font-medium">Deadline</th>
                <th className="text-left px-4 py-3 font-medium">Score</th>
                <th className="text-left px-4 py-3 font-medium">GO/NO-GO</th>
                <th className="text-left px-4 py-3 font-medium">Statut</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  className="border-b border-gray-50 hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">
                    {t.title}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.domaine || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{t.territoire || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {formatDate(t.deadline)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-indigo-500 h-1.5 rounded-full"
                          style={{ width: `${Math.min(t.relevance_score, 100)}%` }}
                        />
                      </div>
                      <span className="text-gray-700 tabular-nums">{t.relevance_score}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <GonogoBadge gonogo={t.gonogo} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.status}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{t.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd frontend && npx vitest run src/components/TendersTable.test.jsx
```

Résultat attendu : 12 tests PASS.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/TendersTable.jsx frontend/src/components/TendersTable.test.jsx
git commit -m "feat: add TendersTable with filters and GO/NO-GO badges"
```

---

## Task 4 : Dashboard.jsx — remplacer le stub par l'implémentation finale

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`
- Create: `frontend/src/pages/Dashboard.test.jsx`

### 4a — Écrire les tests en premier

- [ ] **Step 1 : Créer Dashboard.test.jsx**

```jsx
// frontend/src/pages/Dashboard.test.jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import Dashboard from './Dashboard'

vi.mock('../components/KpiGrid', () => ({
  default: () => <div data-testid="kpi-grid">KpiGrid</div>,
}))

vi.mock('../components/TendersTable', () => ({
  default: (props) => (
    <div data-testid="tenders-table">
      <span data-testid="prop-status">{props.status}</span>
      <span data-testid="prop-secteur">{props.secteur}</span>
      <span data-testid="prop-search">{props.searchText}</span>
      <button onClick={() => props.onStatusChange('En cours')}>set-status</button>
      <button onClick={() => props.onSecteurChange('Privé')}>set-secteur</button>
      <button onClick={() => props.onSearchChange('test')}>set-search</button>
    </div>
  ),
}))

describe('Dashboard', () => {
  it('rend KpiGrid et TendersTable', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('kpi-grid')).toBeInTheDocument()
    expect(screen.getByTestId('tenders-table')).toBeInTheDocument()
  })

  it('initialise status à "Tous"', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('prop-status').textContent).toBe('Tous')
  })

  it('initialise secteur à "Public"', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('prop-secteur').textContent).toBe('Public')
  })

  it('initialise searchText à ""', () => {
    render(<Dashboard />)
    expect(screen.getByTestId('prop-search').textContent).toBe('')
  })

  it('met à jour status via onStatusChange', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('set-status'))
    expect(screen.getByTestId('prop-status').textContent).toBe('En cours')
  })

  it('met à jour secteur via onSecteurChange', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('set-secteur'))
    expect(screen.getByTestId('prop-secteur').textContent).toBe('Privé')
  })

  it('met à jour searchText via onSearchChange', () => {
    render(<Dashboard />)
    fireEvent.click(screen.getByText('set-search'))
    expect(screen.getByTestId('prop-search').textContent).toBe('test')
  })
})
```

- [ ] **Step 2 : Vérifier que les tests échouent (stub ne rend pas KpiGrid/TendersTable)**

```bash
cd frontend && npx vitest run src/pages/Dashboard.test.jsx
```

Résultat attendu : FAIL — les testids `kpi-grid` et `tenders-table` sont absents du stub.

### 4b — Implémenter Dashboard.jsx

- [ ] **Step 3 : Remplacer le stub par l'implémentation finale**

```jsx
// frontend/src/pages/Dashboard.jsx
import { useState } from 'react'
import KpiGrid from '../components/KpiGrid'
import TendersTable from '../components/TendersTable'

export default function Dashboard() {
  const [status, setStatus] = useState('Tous')
  const [secteur, setSecteur] = useState('Public')
  const [searchText, setSearchText] = useState('')

  return (
    <div className="p-5 space-y-5">
      <KpiGrid />
      <TendersTable
        status={status}
        secteur={secteur}
        searchText={searchText}
        onStatusChange={setStatus}
        onSecteurChange={setSecteur}
        onSearchChange={setSearchText}
      />
    </div>
  )
}
```

- [ ] **Step 4 : Vérifier que les tests Dashboard passent**

```bash
cd frontend && npx vitest run src/pages/Dashboard.test.jsx
```

Résultat attendu : 7 tests PASS.

- [ ] **Step 5 : Lancer tous les tests pour s'assurer qu'aucune régression**

```bash
cd frontend && npx vitest run
```

Résultat attendu : tous les tests PASS (Layout, Sidebar, api, KpiGrid, TendersTable, Dashboard).

- [ ] **Step 6 : Commit**

```bash
git add frontend/src/pages/Dashboard.jsx frontend/src/pages/Dashboard.test.jsx
git commit -m "feat: implement Dashboard page with KpiGrid and TendersTable"
```

---

## Self-Review

**Couverture spec :**
- ✅ KpiGrid appelant `/api/kpis/public` via `useKpisPublic`
- ✅ TendersTable appelant `/api/tenders` via `useTenders`
- ✅ Badges 🟢 GO / 🟡 Étudier / 🔴 Passer basés sur `gonogo`
- ✅ Filtres Statut, Secteur, Recherche textuelle en haut du tableau
- ✅ App.jsx mis à jour pour pointer l'index vers Dashboard
- ✅ États loading (skeleton) et error gérés dans les deux composants

**Types/signatures cohérentes :**
- `useTenders({ status, secteur })` — cohérent avec `hooks/useTenders.js:24-29`
- `useKpisPublic()` — cohérent avec `hooks/useTenders.js:38-40`
- Champ `gonogo` vient de `_tender_to_dict()` dans `backend/main.py:158`
- Props TendersTable → Dashboard → TendersTable : signature complète et cohérente dans tous les tasks

**Aucun placeholder détecté.**
