# TenderDetail — Fiche marché React (slide-over) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer `_render_fiche` Streamlit par un panneau slide-over React qui s'ouvre au clic sur une ligne du tableau et expose les mêmes sections (header, plan d'action, technique, IA, actions).

**Architecture:** Le backend enrichit `_tender_to_dict` avec `fiche_data` + `jours_restants` (calculés via `fiche_logic._compute_fiche_data`). Le composant `TenderDetail` orchestre 5 sous-composants inline et consomme `useTender` + les mutations déjà présentes dans `useTenders.js`. `Dashboard` gère `selectedId` et passe `onRowClick` à `TendersTable`.

**Tech Stack:** Python/FastAPI (backend), React 18, TailwindCSS, @tanstack/react-query, Vitest + React Testing Library (tests frontend), pytest + unittest.mock (tests backend).

---

## Fichiers

| Fichier | Action |
|---|---|
| `backend/main.py` | Modifier `_tender_to_dict` (import + 3 lignes) |
| `backend/test_main.py` | Créer (tests unitaires `_tender_to_dict`) |
| `frontend/src/components/TendersTable.jsx` | Ajouter prop `onRowClick` + `onClick` sur `<tr>` |
| `frontend/src/components/TendersTable.test.jsx` | Ajouter 1 test `onRowClick` |
| `frontend/src/components/TenderDetail.jsx` | Créer (composant principal + 5 sous-composants) |
| `frontend/src/components/TenderDetail.test.jsx` | Créer (12 tests) |
| `frontend/src/pages/Dashboard.jsx` | Ajouter `selectedId` + `<TenderDetail>` |
| `frontend/src/pages/Dashboard.test.jsx` | Ajouter 2 tests |

---

## Task 1 : Backend — enrichir `_tender_to_dict`

**Files:**
- Modify: `backend/main.py:144-172`
- Create: `backend/test_main.py`

- [ ] **Step 1 : Écrire le test qui doit échouer**

Créer `backend/test_main.py` :

```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
from main import _tender_to_dict


def _make_mock_tender():
    t = MagicMock()
    t.id = 'test-1'
    t.title = 'Marché SSI La Réunion'
    t.description = 'ssi détection incendie la réunion'
    t.source = 'DECP'
    t.publication_date = None
    t.date_extraction = None
    t.deadline = None
    t.status = 'À qualifier'
    t.relevance_score = 75
    t.adaptive_score = None
    t.is_maintenance = False
    t.secteur = 'Public'
    t.type_opportunite = 'Marché Public'
    t.amount = None
    t.is_blacklisted = False
    t.is_saved = False
    t.notes = None
    t.tags = []
    t.llm_analysis = {}
    t.llm_structured = None
    return t


def test_tender_to_dict_includes_fiche_data_and_jours_restants():
    result = _tender_to_dict(_make_mock_tender())
    assert 'fiche_data' in result
    assert 'jours_restants' in result


def test_fiche_data_has_required_keys():
    result = _tender_to_dict(_make_mock_tender())
    fd = result['fiche_data']
    for key in ('sm', 'sg', 'sk', 'smaint', 'label_action', 'steps', 'atouts', 'risques'):
        assert key in fd, f"Clé manquante : {key}"
    assert isinstance(fd['steps'], list)
    assert isinstance(fd['atouts'], list)
    assert isinstance(fd['risques'], list)


def test_jours_restants_is_none_when_no_deadline():
    result = _tender_to_dict(_make_mock_tender())
    assert result['jours_restants'] is None
```

- [ ] **Step 2 : Vérifier que le test échoue**

```
cd backend && python -m pytest test_main.py -v
```

Résultat attendu : `FAILED — KeyError 'fiche_data'` (les clés n'existent pas encore).

- [ ] **Step 3 : Modifier `backend/main.py`**

En tête du fichier, après les imports existants, ajouter :

```python
from fiche_logic import _compute_fiche_data
```

Remplacer la fonction `_tender_to_dict` (lignes 144-172) par :

```python
def _tender_to_dict(t: Tender) -> dict:
    a = t.llm_analysis or {}
    score = a.get("score_pertinence", t.relevance_score or 0)
    domaine = _detect_domaine(t.title or "", t.description or "")
    territoire = _detect_territoire(t.title or "", t.description or "")
    jours_restants = (t.deadline - datetime.utcnow()).days if t.deadline else None
    fiche_data = _compute_fiche_data(
        score, jours_restants, domaine, territoire,
        bool(t.is_maintenance), t.title or "", a
    )
    return {
        "id": t.id,
        "title": t.title or "Sans titre",
        "description": t.description or "",
        "source": t.source or "",
        "publication_date": _ser_dt(t.publication_date),
        "date_extraction": _ser_dt(t.date_extraction),
        "deadline": _ser_dt(t.deadline),
        "status": t.status or "À qualifier",
        "relevance_score": score,
        "gonogo": _gonogo(score),
        "adaptive_score": t.adaptive_score,
        "is_maintenance": bool(t.is_maintenance),
        "secteur": t.secteur or "Public",
        "type_opportunite": t.type_opportunite or "Marché Public",
        "amount": t.amount,
        "is_blacklisted": bool(t.is_blacklisted),
        "is_saved": bool(t.is_saved),
        "notes": t.notes,
        "tags": t.tags if isinstance(t.tags, list) else [],
        "domaine": domaine,
        "territoire": territoire,
        "type_marche": a.get("type_marche") or t.type_opportunite or "",
        "concurrents": ", ".join(a.get("marques_concurrentes_citees", [])),
        "llm_structured": t.llm_structured,
        "jours_restants": jours_restants,
        "fiche_data": fiche_data,
    }
```

- [ ] **Step 4 : Vérifier que les tests passent**

```
cd backend && python -m pytest test_main.py -v
```

Résultat attendu : `3 passed`.

- [ ] **Step 5 : Commit**

```bash
git add backend/main.py backend/test_main.py
git commit -m "feat: enrich _tender_to_dict with fiche_data and jours_restants"
```

---

## Task 2 : TendersTable — ajouter `onRowClick`

**Files:**
- Modify: `frontend/src/components/TendersTable.jsx`
- Modify: `frontend/src/components/TendersTable.test.jsx`

- [ ] **Step 1 : Écrire le test qui doit échouer**

Dans `TendersTable.test.jsx`, ajouter après le dernier `it(...)` :

```jsx
import { fireEvent } from '@testing-library/react'

// (ajouter fireEvent à l'import existant en haut du fichier)

it('appelle onRowClick avec l\'id du marché au clic sur une ligne', () => {
  useTenders.mockReturnValue({ data: MOCK_TENDERS, isLoading: false, isError: false })
  const onRowClick = vi.fn()
  render(<TendersTable {...DEFAULT_PROPS} onRowClick={onRowClick} />)
  fireEvent.click(screen.getByText('Marché SSI Réunion'))
  expect(onRowClick).toHaveBeenCalledWith('1')
})
```

Note : ajouter `fireEvent` à la ligne d'import existante :
```jsx
import { render, screen, fireEvent } from '@testing-library/react'
```

- [ ] **Step 2 : Vérifier que le test échoue**

```
cd frontend && npm test -- --reporter=verbose TendersTable
```

Résultat attendu : `FAIL — onRowClick not called`.

- [ ] **Step 3 : Modifier `TendersTable.jsx`**

Ajouter `onRowClick` dans les props destructurées :

```jsx
export default function TendersTable({
  status,
  secteur,
  searchText,
  onStatusChange,
  onSecteurChange,
  onSearchChange,
  onRowClick,
}) {
```

Sur la balise `<tr>` dans le rendu des lignes, ajouter `onClick` et `cursor-pointer` :

```jsx
<tr
  key={t.id}
  onClick={() => onRowClick?.(t.id)}
  className="border-b border-gray-50 hover:bg-gray-50 transition-colors cursor-pointer"
>
```

- [ ] **Step 4 : Vérifier que tous les tests TendersTable passent**

```
cd frontend && npm test -- --reporter=verbose TendersTable
```

Résultat attendu : `14 passed`.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/TendersTable.jsx frontend/src/components/TendersTable.test.jsx
git commit -m "feat: add onRowClick prop to TendersTable rows"
```

---

## Task 3 : Créer `TenderDetail.jsx`

**Files:**
- Create: `frontend/src/components/TenderDetail.jsx`
- Create: `frontend/src/components/TenderDetail.test.jsx`

- [ ] **Step 1 : Écrire les tests qui doivent échouer**

Créer `frontend/src/components/TenderDetail.test.jsx` :

```jsx
// frontend/src/components/TenderDetail.test.jsx
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import TenderDetail from './TenderDetail'

vi.mock('../hooks/useTenders', () => ({
  useTender: vi.fn(),
  useUpdateStatus: vi.fn(),
  useUpdateSaved: vi.fn(),
}))

import { useTender, useUpdateStatus, useUpdateSaved } from '../hooks/useTenders'

const MOCK_TENDER = {
  id: 'abc1',
  title: 'Marché SSI La Réunion',
  description: 'Travaux SSI détection incendie',
  source: 'DECP',
  deadline: '2026-06-30T00:00:00',
  jours_restants: 40,
  status: 'À qualifier',
  relevance_score: 78,
  gonogo: 'GO',
  adaptive_score: null,
  is_maintenance: false,
  secteur: 'Public',
  type_opportunite: 'Marché Public',
  type_marche: 'Marché Public',
  amount: 150000,
  is_blacklisted: false,
  is_saved: false,
  notes: null,
  tags: [],
  domaine: '🔥 SSI / Détection incendie',
  territoire: 'La Réunion',
  concurrents: '',
  llm_structured: null,
  fiche_data: {
    sm: 45, sg: 30, sk: 6, smaint: 0,
    label_action: '🟢 Planifier la réponse',
    steps: ['Inscrire au planning', 'Télécharger le DCE'],
    atouts: ['✅ Cœur de métier — SSI/CMSI'],
    risques: [],
  },
}

const MOCK_MUTATION = { mutate: vi.fn(), isPending: false }

describe('TenderDetail', () => {
  beforeEach(() => {
    useUpdateStatus.mockReturnValue(MOCK_MUTATION)
    useUpdateSaved.mockReturnValue(MOCK_MUTATION)
  })

  it('ne rend rien si tenderId est null', () => {
    useTender.mockReturnValue({ data: null, isLoading: false, isError: false })
    const { container } = render(<TenderDetail tenderId={null} onClose={vi.fn()} />)
    expect(container.firstChild).toBeNull()
  })

  it('affiche 3 skeletons en état loading', () => {
    useTender.mockReturnValue({ data: null, isLoading: true, isError: false })
    const { container } = render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(3)
  })

  it('affiche le message erreur si isError', () => {
    useTender.mockReturnValue({ data: null, isLoading: false, isError: true })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText(/impossible de charger ce marché/i)).toBeInTheDocument()
  })

  it('affiche le badge 🟢 GO', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText(/🟢 GO/)).toBeInTheDocument()
  })

  it('affiche le titre du marché', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText('Marché SSI La Réunion')).toBeInTheDocument()
  })

  it('affiche le label_action du plan d\'action', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText('🟢 Planifier la réponse')).toBeInTheDocument()
  })

  it('affiche les étapes du plan d\'action', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByText('Inscrire au planning')).toBeInTheDocument()
    expect(screen.getByText('Télécharger le DCE')).toBeInTheDocument()
  })

  it('appelle onClose au clic sur le bouton Fermer', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    const onClose = vi.fn()
    render(<TenderDetail tenderId="abc1" onClose={onClose} />)
    fireEvent.click(screen.getByRole('button', { name: /fermer/i }))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('appelle onClose au clic sur l\'overlay', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    const onClose = vi.fn()
    render(<TenderDetail tenderId="abc1" onClose={onClose} />)
    fireEvent.click(document.querySelector('[aria-hidden="true"]'))
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('appelle onClose à la touche Escape', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    const onClose = vi.fn()
    render(<TenderDetail tenderId="abc1" onClose={onClose} />)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(onClose).toHaveBeenCalledOnce()
  })

  it('affiche le select de qualification', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByRole('combobox', { name: /qualifier/i })).toBeInTheDocument()
  })

  it('affiche le bouton étoile non sauvegardé', () => {
    useTender.mockReturnValue({ data: MOCK_TENDER, isLoading: false, isError: false })
    render(<TenderDetail tenderId="abc1" onClose={vi.fn()} />)
    expect(screen.getByRole('button', { name: /sauvegarder/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
cd frontend && npm test -- --reporter=verbose TenderDetail
```

Résultat attendu : `Cannot find module './TenderDetail'`.

- [ ] **Step 3 : Créer `TenderDetail.jsx`**

Créer `frontend/src/components/TenderDetail.jsx` avec le contenu suivant :

```jsx
// frontend/src/components/TenderDetail.jsx
import { useEffect, useState } from 'react'
import { useTender, useUpdateStatus, useUpdateSaved } from '../hooks/useTenders'

const STATUTS = ['À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

function formatAmount(amount) {
  if (!amount) return '—'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency', currency: 'EUR', maximumFractionDigits: 0,
  }).format(amount)
}

function GonogoBadge({ gonogo }) {
  if (gonogo === 'GO')
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-green-100 text-green-800">🟢 GO</span>
  if (gonogo === 'Étudier')
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-yellow-100 text-yellow-800">🟡 Étudier</span>
  return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-red-100 text-red-800">🔴 Passer</span>
}

function ScoreBar({ label, value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span className="tabular-nums font-medium">{value}/{max}</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full">
        <div className="h-2 bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
      ))}
    </div>
  )
}

function TenderDetailHeader({ tender }) {
  return (
    <div className="space-y-3">
      <GonogoBadge gonogo={tender.gonogo} />
      <h2 className="text-base font-semibold text-gray-900 line-clamp-2">{tender.title}</h2>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        <span>
          Score : <strong className="text-gray-700">{tender.relevance_score ?? 0}</strong>/100
        </span>
        <span>
          Deadline : <strong className="text-gray-700">{formatDate(tender.deadline)}</strong>
          {tender.jours_restants != null && (
            <span className={`ml-1 ${
              tender.jours_restants <= 7
                ? 'text-red-600 font-bold'
                : tender.jours_restants <= 30
                ? 'text-orange-500'
                : ''
            }`}>
              ({tender.jours_restants} j)
            </span>
          )}
        </span>
        <span>Montant : <strong className="text-gray-700">{formatAmount(tender.amount)}</strong></span>
        <span>Secteur : <strong className="text-gray-700">{tender.secteur || '—'}</strong></span>
        <span>Source : <strong className="text-gray-700">{tender.source || '—'}</strong></span>
      </div>
    </div>
  )
}

function TenderDetailActionPlan({ ficheData }) {
  if (!ficheData) return null
  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-gray-800">{ficheData.label_action}</h3>
      <ol className="space-y-1.5 pl-5">
        {ficheData.steps.map((step, i) => (
          <li key={i} className="text-sm text-gray-700 list-decimal">{step}</li>
        ))}
      </ol>
      {ficheData.risques.length > 0 && (
        <div className="space-y-1">
          {ficheData.risques.map((r, i) => (
            <div key={i} className="text-sm px-3 py-2 bg-orange-50 border border-orange-200 rounded text-orange-800">
              {r}
            </div>
          ))}
        </div>
      )}
      {ficheData.atouts.length > 0 && (
        <div className="space-y-1">
          {ficheData.atouts.map((a, i) => (
            <div key={i} className="text-sm px-3 py-2 bg-green-50 border border-green-200 rounded text-green-800">
              {a}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TenderDetailTechnical({ tender }) {
  const [open, setOpen] = useState(false)
  const fd = tender.fiche_data
  return (
    <div className="border border-gray-200 rounded">
      <button
        className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span>📊 Détail du score & mots-clés</span>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && fd && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase pt-3">Décomposition du score</p>
          <ScoreBar label="Pertinence métier" value={fd.sm} max={45} />
          <ScoreBar label="Proximité géographique" value={fd.sg} max={30} />
          <ScoreBar label="Mots-clés dans le titre" value={fd.sk} max={15} />
          <ScoreBar label="Maintenance / Récurrence" value={fd.smaint} max={10} />
          <div className="pt-2 space-y-1 text-xs text-gray-600 border-t border-gray-100">
            <div><span className="font-medium">Type : </span>{tender.type_marche || tender.type_opportunite || '—'}</div>
            <div><span className="font-medium">Territoire : </span>{tender.territoire || '—'}</div>
            <div><span className="font-medium">Domaine : </span>{tender.domaine || '—'}</div>
            {tender.concurrents && (
              <div><span className="font-medium">Concurrents : </span>{tender.concurrents}</div>
            )}
          </div>
          {tender.description && (
            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Description</p>
              <p className="text-xs text-gray-600 whitespace-pre-wrap line-clamp-6">{tender.description}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TenderDetailAI({ llmStructured }) {
  const s = llmStructured
  const recoBadge =
    s.recommandation === 'GO' ? (
      <span className="text-green-700 font-semibold">✅ GO</span>
    ) : s.recommandation === 'NON' ? (
      <span className="text-red-700 font-semibold">🔴 NON</span>
    ) : (
      <span>—</span>
    )
  return (
    <div className="border border-gray-200 rounded px-4 py-3 space-y-2">
      <p className="text-xs font-semibold text-gray-500 uppercase">🤖 Analyse IA</p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs text-gray-700">
        <div><span className="font-medium">Budget estimé</span><br />{s.budget_estime || '—'}</div>
        <div><span className="font-medium">Type de travaux</span><br />{s.type_travaux || '—'}</div>
        <div><span className="font-medium">Acheteur</span><br />{s.acheteur_type || '—'}</div>
        <div><span className="font-medium">Concurrence</span><br />{s.niveau_concurrence || '—'}</div>
        <div>
          <span className="font-medium">Confiance IA</span><br />
          {s.score_confiance != null ? `${s.score_confiance} %` : '—'}
        </div>
        <div><span className="font-medium">Recommandation</span><br />{recoBadge}</div>
      </div>
      {s.lots && s.lots.length > 0 && (
        <p className="text-xs text-gray-600">
          <span className="font-medium">Lots : </span>{s.lots.join(' · ')}
        </p>
      )}
      {s.justification && (
        <p className="text-xs text-gray-500 italic">{s.justification}</p>
      )}
    </div>
  )
}

function TenderDetailActions({ tender }) {
  const updateStatus = useUpdateStatus()
  const updateSaved = useUpdateSaved()
  return (
    <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
      <select
        value={tender.status}
        onChange={(e) => updateStatus.mutate({ id: tender.id, status: e.target.value })}
        disabled={updateStatus.isPending}
        aria-label="Qualifier le marché"
        className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white flex-1"
      >
        {STATUTS.map((s) => <option key={s}>{s}</option>)}
      </select>
      <button
        onClick={() => updateSaved.mutate({ id: tender.id, is_saved: !tender.is_saved })}
        disabled={updateSaved.isPending}
        aria-label={tender.is_saved ? 'Retirer des favoris' : 'Sauvegarder'}
        className={`text-xl px-2 py-1 rounded transition-colors ${
          tender.is_saved
            ? 'text-yellow-500 hover:text-yellow-600'
            : 'text-gray-300 hover:text-yellow-400'
        }`}
      >
        {tender.is_saved ? '⭐' : '☆'}
      </button>
    </div>
  )
}

export default function TenderDetail({ tenderId, onClose }) {
  useEffect(() => {
    if (!tenderId) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [tenderId, onClose])

  const { data: tender, isLoading, isError } = useTender(tenderId)

  if (!tenderId) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-label="Fiche marché"
        className="fixed right-0 top-0 bottom-0 w-[480px] z-50 bg-white overflow-y-auto shadow-xl flex flex-col"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0">
          <span className="text-sm font-medium text-gray-500">Fiche marché</span>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {isLoading && <LoadingSkeleton />}
        {isError && (
          <p className="p-6 text-red-600 text-sm">Impossible de charger ce marché.</p>
        )}
        {tender && (
          <div className="p-4 space-y-5">
            <TenderDetailHeader tender={tender} />
            <hr className="border-gray-100" />
            <TenderDetailActionPlan ficheData={tender.fiche_data} />
            <TenderDetailTechnical tender={tender} />
            {tender.llm_structured && (
              <TenderDetailAI llmStructured={tender.llm_structured} />
            )}
            <TenderDetailActions tender={tender} />
          </div>
        )}
      </div>
    </>
  )
}
```

- [ ] **Step 4 : Vérifier que tous les tests TenderDetail passent**

```
cd frontend && npm test -- --reporter=verbose TenderDetail
```

Résultat attendu : `12 passed`.

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/TenderDetail.jsx frontend/src/components/TenderDetail.test.jsx
git commit -m "feat: add TenderDetail slide-over component"
```

---

## Task 4 : Câbler `Dashboard.jsx`

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`
- Modify: `frontend/src/pages/Dashboard.test.jsx`

- [ ] **Step 1 : Écrire les tests qui doivent échouer**

Dans `Dashboard.test.jsx`, ajouter le mock `TenderDetail` et 2 nouveaux tests.

En haut du fichier, ajouter le mock après les mocks existants :

```jsx
vi.mock('../components/TenderDetail', () => ({
  default: (props) =>
    props.tenderId
      ? <div data-testid="tender-detail" data-tender-id={props.tenderId} />
      : null,
}))
```

Mettre à jour le mock `TendersTable` pour exposer `onRowClick` :

```jsx
vi.mock('../components/TendersTable', () => ({
  default: (props) => (
    <div data-testid="tenders-table">
      <span data-testid="prop-status">{props.status}</span>
      <span data-testid="prop-secteur">{props.secteur}</span>
      <span data-testid="prop-search">{props.searchText}</span>
      <button onClick={() => props.onStatusChange('En cours')}>set-status</button>
      <button onClick={() => props.onSecteurChange('Privé')}>set-secteur</button>
      <button onClick={() => props.onSearchChange('test')}>set-search</button>
      <button onClick={() => props.onRowClick?.('t-1')}>row-click</button>
    </div>
  ),
}))
```

Ajouter dans le `describe('Dashboard')` :

```jsx
it('TenderDetail n\'est pas rendu initialement', () => {
  render(<Dashboard />)
  expect(screen.queryByTestId('tender-detail')).not.toBeInTheDocument()
})

it('ouvre TenderDetail avec le bon tenderId au clic sur une ligne', () => {
  render(<Dashboard />)
  fireEvent.click(screen.getByText('row-click'))
  const detail = screen.getByTestId('tender-detail')
  expect(detail).toBeInTheDocument()
  expect(detail.dataset.tenderId).toBe('t-1')
})
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```
cd frontend && npm test -- --reporter=verbose Dashboard
```

Résultat attendu : `2 failed — Cannot find module '../components/TenderDetail'` ou `TenderDetail not rendered`.

- [ ] **Step 3 : Modifier `Dashboard.jsx`**

Remplacer le contenu de `frontend/src/pages/Dashboard.jsx` par :

```jsx
import { useState } from 'react'
import KpiGrid from '../components/KpiGrid'
import TendersTable from '../components/TendersTable'
import TenderDetail from '../components/TenderDetail'

export default function Dashboard() {
  const [status, setStatus] = useState('Tous')
  const [secteur, setSecteur] = useState('Public')
  const [searchText, setSearchText] = useState('')
  const [selectedId, setSelectedId] = useState(null)

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
        onRowClick={setSelectedId}
      />
      <TenderDetail tenderId={selectedId} onClose={() => setSelectedId(null)} />
    </div>
  )
}
```

- [ ] **Step 4 : Vérifier que tous les tests Dashboard passent**

```
cd frontend && npm test -- --reporter=verbose Dashboard
```

Résultat attendu : `9 passed`.

- [ ] **Step 5 : Lancer la suite complète**

```
cd frontend && npm test
```

Résultat attendu : tous les tests passent (TendersTable, TenderDetail, Dashboard, KpiGrid, etc.).

- [ ] **Step 6 : Commit**

```bash
git add frontend/src/pages/Dashboard.jsx frontend/src/pages/Dashboard.test.jsx
git commit -m "feat: wire TenderDetail into Dashboard with selectedId state"
```
