# Urgences Enrichies — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrichir les cartes urgences avec la description/résumé LLM, le secteur, le montant et le lien vers l'annonce, en corrigeant le bug de nommage dans `load_urgences`.

**Architecture:** 4 fichiers modifiés : `models.py` (ajout colonne `url`), `database.py` (migration + fix `load_urgences`), `tests/test_urgences_pipeline.py` (mise à jour tests), `frontend/src/components/UrgenceCard.jsx` + `UrgenceCard.test.jsx` (enrichissement carte), `frontend/src/pages/Urgences.jsx` (passage des nouveaux props).

**Tech Stack:** Python/SQLAlchemy (backend), React 19 + Tailwind (frontend), pytest (tests Python), Vitest + Testing Library (tests frontend).

---

## File Map

| Fichier | Action | Rôle |
|---|---|---|
| `models.py` | Modify | Ajouter `url = Column(String, nullable=True)` à `Tender` |
| `database.py` | Modify | Migration `url` + fix `load_urgences` (noms + nouveaux champs) |
| `tests/test_urgences_pipeline.py` | Modify | Mettre à jour assertions pour les nouveaux noms de clés |
| `frontend/src/components/UrgenceCard.jsx` | Modify | Carte enrichie avec description, secteur, montant, lien |
| `frontend/src/components/UrgenceCard.test.jsx` | Modify | Tests pour les nouveaux comportements |
| `frontend/src/pages/Urgences.jsx` | Modify | Passer les nouveaux props à `UrgenceCard` |

---

## Task 1 — Ajout colonne `url` dans `Tender` + migration

**Files:**
- Modify: `models.py:29` (après `adaptive_score`)
- Modify: `database.py:21-33` (liste `_MIGRATIONS`)

- [ ] **Step 1 : Ajouter `url` dans `models.py`**

Dans `models.py`, après la ligne `adaptive_score = Column(Integer, default=None)`, ajouter :

```python
url = Column(String, nullable=True)
```

Le bloc `Tender` doit ressembler à :
```python
class Tender(Base):
    __tablename__ = "tenders"
    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String)
    source = Column(String)
    publication_date = Column(DateTime)
    date_extraction = Column(DateTime)
    deadline = Column(DateTime)
    status = Column(String, default="À qualifier")
    relevance_score = Column(Integer, default=0)
    is_maintenance = Column(Boolean, default=False)
    llm_analysis = Column(JSON)
    secteur = Column(String, default=None)
    type_opportunite = Column(String, default="Marché Public")
    amount = Column(Integer, default=None)
    is_blacklisted = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False)
    notes = Column(String, default=None)
    tags = Column(JSON, default=list)
    llm_structured = Column(JSON, default=None)
    adaptive_score = Column(Integer, default=None)
    url = Column(String, nullable=True)   # ← ajout
```

- [ ] **Step 2 : Ajouter la migration dans `database.py`**

Dans `database.py`, dans la liste `_MIGRATIONS`, ajouter en dernière position :

```python
_MIGRATIONS: list[tuple[str, str, str]] = [
    ("tenders", "date_extraction", "DATETIME DEFAULT NULL"),
    ("tenders", "secteur", "VARCHAR"),
    ("tenders", "type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
    ("tenders", "amount", "INTEGER"),
    ("tenders", "is_blacklisted", "BOOLEAN DEFAULT 0"),
    ("tenders", "is_saved", "BOOLEAN DEFAULT 0"),
    ("tenders", "notes", "TEXT"),
    ("tenders", "tags", "JSON DEFAULT '[]'"),
    ("sources", "is_validated", "BOOLEAN DEFAULT 0"),
    ("sources", "ping_failures_count", "INTEGER DEFAULT 0"),
    ("sources", "last_ping_at", "DATETIME DEFAULT NULL"),
    ("tenders", "url", "VARCHAR DEFAULT NULL"),   # ← ajout
]
```

- [ ] **Step 3 : Vérifier que les tests Python existants passent encore**

```powershell
pytest tests/test_urgences_pipeline.py -v
```

Résultat attendu : tous les tests passent (la migration est idempotente — si la colonne existe déjà, `OperationalError` est silencieusement ignorée).

- [ ] **Step 4 : Commit**

```powershell
git add models.py database.py
git commit -m "feat(db): add url column to Tender + migration"
```

---

## Task 2 — Fix `load_urgences` : nommage + nouveaux champs

**Files:**
- Modify: `database.py:277-306` (fonction `load_urgences`)
- Modify: `tests/test_urgences_pipeline.py` (mise à jour assertions)

- [ ] **Step 1 : Écrire les tests d'abord (TDD)**

Dans `tests/test_urgences_pipeline.py`, mettre à jour le test existant qui vérifie les clés retournées, et ajouter les nouveaux tests :

Remplacer le test `test_urgences_returns_go_with_deadline_in_range` (ligne 60-69) par :

```python
def test_urgences_returns_go_with_deadline_in_range(db):
    from database import load_urgences

    _add_tender(db, "u1", "SSI CHU Mayotte", score=80, deadline_offset_days=5)

    result = load_urgences(db)

    assert len(result) == 1
    assert result[0]["id"] == "u1"
    assert result[0]["jours_restants"] == 5   # fix: était "jours"
```

Ajouter après `test_urgences_sorted_by_deadline_asc` :

```python
def test_urgences_returns_required_fields(db):
    from database import load_urgences
    from models import Tender

    midnight = _today_midnight()
    t = Tender(
        id="u_fields",
        title="SSI Mairie",
        source="BOAMP",
        relevance_score=75,
        deadline=midnight + timedelta(days=10),
        status="À qualifier",
        is_blacklisted=False,
        description="Installation système SSI",
        secteur="Public",
        amount=45000,
        url="https://www.boamp.fr/aides-a-la-recherche/detail/12345",
        llm_analysis={"resume": "Marché SSI pour une mairie"},
    )
    db.add(t)
    db.commit()

    result = load_urgences(db)
    item = next(r for r in result if r["id"] == "u_fields")

    assert item["relevance_score"] == 75
    assert item["jours_restants"] == 10
    assert item["source"] == "BOAMP"
    assert item["url"] == "https://www.boamp.fr/aides-a-la-recherche/detail/12345"
    assert item["description"] == "Installation système SSI"
    assert item["secteur"] == "Public"
    assert item["amount"] == 45000
    assert item["llm_resume"] == "Marché SSI pour une mairie"


def test_urgences_description_truncated_at_300_chars(db):
    from database import load_urgences
    from models import Tender

    midnight = _today_midnight()
    long_desc = "A" * 400
    t = Tender(
        id="u_trunc",
        title="SSI Long",
        source="TEST",
        relevance_score=75,
        deadline=midnight + timedelta(days=5),
        status="À qualifier",
        is_blacklisted=False,
        description=long_desc,
    )
    db.add(t)
    db.commit()

    result = load_urgences(db)
    item = next(r for r in result if r["id"] == "u_trunc")

    assert len(item["description"]) == 300


def test_urgences_llm_resume_none_when_no_analysis(db):
    from database import load_urgences

    _add_tender(db, "u_no_llm", "CMSI Hôpital", score=75, deadline_offset_days=5)

    result = load_urgences(db)
    item = next(r for r in result if r["id"] == "u_no_llm")

    assert item["llm_resume"] is None
    assert item["url"] is None
```

- [ ] **Step 2 : Vérifier que les nouveaux tests échouent (TDD)**

```powershell
pytest tests/test_urgences_pipeline.py -v
```

Résultat attendu : `test_urgences_returns_go_with_deadline_in_range` FAIL (`KeyError: 'jours_restants'`), les nouveaux tests FAIL également.

- [ ] **Step 3 : Implémenter le fix dans `load_urgences`**

Dans `database.py`, remplacer le bloc `return [...]` de `load_urgences` (lignes 298-306) par :

```python
    return [
        {
            "id": t.id,
            "title": t.title,
            "relevance_score": t.relevance_score,
            "jours_restants": (t.deadline.replace(tzinfo=None) - today).days,
            "source": t.source,
            "url": t.url,
            "description": (t.description or "")[:300] if t.description else None,
            "secteur": t.secteur,
            "amount": t.amount,
            "llm_resume": (t.llm_analysis or {}).get("resume") if t.llm_analysis else None,
        }
        for t in rows
    ]
```

- [ ] **Step 4 : Vérifier que tous les tests passent**

```powershell
pytest tests/test_urgences_pipeline.py -v
```

Résultat attendu : tous les tests PASS.

- [ ] **Step 5 : Commit**

```powershell
git add database.py tests/test_urgences_pipeline.py
git commit -m "fix(api): load_urgences returns jours_restants, relevance_score + enriched fields"
```

---

## Task 3 — Enrichir `UrgenceCard.jsx` + mise à jour des tests

**Files:**
- Modify: `frontend/src/components/UrgenceCard.jsx`
- Modify: `frontend/src/components/UrgenceCard.test.jsx`

- [ ] **Step 1 : Écrire les tests enrichis**

Remplacer l'intégralité de `frontend/src/components/UrgenceCard.test.jsx` par :

```jsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import UrgenceCard from './UrgenceCard'

const baseProps = {
  title: 'SSI CHU Mayotte',
  jours_restants: 5,
  score: 80,
  source: 'BOAMP',
}

describe('UrgenceCard — base', () => {
  it('affiche le titre', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('SSI CHU Mayotte')).toBeInTheDocument()
  })

  it('affiche J-5', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('J-5')).toBeInTheDocument()
  })

  it('affiche le score', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('80')).toBeInTheDocument()
  })

  it('affiche la source', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.getByText('BOAMP')).toBeInTheDocument()
  })
})

describe('UrgenceCard — lien annonce', () => {
  it('affiche le lien si url présente', () => {
    render(<UrgenceCard {...baseProps} url="https://www.boamp.fr/detail/123" />)
    const link = screen.getByRole('link', { name: /annonce/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', 'https://www.boamp.fr/detail/123')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('n\'affiche pas de lien si url absente', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.queryByRole('link', { name: /annonce/i })).not.toBeInTheDocument()
  })
})

describe('UrgenceCard — contenu texte', () => {
  it('affiche le résumé LLM si disponible', () => {
    render(<UrgenceCard {...baseProps} llm_resume="Résumé IA du marché" />)
    expect(screen.getByText('Résumé IA du marché')).toBeInTheDocument()
  })

  it('affiche la description en fallback si pas de llm_resume', () => {
    render(<UrgenceCard {...baseProps} description="Description du marché" />)
    expect(screen.getByText('Description du marché')).toBeInTheDocument()
  })

  it('n\'affiche pas de bloc texte si ni llm_resume ni description', () => {
    const { container } = render(<UrgenceCard {...baseProps} />)
    expect(container.querySelector('[data-testid="card-content"]')).not.toBeInTheDocument()
  })
})

describe('UrgenceCard — secteur', () => {
  it('affiche le badge secteur si présent', () => {
    render(<UrgenceCard {...baseProps} secteur="SSI" />)
    expect(screen.getByText('SSI')).toBeInTheDocument()
  })

  it('n\'affiche pas de badge secteur si absent', () => {
    render(<UrgenceCard {...baseProps} />)
    expect(screen.queryByTestId('secteur-badge')).not.toBeInTheDocument()
  })
})

describe('UrgenceCard — montant', () => {
  it('affiche le montant formaté si présent', () => {
    render(<UrgenceCard {...baseProps} amount={45000} />)
    expect(screen.getByText(/45/)).toBeInTheDocument()
  })

  it('n\'affiche pas de montant si absent', () => {
    const { container } = render(<UrgenceCard {...baseProps} />)
    expect(container.querySelector('[data-testid="amount"]')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2 : Vérifier que les nouveaux tests échouent**

```powershell
cd frontend && npm test -- UrgenceCard
```

Résultat attendu : plusieurs FAIL (lien annonce, contenu texte, secteur, montant).

- [ ] **Step 3 : Implémenter la carte enrichie**

Remplacer l'intégralité de `frontend/src/components/UrgenceCard.jsx` par :

```jsx
function urgenceStyle(jours) {
  if (jours < 7) return { accent: 'border-l-2 border-ocean-coral', badge: 'bg-ocean-coral/10 text-ocean-coral', emoji: '🔴' }
  if (jours <= 15) return { accent: 'border-l-2 border-ocean-gold', badge: 'bg-ocean-gold/10 text-ocean-gold', emoji: '🟡' }
  return { accent: 'border-l-2 border-ocean-teal', badge: 'bg-ocean-teal/10 text-ocean-teal', emoji: '🟢' }
}

const EUR = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
})

export default function UrgenceCard({
  title,
  jours_restants,
  score,
  source,
  url,
  description,
  secteur,
  amount,
  llm_resume,
}) {
  const style = urgenceStyle(jours_restants)
  const contenu = llm_resume ?? description

  return (
    <div className={`bg-ocean-panel border border-ocean-border rounded-xl p-4 flex flex-col gap-3 ${style.accent}`}>
      {/* Ligne 1 : badge J-X + score + lien annonce */}
      <div className="flex items-center justify-between gap-2">
        <span className={`font-mono text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 ${style.badge}`}>
          <span>{style.emoji}</span> <span>J-{jours_restants}</span>
        </span>
        <div className="flex items-center gap-2 ml-auto">
          <span className="font-mono text-xs bg-ocean-cyan/8 text-ocean-cyan font-semibold rounded px-1.5 py-0.5">
            {score}
          </span>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-ocean-muted hover:text-ocean-cyan underline underline-offset-2"
              aria-label="Voir l'annonce"
            >
              Annonce
            </a>
          )}
        </div>
      </div>

      {/* Ligne 2 : titre */}
      <p className="font-sans text-sm font-semibold text-ocean-text line-clamp-2">{title}</p>

      {/* Ligne 3 : résumé LLM ou description */}
      {contenu && (
        <p
          className="font-sans text-xs italic text-ocean-muted line-clamp-3"
          data-testid="card-content"
        >
          {contenu}
        </p>
      )}

      {/* Ligne 4 : secteur + montant */}
      {(secteur || amount != null) && (
        <div className="flex items-center gap-2 flex-wrap">
          {secteur && (
            <span
              className="font-mono text-xs bg-ocean-cyan/10 text-ocean-cyan rounded px-1.5 py-0.5"
              data-testid="secteur-badge"
            >
              {secteur}
            </span>
          )}
          {amount != null && (
            <span className="font-mono text-xs text-ocean-muted" data-testid="amount">
              💰 {EUR.format(amount)}
            </span>
          )}
        </div>
      )}

      {/* Ligne 5 : source */}
      <p className="font-mono text-xs text-ocean-muted">{source}</p>
    </div>
  )
}
```

- [ ] **Step 4 : Vérifier que tous les tests passent**

```powershell
cd frontend && npm test -- UrgenceCard
```

Résultat attendu : tous les tests PASS.

- [ ] **Step 5 : Commit**

```powershell
git add frontend/src/components/UrgenceCard.jsx frontend/src/components/UrgenceCard.test.jsx
git commit -m "feat(ui): UrgenceCard enrichie — description, LLM, secteur, montant, lien annonce"
```

---

## Task 4 — Mettre à jour `Urgences.jsx`

**Files:**
- Modify: `frontend/src/pages/Urgences.jsx`

- [ ] **Step 1 : Mettre à jour le passage des props**

Dans `frontend/src/pages/Urgences.jsx`, remplacer le bloc `return` intérieur du map par :

```jsx
{urgences.map((u) => {
  const jours = u.jours_restants ?? Math.ceil((new Date(u.deadline) - new Date()) / 86400000)
  return (
    <UrgenceCard
      key={u.id}
      title={u.title}
      jours_restants={jours}
      score={u.relevance_score}
      source={u.source}
      url={u.url}
      description={u.description}
      secteur={u.secteur}
      amount={u.amount}
      llm_resume={u.llm_resume}
    />
  )
})}
```

- [ ] **Step 2 : Lancer la suite de tests complète frontend**

```powershell
cd frontend && npm test
```

Résultat attendu : tous les tests PASS (0 failed).

- [ ] **Step 3 : Lancer la suite de tests Python complète**

```powershell
pytest -x
```

Résultat attendu : tous les tests PASS.

- [ ] **Step 4 : Commit**

```powershell
git add frontend/src/pages/Urgences.jsx
git commit -m "fix(ui): Urgences.jsx passe les nouveaux props enrichis à UrgenceCard"
```

---

## Self-Review

**Spec coverage :**

| Exigence spec | Tâche |
|---|---|
| Ajout colonne `url` dans Tender | Task 1 |
| Migration DB | Task 1 |
| Fix nommage `jours_restants` / `relevance_score` | Task 2 |
| `source` retourné par `load_urgences` | Task 2 |
| `description` (tronqué 300 chars) | Task 2 |
| `secteur`, `amount`, `llm_resume` | Task 2 |
| Lien annonce conditionnel | Task 3 |
| Affichage résumé LLM (fallback description) | Task 3 |
| Badge secteur | Task 3 |
| Montant formaté | Task 3 |
| `Urgences.jsx` — nouveaux props | Task 4 |
| Tests backend mis à jour | Task 2 |
| Tests frontend mis à jour | Task 3 |

**Placeholder scan :** aucun TBD/TODO. Tous les steps ont du code complet.

**Type consistency :**
- `jours_restants` : cohérent entre `load_urgences` (Task 2), `UrgenceCard` props (Task 3), `Urgences.jsx` (Task 4)
- `relevance_score` : cohérent entre `load_urgences` (Task 2) et `score={u.relevance_score}` (Task 4) → passé en `score` à `UrgenceCard` (Task 3 : prop `score`)
- `llm_resume` : cohérent partout
- `data-testid="card-content"` : défini dans Task 3 step 3, référencé dans Task 3 step 1 ✓
- `data-testid="secteur-badge"` et `data-testid="amount"` : idem ✓
