# Indicateur Analyse IA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une colonne "IA" dans le tableau des marchés avec un badge vert pour les tenders déjà analysés et un bouton pour déclencher l'analyse sur les autres.

**Architecture:** Le backend `POST /api/tenders/{id}/analyze`, la fonction `analyzeTender` dans `api.js` et le hook `useAnalyzeTender` dans `useTenders.js` existent déjà. Il faut (1) corriger l'invalidation du cache dans le hook et (2) ajouter la colonne IA dans `TendersTable.jsx` avec un état local `analyzingIds` pour la barre animée.

**Tech Stack:** React 18, React Query (`@tanstack/react-query`), Vitest + Testing Library, Tailwind CSS (classes `ocean-*`)

---

## Fichiers modifiés

| Fichier | Rôle |
|---|---|
| `frontend/src/hooks/useTenders.js` | Corriger `useAnalyzeTender` : invalider `['tenders']` en plus de `['tender', id]` |
| `frontend/src/components/TendersTable.jsx` | Ajouter colonne IA avec 3 états + handler |
| `frontend/src/components/TendersTable.test.jsx` | Tests de la colonne IA |

---

## Task 1 : Corriger useAnalyzeTender (useTenders.js)

**Contexte :** `useAnalyzeTender` n'invalide que `['tender', id]` (la fiche individuelle), pas `['tenders']` (la liste). Résultat : après analyse, le badge vert n'apparaît pas dans le tableau sans rechargement manuel.

**Files:**
- Modify: `frontend/src/hooks/useTenders.js:129-135`

- [ ] **Step 1 : Ouvrir useTenders.js et repérer useAnalyzeTender (ligne 129)**

```js
// Actuellement :
export const useAnalyzeTender = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }) => analyzeTender(id),
    onSuccess: (_, { id }) => qc.invalidateQueries({ queryKey: ['tender', id] }),
  })
}
```

- [ ] **Step 2 : Ajouter l'invalidation de ['tenders']**

Remplacer le bloc `useAnalyzeTender` par :

```js
export const useAnalyzeTender = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id }) => analyzeTender(id),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['tenders'] })
      qc.invalidateQueries({ queryKey: ['tender', id] })
    },
  })
}
```

- [ ] **Step 3 : Vérifier que les tests existants passent encore**

```bash
cd frontend && npx vitest run src/services/api.test.js
```

Résultat attendu : tous les tests PASS.

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/hooks/useTenders.js
git commit -m "fix(hooks): useAnalyzeTender invalide aussi la liste ['tenders']"
```

---

## Task 2 : Colonne IA dans TendersTable

**Contexte :** Ajouter une 9e colonne dans le tableau. Chaque cellule affiche l'un de ces 3 états selon `tender.llm_analysis` et `analyzingIds` :
- `llm_analysis !== null` → badge vert `✓ Analysé`
- ID dans `analyzingIds` → barre bleue animée (en cours)
- sinon → bouton `▶ Analyser`

**Files:**
- Modify: `frontend/src/components/TendersTable.jsx`
- Modify: `frontend/src/components/TendersTable.test.jsx`

- [ ] **Step 1 : Écrire les tests qui échouent**

Dans `frontend/src/components/TendersTable.test.jsx`, modifier le mock en haut pour inclure `useAnalyzeTender`, et ajouter `llm_analysis` aux données de mock, puis ajouter les nouveaux cas de test à la fin du `describe` existant :

```jsx
// 0. Modifier l'import vitest ligne 1 pour ajouter beforeEach :
import { describe, it, expect, vi, beforeEach } from 'vitest'

// 1. Remplacer le mock existant (ligne 6-8) par :
vi.mock('../hooks/useTenders', () => ({
  useTenders: vi.fn(),
  useAnalyzeTender: vi.fn(),
}))

// 2. Ajouter l'import de useAnalyzeTender (après l'import de useTenders ligne 10) :
import { useTenders, useAnalyzeTender } from '../hooks/useTenders'

// 3. Ajouter llm_analysis dans MOCK_TENDERS :
// tender id:'1' → llm_analysis: { score_pertinence: 75 }   (analysé)
// tender id:'2' → llm_analysis: null                        (non analysé)
// tender id:'3' → llm_analysis: null                        (non analysé)
// Le tableau MOCK_TENDERS devient :
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
    llm_analysis: { score_pertinence: 75 },
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
    llm_analysis: null,
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
    llm_analysis: null,
  },
]

// 4. Avant chaque test, initialiser useAnalyzeTender.
// Ajouter un beforeEach au début du describe (avant le premier it) :
beforeEach(() => {
  useAnalyzeTender.mockReturnValue({ mutate: vi.fn() })
})

// 5. Ajouter ces nouveaux tests à la fin du describe :
it('affiche le badge ✓ Analysé pour un tender avec llm_analysis', () => {
  useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
  render(<TendersTable {...DEFAULT_PROPS} />)
  expect(screen.getByText(/✓ Analysé/)).toBeInTheDocument()
})

it('affiche le bouton ▶ Analyser pour un tender sans llm_analysis', () => {
  useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
  render(<TendersTable {...DEFAULT_PROPS} />)
  const buttons = screen.getAllByText(/▶ Analyser/)
  expect(buttons.length).toBe(2)
})

it('le clic sur ▶ Analyser ne déclenche pas onRowClick', () => {
  useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
  const onRowClick = vi.fn()
  render(<TendersTable {...DEFAULT_PROPS} onRowClick={onRowClick} />)
  const analyzeBtn = screen.getAllByText(/▶ Analyser/)[0]
  fireEvent.click(analyzeBtn)
  expect(onRowClick).not.toHaveBeenCalled()
})

it('le bouton ▶ Analyser a un aria-label contenant le titre', () => {
  useTenders.mockReturnValue({ data: [MOCK_TENDERS[1]], isLoading: false, isError: false })
  render(<TendersTable {...DEFAULT_PROPS} />)
  expect(screen.getByRole('button', { name: /Vidéosurveillance Mayotte/i })).toBeInTheDocument()
})
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd frontend && npx vitest run src/components/TendersTable.test.jsx
```

Résultat attendu : les 4 nouveaux tests FAIL (✓ Analysé, ▶ Analyser introuvables).

- [ ] **Step 3 : Modifier TendersTable.jsx**

Remplacer le contenu complet de `frontend/src/components/TendersTable.jsx` par :

```jsx
import { useMemo, useState, useCallback } from 'react'
import { useTenders, useAnalyzeTender } from '../hooks/useTenders'

const STATUTS = ['Tous', 'À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']
const SECTEURS = ['Public', 'Privé', 'International']

function GonogoBadge({ gonogo }) {
  if (!gonogo) return <span className="text-ocean-muted text-xs">—</span>
  if (gonogo === 'GO')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-teal/10 text-ocean-teal">
        🟢 GO
      </span>
    )
  if (gonogo === 'Étudier')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-gold/10 text-ocean-gold">
        🟡 Étudier
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-coral/10 text-ocean-coral">
      🔴 Passer
    </span>
  )
}

function IaBadge({ tender, isAnalyzing, onAnalyze }) {
  if (isAnalyzing) {
    return (
      <div className="w-16 bg-white/6 rounded-full h-2 overflow-hidden">
        <div className="h-2 bg-gradient-to-r from-ocean-cyan to-ocean-teal rounded-full animate-pulse" style={{ width: '60%' }} />
      </div>
    )
  }
  if (tender.llm_analysis) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-teal/10 text-ocean-teal">
        ✓ Analysé
      </span>
    )
  }
  return (
    <button
      onClick={(e) => { e.stopPropagation(); onAnalyze(tender.id) }}
      aria-label={`Analyser ${tender.title}`}
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-coral/10 text-ocean-coral hover:bg-ocean-coral/20 transition-colors"
    >
      ▶ Analyser
    </button>
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
  onRowClick,
}) {
  const { data: tenders = [], isLoading, isError } = useTenders({ status, secteur })
  const [analyzingIds, setAnalyzingIds] = useState(new Set())
  const { mutate: triggerAnalysis } = useAnalyzeTender()

  const filtered = useMemo(() => {
    if (!searchText) return tenders
    const q = searchText.toLowerCase()
    return tenders.filter((t) =>
      `${t.title} ${t.domaine} ${t.territoire}`.toLowerCase().includes(q)
    )
  }, [tenders, searchText])

  const handleAnalyze = useCallback((id) => {
    setAnalyzingIds((prev) => new Set([...prev, id]))
    triggerAnalysis({ id }, {
      onSettled: () => setAnalyzingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      }),
    })
  }, [triggerAnalysis])

  return (
    <div className="bg-ocean-panel border border-ocean-border rounded-xl overflow-hidden">
      {/* Filtres */}
      <div className="flex flex-wrap gap-3 items-center p-4 border-b border-ocean-border">
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filtrer par statut"
          className="font-sans text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text focus:border-ocean-cyan/20 focus:outline-none"
        >
          {STATUTS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          value={secteur}
          onChange={(e) => onSecteurChange(e.target.value)}
          aria-label="Filtrer par secteur"
          className="font-sans text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text focus:border-ocean-cyan/20 focus:outline-none"
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
          className="font-sans text-sm border border-ocean-border rounded-lg px-2 py-1.5 flex-1 min-w-[200px] bg-ocean-navy text-ocean-text placeholder:text-ocean-muted focus:border-ocean-cyan/20 focus:outline-none"
        />
      </div>

      {/* Corps */}
      {isLoading && (
        <div className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-ocean-panel/50 rounded animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <p className="p-4 text-ocean-coral text-sm">Impossible de charger les marchés.</p>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <p className="p-8 text-center text-ocean-muted text-sm">Aucun marché trouvé.</p>
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="font-mono text-xs uppercase tracking-widest text-ocean-muted bg-black/20">
                <th className="text-left px-4 py-3 font-medium">Titre</th>
                <th className="text-left px-4 py-3 font-medium">Domaine</th>
                <th className="text-left px-4 py-3 font-medium">Territoire</th>
                <th className="text-left px-4 py-3 font-medium">Deadline</th>
                <th className="text-left px-4 py-3 font-medium">Score</th>
                <th className="text-left px-4 py-3 font-medium">GO/NO-GO</th>
                <th className="text-left px-4 py-3 font-medium">Statut</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
                <th className="text-left px-4 py-3 font-medium">IA</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => onRowClick?.(t.id)}
                  className={`border-b border-ocean-cyan/4 hover:bg-ocean-cyan/2 transition-colors${onRowClick ? ' cursor-pointer' : ''}`}
                  role={onRowClick ? 'button' : undefined}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onRowClick(t.id) } : undefined}
                >
                  <td className="px-4 py-3 font-sans font-medium text-ocean-text max-w-xs truncate">
                    {t.title}
                  </td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80">{t.domaine || '—'}</td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80">{t.territoire || '—'}</td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80 whitespace-nowrap">
                    {formatDate(t.deadline)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-white/6 rounded-full h-1">
                        <div
                          className="bg-gradient-to-r from-ocean-cyan to-ocean-teal h-1 rounded-full"
                          style={{ width: `${Math.min(t.relevance_score ?? 0, 100)}%` }}
                        />
                      </div>
                      <span className="font-mono text-xs text-ocean-text/80 tabular-nums">{t.relevance_score ?? 0}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <GonogoBadge gonogo={t.gonogo} />
                  </td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80">{t.status}</td>
                  <td className="px-4 py-3 font-mono text-xs text-ocean-muted">{t.source}</td>
                  <td className="px-4 py-3">
                    <IaBadge
                      tender={t}
                      isAnalyzing={analyzingIds.has(t.id)}
                      onAnalyze={handleAnalyze}
                    />
                  </td>
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

- [ ] **Step 4 : Vérifier que tous les tests passent**

```bash
cd frontend && npx vitest run src/components/TendersTable.test.jsx
```

Résultat attendu : tous les tests PASS (anciens + 4 nouveaux).

- [ ] **Step 5 : Lancer la suite complète**

```bash
cd frontend && npx vitest run
```

Résultat attendu : aucune régression, tous les tests PASS.

- [ ] **Step 6 : Commit**

```bash
git add frontend/src/components/TendersTable.jsx frontend/src/components/TendersTable.test.jsx
git commit -m "feat(table): colonne IA avec badge analysé / bouton analyser / barre de chargement"
```
