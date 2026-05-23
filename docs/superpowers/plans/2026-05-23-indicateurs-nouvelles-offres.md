# Indicateurs nouvelles offres Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter un indicateur "Nouvelles 24h" fiable dans le KpiGrid, rafraîchir les KPIs après collecte, et nettoyer les barres de progression fausses dans la Sidebar.

**Architecture:** Le backend ajoute `new_24h` au endpoint `/api/kpis/public` existant via une requête SQL sur `Tender.date_extraction`. Le frontend corrige `useCollectMutation` pour invalider les KPIs après collecte, met à jour `KpiGrid` avec une 6ème card, et nettoie la Sidebar.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + TanStack Query + Vitest (frontend)

---

## Fichiers modifiés

| Fichier | Changement |
|---|---|
| `backend/main.py` | Ajouter `new_24h` dans `get_kpis_public()` |
| `backend/test_main.py` | Ajouter test pour `new_24h` dans la réponse KPIs |
| `frontend/src/hooks/useTenders.js` | `useCollectMutation.onSuccess` invalide `['kpis']` et `['tenders']` |
| `frontend/src/components/KpiGrid.jsx` | Ajouter 6ème card "Nouvelles 24h", grille 6 colonnes |
| `frontend/src/components/KpiGrid.test.jsx` | Mettre à jour les tests (6 skeletons, 6 labels, champ `new_24h`) |
| `frontend/src/components/Sidebar.jsx` | Supprimer barres "Collecte" + "Mots-clés", ajouter résumé texte |

---

## Task 1 : Backend — ajouter `new_24h` dans `/api/kpis/public`

**Files:**
- Modify: `backend/main.py` (fonction `get_kpis_public`, ligne ~494)
- Test: `backend/test_main.py`

- [ ] **Step 1 : Écrire le test qui échoue**

Dans `backend/test_main.py`, ajouter à la fin du fichier :

```python
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta

def test_get_kpis_public_includes_new_24h():
    """get_kpis_public doit retourner new_24h dans sa réponse."""
    from fastapi.testclient import TestClient
    from main import app

    with patch('main.get_db') as mock_get_db:
        mock_db = MagicMock()
        # group_by query pour les statuts
        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ('À qualifier', 5), ('En cours', 3),
        ]
        # scalar queries pour new_24h et new_7d
        mock_db.query.return_value.filter.return_value.scalar.return_value = 7

        def override_get_db():
            yield mock_db

        from main import get_db
        app.dependency_overrides[get_db] = override_get_db
        client = TestClient(app)
        response = client.get('/api/kpis/public')
        app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert 'new_24h' in data, f"'new_24h' absent de la réponse : {data}"
    assert isinstance(data['new_24h'], int)
```

- [ ] **Step 2 : Vérifier que le test échoue**

```bash
cd backend
python -m pytest test_main.py::test_get_kpis_public_includes_new_24h -v
```

Attendu : FAILED — `AssertionError: 'new_24h' absent de la réponse`

- [ ] **Step 3 : Implémenter le changement dans `backend/main.py`**

Localiser la fonction `get_kpis_public` (vers la ligne 494). Ajouter en tête du fichier si absent :

```python
from datetime import datetime, timedelta
```

Puis modifier le corps de `get_kpis_public` pour ajouter les deux scalaires **après** le bloc `counts` existant, juste avant le `return` :

```python
@app.get("/api/kpis/public", summary="KPIs marchés publics (compteurs par statut)")
def get_kpis_public(db: Session = Depends(get_db)):
    pub_filter = or_(Tender.secteur == "Public", Tender.secteur == None)
    counts = dict(
        db.query(Tender.status, _func.count(Tender.id))
        .filter(Tender.is_blacklisted == False, pub_filter)
        .group_by(Tender.status)
        .all()
    )
    a_qualifier = counts.get("À qualifier", 0) + counts.get(None, 0)
    en_cours = counts.get("En cours", 0)
    soumis = counts.get("Soumis", 0)
    gagnes = counts.get("Gagné", 0)
    total = a_qualifier + en_cours + soumis + gagnes

    now = datetime.utcnow()
    new_24h = db.query(_func.count(Tender.id)).filter(
        Tender.is_blacklisted == False,
        Tender.date_extraction >= now - timedelta(hours=24),
    ).scalar() or 0

    return {
        "total": total,
        "a_qualifier": a_qualifier,
        "en_cours": en_cours,
        "soumis": soumis,
        "gagnes": gagnes,
        "new_24h": new_24h,
    }
```

- [ ] **Step 4 : Vérifier que le test passe**

```bash
cd backend
python -m pytest test_main.py::test_get_kpis_public_includes_new_24h -v
```

Attendu : PASSED

- [ ] **Step 5 : Vérifier que les tests existants passent toujours**

```bash
cd backend
python -m pytest test_main.py -v
```

Attendu : tous PASSED

- [ ] **Step 6 : Commit**

```bash
git add backend/main.py backend/test_main.py
git commit -m "feat(backend): ajouter new_24h dans /api/kpis/public"
```

---

## Task 2 : Frontend hooks — rafraîchir KPIs après collecte

**Files:**
- Modify: `frontend/src/hooks/useTenders.js` (lignes 61-67)

> Il n'y a pas de test unitaire pour `useCollectMutation` car c'est un hook de mutation TanStack Query — le comportement est validé par les tests d'intégration des composants qui l'utilisent. Le test de non-régression ici est de vérifier que le KpiGrid se rafraîchit visuellement après une collecte (testé manuellement à la Task 6).

- [ ] **Step 1 : Modifier `useCollectMutation` dans `frontend/src/hooks/useTenders.js`**

Remplacer le bloc actuel :

```js
export const useCollectMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: collect,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scraper-runs'] }),
  })
}
```

Par :

```js
export const useCollectMutation = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: collect,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scraper-runs'] })
      qc.invalidateQueries({ queryKey: ['kpis'] })
      qc.invalidateQueries({ queryKey: ['tenders'] })
    },
  })
}
```

- [ ] **Step 2 : Commit**

```bash
git add frontend/src/hooks/useTenders.js
git commit -m "fix(hooks): invalider kpis et tenders apres collecte"
```

---

## Task 3 : Frontend KpiGrid — ajouter la 6ème card "Nouvelles 24h"

**Files:**
- Modify: `frontend/src/components/KpiGrid.jsx`
- Test: `frontend/src/components/KpiGrid.test.jsx`

- [ ] **Step 1 : Écrire les tests qui échouent**

Remplacer **tout le contenu** de `frontend/src/components/KpiGrid.test.jsx` par :

```jsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import KpiGrid from './KpiGrid'

vi.mock('../hooks/useTenders', () => ({
  useKpisPublic: vi.fn(),
}))

import { useKpisPublic } from '../hooks/useTenders'

describe('KpiGrid', () => {
  it('affiche 6 skeletons en état loading', () => {
    useKpisPublic.mockReturnValue({ data: null, isLoading: true, isError: false })
    const { container } = render(<KpiGrid />)
    expect(container.querySelectorAll('.animate-pulse')).toHaveLength(6)
  })

  it("affiche un message d'erreur si isError", () => {
    useKpisPublic.mockReturnValue({ data: null, isLoading: false, isError: true })
    render(<KpiGrid />)
    expect(screen.getByText(/impossible de charger les kpis/i)).toBeInTheDocument()
  })

  it('affiche les 6 compteurs KPI avec les bonnes valeurs', () => {
    useKpisPublic.mockReturnValue({
      data: { total: 42, a_qualifier: 10, en_cours: 5, soumis: 3, gagnes: 2, new_24h: 7 },
      isLoading: false,
      isError: false,
    })
    render(<KpiGrid />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('affiche les labels des 6 cartes', () => {
    useKpisPublic.mockReturnValue({
      data: { total: 0, a_qualifier: 0, en_cours: 0, soumis: 0, gagnes: 0, new_24h: 0 },
      isLoading: false,
      isError: false,
    })
    render(<KpiGrid />)
    expect(screen.getByText(/total marchés/i)).toBeInTheDocument()
    expect(screen.getByText(/à qualifier/i)).toBeInTheDocument()
    expect(screen.getByText(/en cours/i)).toBeInTheDocument()
    expect(screen.getByText(/soumis/i)).toBeInTheDocument()
    expect(screen.getByText(/gagnés/i)).toBeInTheDocument()
    expect(screen.getByText(/nouvelles 24h/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd frontend
npm test -- --run KpiGrid
```

Attendu : 2 tests FAILED (skeleton count et label "Nouvelles 24h")

- [ ] **Step 3 : Modifier `frontend/src/components/KpiGrid.jsx`**

Remplacer **tout le contenu** par :

```jsx
import { useKpisPublic } from '../hooks/useTenders'

const KPI_CARDS = [
  { key: 'total',       label: 'Total marchés',  icon: '📋', topColor: 'border-t-2 border-ocean-cyan' },
  { key: 'a_qualifier', label: 'À qualifier',    icon: '🔍', topColor: 'border-t-2 border-ocean-muted' },
  { key: 'en_cours',   label: 'En cours',        icon: '⚙️', topColor: 'border-t-2 border-ocean-teal' },
  { key: 'soumis',     label: 'Soumis',          icon: '📤', topColor: 'border-t-2 border-ocean-gold' },
  { key: 'gagnes',     label: 'Gagnés',          icon: '✅', topColor: 'border-t-2 border-ocean-teal' },
  { key: 'new_24h',    label: 'Nouvelles 24h',   icon: '🆕', topColor: 'border-t-2 border-ocean-cyan/50' },
]

export default function KpiGrid() {
  const { data, isLoading, isError } = useKpisPublic()

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-ocean-panel/50 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="text-ocean-coral text-sm">Impossible de charger les KPIs.</p>
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
      {KPI_CARDS.map(({ key, label, icon, topColor }) => (
        <div key={key} className={`bg-ocean-panel border border-ocean-border rounded-xl p-5 flex flex-col gap-1 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-ocean-cyan/6 transition-all duration-200 ${topColor}`}>
          <span className="font-sans text-xs uppercase tracking-widest text-ocean-muted">{icon} {label}</span>
          <span className="font-serif text-4xl font-bold text-ocean-text">{data?.[key] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
cd frontend
npm test -- --run KpiGrid
```

Attendu : 4 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/KpiGrid.jsx frontend/src/components/KpiGrid.test.jsx
git commit -m "feat(kpigrid): ajouter card Nouvelles 24h, grille 6 colonnes"
```

---

## Task 4 : Frontend Sidebar — nettoyer les barres fausses

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx` (section `showResults`, lignes ~216-261)
- Test: `frontend/src/components/Sidebar.test.jsx`

- [ ] **Step 1 : Écrire le test qui vérifie la suppression des barres fausses**

Ajouter à la fin de `frontend/src/components/Sidebar.test.jsx` :

```jsx
import { vi } from 'vitest'

vi.mock('../hooks/useTenders', () => ({
  useUrgences: vi.fn(() => ({ data: [] })),
  useSources: vi.fn(() => ({ data: [] })),
  useCredentials: vi.fn(() => ({ data: [] })),
  useCollectMutation: vi.fn(() => ({
    mutate: vi.fn(),
    isPending: false,
    data: {
      status: 'ok',
      results: [
        { source: 'DECP', status: 'ok', nb_new: 5 },
        { source: 'AFD', status: 'ok', nb_new: 3 },
      ],
    },
    reset: vi.fn(),
  })),
  useAnalyzePending: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}))

describe('Sidebar — résultats post-collecte', () => {
  it('affiche le total de nouvelles offres après collecte', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText(/\+8 nouvelles offres/i)).toBeInTheDocument()
  })

  it("n'affiche pas les barres Collecte et Mots-clés", () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.queryByText(/^collecte$/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/mots-clés/i)).not.toBeInTheDocument()
  })

  it('affiche la barre Analyse IA', () => {
    render(<Sidebar />, { wrapper: Wrapper })
    expect(screen.getByText(/analyse ia/i)).toBeInTheDocument()
  })
})
```

> **Note :** Le `vi.mock` en haut du fichier remplace le mock partiel existant. Si le fichier contient déjà un `vi.mock('../hooks/useTenders', ...)`, fusionner les deux objets de retour.

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
cd frontend
npm test -- --run Sidebar
```

Attendu : les nouveaux tests FAILED ("+8 nouvelles offres" absent, barres Collecte/Mots-clés présentes)

- [ ] **Step 3 : Modifier la section `showResults` dans `frontend/src/components/Sidebar.jsx`**

Remplacer le bloc `{showResults && (...)}` existant (lignes ~216-261) par :

```jsx
{showResults && (
  <div className="space-y-2">
    <p className="text-sm font-semibold text-ocean-cyan font-mono">
      +{totalNew} nouvelles offres
    </p>

    <div className="space-y-0.5">
      {results.map((r) => (
        <div key={r.source} className="flex items-center gap-1.5 text-[10px] font-mono">
          <span className={
            r.status === 'ok' ? 'text-ocean-teal flex-shrink-0' :
            r.error === 'CREDENTIALS_MISSING' ? 'text-ocean-gold flex-shrink-0' :
            'text-ocean-coral flex-shrink-0'
          }>
            {r.status === 'ok' ? '✓' : r.error === 'CREDENTIALS_MISSING' ? '🔒' : '✗'}
          </span>
          <span className="text-ocean-muted truncate flex-1 min-w-0">{r.source}</span>
          {r.status === 'ok' && (
            <span className="text-ocean-muted/60 flex-shrink-0">+{r.nb_new}</span>
          )}
        </div>
      ))}
    </div>

    <div className="pt-1.5 border-t border-ocean-border">
      <StepBar
        label="Analyse IA"
        value={aiAnalyzed}
        total={totalNew}
        color={aiPending > 0 ? 'amber' : 'green'}
      />
    </div>

    {aiPending > 0 && !analyzeTriggered && (
      <button
        onClick={handleAnalyze}
        disabled={analyzing}
        className="w-full py-1 bg-ocean-gold/10 border border-ocean-gold/20 text-ocean-gold text-[10px] rounded hover:bg-ocean-gold/15 disabled:opacity-50 transition-colors"
      >
        {analyzing ? 'Analyse IA en cours…' : `Analyser les ${aiPending} restants`}
      </button>
    )}

    {analyzeTriggered && (
      <p className="text-[10px] text-ocean-muted font-mono">✓ Analyse IA lancée en arrière-plan</p>
    )}
  </div>
)}
```

- [ ] **Step 4 : Vérifier que tous les tests Sidebar passent**

```bash
cd frontend
npm test -- --run Sidebar
```

Attendu : tous PASSED

- [ ] **Step 5 : Commit**

```bash
git add frontend/src/components/Sidebar.jsx frontend/src/components/Sidebar.test.jsx
git commit -m "fix(sidebar): supprimer barres fausses, afficher total nouvelles offres"
```

---

## Task 5 : Vérification finale — tous les tests

- [ ] **Step 1 : Lancer la suite complète frontend**

```bash
cd frontend
npm test -- --run
```

Attendu : tous les tests PASSED, aucune régression

- [ ] **Step 2 : Lancer la suite backend**

```bash
cd backend
python -m pytest test_main.py -v
```

Attendu : tous PASSED

- [ ] **Step 3 : Vérification manuelle (si serveur disponible)**

Démarrer l'app (`start.ps1` ou `start.bat`), lancer une collecte depuis la Sidebar, vérifier :
- La card "Nouvelles 24h" dans le Dashboard affiche un nombre > 0
- Les KPIs du Dashboard se rafraîchissent après la collecte (total, à qualifier changent si de nouveaux tenders ont été insérés)
- Dans la Sidebar post-collecte : "+N nouvelles offres" en bleu, pas de barres "Collecte" ni "Mots-clés", barre "Analyse IA" toujours présente
