# Spec : Scaffold Frontend React — DEF OI Veille Marchés

**Date :** 2026-05-21  
**Statut :** Approuvé  
**Périmètre :** Étape 1 — initialisation, layout et service API

---

## Contexte

L'application existante tourne sous Streamlit (`app.py`). Un backend FastAPI a été créé dans `backend/main.py`, exposant une API REST complète sur `http://localhost:8000/api`. Le CORS est déjà configuré pour `localhost:5173` (port Vite par défaut). Cette spec couvre la mise en place du frontend React qui remplacera Streamlit.

## Stack technique

| Technologie | Rôle |
|---|---|
| React 18 + Vite | Framework UI + bundler |
| Tailwind CSS v3 | Styles utilitaires |
| React Router DOM v6 | Routing SPA |
| Axios | Client HTTP (couche service) |
| TanStack React Query v5 | Cache, fetching, polling |

## Architecture

### Structure des fichiers

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Layout.jsx        ← wrapper global : Sidebar + topbar + <Outlet/>
│   │   └── Sidebar.jsx       ← nav items, badge urgences, logo
│   ├── pages/
│   │   ├── Pipeline.jsx
│   │   ├── Analytics.jsx
│   │   ├── Direction.jsx
│   │   ├── Urgences.jsx
│   │   ├── Parametres.jsx
│   │   └── Guide.jsx
│   ├── services/
│   │   └── api.js            ← instance axios + fonctions par endpoint
│   ├── hooks/
│   │   └── useTenders.js     ← hooks React Query (ex: useKpisPublic)
│   ├── App.jsx               ← <Routes> avec Layout comme wrapper
│   └── main.jsx              ← QueryClientProvider + RouterProvider
├── index.html
├── package.json
├── vite.config.js
└── tailwind.config.js
```

### Routing (App.jsx)

```
/              → Pipeline
/analytics     → Analytics
/direction     → Direction
/urgences      → Urgences
/parametres    → Parametres
/guide         → Guide
```

Toutes les routes sont wrappées dans `<Layout>` via `<Outlet/>` de React Router.

## Composants principaux

### Layout.jsx

Wrapper à deux colonnes :
- **Gauche :** `<Sidebar>` (fixe, non scrollable)
- **Droite :** topbar + zone `<Outlet/>` scrollable

La topbar légère affiche le titre de la page courante et un compteur (ex : "247 marchés actifs"). Le bouton "Lancer collecte" y est ancré.

### Sidebar.jsx

- **Couleur de fond :** `#16213e`
- **Logo :** carré rouge `#e94560` + texte "DEF Océan Indien / Veille Marchés"
- **Items nav principaux (haut → bas) :**
  - 📋 Pipeline → `/`
  - 📊 Analytics → `/analytics`
  - 🎯 Direction → `/direction`
  - 🔔 Urgences → `/urgences` *(badge rouge avec compteur urgences actives)*
  - 📖 Guide → `/guide`
- **Item épinglé en bas :**
  - ⚙️ Paramètres → `/parametres`
- **Item actif :** fond `rgba(233,69,96,0.15)` + bordure gauche `3px solid #e94560`
- **Items inactifs :** texte `#5a6e8a`

### services/api.js

Instance axios avec `baseURL: 'http://localhost:8000/api'`. Exporte des fonctions nommées par ressource :

```js
// Tenders
getTenders(params)         // GET /tenders
getTender(id)              // GET /tenders/:id
updateStatus(id, status)   // POST /tenders/:id/status
updateSaved(id, isSaved)   // POST /tenders/:id/saved

// KPIs
getKpisPublic()            // GET /kpis/public
getKpisCa()                // GET /kpis/ca
getKpisPriv()              // GET /kpis/priv

// Pipeline & urgences
getPipeline()              // GET /pipeline
getUrgences()              // GET /urgences

// Collecte
collect(sourceNames?)      // POST /collect
analyzePending()           // POST /analyze-pending

// Scraper runs & sources
getScraperRuns()           // GET /scraper-runs
getSources()               // GET /sources

// Chart data
getChartData()             // GET /chart-data
```

### Hooks React Query (hooks/useTenders.js)

Wrappent les fonctions `api.js` avec `useQuery` / `useMutation`. Exemple :

```js
useKpisPublic()   // staleTime: 30s
useUrgences()     // staleTime: 60s, polling auto
useTenders(params)
useCollectMutation()
```

## Décisions de design

- **Pas de store global (Zustand)** pour cette étape — React Query gère le cache serveur. Un contexte React léger suffira si besoin pour l'état UI local (page active déjà gérée par React Router).
- **Pages stub** : les 6 pages sont créées vides (`<div>Page X</div>`) à l'étape 1, remplies aux étapes suivantes.
- **Tailwind uniquement** : pas de composant UI library (shadcn, MUI) à ce stade.
- **Proxy Vite** : `vite.config.js` configure un proxy `/api → http://localhost:8000/api` pour éviter le CORS en dev.
