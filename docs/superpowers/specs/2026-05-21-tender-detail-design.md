# Spec — TenderDetail : fiche marché React (slide-over)

**Date :** 2026-05-21  
**Remplace :** logique Streamlit `_render_fiche` (app.py:1856)  
**Approche retenue :** B — composant principal + sous-sections inline

---

## Contexte

L'ancienne fiche marché est rendue côté Streamlit via `_render_fiche` et ses cinq sous-fonctions. L'objectif est de reproduire ce rendu dans le frontend React sous forme d'un panneau latéral (slide-over) qui s'ouvre quand l'utilisateur clique sur une ligne du tableau.

---

## Fichiers touchés

| Fichier | Nature de la modification |
|---|---|
| `backend/main.py` | Enrichir `_tender_to_dict` : ajouter `jours_restants` + `fiche_data` |
| `frontend/src/components/TenderDetail.jsx` | Nouveau composant (créer) |
| `frontend/src/components/TendersTable.jsx` | Ajouter prop `onRowClick(id)` + `onClick` sur `<tr>` |
| `frontend/src/pages/Dashboard.jsx` | Ajouter `selectedId` state + rendre `TenderDetail` |

Aucun nouveau hook, aucune nouvelle route API, aucun nouveau fichier CSS.

---

## Backend — enrichissement de `_tender_to_dict`

**Import à ajouter dans `backend/main.py` :**
```python
from fiche_logic import _compute_fiche_data
```

**Champs à ajouter dans le dict retourné :**
```python
jours_restants = (t.deadline - datetime.utcnow()).days if t.deadline else None
fiche_data = _compute_fiche_data(
    score, jours_restants,
    _detect_domaine(t.title or "", t.description or ""),
    _detect_territoire(t.title or "", t.description or ""),
    bool(t.is_maintenance), t.title or "", a
)
# dans le return :
"jours_restants": jours_restants,
"fiche_data": fiche_data,
```

**Structure de `fiche_data` :**
```json
{
  "sm": 45, "sg": 30, "sk": 6, "smaint": 10,
  "label_action": "🟢 Traiter en priorité",
  "steps": ["Affecter un chargé d'affaires...", "..."],
  "atouts": ["✅ Cœur de métier — SSI/CMSI...", "..."],
  "risques": ["⚠️ Concurrents nommés : ..."]
}
```

---

## Composant `TenderDetail.jsx`

### Props

```jsx
TenderDetail({ tenderId, onClose })
// tenderId : string|null — null = panneau fermé
// onClose  : () => void
```

### Layout (slide-over)

- `fixed inset-0 z-40` — overlay semi-transparent (`bg-black/40`)
- `fixed right-0 top-0 bottom-0 w-[480px] z-50 bg-white overflow-y-auto shadow-xl`
- Fermeture : clic overlay, bouton `[×]`, touche `Escape` (useEffect)
- Si `!tenderId` : `return null`

### Sections

#### 1. `TenderDetailHeader` (toujours visible)

- Badge GO/NO-GO : vert (`bg-green-100 text-green-800`) / jaune (`bg-yellow-100`) / rouge (`bg-red-100`)
- Titre (2 lignes max, `line-clamp-2`)
- Ligne métriques : Score · Deadline (`jours_restants` J) · Montant (€) · Secteur · Source

#### 2. `TenderDetailActionPlan`

- Titre : `fiche_data.label_action`
- Liste `<ol>` des `fiche_data.steps`
- Alertes `fiche_data.risques` (fond `bg-orange-50 border-orange-200`)
- Puces `fiche_data.atouts` (fond `bg-green-50`)

#### 3. `TenderDetailTechnical` (accordéon, fermé par défaut)

- Toggle `isTechnicalOpen` (useState local)
- 4 barres de progression Tailwind :
  - Pertinence métier `sm/45`
  - Proximité géographique `sg/30`
  - Mots-clés titre `sk/15`
  - Maintenance/Récurrence `smaint/10`
- Contexte : type_marche · territoire · domaine · concurrents
- Description brute (si présente)

#### 4. `TenderDetailAI` (rendu uniquement si `llm_structured` présent)

- Grille 2 colonnes : budget_estime · type_travaux · acheteur_type · niveau_concurrence · score_confiance · recommandation (badge ✅ GO / 🔴 NON)
- Lots (si présents)
- Justification (caption)

#### 5. `TenderDetailActions`

- `<select>` statuts : À qualifier / En cours / Soumis / Gagné / Perdu → `useUpdateStatus`
- Bouton étoile : `⭐` / `★` toggle → `useUpdateSaved`
- Boutons `disabled` pendant `mutation.isPending`

### États de chargement

- `isLoading` → 3 blocs skeleton animés (`animate-pulse`)
- `isError` → message `"Impossible de charger ce marché."`

---

## Modifications connexes

### `TendersTable.jsx`

Ajouter prop `onRowClick` :
```jsx
// dans les props
onRowClick,     // (id: string) => void

// sur chaque <tr>
onClick={() => onRowClick?.(t.id)}
className="... cursor-pointer"
```

### `Dashboard.jsx`

```jsx
const [selectedId, setSelectedId] = useState(null)

<TendersTable ... onRowClick={setSelectedId} />
<TenderDetail tenderId={selectedId} onClose={() => setSelectedId(null)} />
```

---

## Ce qui n'est PAS inclus dans cette spec

- Bouton "Ré-analyser LLM structuré" (nécessite `analyzeTender` — hors scope)
- Historique marchés similaires (`get_acheteur_history` — hors scope)
- Notes et tags éditables (hors scope)
- Tests unitaires du composant (phase suivante)
