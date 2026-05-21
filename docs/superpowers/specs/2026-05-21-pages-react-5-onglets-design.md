# Design — Implémentation des 5 pages React

**Date :** 2026-05-21
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** Pages Analytics, Direction, Urgences, Paramètres, Guide — toutes actuellement vides

---

## Contexte

Le frontend React a été scaffoldé avec un Dashboard Pipeline fonctionnel. Les 5 autres pages du routeur (`/analytics`, `/direction`, `/urgences`, `/parametres`, `/guide`) affichent un placeholder. Le backend expose toutes les APIs nécessaires. Ce spec couvre l'implémentation complète de ces 5 pages.

---

## Architecture

**Approche choisie :** Pages + sous-composants extraits (B)

Les pages sont de minces orchestrateurs. Les blocs complexes deviennent des composants dans `components/`.

### Nouveaux fichiers

```
frontend/src/
  pages/
    Analytics.jsx        ← recharts + hooks existants
    Direction.jsx        ← kanban, mutations status
    Urgences.jsx         ← cartes urgences
    Parametres.jsx       ← 4 sections admin
    Guide.jsx            ← contenu statique

  components/
    KanbanColumn.jsx     ← colonne kanban réutilisable
    UrgenceCard.jsx      ← carte urgence colorée
    ScraperRunsTable.jsx ← historique runs scrapers
    DuplicatePair.jsx    ← paire de doublons à résoudre
```

### Dépendance ajoutée

`recharts` — librairie React native, composants déclaratifs, compatible Tailwind.

```bash
npm install recharts
```

---

## Page Analytics (`/analytics`)

### Sources de données

| Hook | Endpoint | Usage |
|---|---|---|
| `useChartData()` | `GET /api/chart-data` | Données brutes pour graphiques |
| `useKpisCa()` | `GET /api/kpis/ca` | CA pipeline (en_cours, soumis, gagne) |
| `useKpisPriv()` | `GET /api/kpis/priv` | Signaux privés (permis, presse, etc.) |

Tous ces hooks existent déjà dans `useTenders.js`.

### Layout

**Section 1 — KPIs globaux (4 cartes)**

Calculés depuis les données `chart-data` :
- Total collecté : `data.length`
- Taux GO : `(data.filter(score >= 65).length / total * 100)%`
- CA gagné : depuis `kpisCa.gagne` (formaté en k€)
- Sources distinctes : `new Set(data.map(d => d.source)).size` — retiré, utiliser `useKpisPublic` déjà disponible

Mise en page : grille 4 colonnes identique à `KpiGrid`.

**Section 2 — 3 graphiques Recharts (colonnes égales)**

1. **Barres verticales — Publications par semaine**
   - Données : agréger `publication_date` par semaine ISO, 30 dernières semaines
   - Composant : `BarChart` Recharts
   - Couleur : `#e94560` (rouge DEF, déjà dans Tailwind config)
   - Axe X : label semaine (ex. `S18 2026`), axe Y : nombre de marchés

2. **Donut — Répartition par territoire**
   - Données : compter `territoire` dans les données chart-data
   - Grouper : La Réunion, Mayotte, Madagascar, Maurice, Comores, Autres
   - Composant : `PieChart` avec `innerRadius` (donut)

3. **Barres horizontales — Répartition par domaine**
   - Données : compter `domaine` dans les données chart-data
   - Labels : SSI, CMSI, Vidéo, Courants faibles, Autre
   - Composant : `BarChart` avec `layout="vertical"`
   - Trié par count décroissant

**Section 3 — Top 5 sources par volume**

Tableau simple (pas de composant dédié) : `source` | `Marchés`.
Calculé depuis `chart-data` en agrégeant par `source`, trié décroissant, limité à 5.

### États de chargement / erreur

- Skeleton rectangulaire pendant le chargement (animate-pulse)
- Message d'erreur rouge si `isError`

---

## Page Direction (`/direction`)

### Source de données

| Hook | Endpoint | Usage |
|---|---|---|
| `usePipeline()` | `GET /api/pipeline` | Marchés groupés par statut |
| `useUpdateStatus()` | `POST /api/tenders/{id}/status` | Transition de statut |

### Composant `KanbanColumn`

Props : `title: string`, `items: TenderCard[]`, `color: string`, `onStatusChange: (id, status) => void`

Chaque item affiché contient :
- Titre tronqué à 60 caractères
- Score de pertinence (badge)
- Jours restants avant deadline, coloré :
  - Rouge `text-red-600` si < 7 jours
  - Orange `text-orange-500` si 7–30 jours
  - Gris `text-gray-400` si deadline absente

Boutons de transition inline sur la carte :
- Colonne GO → bouton `[Marquer Soumis]`
- Colonne Soumis → boutons `[Gagné 🏆]` `[Perdu]`
- Colonne Résultats → lecture seule

### Layout de Direction

Header avec titre + sous-titre. Grille 3 colonnes :

| Colonne | Critère | Couleur |
|---|---|---|
| ✅ GO | score ≥ 65, statut hors Soumis/Gagné/Perdu | Vert |
| 📤 Soumis | statut == "Soumis" | Bleu |
| 🏆 Résultats | statut Gagné ou Perdu (sous-groupés) | Ambré |

Après `onStatusChange` : invalider les queries `['pipeline']` et `['tenders']` via `queryClient`.

---

## Page Urgences (`/urgences`)

### Source de données

`useUrgences()` → `GET /api/urgences` (hook déjà existant, retourne les marchés GO avec deadline ≤ 30j)

### Composant `UrgenceCard`

Props : `tender: { id, title, jours_restants, relevance_score, source }`

Affiche :
- Badge coloré + jours restants (texte ex. `J-5`)
  - 🔴 rouge si `jours_restants < 7`
  - 🟡 orange si `7 ≤ jours_restants ≤ 15`
  - 🟢 vert si `15 < jours_restants ≤ 30`
- Titre (2 lignes max, ellipsis)
- Score + source en bas de carte

### Layout de Urgences

- Titre de page + compteur ("X marchés à traiter")
- Grille responsive : 1 col mobile, 2 col md, 3 col lg, 4 col xl
- Message vide stylisé si aucune urgence : "Aucun marché urgent pour le moment ✅"
- Skeleton pendant chargement (4 cartes fantômes)

---

## Page Paramètres (`/parametres`)

4 sections séparées par des titres et des dividers.

### Section 1 — Collecte des sources

**Données** : `useSources()` → `GET /api/sources`, `useCollectMutation()` → `POST /api/collect`

- Liste des sources avec checkboxes (filtre par `enabled == true`)
- Bouton "Lancer la collecte" → envoie `{ source_names: [sélectionnées] }` ou `null` pour toutes
- Résultats affichés après collecte : par source, statut ok/erreur, nb_new

**Composant `ScraperRunsTable`** (affiché sous les résultats) :
- Props : `runs[]` depuis `useScraperRuns()`
- Colonnes : Source | Démarré | Durée | Trouvés | Nouveaux | Statut
- Statut coloré : `ok` → vert, `error` → rouge, `running` → bleu animé
- Limité aux 20 derniers runs, auto-refresh toutes les 30s (déjà dans le hook)

### Section 2 — Analyse LLM

**Données** : `useAnalyzePending()` mutation → `POST /api/analyze-pending`

- Bouton "Analyser les marchés en attente"
- Affichage du résultat : "X marchés analysés"
- État loading sur le bouton pendant l'opération

### Section 3 — Doublons

**Données** : `detectDuplicates()` → `POST /api/detect-duplicates`, `GET /api/duplicates`

**Composant `DuplicatePair`** :
- Props : `pair: { id, similarity_score, tender_a, tender_b }`, `onResolve: (id, action) => void`
- Deux cartes côte à côte : titre, score, source, deadline
- Le tender avec le score le plus élevé a un fond coloré (recommandé à conserver)
- Boutons : `[Garder A — archiver B]` `[Garder B — archiver A]` `[Ignorer]`
- Actions : appel `DELETE /api/tenders/{id}` pour l'archivé + refresh

### Section 4 — Maintenance

- Bouton "Archiver les marchés > 30 jours" → `POST /api/admin/archive-old`
- Bouton "Réinitialiser la base de données" → `POST /api/admin/reset-db`
  - Confirmation modale avant exécution : "Êtes-vous sûr ? Cette action est irréversible."
  - Modal inline (pas de librairie externe) : `useState(showConfirm)`

---

## Page Guide (`/guide`)

Contenu statique JSX, aucun appel API.

### Sections

1. **Workflow** — Pipeline en 4 étapes : Collecte → Qualification → En cours → Soumission
2. **Scores de pertinence** — Tableau : GO ≥ 65 | Étudier 35–64 | Passer < 35
3. **Statuts** — Tableau : À qualifier / En cours / Soumis / Gagné / Perdu / Archivé
4. **Sources surveillées** — Liste par catégorie : BOAMP, DECP, Banques de développement, Presse, etc.

Mise en page : fond blanc, typographie claire, sections avec icônes. Pas de composant dédié.

---

## Dépendances

| Package | Raison | Action |
|---|---|---|
| `recharts` | Graphiques page Analytics | `npm install recharts` |

Toutes les APIs backend nécessaires existent. Tous les hooks nécessaires existent dans `useTenders.js` sauf `detectDuplicates` (à ajouter) et la résolution de doublons (à ajouter).

### Hooks à ajouter dans `useTenders.js`

```js
export const useDetectDuplicates = () => { ... }  // POST /api/detect-duplicates
export const useDuplicates = () => { ... }         // GET /api/duplicates
export const useArchiveOld = () => { ... }         // POST /api/admin/archive-old
export const useResetDb = () => { ... }            // POST /api/admin/reset-db
```

### Fonctions à ajouter dans `api.js`

```js
export const getDuplicates = () => api.get('/duplicates').then(r => r.data)
```

(`detectDuplicates` et `resetDb` et `archiveOld` sont déjà dans `api.js`)

---

## Critères de succès

1. **Analytics** — Les 3 graphiques s'affichent avec les données réelles ; les KPIs reflètent la base
2. **Direction** — Le kanban affiche les marchés par colonne ; les boutons de transition changent le statut et la vue se met à jour
3. **Urgences** — Les cartes apparaissent avec la bonne couleur selon l'urgence ; message vide si aucune urgence
4. **Paramètres** — La collecte se lance, l'historique se rafraîchit, les doublons se résolvent, la confirmation modale bloque le reset accidentel
5. **Guide** — Contenu lisible, aucun appel réseau

---

## Ce qui n'est PAS dans ce périmètre

- Drag-and-drop dans le kanban (lecture + boutons inline suffisent)
- Export PDF/Excel des graphiques
- Filtres de date sur Analytics
- Pipeline pour les marchés privés dans Direction
- Authentification / gestion des utilisateurs
