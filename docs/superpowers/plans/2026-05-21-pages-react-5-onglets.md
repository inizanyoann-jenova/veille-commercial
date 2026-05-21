# Pages React — 5 Onglets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implémenter les 5 pages vides (Analytics, Direction, Urgences, Paramètres, Guide) avec leurs composants dédiés.

**Architecture:** Approche B — pages minces + composants extraits. Les composants réutilisables (`KanbanColumn`, `UrgenceCard`, `ScraperRunsTable`, `DuplicatePair`) vivent dans `components/`. Les pages orchestrent les hooks et composants existants. TDD strict : test échoue → implémentation → test passe → commit.

**Tech Stack:** React 19, Vite, Tailwind CSS 3, Recharts, @tanstack/react-query, Vitest + @testing-library/react

---

## Fichiers créés / modifiés

| Fichier | Action | Responsabilité |
|---|---|---|
| `frontend/package.json` | Modifier | Ajouter recharts |
| `frontend/src/services/api.js` | Modifier | Ajouter `getDuplicates`, `resolveDuplicate` |
| `frontend/src/hooks/useTenders.js` | Modifier | Ajouter hooks doublons, maintenance |
| `frontend/src/components/KanbanColumn.jsx` | Créer | Colonne kanban réutilisable |
| `frontend/src/components/KanbanColumn.test.jsx` | Créer | Tests KanbanColumn |
| `frontend/src/components/UrgenceCard.jsx` | Créer | Carte urgence colorée |
| `frontend/src/components/UrgenceCard.test.jsx` | Créer | Tests UrgenceCard |
| `frontend/src/components/ScraperRunsTable.jsx` | Créer | Tableau historique runs |
| `frontend/src/components/ScraperRunsTable.test.jsx` | Créer | Tests ScraperRunsTable |
| `frontend/src/components/DuplicatePair.jsx` | Créer | Paire de doublons à résoudre |
| `frontend/src/components/DuplicatePair.test.jsx` | Créer | Tests DuplicatePair |
| `frontend/src/pages/Analytics.jsx` | Modifier | Page graphiques + KPIs |
| `frontend/src/pages/Direction.jsx` | Modifier | Page kanban pipeline |
| `frontend/src/pages/Urgences.jsx` | Modifier | Page cartes urgences |
| `frontend/src/pages/Parametres.jsx` | Modifier | Page admin 4 sections |
| `frontend/src/pages/Guide.jsx` | Modifier | Page aide statique |

---

## Task 1 : Installer recharts + ajouter fonctions API + hooks

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/services/api.js`
- Modify: `frontend/src/hooks/useTenders.js`
- Test: `frontend/src/services/api.test.js`

- [ ] **Step 1.1 : Ajouter le test d'existence des nouvelles fonctions API**

Ouvrir `frontend/src/services/api.test.js` et ajouter à la fin du `describe` existant :

```js
it('exports getDuplicates as a function', async () => {
  const { getDuplicates } = await import('./api.js')
  expect(typeof getDuplicates).toBe('function')
})

it('exports resolveDuplicate as a function', async () => {
  const { resolveDuplicate } = await import('./api.js')
  expect(typeof resolveDuplicate).toBe('function')
})
```

- [ ] **Step 1.2 : Vérifier que les tests échouent**

```bash
cd frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Attendu : 2 tests FAIL avec "getDuplicates is not a function" / "resolveDuplicate is not a function"

- [ ] **Step 1.3 : Ajouter les fonctions dans api.js**

Ouvrir `frontend/src/services/api.js`, ajouter à la fin (avant `export default api`) :

```js
// ── Doublons ──────────────────────────────────────────────────────────────────

export const getDuplicates = () =>
  api.get('/duplicates').then((r) => r.data)

export const resolveDuplicate = (pairId, action, keepId, archiveId) => {
  if (action === 'ignore') {
    return api.post(`/duplicates/${pairId}/resolve`, { action: 'ignore' }).then((r) => r.data)
  }
  return api
    .delete(`/tenders/${archiveId}`)
    .then(() => api.post(`/duplicates/${pairId}/resolve`, { action: 'keep' }))
    .then((r) => r.data)
}
```

> Note : le backend n'a pas de `POST /api/duplicates/{id}/resolve` — il faut l'ajouter. Voir Task 1.4.

- [ ] **Step 1.4 : Ajouter l'endpoint resolve dans le backend**

Ouvrir `backend/main.py`. Après l'endpoint `GET /api/duplicates` (ligne ~552), ajouter :

```python
class ResolveAction(BaseModel):
    action: str  # "keep" | "ignore"


@app.post("/api/duplicates/{pair_id}/resolve", summary="Marquer une paire de doublons comme résolue")
def resolve_duplicate(pair_id: int, body: ResolveAction, db: Session = Depends(get_db)):
    pair = db.query(DuplicateCandidate).filter(DuplicateCandidate.id == pair_id).first()
    if not pair:
        raise HTTPException(404, "Paire introuvable")
    pair.resolved = True
    db.commit()
    return {"id": pair_id, "resolved": True}
```

- [ ] **Step 1.5 : Ajouter les hooks dans useTenders.js**

Ouvrir `frontend/src/hooks/useTenders.js`. Ajouter les imports manquants en haut :

```js
import {
  // ... imports existants ...
  getDuplicates,
  resolveDuplicate,
} from '../services/api'
```

Puis ajouter à la fin du fichier :

```js
export const useDuplicates = () =>
  useQuery({ queryKey: ['duplicates'], queryFn: getDuplicates, staleTime: 30_000 })

export const useDetectDuplicates = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: detectDuplicates,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['duplicates'] }),
  })
}

export const useResolveDuplicate = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ pairId, action, keepId, archiveId }) =>
      resolveDuplicate(pairId, action, keepId, archiveId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['duplicates'] })
      qc.invalidateQueries({ queryKey: ['tenders'] })
    },
  })
}

export const useArchiveOld = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => archiveOld(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['tenders'] }),
  })
}

export const useResetDb = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: resetDb,
    onSuccess: () => {
      qc.invalidateQueries()
    },
  })
}
```

Ajouter les imports manquants dans la ligne d'import de `../services/api` :

```js
import {
  getTenders, getTender, getKpisPublic, getKpisCa, getKpisPriv,
  getPipeline, getUrgences, getScraperRuns, getSources, getChartData,
  collect, analyzePending, updateStatus, updateSaved, updateNotes,
  updateTags, updateAmount, deleteTender, analyzeTender,
  getDuplicates, resolveDuplicate, detectDuplicates, archiveOld, resetDb,
} from '../services/api'
```

- [ ] **Step 1.6 : Installer recharts**

```bash
cd frontend && npm install recharts
```

Attendu : recharts ajouté dans `node_modules/`, `package.json` mis à jour.

- [ ] **Step 1.7 : Vérifier que les tests API passent**

```bash
cd frontend && npm test -- --reporter=verbose 2>&1 | tail -20
```

Attendu : tous les tests PASS (y compris les 2 nouveaux).

- [ ] **Step 1.8 : Commit**

```bash
cd frontend && git add src/services/api.js src/hooks/useTenders.js package.json package-lock.json
cd .. && git add backend/main.py
git commit -m "feat(api): add getDuplicates, resolveDuplicate, resolve endpoint + hooks"
```

---

## Task 2 : Composant KanbanColumn

**Files:**
- Create: `frontend/src/components/KanbanColumn.jsx`
- Create: `frontend/src/components/KanbanColumn.test.jsx`

- [ ] **Step 2.1 : Créer le fichier de test**

Créer `frontend/src/components/KanbanColumn.test.jsx` :

```jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import KanbanColumn from './KanbanColumn'

const ITEMS = [
  { id: 'a1', title: 'Marché SSI La Réunion', score: 80, jours_restants: 5, amount: 100000 },
  { id: 'a2', title: 'Vidéosurveillance Mayotte', score: 72, jours_restants: 20, amount: null },
  { id: 'a3', title: 'CMSI sans deadline', score: 65, jours_restants: null, amount: 50000 },
]

describe('KanbanColumn', () => {
  it('affiche le titre de la colonne', () => {
    render(<KanbanColumn title="✅ GO" items={ITEMS} />)
    expect(screen.getByText('✅ GO')).toBeInTheDocument()
  })

  it('affiche le nombre de cartes', () => {
    render(<KanbanColumn title="✅ GO" items={ITEMS} />)
    expect(screen.getAllByRole('article')).toHaveLength(3)
  })

  it('affiche le titre tronqué à 60 chars', () => {
    const longTitle = 'A'.repeat(70)
    render(<KanbanColumn title="GO" items={[{ id: 'x', title: longTitle, score: 70, jours_restants: 10 }]} />)
    expect(screen.getByText(longTitle.slice(0, 60) + '…')).toBeInTheDocument()
  })

  it('colorie en rouge si jours_restants < 7', () => {
    const { container } = render(<KanbanColumn title="GO" items={[ITEMS[0]]} />)
    expect(container.querySelector('.text-red-600')).toBeInTheDocument()
  })

  it('colorie en orange si jours_restants entre 7 et 30', () => {
    const { container } = render(<KanbanColumn title="GO" items={[ITEMS[1]]} />)
    expect(container.querySelector('.text-orange-500')).toBeInTheDocument()
  })

  it('affiche gris si jours_restants est null', () => {
    const { container } = render(<KanbanColumn title="GO" items={[ITEMS[2]]} />)
    expect(container.querySelector('.text-gray-400')).toBeInTheDocument()
  })

  it('appelle onStatusChange avec le bon statut au clic bouton', () => {
    const onStatusChange = vi.fn()
    render(
      <KanbanColumn
        title="GO"
        items={[ITEMS[0]]}
        actions={[{ label: 'Marquer Soumis', nextStatus: 'Soumis' }]}
        onStatusChange={onStatusChange}
      />
    )
    fireEvent.click(screen.getByRole('button', { name: /marquer soumis/i }))
    expect(onStatusChange).toHaveBeenCalledWith('a1', 'Soumis')
  })

  it('affiche un message vide si items est vide', () => {
    render(<KanbanColumn title="GO" items={[]} />)
    expect(screen.getByText(/aucun marché/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2.2 : Vérifier que les tests échouent**

```bash
cd frontend && npm test -- KanbanColumn --reporter=verbose 2>&1 | tail -20
```

Attendu : FAIL "Cannot find module './KanbanColumn'"

- [ ] **Step 2.3 : Créer KanbanColumn.jsx**

Créer `frontend/src/components/KanbanColumn.jsx` :

```jsx
function DeadlineBadge({ jours_restants }) {
  if (jours_restants === null || jours_restants === undefined) {
    return <span className="text-xs text-gray-400">Pas de deadline</span>
  }
  const color =
    jours_restants < 7
      ? 'text-red-600'
      : jours_restants <= 30
      ? 'text-orange-500'
      : 'text-gray-500'
  return (
    <span className={`text-xs font-medium ${color}`}>
      J-{jours_restants}
    </span>
  )
}

export default function KanbanColumn({ title, items = [], actions = [], onStatusChange }) {
  return (
    <div className="flex flex-col gap-2 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-semibold text-gray-700">{title}</span>
        <span className="bg-gray-200 text-gray-600 text-xs font-bold rounded-full px-2 py-px">
          {items.length}
        </span>
      </div>

      {items.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-6">Aucun marché</p>
      )}

      {items.map((item) => (
        <article
          key={item.id}
          className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col gap-2 shadow-sm"
        >
          <p className="text-sm font-medium text-gray-800 leading-snug">
            {item.title.length > 60 ? item.title.slice(0, 60) + '…' : item.title}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs bg-indigo-100 text-indigo-700 font-semibold rounded px-1.5 py-0.5">
              {item.score}
            </span>
            <DeadlineBadge jours_restants={item.jours_restants} />
          </div>
          {actions.length > 0 && (
            <div className="flex gap-1 flex-wrap mt-1">
              {actions.map(({ label, nextStatus }) => (
                <button
                  key={nextStatus}
                  onClick={() => onStatusChange?.(item.id, nextStatus)}
                  className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 transition-colors"
                >
                  {label}
                </button>
              ))}
            </div>
          )}
        </article>
      ))}
    </div>
  )
}
```

- [ ] **Step 2.4 : Vérifier que les tests passent**

```bash
cd frontend && npm test -- KanbanColumn --reporter=verbose 2>&1 | tail -20
```

Attendu : 8 tests PASS

- [ ] **Step 2.5 : Commit**

```bash
cd frontend && git add src/components/KanbanColumn.jsx src/components/KanbanColumn.test.jsx
git commit -m "feat(components): add KanbanColumn with deadline coloring and action buttons"
```

---

## Task 3 : Composant UrgenceCard

**Files:**
- Create: `frontend/src/components/UrgenceCard.jsx`
- Create: `frontend/src/components/UrgenceCard.test.jsx`

- [ ] **Step 3.1 : Créer le fichier de test**

Créer `frontend/src/components/UrgenceCard.test.jsx` :

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UrgenceCard from './UrgenceCard'

describe('UrgenceCard', () => {
  it('affiche le titre', () => {
    render(<UrgenceCard title="SSI Réunion" jours_restants={5} score={80} source="DECP" />)
    expect(screen.getByText('SSI Réunion')).toBeInTheDocument()
  })

  it('affiche J-5', () => {
    render(<UrgenceCard title="Test" jours_restants={5} score={80} source="DECP" />)
    expect(screen.getByText('J-5')).toBeInTheDocument()
  })

  it('affiche badge rouge si jours_restants < 7', () => {
    const { container } = render(<UrgenceCard title="Test" jours_restants={3} score={80} source="DECP" />)
    expect(container.querySelector('.bg-red-100')).toBeInTheDocument()
  })

  it('affiche badge orange si jours_restants entre 7 et 15', () => {
    const { container } = render(<UrgenceCard title="Test" jours_restants={10} score={80} source="DECP" />)
    expect(container.querySelector('.bg-orange-100')).toBeInTheDocument()
  })

  it('affiche badge vert si jours_restants entre 16 et 30', () => {
    const { container } = render(<UrgenceCard title="Test" jours_restants={20} score={80} source="DECP" />)
    expect(container.querySelector('.bg-green-100')).toBeInTheDocument()
  })

  it('affiche le score et la source', () => {
    render(<UrgenceCard title="Test" jours_restants={10} score={78} source="BOAMP" />)
    expect(screen.getByText('78')).toBeInTheDocument()
    expect(screen.getByText('BOAMP')).toBeInTheDocument()
  })
})
```

- [ ] **Step 3.2 : Vérifier que les tests échouent**

```bash
cd frontend && npm test -- UrgenceCard --reporter=verbose 2>&1 | tail -15
```

Attendu : FAIL "Cannot find module './UrgenceCard'"

- [ ] **Step 3.3 : Créer UrgenceCard.jsx**

Créer `frontend/src/components/UrgenceCard.jsx` :

```jsx
function urgenceStyle(jours) {
  if (jours < 7) return { bg: 'bg-red-100 border-red-300', badge: 'bg-red-100 text-red-700', emoji: '🔴' }
  if (jours <= 15) return { bg: 'bg-orange-50 border-orange-300', badge: 'bg-orange-100 text-orange-700', emoji: '🟡' }
  return { bg: 'bg-green-50 border-green-300', badge: 'bg-green-100 text-green-700', emoji: '🟢' }
}

export default function UrgenceCard({ title, jours_restants, score, source }) {
  const style = urgenceStyle(jours_restants)
  return (
    <div className={`rounded-lg border p-4 flex flex-col gap-3 ${style.bg}`}>
      <div className="flex items-start justify-between gap-2">
        <span className={`text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 ${style.badge}`}>
          {style.emoji} J-{jours_restants}
        </span>
        <span className="text-xs bg-indigo-100 text-indigo-700 font-semibold rounded px-1.5 py-0.5">
          {score}
        </span>
      </div>
      <p className="text-sm font-semibold text-gray-800 line-clamp-2">{title}</p>
      <p className="text-xs text-gray-500">{source}</p>
    </div>
  )
}
```

- [ ] **Step 3.4 : Vérifier que les tests passent**

```bash
cd frontend && npm test -- UrgenceCard --reporter=verbose 2>&1 | tail -15
```

Attendu : 6 tests PASS

- [ ] **Step 3.5 : Commit**

```bash
cd frontend && git add src/components/UrgenceCard.jsx src/components/UrgenceCard.test.jsx
git commit -m "feat(components): add UrgenceCard with color-coded urgency levels"
```

---

## Task 4 : Composant ScraperRunsTable

**Files:**
- Create: `frontend/src/components/ScraperRunsTable.jsx`
- Create: `frontend/src/components/ScraperRunsTable.test.jsx`

- [ ] **Step 4.1 : Créer le fichier de test**

Créer `frontend/src/components/ScraperRunsTable.test.jsx` :

```jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScraperRunsTable from './ScraperRunsTable'

vi.mock('../hooks/useTenders', () => ({
  useScraperRuns: vi.fn(),
}))
import { useScraperRuns } from '../hooks/useTenders'

const MOCK_RUNS = [
  { id: 1, source_name: 'BOAMP', started_at: '2026-05-21T10:00:00', finished_at: '2026-05-21T10:01:00', nb_found: 12, nb_new: 3, status: 'ok', error: null },
  { id: 2, source_name: 'DECP', started_at: '2026-05-21T10:01:00', finished_at: null, nb_found: null, nb_new: null, status: 'error', error: 'Timeout' },
]

describe('ScraperRunsTable', () => {
  it('affiche un message vide si aucun run', () => {
    useScraperRuns.mockReturnValue({ data: [], isLoading: false })
    render(<ScraperRunsTable />)
    expect(screen.getByText(/aucun historique/i)).toBeInTheDocument()
  })

  it('affiche le nom de la source', () => {
    useScraperRuns.mockReturnValue({ data: MOCK_RUNS, isLoading: false })
    render(<ScraperRunsTable />)
    expect(screen.getByText('BOAMP')).toBeInTheDocument()
    expect(screen.getByText('DECP')).toBeInTheDocument()
  })

  it('affiche le statut ok en vert', () => {
    useScraperRuns.mockReturnValue({ data: [MOCK_RUNS[0]], isLoading: false })
    const { container } = render(<ScraperRunsTable />)
    expect(container.querySelector('.text-green-700')).toBeInTheDocument()
  })

  it('affiche le statut error en rouge', () => {
    useScraperRuns.mockReturnValue({ data: [MOCK_RUNS[1]], isLoading: false })
    const { container } = render(<ScraperRunsTable />)
    expect(container.querySelector('.text-red-700')).toBeInTheDocument()
  })

  it('affiche les skeletons en chargement', () => {
    useScraperRuns.mockReturnValue({ data: [], isLoading: true })
    const { container } = render(<ScraperRunsTable />)
    expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0)
  })
})
```

- [ ] **Step 4.2 : Vérifier que les tests échouent**

```bash
cd frontend && npm test -- ScraperRunsTable --reporter=verbose 2>&1 | tail -15
```

Attendu : FAIL "Cannot find module './ScraperRunsTable'"

- [ ] **Step 4.3 : Créer ScraperRunsTable.jsx**

Créer `frontend/src/components/ScraperRunsTable.jsx` :

```jsx
import { useScraperRuns } from '../hooks/useTenders'

function StatusBadge({ status }) {
  if (status === 'ok')
    return <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">✓ ok</span>
  if (status === 'error')
    return <span className="text-xs font-semibold text-red-700 bg-red-100 px-2 py-0.5 rounded-full">✗ erreur</span>
  return <span className="text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full animate-pulse">⟳ en cours</span>
}

function formatDuration(started, finished) {
  if (!started || !finished) return '—'
  const s = Math.round((new Date(finished) - new Date(started)) / 1000)
  return s < 60 ? `${s}s` : `${Math.round(s / 60)}m`
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

export default function ScraperRunsTable() {
  const { data: runs = [], isLoading } = useScraperRuns()

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (runs.length === 0) {
    return <p className="text-sm text-gray-400">Aucun historique disponible.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-gray-500 border-b border-gray-200">
            <th className="text-left py-2 pr-4 font-medium">Source</th>
            <th className="text-left py-2 pr-4 font-medium">Heure</th>
            <th className="text-left py-2 pr-4 font-medium">Durée</th>
            <th className="text-left py-2 pr-4 font-medium">Trouvés</th>
            <th className="text-left py-2 pr-4 font-medium">Nouveaux</th>
            <th className="text-left py-2 font-medium">Statut</th>
          </tr>
        </thead>
        <tbody>
          {runs.slice(0, 20).map((r) => (
            <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 pr-4 font-medium text-gray-700">{r.source_name}</td>
              <td className="py-2 pr-4 text-gray-500">{formatTime(r.started_at)}</td>
              <td className="py-2 pr-4 text-gray-500">{formatDuration(r.started_at, r.finished_at)}</td>
              <td className="py-2 pr-4 text-gray-600">{r.nb_found ?? '—'}</td>
              <td className="py-2 pr-4 text-gray-600">{r.nb_new ?? '—'}</td>
              <td className="py-2">
                <StatusBadge status={r.status} />
                {r.error && <span className="ml-2 text-xs text-red-500">{r.error}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

- [ ] **Step 4.4 : Vérifier que les tests passent**

```bash
cd frontend && npm test -- ScraperRunsTable --reporter=verbose 2>&1 | tail -15
```

Attendu : 5 tests PASS

- [ ] **Step 4.5 : Commit**

```bash
cd frontend && git add src/components/ScraperRunsTable.jsx src/components/ScraperRunsTable.test.jsx
git commit -m "feat(components): add ScraperRunsTable with status coloring and duration"
```

---

## Task 5 : Composant DuplicatePair

**Files:**
- Create: `frontend/src/components/DuplicatePair.jsx`
- Create: `frontend/src/components/DuplicatePair.test.jsx`

- [ ] **Step 5.1 : Créer le fichier de test**

Créer `frontend/src/components/DuplicatePair.test.jsx` :

```jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import DuplicatePair from './DuplicatePair'

const PAIR = {
  id: 1,
  similarity_score: 0.92,
  tender_a: { id: 'a1', title: 'SSI Réunion A', relevance_score: 80, source: 'BOAMP', deadline: '2026-06-30T00:00:00' },
  tender_b: { id: 'b1', title: 'SSI Réunion B', relevance_score: 65, source: 'DECP', deadline: '2026-06-30T00:00:00' },
}

describe('DuplicatePair', () => {
  it('affiche les titres des deux tenders', () => {
    render(<DuplicatePair pair={PAIR} onResolve={vi.fn()} />)
    expect(screen.getByText('SSI Réunion A')).toBeInTheDocument()
    expect(screen.getByText('SSI Réunion B')).toBeInTheDocument()
  })

  it('affiche le score de similarité', () => {
    render(<DuplicatePair pair={PAIR} onResolve={vi.fn()} />)
    expect(screen.getByText(/92%/)).toBeInTheDocument()
  })

  it('appelle onResolve avec keepId=a1 archiveId=b1 au clic Garder A', () => {
    const onResolve = vi.fn()
    render(<DuplicatePair pair={PAIR} onResolve={onResolve} />)
    fireEvent.click(screen.getByRole('button', { name: /garder a/i }))
    expect(onResolve).toHaveBeenCalledWith({ pairId: 1, action: 'keep', keepId: 'a1', archiveId: 'b1' })
  })

  it('appelle onResolve avec keepId=b1 archiveId=a1 au clic Garder B', () => {
    const onResolve = vi.fn()
    render(<DuplicatePair pair={PAIR} onResolve={onResolve} />)
    fireEvent.click(screen.getByRole('button', { name: /garder b/i }))
    expect(onResolve).toHaveBeenCalledWith({ pairId: 1, action: 'keep', keepId: 'b1', archiveId: 'a1' })
  })

  it('appelle onResolve avec action=ignore au clic Ignorer', () => {
    const onResolve = vi.fn()
    render(<DuplicatePair pair={PAIR} onResolve={onResolve} />)
    fireEvent.click(screen.getByRole('button', { name: /ignorer/i }))
    expect(onResolve).toHaveBeenCalledWith({ pairId: 1, action: 'ignore', keepId: null, archiveId: null })
  })

  it('met en évidence tender_a (score plus élevé)', () => {
    const { container } = render(<DuplicatePair pair={PAIR} onResolve={vi.fn()} />)
    expect(container.querySelector('.ring-2')).toBeInTheDocument()
  })
})
```

- [ ] **Step 5.2 : Vérifier que les tests échouent**

```bash
cd frontend && npm test -- DuplicatePair --reporter=verbose 2>&1 | tail -15
```

Attendu : FAIL "Cannot find module './DuplicatePair'"

- [ ] **Step 5.3 : Créer DuplicatePair.jsx**

Créer `frontend/src/components/DuplicatePair.jsx` :

```jsx
function TenderCard({ tender, highlighted }) {
  return (
    <div className={`flex-1 rounded-lg border p-3 ${highlighted ? 'ring-2 ring-indigo-400 bg-indigo-50' : 'bg-gray-50'}`}>
      {highlighted && (
        <span className="text-xs text-indigo-600 font-semibold mb-1 block">Recommandé ✓</span>
      )}
      <p className="text-sm font-semibold text-gray-800 mb-2">{tender.title}</p>
      <div className="flex gap-3 text-xs text-gray-500 flex-wrap">
        <span>Score : <strong>{tender.relevance_score}</strong></span>
        <span>Source : {tender.source}</span>
        {tender.deadline && (
          <span>Deadline : {new Date(tender.deadline).toLocaleDateString('fr-FR')}</span>
        )}
      </div>
    </div>
  )
}

export default function DuplicatePair({ pair, onResolve }) {
  const aIsHigher = pair.tender_a.relevance_score >= pair.tender_b.relevance_score

  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Similarité :</span>
        <span className="text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
          {Math.round(pair.similarity_score * 100)}%
        </span>
      </div>

      <div className="flex gap-3">
        <TenderCard tender={pair.tender_a} highlighted={aIsHigher} />
        <TenderCard tender={pair.tender_b} highlighted={!aIsHigher} />
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', keepId: pair.tender_a.id, archiveId: pair.tender_b.id })}
          className="text-xs px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 transition-colors"
        >
          Garder A — archiver B
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', keepId: pair.tender_b.id, archiveId: pair.tender_a.id })}
          className="text-xs px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 transition-colors"
        >
          Garder B — archiver A
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'ignore', keepId: null, archiveId: null })}
          className="text-xs px-3 py-1.5 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors"
        >
          Ignorer
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5.4 : Vérifier que les tests passent**

```bash
cd frontend && npm test -- DuplicatePair --reporter=verbose 2>&1 | tail -15
```

Attendu : 6 tests PASS

- [ ] **Step 5.5 : Commit**

```bash
cd frontend && git add src/components/DuplicatePair.jsx src/components/DuplicatePair.test.jsx
git commit -m "feat(components): add DuplicatePair with keep/archive/ignore actions"
```

---

## Task 6 : Page Urgences

**Files:**
- Modify: `frontend/src/pages/Urgences.jsx`

- [ ] **Step 6.1 : Écrire Urgences.jsx**

Remplacer le contenu de `frontend/src/pages/Urgences.jsx` :

```jsx
import UrgenceCard from '../components/UrgenceCard'
import { useUrgences } from '../hooks/useTenders'

export default function Urgences() {
  const { data: urgences = [], isLoading, isError } = useUrgences()

  if (isLoading) {
    return (
      <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="p-5 text-red-600 text-sm">Impossible de charger les urgences.</p>
  }

  return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-gray-700">Marchés à traiter en urgence</h2>
        {urgences.length > 0 && (
          <span className="bg-red-500 text-white text-xs font-bold rounded-full px-2 py-px">
            {urgences.length}
          </span>
        )}
      </div>

      {urgences.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-3xl mb-2">✅</p>
          <p className="text-sm">Aucun marché urgent pour le moment.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {urgences.map((u) => (
            <UrgenceCard
              key={u.id}
              title={u.title}
              jours_restants={u.jours_restants}
              score={u.relevance_score}
              source={u.source}
            />
          ))}
        </div>
      )}
    </div>
  )
}
```

> Note : l'endpoint `/api/urgences` retourne les champs `{ id, title, jours_restants, relevance_score, source, deadline }`. Vérifier dans `database.py` → `load_urgences()` que ces champs sont bien présents. Si `jours_restants` n'est pas retourné, le calculer côté frontend : `Math.ceil((new Date(deadline) - new Date()) / 86400000)`.

- [ ] **Step 6.2 : Tester visuellement dans le navigateur**

Ouvrir `http://localhost:5173/urgences`. Vérifier :
- Skeleton pendant chargement
- Message vert si base vide
- Cartes colorées si des urgences existent

- [ ] **Step 6.3 : Commit**

```bash
cd frontend && git add src/pages/Urgences.jsx
git commit -m "feat(pages): implement Urgences page with color-coded urgency cards"
```

---

## Task 7 : Page Direction (Kanban)

**Files:**
- Modify: `frontend/src/pages/Direction.jsx`

- [ ] **Step 7.1 : Vérifier le format retourné par /api/pipeline**

```bash
curl http://localhost:8000/api/pipeline 2>&1 | python -m json.tool | head -40
```

Attendu : objet JSON avec clés `"À qualifier"`, `"En cours"`, `"Soumis"`, `"Gagné"`, `"Perdu"`, chacune contenant un tableau de `{ id, title, amount, deadline, score }`.

- [ ] **Step 7.2 : Écrire Direction.jsx**

Remplacer le contenu de `frontend/src/pages/Direction.jsx` :

```jsx
import { useQueryClient } from '@tanstack/react-query'
import KanbanColumn from '../components/KanbanColumn'
import { usePipeline, useUpdateStatus } from '../hooks/useTenders'

const GO_SCORE = 65

function enrichWithJours(items) {
  return (items || []).map((item) => ({
    ...item,
    jours_restants: item.deadline
      ? Math.ceil((new Date(item.deadline) - new Date()) / 86400000)
      : null,
  }))
}

export default function Direction() {
  const { data: pipeline = {}, isLoading, isError } = usePipeline()
  const { mutate: changeStatus } = useUpdateStatus()
  const qc = useQueryClient()

  const handleStatusChange = (id, status) => {
    changeStatus(
      { id, status },
      { onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline'] }) }
    )
  }

  if (isLoading) {
    return (
      <div className="p-5 grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="h-6 w-24 bg-gray-200 rounded animate-pulse" />
            {Array.from({ length: 3 }).map((_, j) => (
              <div key={j} className="h-24 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="p-5 text-red-600 text-sm">Impossible de charger le pipeline.</p>
  }

  const goItems = enrichWithJours(
    [
      ...(pipeline['À qualifier'] || []),
      ...(pipeline['En cours'] || []),
    ].filter((t) => t.score >= GO_SCORE)
  )

  const soumisItems = enrichWithJours(pipeline['Soumis'] || [])

  const resultatsItems = enrichWithJours([
    ...(pipeline['Gagné'] || []).map((t) => ({ ...t, _sub: '🏆 Gagné' })),
    ...(pipeline['Perdu'] || []).map((t) => ({ ...t, _sub: '❌ Perdu' })),
  ])

  return (
    <div className="p-5 space-y-4">
      <p className="text-xs text-gray-500">Marchés publics — score ≥ {GO_SCORE}</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
        <KanbanColumn
          title="✅ GO"
          items={goItems}
          actions={[{ label: 'Marquer Soumis', nextStatus: 'Soumis' }]}
          onStatusChange={handleStatusChange}
        />
        <KanbanColumn
          title="📤 Soumis"
          items={soumisItems}
          actions={[
            { label: 'Gagné 🏆', nextStatus: 'Gagné' },
            { label: 'Perdu', nextStatus: 'Perdu' },
          ]}
          onStatusChange={handleStatusChange}
        />
        <KanbanColumn
          title="🏆 Résultats"
          items={resultatsItems}
          actions={[]}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 7.3 : Tester visuellement dans le navigateur**

Ouvrir `http://localhost:5173/direction`. Vérifier :
- 3 colonnes visibles avec leurs titres
- Cartes avec score, deadline colorée
- Boutons de transition visibles dans GO et Soumis

- [ ] **Step 7.4 : Commit**

```bash
cd frontend && git add src/pages/Direction.jsx
git commit -m "feat(pages): implement Direction kanban with status transition buttons"
```

---

## Task 8 : Page Paramètres

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx`

- [ ] **Step 8.1 : Écrire Parametres.jsx**

Remplacer le contenu de `frontend/src/pages/Parametres.jsx` :

```jsx
import { useState } from 'react'
import ScraperRunsTable from '../components/ScraperRunsTable'
import DuplicatePair from '../components/DuplicatePair'
import {
  useSources,
  useCollectMutation,
  useAnalyzePending,
  useDuplicates,
  useDetectDuplicates,
  useResolveDuplicate,
  useArchiveOld,
  useResetDb,
} from '../hooks/useTenders'

function SectionTitle({ children }) {
  return (
    <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide border-b border-gray-200 pb-2 mb-4">
      {children}
    </h2>
  )
}

function CollectSection() {
  const { data: sources = [] } = useSources()
  const { mutate: collect, isPending, data: collectResult } = useCollectMutation()
  const enabled = sources.filter((s) => s.enabled && !s.is_manual)
  const [selected, setSelected] = useState(null) // null = toutes

  const toggle = (name) => {
    setSelected((prev) => {
      if (prev === null) {
        const all = enabled.map((s) => s.name).filter((n) => n !== name)
        return all.length === 0 ? null : all
      }
      if (prev.includes(name)) {
        const next = prev.filter((n) => n !== name)
        return next.length === 0 ? null : next
      }
      const next = [...prev, name]
      return next.length === enabled.length ? null : next
    })
  }

  const isChecked = (name) => selected === null || selected.includes(name)

  return (
    <div className="space-y-4">
      <SectionTitle>🔄 Collecte des sources</SectionTitle>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        {enabled.map((s) => (
          <label key={s.name} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={isChecked(s.name)}
              onChange={() => toggle(s.name)}
              className="rounded"
            />
            <span className="text-gray-700">{s.name}</span>
          </label>
        ))}
      </div>

      <button
        onClick={() => collect(selected)}
        disabled={isPending}
        className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {isPending ? 'Collecte en cours…' : 'Lancer la collecte'}
      </button>

      {collectResult && Array.isArray(collectResult) && (
        <div className="space-y-1 mt-2">
          {collectResult.map((r) => (
            <div key={r.source} className="flex items-center gap-3 text-sm">
              <span className={r.status === 'ok' ? 'text-green-600' : 'text-red-600'}>
                {r.status === 'ok' ? '✓' : '✗'}
              </span>
              <span className="font-medium w-32 truncate">{r.source}</span>
              {r.status === 'ok' && (
                <span className="text-gray-500">+{r.nb_new} nouveaux</span>
              )}
              {r.status === 'error' && (
                <span className="text-red-500 text-xs">{r.error}</span>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="mt-4">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-2">Historique des runs</p>
        <ScraperRunsTable />
      </div>
    </div>
  )
}

function AnalyseSection() {
  const { mutate: analyze, isPending, data } = useAnalyzePending()

  return (
    <div className="space-y-4">
      <SectionTitle>🤖 Analyse LLM</SectionTitle>
      <p className="text-sm text-gray-600">
        Lance l'analyse IA sur les marchés qui n'ont pas encore été analysés.
      </p>
      <button
        onClick={() => analyze()}
        disabled={isPending}
        className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {isPending ? 'Analyse en cours…' : 'Analyser les marchés en attente'}
      </button>
      {data && (
        <p className="text-sm text-green-700">
          ✓ {data.message ?? 'Analyse lancée en arrière-plan.'}
        </p>
      )}
    </div>
  )
}

function DoublonsSection() {
  const { data: duplicates = [], isLoading } = useDuplicates()
  const { mutate: detect, isPending: detecting, data: detectResult } = useDetectDuplicates()
  const { mutate: resolve } = useResolveDuplicate()

  return (
    <div className="space-y-4">
      <SectionTitle>🔍 Détection des doublons</SectionTitle>
      <div className="flex items-center gap-4">
        <button
          onClick={() => detect()}
          disabled={detecting}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {detecting ? 'Détection en cours…' : 'Détecter les doublons'}
        </button>
        {detectResult !== undefined && (
          <p className="text-sm text-gray-700">
            {detectResult?.new_pairs ?? 0} nouvelle(s) paire(s) détectée(s).
          </p>
        )}
      </div>

      {isLoading && <p className="text-sm text-gray-400">Chargement…</p>}

      {!isLoading && duplicates.length === 0 && (
        <p className="text-sm text-gray-400">Aucun doublon non résolu.</p>
      )}

      <div className="space-y-3">
        {duplicates.map((pair) => (
          <DuplicatePair key={pair.id} pair={pair} onResolve={resolve} />
        ))}
      </div>
    </div>
  )
}

function MaintenanceSection() {
  const { mutate: archive, isPending: archiving, data: archiveResult } = useArchiveOld()
  const { mutate: reset, isPending: resetting } = useResetDb()
  const [showConfirm, setShowConfirm] = useState(false)

  return (
    <div className="space-y-4">
      <SectionTitle>🛠️ Maintenance</SectionTitle>

      <div className="flex flex-wrap gap-3 items-center">
        <button
          onClick={() => archive()}
          disabled={archiving}
          className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded border border-gray-300 hover:bg-gray-200 disabled:opacity-50 transition-colors"
        >
          {archiving ? 'Archivage…' : 'Archiver les marchés > 30 jours'}
        </button>
        {archiveResult && (
          <span className="text-sm text-gray-600">✓ {archiveResult.archived ?? 0} archivé(s)</span>
        )}
      </div>

      <div>
        {!showConfirm ? (
          <button
            onClick={() => setShowConfirm(true)}
            className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded border border-red-300 hover:bg-red-100 transition-colors"
          >
            Réinitialiser la base de données
          </button>
        ) : (
          <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700 font-medium">
              ⚠️ Cette action est irréversible. Confirmer ?
            </p>
            <button
              onClick={() => { reset(); setShowConfirm(false) }}
              disabled={resetting}
              className="px-3 py-1.5 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
            >
              Oui, réinitialiser
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="px-3 py-1.5 bg-white text-gray-700 text-xs rounded border border-gray-300 hover:bg-gray-100"
            >
              Annuler
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Parametres() {
  return (
    <div className="p-5 space-y-10 max-w-4xl">
      <CollectSection />
      <AnalyseSection />
      <DoublonsSection />
      <MaintenanceSection />
    </div>
  )
}
```

- [ ] **Step 8.2 : Tester visuellement dans le navigateur**

Ouvrir `http://localhost:5173/parametres`. Vérifier :
- Section Collecte : checkboxes des sources, bouton "Lancer la collecte"
- Section Analyse LLM : bouton visible
- Section Doublons : bouton "Détecter", message "Aucun doublon"
- Section Maintenance : bouton archivage + bouton reset rouge
- Cliquer "Reset" → modale de confirmation apparaît → "Annuler" ferme la modale

- [ ] **Step 8.3 : Commit**

```bash
cd frontend && git add src/pages/Parametres.jsx
git commit -m "feat(pages): implement Parametres page with collect/LLM/duplicates/maintenance sections"
```

---

## Task 9 : Page Analytics

**Files:**
- Modify: `frontend/src/pages/Analytics.jsx`

> Note : recharts ne rend pas dans jsdom (pas de ResizeObserver). Les tests de la page Analytics sont limités aux états loading/error — pas aux graphiques eux-mêmes.

- [ ] **Step 9.1 : Écrire Analytics.jsx**

Remplacer le contenu de `frontend/src/pages/Analytics.jsx` :

```jsx
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { useChartData, useKpisCa } from '../hooks/useTenders'

const COLORS_TERRITOIRE = ['#6366f1', '#e94560', '#f59e0b', '#10b981', '#94a3b8']
const COULEUR_DEF = '#e94560'

function getWeekLabel(date) {
  const d = new Date(date)
  const start = new Date(d.getFullYear(), 0, 1)
  const week = Math.ceil(((d - start) / 86400000 + start.getDay() + 1) / 7)
  return `S${week} ${d.getFullYear()}`
}

function computeCharts(data) {
  const now = new Date()
  const cutoff = new Date(now)
  cutoff.setDate(cutoff.getDate() - 7 * 30)

  // Publications par semaine (30 dernières semaines)
  const weekMap = {}
  data.forEach((d) => {
    if (!d.publication_date) return
    const dt = new Date(d.publication_date)
    if (dt < cutoff) return
    const label = getWeekLabel(dt)
    weekMap[label] = (weekMap[label] || 0) + 1
  })
  const byWeek = Object.entries(weekMap)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([week, count]) => ({ week, count }))

  // Par territoire
  const terMap = {}
  data.forEach((d) => {
    const t = d.territoire || 'Non précisé'
    terMap[t] = (terMap[t] || 0) + 1
  })
  const byTerritoire = Object.entries(terMap)
    .sort((a, b) => b[1] - a[1])
    .map(([name, value]) => ({ name, value }))

  // Par domaine
  const domMap = {}
  data.forEach((d) => {
    const parts = (d.domaine || 'Autre').split(', ')
    parts.forEach((p) => { domMap[p] = (domMap[p] || 0) + 1 })
  })
  const byDomaine = Object.entries(domMap)
    .sort((a, b) => b[1] - a[1])
    .map(([domaine, count]) => ({ domaine, count }))

  // Top 5 sources
  const srcMap = {}
  data.forEach((d) => { if (d.source) srcMap[d.source] = (srcMap[d.source] || 0) + 1 })
  const topSources = Object.entries(srcMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([source, count]) => ({ source, count }))

  // KPIs
  const total = data.length
  const goCount = data.filter((d) => {
    // score non disponible dans chart-data, on skip le taux GO ici
    return false
  }).length
  const sources = new Set(data.map((d) => d.source).filter(Boolean)).size

  return { byWeek, byTerritoire, byDomaine, topSources, total, sources }
}

function KpiCard({ label, value, color }) {
  return (
    <div className={`rounded-lg border p-4 flex flex-col gap-1 ${color}`}>
      <span className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</span>
      <span className="text-3xl font-bold">{value}</span>
    </div>
  )
}

export default function Analytics() {
  const { data: chartData = [], isLoading, isError } = useChartData()
  const { data: kpisCa } = useKpisCa()

  if (isLoading) {
    return (
      <div className="p-5 space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-56 rounded-lg bg-gray-100 animate-pulse" />
          ))}
        </div>
      </div>
    )
  }

  if (isError) {
    return <p className="p-5 text-red-600 text-sm">Impossible de charger les données analytics.</p>
  }

  const { byWeek, byTerritoire, byDomaine, topSources, total, sources } = computeCharts(chartData)
  const caGagne = kpisCa?.gagne ?? 0
  const caFormatted = caGagne >= 1000
    ? `${Math.round(caGagne / 1000)} k€`
    : `${caGagne} €`

  return (
    <div className="p-5 space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KpiCard label="Total collecté" value={total} color="bg-blue-50 border-blue-200 text-blue-700" />
        <KpiCard label="Sources actives" value={sources} color="bg-indigo-50 border-indigo-200 text-indigo-700" />
        <KpiCard label="CA gagné" value={caFormatted} color="bg-green-50 border-green-200 text-green-700" />
        <KpiCard label="CA pipeline" value={`${Math.round((kpisCa?.pipeline ?? 0) / 1000)} k€`} color="bg-amber-50 border-amber-200 text-amber-700" />
      </div>

      {/* Graphiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Publications par semaine */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Publications / semaine</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={byWeek} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
              <XAxis dataKey="week" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill={COULEUR_DEF} radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Donut territoire */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Par territoire</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie
                data={byTerritoire}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                dataKey="value"
                nameKey="name"
              >
                {byTerritoire.map((_, i) => (
                  <Cell key={i} fill={COLORS_TERRITOIRE[i % COLORS_TERRITOIRE.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend iconSize={8} wrapperStyle={{ fontSize: '10px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Barres horizontales domaine */}
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Par domaine</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              layout="vertical"
              data={byDomaine}
              margin={{ top: 0, right: 20, left: 0, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis type="category" dataKey="domaine" tick={{ fontSize: 9 }} width={80} />
              <Tooltip />
              <Bar dataKey="count" fill="#6366f1" radius={[0, 2, 2, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top 5 sources */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 max-w-sm">
        <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3">Top 5 sources</p>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs text-gray-500 border-b border-gray-200">
              <th className="text-left py-1 font-medium">Source</th>
              <th className="text-right py-1 font-medium">Marchés</th>
            </tr>
          </thead>
          <tbody>
            {topSources.map(({ source, count }) => (
              <tr key={source} className="border-b border-gray-50">
                <td className="py-1.5 text-gray-700">{source}</td>
                <td className="py-1.5 text-right font-semibold text-gray-800">{count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
```

- [ ] **Step 9.2 : Tester visuellement dans le navigateur**

Ouvrir `http://localhost:5173/analytics`. Vérifier :
- 4 cartes KPI visibles avec valeurs
- 3 graphiques Recharts rendus (même vides si base vide)
- Tableau Top 5 sources visible

- [ ] **Step 9.3 : Commit**

```bash
cd frontend && git add src/pages/Analytics.jsx
git commit -m "feat(pages): implement Analytics page with recharts and KPIs"
```

---

## Task 10 : Page Guide

**Files:**
- Modify: `frontend/src/pages/Guide.jsx`

- [ ] **Step 10.1 : Écrire Guide.jsx**

Remplacer le contenu de `frontend/src/pages/Guide.jsx` :

```jsx
function Section({ title, children }) {
  return (
    <section>
      <h2 className="text-base font-bold text-gray-800 mb-3">{title}</h2>
      {children}
    </section>
  )
}

function Table({ headers, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((h) => (
              <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wide border-b border-gray-200">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 text-gray-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Guide() {
  return (
    <div className="p-5 max-w-3xl space-y-8">
      <Section title="📋 Workflow — Comment utiliser l'app">
        <ol className="space-y-3">
          {[
            ['1 — Collecte', 'Aller dans Paramètres → Lancer la collecte. Les scrapers récupèrent les marchés depuis les sources configurées.'],
            ['2 — Qualification', 'Dans Pipeline, chaque marché est "À qualifier". Ouvrez la fiche, lisez l\'analyse IA, et choisissez un statut.'],
            ['3 — Suivi', 'Les marchés "En cours" apparaissent dans le kanban Direction. Mettez à jour le statut à chaque étape.'],
            ['4 — Clôture', 'Marquez le marché Gagné ou Perdu depuis le kanban. Les marchés Gagnés alimentent le CA pipeline.'],
          ].map(([step, desc]) => (
            <li key={step} className="flex gap-3">
              <span className="font-semibold text-gray-800 w-32 flex-shrink-0">{step}</span>
              <span className="text-gray-600">{desc}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="🎯 Scores de pertinence">
        <Table
          headers={['Score', 'Décision', 'Signification']}
          rows={[
            ['≥ 65', '🟢 GO', 'Marché dans notre cœur de métier, territoire prioritaire. À traiter en priorité.'],
            ['35 – 64', '🟡 Étudier', 'Marché potentiellement intéressant. Analyse approfondie recommandée.'],
            ['< 35', '🔴 Passer', 'Hors périmètre ou faible probabilité de succès. Archiver.'],
          ]}
        />
      </Section>

      <Section title="📊 Statuts des marchés">
        <Table
          headers={['Statut', 'Signification']}
          rows={[
            ['À qualifier', 'Marché fraîchement collecté, non encore analysé par l\'équipe.'],
            ['En cours', 'En cours d\'analyse ou de préparation de réponse.'],
            ['Soumis', 'Offre déposée, en attente de résultat.'],
            ['Gagné', 'Marché remporté ✅'],
            ['Perdu', 'Marché non remporté ❌'],
            ['Archivé', 'Ancien marché retiré de la vue active.'],
          ]}
        />
      </Section>

      <Section title="🌐 Sources surveillées">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { cat: '🏛️ Marchés publics France', sources: ['BOAMP', 'DECP', 'Marchés Publics Info', 'Marchés Sécurisés'] },
            { cat: '🌍 Banques de développement', sources: ['Banque Mondiale', 'AFD', 'BID', 'ISDB'] },
            { cat: '🏝️ Sources locales OI', sources: ['Département 974', 'SEMADER', 'NUKEMA', 'Presse locale'] },
            { cat: '🏗️ Signaux privés', sources: ['Permis de construire', 'Presse économique', 'Instao'] },
          ].map(({ cat, sources }) => (
            <div key={cat} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs font-semibold text-gray-700 mb-2">{cat}</p>
              <ul className="space-y-1">
                {sources.map((s) => (
                  <li key={s} className="text-sm text-gray-600">• {s}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
```

- [ ] **Step 10.2 : Tester visuellement dans le navigateur**

Ouvrir `http://localhost:5173/guide`. Vérifier :
- 4 sections visibles avec tableaux et listes
- Mise en page lisible, aucun appel réseau (vérifier l'onglet Network dans les DevTools — zéro requête)

- [ ] **Step 10.3 : Commit**

```bash
cd frontend && git add src/pages/Guide.jsx
git commit -m "feat(pages): implement Guide page with static help content"
```

---

## Task 11 : Vérification finale

- [ ] **Step 11.1 : Lancer la suite de tests complète**

```bash
cd frontend && npm test -- --reporter=verbose 2>&1
```

Attendu : tous les tests PASS (anciens + nouveaux composants)

- [ ] **Step 11.2 : Vérifier tous les onglets dans le navigateur**

Ouvrir `http://localhost:5173` et naviguer sur chaque onglet :
- `/` (Pipeline) — inchangé, KPIs + tableau
- `/analytics` — KPIs + 3 graphiques + top sources
- `/direction` — 3 colonnes kanban
- `/urgences` — cartes ou message vide
- `/parametres` — 4 sections fonctionnelles
- `/guide` — contenu statique

- [ ] **Step 11.3 : Vérifier le badge urgences dans la sidebar**

Le badge rouge sur "Urgences" dans la sidebar doit afficher le bon compteur (peut être 0 si base vide).

- [ ] **Step 11.4 : Commit final de vérification**

```bash
cd frontend && git status
```

Si tous les fichiers sont committés : aucune action. Sinon committer les fichiers restants.
