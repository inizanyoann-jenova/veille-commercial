# Design : Dashboard principal — KpiGrid + TendersTable

**Date :** 2026-05-21
**Statut :** Approuvé

---

## Contexte

La page principale (`/`) affiche actuellement un placeholder `Pipeline.jsx`. L'objectif est de la remplacer par un tableau de bord fonctionnel avec des KPIs et une liste de marchés filtrable.

Stack : React 18, Vite, TailwindCSS, React Query (`@tanstack/react-query`), React Router v6.

---

## Architecture

```
src/
  pages/
    Dashboard.jsx          ← page principale (index route "/")
  components/
    KpiGrid.jsx            ← grille de 5 cartes KPI
    TendersTable.jsx       ← tableau marchés + filtres intégrés
```

`Pipeline.jsx` est conservé mais vide — `App.jsx` est mis à jour pour importer `Dashboard` à l'index route.

---

## Dashboard.jsx

Responsabilité unique : orchestrer l'état des filtres et composer les deux sous-composants.

**State local :**
- `status` : string, défaut `"Tous"` — valeurs possibles : `"Tous" | "À qualifier" | "En cours" | "Soumis" | "Gagné" | "Perdu"`
- `secteur` : string, défaut `"Public"` — valeurs : `"Public" | "Privé" | "International"`
- `searchText` : string, défaut `""`

**Rendu :**
```jsx
<div className="p-5 space-y-5">
  <KpiGrid />
  <TendersTable
    status={status} secteur={secteur} searchText={searchText}
    onStatusChange={setStatus}
    onSecteurChange={setSecteur}
    onSearchChange={setSearchText}
  />
</div>
```

---

## KpiGrid.jsx

**Données :** `useKpisPublic()` → `{ total, a_qualifier, en_cours, soumis, gagnes }`

**Rendu :** grille de 5 cartes (`grid-cols-2 md:grid-cols-5`), chacune avec :
- Icône + label
- Compteur en gros
- Couleur de fond distincte

| Carte | Label | Couleur Tailwind |
|---|---|---|
| total | Total marchés | `bg-blue-50 border-blue-200 text-blue-700` |
| a_qualifier | À qualifier | `bg-slate-50 border-slate-200 text-slate-700` |
| en_cours | En cours | `bg-indigo-50 border-indigo-200 text-indigo-700` |
| soumis | Soumis | `bg-amber-50 border-amber-200 text-amber-700` |
| gagnes | Gagnés | `bg-green-50 border-green-200 text-green-700` |

États loading/error : skeleton gris animé (`animate-pulse`) / message d'erreur simple.

---

## TendersTable.jsx

**Props :**
```ts
{
  status: string, secteur: string, searchText: string,
  onStatusChange: (s: string) => void,
  onSecteurChange: (s: string) => void,
  onSearchChange: (s: string) => void,
}
```

**Données :** `useTenders({ status, secteur })` — les params status/secteur sont envoyés au backend (filtre serveur). `searchText` est appliqué côté client sur `title + domaine + territoire`.

**Filtre client (recherche textuelle) :**
```js
const filtered = tenders.filter(t =>
  `${t.title} ${t.domaine} ${t.territoire}`.toLowerCase()
    .includes(searchText.toLowerCase())
)
```

**Barre de filtres (en-tête du composant) :**
- Sélect `Statut` : Tous / À qualifier / En cours / Soumis / Gagné / Perdu
- Sélect `Secteur` : Public / Privé / International
- Input texte `Recherche` (placeholder "Rechercher un marché…")

**Colonnes du tableau :**

| # | Colonne | Source champ |
|---|---|---|
| 1 | Titre | `title` |
| 2 | Domaine | `domaine` |
| 3 | Territoire | `territoire` |
| 4 | Deadline | `deadline` (format DD/MM/YYYY, `—` si null) |
| 5 | Score | `relevance_score` (barre de progression + chiffre) |
| 6 | GO/NO-GO | `gonogo` → badge coloré |
| 7 | Statut | `status` |
| 8 | Source | `source` |

**Badges GO/NO-GO :**
- `"GO"` → `🟢` fond `bg-green-100 text-green-800`
- `"Étudier"` → `🟡` fond `bg-yellow-100 text-yellow-800`
- `"Passer"` → `🔴` fond `bg-red-100 text-red-800`

**État vide :** message "Aucun marché trouvé" centré.
**État loading :** 5 lignes skeleton animées.
**État error :** message d'erreur rouge.

---

## Mise à jour App.jsx

```jsx
import Dashboard from './pages/Dashboard'
// ...
<Route index element={<Dashboard />} />
```

---

## Ce qui n'est PAS dans ce scope

- Pagination (les données tiennent en mémoire, tri côté client suffit pour l'instant)
- Tri de colonnes (feature future)
- Détail d'un marché (page séparée à implémenter plus tard)
- Filtres avancés (date, territoire, domaine) — hors scope
