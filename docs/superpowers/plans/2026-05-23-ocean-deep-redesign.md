# Ocean Deep Redesign — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Appliquer le thème "Océan Profond" (navy/cyan, Playfair Display + DM Sans + DM Mono) à tous les composants et pages React — styling pur, zéro changement logique.

**Architecture:** Token-first — `tailwind.config.js` définit tous les tokens d'abord, puis chaque fichier est restylisté indépendamment. Fonts via Google Fonts CDN dans `index.html`.

**Tech Stack:** React 19, Tailwind CSS 3 (JIT), Vite 8, Google Fonts CDN

> **Note TDD:** Ce plan est 100% styling. Les tests existants (rendering/logic) ne sont pas impactés. Aucun test visuel à écrire. Vérification via `npm run dev` après chaque tâche.

---

### Task 1 : tailwind.config.js — Palette ocean + fontFamily

**Files:**
- Modify: `frontend/tailwind.config.js`

- [ ] **Step 1 : Démarrer le serveur de dev (garder ouvert pour toute la session)**

```bash
cd frontend && npm run dev
```
Expected: `Local: http://localhost:5173/` — garder ce terminal ouvert.

- [ ] **Step 2 : Remplacer le contenu de `frontend/tailwind.config.js`**

```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#16213e',
        accent: '#e94560',
        ocean: {
          deep:   '#040d1a',
          navy:   '#071428',
          panel:  '#0a1c35',
          border: 'rgba(0,200,255,0.08)',
          glow:   'rgba(0,200,255,0.15)',
          cyan:   '#00c8ff',
          teal:   '#00e5c0',
          coral:  '#ff6b6b',
          gold:   '#ffd700',
          text:   '#ddeeff',
          muted:  'rgba(150,200,240,0.4)',
        },
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'serif'],
        sans:  ['DM Sans', 'system-ui', 'sans-serif'],
        mono:  ['DM Mono', 'Inconsolata', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

> Note : `ocean-border` et `ocean-muted` sont des rgba statiques. Ne pas utiliser les modificateurs d'opacité Tailwind (`/50`) sur ces tokens — l'opacité est baked-in. Pour les surfaces semi-transparentes, utiliser les couleurs hex avec modificateurs (ex: `bg-ocean-cyan/10`).

- [ ] **Step 3 : Commit**

```bash
git add frontend/tailwind.config.js
git commit -m "feat(design): add ocean color palette and DM Sans/Playfair/DM Mono to tailwind config"
```

---

### Task 2 : index.html — Google Fonts CDN

**Files:**
- Modify: `frontend/index.html`

- [ ] **Step 1 : Remplacer le contenu de `frontend/index.html`**

```html
<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>DEF Océan Indien — Veille Marchés</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

- [ ] **Step 2 : Vérifier dans le navigateur** — ouvrir http://localhost:5173, inspecter : le body doit afficher `font-family: "DM Sans"` dans les DevTools.

- [ ] **Step 3 : Commit**

```bash
git add frontend/index.html
git commit -m "feat(design): add Playfair Display, DM Sans, DM Mono via Google Fonts CDN"
```

---

### Task 3 : Layout.jsx — Shell ocean

**Files:**
- Modify: `frontend/src/components/Layout.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/Layout.jsx`**

```jsx
import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'

const PAGE_TITLES = {
  '/': 'Pipeline',
  '/analytics': 'Analytics',
  '/direction': 'Direction',
  '/urgences': 'Urgences',
  '/parametres': 'Paramètres',
  '/guide': 'Guide',
}

export default function Layout() {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'DEF OI'
  const today = new Date().toLocaleDateString('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric',
  })

  return (
    <div className="flex h-screen overflow-hidden bg-ocean-deep">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <header className="h-[52px] bg-ocean-navy border-b border-ocean-border flex items-center px-6 flex-shrink-0">
          <span className="font-serif text-xl font-bold text-ocean-text">{title}</span>
          <span className="ml-auto font-mono text-xs text-ocean-muted">{today}</span>
        </header>
        <main className="flex-1 overflow-auto bg-ocean-deep">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

- [ ] **Step 2 : Vérifier** — fond global doit être `#040d1a`, header `#071428`, titre en Playfair Display.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/components/Layout.jsx
git commit -m "feat(design): apply ocean theme to Layout shell"
```

---

### Task 4 : Sidebar.jsx — Thème ocean complet

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/Sidebar.jsx`**

```jsx
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  useUrgences, useSources, useCollectMutation,
  useCredentials, useAnalyzePending,
} from '../hooks/useTenders'

const NAV_ITEMS = [
  { to: '/', icon: '📋', label: 'Pipeline', end: true },
  { to: '/analytics', icon: '📊', label: 'Analytics' },
  { to: '/direction', icon: '🎯', label: 'Direction' },
  { to: '/urgences', icon: '🔔', label: 'Urgences', badge: true },
  { to: '/guide', icon: '📖', label: 'Guide' },
]

function NavItem({ to, icon, label, badge, urgenceCount, end }) {
  return (
    <NavLink
      to={to}
      end={end}
      className={({ isActive }) =>
        [
          'flex items-center gap-3 py-2.5 px-3 mx-2 rounded-lg text-sm transition-colors',
          isActive
            ? 'text-ocean-cyan bg-gradient-to-r from-ocean-cyan/8 to-transparent border-l-2 border-ocean-cyan pl-[10px]'
            : 'text-ocean-muted hover:text-ocean-text hover:bg-ocean-cyan/4',
        ].join(' ')
      }
    >
      {({ isActive }) => (
        <>
          <span className={[
            'w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0 border transition-colors',
            isActive
              ? 'bg-ocean-cyan/15 border-ocean-cyan/30'
              : 'bg-white/5 border-white/6',
          ].join(' ')}>
            {icon}
          </span>
          <span className="font-sans font-medium">{label}</span>
          {badge && urgenceCount > 0 && (
            <span className="ml-auto bg-ocean-coral text-white text-[10px] font-bold rounded-full px-1.5 py-px shadow shadow-ocean-coral/40">
              {urgenceCount}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function StepBar({ label, value, total, color = 'green' }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 100
  const barColor = color === 'amber' ? 'bg-ocean-gold/60' : 'bg-ocean-teal/60'
  const textColor = color === 'amber' ? 'text-ocean-gold' : 'text-ocean-teal'
  return (
    <div>
      <div className="flex justify-between items-center mb-0.5">
        <span className="text-[9px] text-ocean-muted">{label}</span>
        <span className={`text-[9px] ${textColor}`}>{value}/{total}</span>
      </div>
      <div className="h-1 bg-white/10 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function CollectSection() {
  const { data: sources = [] } = useSources()
  const { data: creds = [] } = useCredentials()
  const { mutate: collect, isPending: collecting, data: collectResult, reset: resetMutation } = useCollectMutation()
  const { mutate: analyze, isPending: analyzing } = useAnalyzePending()
  const [selected, setSelected] = useState(null)
  const [analyzeTriggered, setAnalyzeTriggered] = useState(false)

  const enabled = sources.filter((s) => s.enabled && !s.is_manual)
  const missingCreds = creds.filter((c) => c.status === 'missing')
  const credBySite = Object.fromEntries(creds.map((c) => [c.site, c.status]))
  const isLocked = (source) =>
    source.credential_site && credBySite[source.credential_site] === 'missing'

  const toggle = (name) => {
    const src = enabled.find((s) => s.name === name)
    if (!src || isLocked(src)) return
    setSelected((prev) => {
      const nonLocked = enabled.filter((s) => !isLocked(s)).map((s) => s.name)
      if (prev === null) {
        const next = nonLocked.filter((n) => n !== name)
        return next.length === 0 ? null : next
      }
      if (prev.includes(name)) {
        const next = prev.filter((n) => n !== name)
        return next.length === 0 ? null : next
      }
      const next = [...prev, name]
      return next.length === nonLocked.length ? null : next
    })
  }

  const isChecked = (source) => {
    if (isLocked(source)) return false
    return selected === null || selected.includes(source.name)
  }

  const handleCollect = () => {
    setAnalyzeTriggered(false)
    if (selected === null && enabled.some((s) => isLocked(s))) {
      collect(enabled.filter((s) => !isLocked(s)).map((s) => s.name))
    } else {
      collect(selected)
    }
  }

  const handleAnalyze = () => {
    setAnalyzeTriggered(true)
    analyze()
  }

  const handleReset = () => {
    resetMutation()
    setSelected(null)
    setAnalyzeTriggered(false)
  }

  const results = collectResult?.results ?? []
  const totalNew = results.reduce((sum, r) => sum + (r.nb_new ?? 0), 0)
  const aiAnalyzed = Math.min(totalNew, 10)
  const aiPending = Math.max(0, totalNew - 10)
  const showResults = !!collectResult && !collecting

  return (
    <div className="border-t border-ocean-border flex-shrink-0">
      <div className="px-3 pt-2.5 pb-1 flex items-center justify-between">
        <p className="text-[10px] font-semibold text-ocean-muted uppercase tracking-widest font-mono">
          Collecte
        </p>
        {showResults && (
          <button
            onClick={handleReset}
            className="text-[10px] text-ocean-muted hover:text-ocean-text transition-colors"
            title="Nouvelle collecte"
          >
            ↺
          </button>
        )}
      </div>

      <div className="px-3 pb-3">
        {missingCreds.length > 0 && !collecting && !showResults && (
          <div className="mb-2 flex items-start gap-1 text-[10px] text-ocean-gold leading-tight">
            <span className="flex-shrink-0">⚠</span>
            <span>
              Identifiants manquants : {missingCreds.map((c) => c.label).join(', ')}
              {missingCreds.some((c) => c.site) && (
                <> — <NavLink to="/parametres" className="underline hover:text-ocean-cyan transition-colors">configurer ↗</NavLink></>
              )}
            </span>
          </div>
        )}

        {!collecting && !showResults && (
          <>
            <div className="flex flex-wrap gap-1.5 mb-2.5">
              {enabled.map((s) => {
                const locked = isLocked(s)
                const checked = isChecked(s)
                return (
                  <label
                    key={s.name}
                    className={[
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[9px] border cursor-pointer select-none transition-colors',
                      locked
                        ? 'opacity-30 cursor-not-allowed bg-ocean-cyan/5 border-ocean-cyan/12 text-ocean-muted'
                        : checked
                        ? 'bg-ocean-cyan/12 border-ocean-cyan/30 text-ocean-cyan'
                        : 'bg-ocean-cyan/5 border-ocean-cyan/12 text-ocean-muted hover:text-ocean-text',
                    ].join(' ')}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggle(s.name)}
                      disabled={locked}
                      className="sr-only"
                    />
                    {locked ? '🔒 ' : ''}{s.name}
                  </label>
                )
              })}
            </div>
            <button
              onClick={handleCollect}
              className="w-full py-2 bg-gradient-to-r from-ocean-cyan/12 to-ocean-teal/8 border border-ocean-cyan/20 text-ocean-cyan font-sans text-[11px] font-semibold rounded-lg hover:shadow hover:shadow-ocean-cyan/15 transition-all"
            >
              ⟳ Lancer la collecte
            </button>
          </>
        )}

        {collecting && (
          <div className="space-y-2 py-1">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-ocean-cyan animate-pulse flex-shrink-0" />
              <span className="text-[10px] text-ocean-muted font-mono">Collecte + analyse en cours…</span>
            </div>
            <div className="h-1 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-ocean-cyan/60 animate-pulse rounded-full" style={{ width: '65%' }} />
            </div>
            <p className="text-[9px] text-ocean-muted/60 leading-tight font-mono">
              Peut prendre plusieurs minutes.
            </p>
          </div>
        )}

        {showResults && (
          <div className="space-y-2">
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

            <div className="space-y-1.5 pt-1.5 border-t border-ocean-border">
              <StepBar label="Collecte" value={totalNew} total={totalNew} />
              <StepBar label="Mots-clés" value={totalNew} total={totalNew} />
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
      </div>
    </div>
  )
}

export default function Sidebar() {
  const { data: urgences = [] } = useUrgences()

  return (
    <aside className="w-[260px] bg-gradient-to-b from-ocean-navy to-ocean-deep flex flex-col flex-shrink-0 h-screen border-r border-ocean-border">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-ocean-border">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-11 h-11 bg-gradient-to-br from-ocean-cyan/20 to-ocean-teal/10 border border-ocean-cyan/25 rounded-xl flex items-center justify-center flex-shrink-0">
            <span className="font-serif font-bold text-ocean-cyan text-sm">OI</span>
          </div>
          <div>
            <p className="font-serif font-bold text-ocean-text text-sm leading-tight">DEF Océan Indien</p>
            <p className="font-sans text-[10px] uppercase tracking-widest text-ocean-muted mt-0.5">Veille Marchés</p>
          </div>
        </div>
        <div className="inline-flex items-center gap-1.5 bg-ocean-teal/8 border border-ocean-teal/15 rounded-full px-2.5 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-ocean-teal animate-pulse flex-shrink-0" />
          <span className="font-mono text-[9px] text-ocean-teal tracking-wide">Système actif</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="py-3 flex-shrink-0 space-y-0.5">
        {NAV_ITEMS.map((item) => (
          <NavItem key={item.to} {...item} urgenceCount={urgences.length} />
        ))}
      </nav>

      {/* Collecte */}
      <div className="flex-1 overflow-y-auto">
        <CollectSection />
      </div>

      {/* Paramètres */}
      <div className="border-t border-ocean-border py-2 flex-shrink-0">
        <NavLink
          to="/parametres"
          className={({ isActive }) =>
            [
              'flex items-center gap-3 py-2.5 px-3 mx-2 rounded-lg text-sm transition-colors',
              isActive
                ? 'text-ocean-cyan bg-gradient-to-r from-ocean-cyan/8 to-transparent border-l-2 border-ocean-cyan pl-[10px]'
                : 'text-ocean-muted hover:text-ocean-text hover:bg-ocean-cyan/4',
            ].join(' ')
          }
        >
          {({ isActive }) => (
            <>
              <span className={[
                'w-7 h-7 rounded-lg flex items-center justify-center text-sm flex-shrink-0 border transition-colors',
                isActive ? 'bg-ocean-cyan/15 border-ocean-cyan/30' : 'bg-white/5 border-white/6',
              ].join(' ')}>⚙️</span>
              <span className="font-sans font-medium">Paramètres</span>
            </>
          )}
        </NavLink>
      </div>
    </aside>
  )
}
```

- [ ] **Step 2 : Vérifier** — sidebar doit être navy→deep, logo avec bordure cyan, chips de sources, bouton collecte gradient.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/components/Sidebar.jsx
git commit -m "feat(design): apply full ocean theme to Sidebar"
```

---

### Task 5 : KpiGrid.jsx — Cartes ocean

**Files:**
- Modify: `frontend/src/components/KpiGrid.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/KpiGrid.jsx`**

```jsx
import { useKpisPublic } from '../hooks/useTenders'

const KPI_CARDS = [
  { key: 'total',       label: 'Total marchés', icon: '📋', topColor: 'border-t-2 border-ocean-cyan'  },
  { key: 'a_qualifier', label: 'À qualifier',   icon: '🔍', topColor: 'border-t-2 border-ocean-muted' },
  { key: 'en_cours',   label: 'En cours',       icon: '⚙️', topColor: 'border-t-2 border-ocean-teal'  },
  { key: 'soumis',     label: 'Soumis',         icon: '📤', topColor: 'border-t-2 border-ocean-gold'  },
  { key: 'gagnes',     label: 'Gagnés',         icon: '✅', topColor: 'border-t-2 border-ocean-teal'  },
]

export default function KpiGrid() {
  const { data, isLoading, isError } = useKpisPublic()

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-24 rounded-xl bg-ocean-panel/50 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="text-ocean-coral text-sm">Impossible de charger les KPIs.</p>
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {KPI_CARDS.map(({ key, label, icon, topColor }) => (
        <div
          key={key}
          className={`bg-ocean-panel border border-ocean-border rounded-xl p-5 flex flex-col gap-1 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-ocean-cyan/6 transition-all duration-200 ${topColor}`}
        >
          <span className="font-sans text-xs uppercase tracking-widest text-ocean-muted">
            {icon} {label}
          </span>
          <span className="font-serif text-4xl font-bold text-ocean-text">{data?.[key] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 2 : Vérifier** — 5 cartes fond `#0a1c35`, valeurs en Playfair Display, bandes colorées en haut, hover subtil.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/components/KpiGrid.jsx
git commit -m "feat(design): apply ocean theme to KpiGrid with colored top borders"
```

---

### Task 6 : TendersTable.jsx — Table ocean

**Files:**
- Modify: `frontend/src/components/TendersTable.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/TendersTable.jsx`**

```jsx
import { useMemo } from 'react'
import { useTenders } from '../hooks/useTenders'

const STATUTS = ['Tous', 'À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']
const SECTEURS = ['Public', 'Privé', 'International']

function GonogoBadge({ gonogo }) {
  if (!gonogo) return <span className="text-ocean-muted text-xs">—</span>
  if (gonogo === 'GO')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-teal/15 text-ocean-teal">
        🟢 GO
      </span>
    )
  if (gonogo === 'Étudier')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-gold/15 text-ocean-gold">
        🟡 Étudier
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-ocean-coral/15 text-ocean-coral">
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
  onRowClick,
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
    <div className="bg-ocean-panel border border-ocean-border rounded-xl overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 items-center p-4 border-b border-ocean-border">
        <span className="font-serif text-base font-semibold text-ocean-text">Appels d'offres</span>
        {!isLoading && !isError && (
          <span className="bg-ocean-cyan/8 border border-ocean-cyan/12 rounded-full font-mono text-xs text-ocean-cyan/60 px-2.5 py-0.5">
            {filtered.length}
          </span>
        )}
        <div className="ml-auto flex flex-wrap gap-2 items-center">
          <select
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            aria-label="Filtrer par statut"
            className="text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text focus:border-ocean-cyan/20 focus:outline-none"
          >
            {STATUTS.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <select
            value={secteur}
            onChange={(e) => onSecteurChange(e.target.value)}
            aria-label="Filtrer par secteur"
            className="text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text focus:border-ocean-cyan/20 focus:outline-none"
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
            className="text-sm border border-ocean-border rounded-lg px-3 py-1.5 bg-ocean-navy text-ocean-text placeholder:text-ocean-muted focus:border-ocean-cyan/20 focus:outline-none min-w-[200px]"
          />
        </div>
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
              <tr className="border-b border-ocean-border font-mono text-xs uppercase tracking-widest text-ocean-muted bg-black/20">
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
                  onClick={() => onRowClick?.(t.id)}
                  className={`border-b border-ocean-cyan/4 hover:bg-ocean-cyan/2 transition-colors${onRowClick ? ' cursor-pointer' : ''}`}
                  role={onRowClick ? 'button' : undefined}
                  tabIndex={onRowClick ? 0 : undefined}
                  onKeyDown={onRowClick ? (e) => { if (e.key === 'Enter' || e.key === ' ') onRowClick(t.id) } : undefined}
                >
                  <td className="px-4 py-3 font-sans font-medium text-ocean-text max-w-xs truncate">
                    {t.title}
                  </td>
                  <td className="px-4 py-3 text-ocean-text/80 font-sans">{t.domaine || '—'}</td>
                  <td className="px-4 py-3 text-ocean-text/80 font-sans">{t.territoire || '—'}</td>
                  <td className="px-4 py-3 text-ocean-muted whitespace-nowrap font-mono text-xs">
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
                      <span className="text-ocean-teal font-mono text-xs tabular-nums">{t.relevance_score ?? 0}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <GonogoBadge gonogo={t.gonogo} />
                  </td>
                  <td className="px-4 py-3 text-ocean-text/80 font-sans text-xs">{t.status}</td>
                  <td className="px-4 py-3 text-ocean-muted font-mono text-xs">{t.source}</td>
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

- [ ] **Step 2 : Vérifier** — table fond `ocean-panel`, en-têtes `font-mono`, score avec barre cyan→teal, hover subtil.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/components/TendersTable.jsx
git commit -m "feat(design): apply ocean theme to TendersTable"
```

---

### Task 7 : TenderDetail.jsx — Panneau latéral ocean

**Files:**
- Modify: `frontend/src/components/TenderDetail.jsx`

- [ ] **Step 1 : Appliquer les changements ciblés dans `frontend/src/components/TenderDetail.jsx`**

Remplacer chaque occurrence indiquée ci-dessous (dans l'ordre) :

**Overlay de fond :**
```
// Avant :
className="fixed inset-0 z-40 bg-black/40"
// Après :
className="fixed inset-0 z-40 bg-black/60"
```

**Panneau latéral :**
```
// Avant :
className="fixed right-0 top-0 bottom-0 w-[480px] z-50 bg-white overflow-y-auto shadow-xl flex flex-col"
// Après :
className="fixed right-0 top-0 bottom-0 w-[480px] z-50 bg-ocean-panel border-l border-ocean-border overflow-y-auto shadow-2xl flex flex-col"
```

**Header du panneau :**
```
// Avant :
className="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0"
// Après :
className="flex items-center justify-between px-4 py-3 border-b border-ocean-border shrink-0"
```

**Label "Fiche marché" :**
```
// Avant :
className="text-sm font-medium text-gray-500"
// Après :
className="font-sans text-sm font-medium text-ocean-muted"
```

**Bouton fermeture :**
```
// Avant :
className="text-gray-400 hover:text-gray-600 text-lg leading-none"
// Après :
className="text-ocean-muted hover:text-ocean-text text-lg leading-none transition-colors"
```

**LoadingSkeleton — remplacer les divs de skeleton :**
```
// Avant :
className="h-16 bg-gray-100 rounded animate-pulse"
// Après :
className="h-16 bg-ocean-panel/50 rounded-lg animate-pulse"
```

**Erreur de chargement :**
```
// Avant :
<p className="p-6 text-red-600 text-sm">
// Après :
<p className="p-6 text-ocean-coral text-sm">
```

**GonogoBadge — 4 variantes :**
```
// Avant (default) :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-gray-100 text-gray-500"
// Après :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-white/5 text-ocean-muted"

// Avant (GO) :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-green-100 text-green-800"
// Après :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-ocean-teal/15 text-ocean-teal"

// Avant (Étudier) :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-yellow-100 text-yellow-800"
// Après :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-ocean-gold/15 text-ocean-gold"

// Avant (Passer) :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-red-100 text-red-800"
// Après :
className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-ocean-coral/15 text-ocean-coral"
```

**TenderDetailHeader — titre h2 :**
```
// Avant :
className="text-base font-semibold text-gray-900 line-clamp-2"
// Après :
className="font-serif text-base font-semibold text-ocean-text line-clamp-2"
```

**TenderDetailHeader — meta wrapper :**
```
// Avant :
className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500"
// Après :
className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ocean-muted font-mono"
```

**TenderDetailHeader — strong tags (2 occurrences pour deadline jours) :**
```
// Avant :
tender.jours_restants <= 7
  ? 'text-red-600 font-bold'
  : tender.jours_restants <= 30
  ? 'text-orange-500'
  : ''
// Après :
tender.jours_restants <= 7
  ? 'text-ocean-coral font-bold'
  : tender.jours_restants <= 30
  ? 'text-ocean-gold'
  : 'text-ocean-muted'
```

**ScoreBar — labels et barres :**
```
// Avant :
className="flex justify-between text-xs text-gray-600"
// Après :
className="flex justify-between text-xs text-ocean-muted font-mono"

// Avant :
className="h-2 bg-gray-200 rounded-full"
// Après :
className="h-2 bg-white/6 rounded-full"

// Avant :
className="h-2 bg-indigo-500 rounded-full"
// Après :
className="h-2 bg-gradient-to-r from-ocean-cyan to-ocean-teal rounded-full"
```

**TenderDetailActionPlan — titre h3 :**
```
// Avant :
className="font-semibold text-gray-800"
// Après :
className="font-serif font-semibold text-ocean-text"
```

**TenderDetailActionPlan — steps list :**
```
// Avant :
className="text-sm text-gray-700 list-decimal"
// Après :
className="text-sm text-ocean-text/80 list-decimal font-sans"
```

**TenderDetailActionPlan — risques :**
```
// Avant :
className="text-sm px-3 py-2 bg-orange-50 border border-orange-200 rounded text-orange-800"
// Après :
className="text-sm px-3 py-2 bg-ocean-gold/8 border border-ocean-gold/20 rounded-lg text-ocean-gold"
```

**TenderDetailActionPlan — atouts :**
```
// Avant :
className="text-sm px-3 py-2 bg-green-50 border border-green-200 rounded text-green-800"
// Après :
className="text-sm px-3 py-2 bg-ocean-teal/8 border border-ocean-teal/20 rounded-lg text-ocean-teal"
```

**TenderDetailTechnical — wrapper :**
```
// Avant :
className="border border-gray-200 rounded"
// Après :
className="border border-ocean-border rounded-lg"
```

**TenderDetailTechnical — bouton toggle :**
```
// Avant :
className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
// Après :
className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-sans font-medium text-ocean-text hover:bg-ocean-panel/50 transition-colors"
```

**TenderDetailTechnical — indicateur ▲▼ :**
```
// Avant :
className="text-gray-400 text-xs"
// Après :
className="text-ocean-muted text-xs"
```

**TenderDetailTechnical — contenu interne border-t :**
```
// Avant :
className="px-4 pb-4 space-y-3 border-t border-gray-100"
// Après :
className="px-4 pb-4 space-y-3 border-t border-ocean-border"
```

**TenderDetailTechnical — label section score :**
```
// Avant :
className="text-xs font-semibold text-gray-500 uppercase pt-3"
// Après :
className="text-xs font-mono font-semibold text-ocean-muted uppercase pt-3"
```

**TenderDetailTechnical — meta divs :**
```
// Avant :
className="pt-2 space-y-1 text-xs text-gray-600 border-t border-gray-100"
// Après :
className="pt-2 space-y-1 text-xs text-ocean-muted font-mono border-t border-ocean-border"
```

**TenderDetailTechnical — label description :**
```
// Avant :
className="text-xs font-semibold text-gray-500 uppercase mb-1"
// Après :
className="text-xs font-mono font-semibold text-ocean-muted uppercase mb-1"
```

**TenderDetailTechnical — texte description :**
```
// Avant :
className="text-xs text-gray-600 whitespace-pre-wrap line-clamp-6"
// Après :
className="text-xs text-ocean-text/70 whitespace-pre-wrap line-clamp-6 font-sans"
```

**TenderDetailAI — conteneur :**
```
// Avant :
className="border border-gray-200 rounded px-4 py-3 space-y-2"
// Après :
className="border border-ocean-border rounded-lg px-4 py-3 space-y-2"
```

**TenderDetailAI — label section :**
```
// Avant :
className="text-xs font-semibold text-gray-500 uppercase"
// Après :
className="text-xs font-mono font-semibold text-ocean-muted uppercase"
```

**TenderDetailAI — grid text :**
```
// Avant :
className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs text-gray-700"
// Après :
className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs text-ocean-text/80 font-sans"
```

**TenderDetailAI — justification italic :**
```
// Avant :
className="text-xs text-gray-500 italic"
// Après :
className="text-xs text-ocean-muted italic font-sans"
```

**TenderDetailActions — border-t :**
```
// Avant :
className="flex items-center gap-3 pt-2 border-t border-gray-100"
// Après :
className="flex items-center gap-3 pt-2 border-t border-ocean-border"
```

**TenderDetailActions — select statut :**
```
// Avant :
className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white flex-1"
// Après :
className="text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text flex-1 focus:outline-none focus:border-ocean-cyan/30"
```

**TenderDetailActions — bouton favori :**
```
// Avant :
tender.is_saved
  ? 'text-yellow-500 hover:text-yellow-600'
  : 'text-gray-300 hover:text-yellow-400'
// Après :
tender.is_saved
  ? 'text-ocean-gold hover:text-ocean-gold/80'
  : 'text-ocean-muted hover:text-ocean-gold'
```

**Séparateur `<hr>` :**
```
// Avant :
<hr className="border-gray-100" />
// Après :
<hr className="border-ocean-border" />
```

- [ ] **Step 2 : Vérifier** — panneau droit fond `ocean-panel`, badges GO/Étudier en couleurs ocean, barre de score cyan→teal.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/components/TenderDetail.jsx
git commit -m "feat(design): apply ocean theme to TenderDetail panel"
```

---

### Task 8 : UrgenceCard.jsx — Cartes urgence ocean

**Files:**
- Modify: `frontend/src/components/UrgenceCard.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/UrgenceCard.jsx`**

```jsx
function urgenceStyle(jours) {
  if (jours < 7) return {
    bg: 'bg-ocean-panel border-l-2 border-ocean-coral',
    badge: 'bg-ocean-coral/15 text-ocean-coral',
  }
  if (jours <= 15) return {
    bg: 'bg-ocean-panel border-l-2 border-ocean-gold',
    badge: 'bg-ocean-gold/15 text-ocean-gold',
  }
  return {
    bg: 'bg-ocean-panel border-l-2 border-ocean-teal',
    badge: 'bg-ocean-teal/15 text-ocean-teal',
  }
}

export default function UrgenceCard({ title, jours_restants, score, source }) {
  const style = urgenceStyle(jours_restants)
  return (
    <div className={`rounded-xl border border-ocean-border p-4 flex flex-col gap-3 ${style.bg}`}>
      <div className="flex items-start justify-between gap-2">
        <span className={`text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 font-mono ${style.badge}`}>
          J-{jours_restants}
        </span>
        <span className="text-xs bg-ocean-cyan/10 text-ocean-cyan font-mono font-semibold rounded px-1.5 py-0.5">
          {score}
        </span>
      </div>
      <p className="font-sans text-sm font-semibold text-ocean-text line-clamp-2">{title}</p>
      <p className="font-mono text-xs text-ocean-muted">{source}</p>
    </div>
  )
}
```

- [ ] **Step 2 : Vérifier** — cartes avec accent gauche coloré selon urgence, fond `ocean-panel`.

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/components/UrgenceCard.jsx
git commit -m "feat(design): apply ocean theme to UrgenceCard"
```

---

### Task 9 : DuplicatePair.jsx — Ocean theme

**Files:**
- Modify: `frontend/src/components/DuplicatePair.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/DuplicatePair.jsx`**

```jsx
function TenderCard({ tender, highlighted }) {
  return (
    <div className={`flex-1 rounded-lg border p-3 ${
      highlighted
        ? 'ring-1 ring-ocean-cyan/40 bg-ocean-cyan/5 border-ocean-cyan/20'
        : 'bg-ocean-panel border-ocean-border'
    }`}>
      {highlighted && (
        <span className="text-xs text-ocean-cyan font-mono font-semibold mb-1 block">Recommandé ✓</span>
      )}
      <p className="font-sans text-sm font-semibold text-ocean-text mb-2">{tender.title}</p>
      <div className="flex gap-3 text-xs text-ocean-muted font-mono flex-wrap">
        <span>Score : <strong className="text-ocean-teal">{tender.relevance_score}</strong></span>
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
    <div className="border border-ocean-border rounded-xl p-4 bg-ocean-panel space-y-3">
      <div className="flex items-center gap-2">
        <span className="font-sans text-xs text-ocean-muted">Similarité :</span>
        <span className="font-mono text-xs font-bold text-ocean-gold bg-ocean-gold/10 px-2 py-0.5 rounded-full">
          {Math.round(pair.similarity_score * 100)}%
        </span>
      </div>

      <div className="flex gap-3">
        <TenderCard tender={pair.tender_a} highlighted={aIsHigher} />
        <TenderCard tender={pair.tender_b} highlighted={!aIsHigher} />
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', archiveId: pair.tender_b.id })}
          className="text-xs px-3 py-1.5 rounded-lg border border-ocean-cyan/20 text-ocean-cyan hover:bg-ocean-cyan/8 transition-colors"
        >
          Garder A — archiver B
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', archiveId: pair.tender_a.id })}
          className="text-xs px-3 py-1.5 rounded-lg border border-ocean-cyan/20 text-ocean-cyan hover:bg-ocean-cyan/8 transition-colors"
        >
          Garder B — archiver A
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'ignore', archiveId: null })}
          className="text-xs px-3 py-1.5 rounded-lg border border-ocean-border text-ocean-muted hover:text-ocean-text hover:bg-ocean-panel/50 transition-colors"
        >
          Ignorer
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2 : Commit**

```bash
git add frontend/src/components/DuplicatePair.jsx
git commit -m "feat(design): apply ocean theme to DuplicatePair"
```

---

### Task 10 : KanbanColumn.jsx — Ocean theme

**Files:**
- Modify: `frontend/src/components/KanbanColumn.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/components/KanbanColumn.jsx`**

```jsx
function DeadlineBadge({ jours_restants }) {
  if (jours_restants === null || jours_restants === undefined) {
    return <span className="font-mono text-xs text-ocean-muted">Pas de deadline</span>
  }
  const color =
    jours_restants < 7
      ? 'text-ocean-coral'
      : jours_restants <= 30
      ? 'text-ocean-gold'
      : 'text-ocean-muted'
  return (
    <span className={`font-mono text-xs font-medium ${color}`}>
      J-{jours_restants}
    </span>
  )
}

export default function KanbanColumn({ title, items = [], actions = [], onStatusChange }) {
  return (
    <div className="flex flex-col gap-2 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-sans text-sm font-semibold text-ocean-text">{title}</span>
        <span className="bg-ocean-panel border border-ocean-border text-ocean-muted font-mono text-xs font-bold rounded-full px-2 py-px">
          {items.length}
        </span>
      </div>

      {items.length === 0 && (
        <p className="font-sans text-xs text-ocean-muted text-center py-6">Aucun marché</p>
      )}

      {items.map((item) => (
        <article
          key={item.id}
          className="bg-ocean-panel rounded-lg border border-ocean-border p-3 flex flex-col gap-2"
        >
          <p className="font-sans text-sm font-medium text-ocean-text leading-snug">
            {item.title.length > 60 ? item.title.slice(0, 60) + '…' : item.title}
          </p>
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs bg-ocean-cyan/10 text-ocean-cyan font-semibold rounded px-1.5 py-0.5">
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
                  className="font-sans text-xs px-2 py-1 rounded-lg border border-ocean-border text-ocean-muted hover:text-ocean-text hover:border-ocean-cyan/20 transition-colors"
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

- [ ] **Step 2 : Commit**

```bash
git add frontend/src/components/KanbanColumn.jsx
git commit -m "feat(design): apply ocean theme to KanbanColumn"
```

---

### Task 11 : Dashboard.jsx — Padding ocean

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/pages/Dashboard.jsx`**

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
    <div className="p-6 space-y-6">
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

- [ ] **Step 2 : Commit**

```bash
git add frontend/src/pages/Dashboard.jsx
git commit -m "feat(design): update Dashboard padding for ocean theme"
```

---

### Task 12 : Analytics.jsx — Couleurs Recharts ocean

**Files:**
- Modify: `frontend/src/pages/Analytics.jsx`

- [ ] **Step 1 : Changer les constantes de couleur en haut du fichier**

```
// Avant :
const COLORS_TERRITOIRE = ['#6366f1', '#e94560', '#f59e0b', '#10b981', '#94a3b8']
const COULEUR_DEF = '#e94560'

// Après :
const COLORS_TERRITOIRE = ['#00c8ff', '#00e5c0', '#ff6b6b', '#ffd700', 'rgba(150,200,240,0.4)']
const COULEUR_DEF = '#00c8ff'
```

- [ ] **Step 2 : Changer KpiCard pour le thème ocean**

```
// Avant :
function KpiCard({ label, value, color }) {
  return (
    <div className={`rounded-lg border p-4 flex flex-col gap-1 ${color}`}>
      <span className="text-xs font-medium uppercase tracking-wide opacity-70">{label}</span>
      <span className="text-3xl font-bold">{value}</span>
    </div>
  )
}

// Après :
function KpiCard({ label, value, topColor }) {
  return (
    <div className={`bg-ocean-panel border border-ocean-border rounded-xl p-4 flex flex-col gap-1 ${topColor}`}>
      <span className="font-sans text-xs uppercase tracking-widest text-ocean-muted">{label}</span>
      <span className="font-serif text-3xl font-bold text-ocean-text">{value}</span>
    </div>
  )
}
```

- [ ] **Step 3 : Mettre à jour les appels à KpiCard (prop `color` → `topColor`)**

```
// Avant :
<KpiCard label="Total collecté" value={total} color="bg-blue-50 border-blue-200 text-blue-700" />
<KpiCard label="Sources actives" value={sources} color="bg-indigo-50 border-indigo-200 text-indigo-700" />
<KpiCard label="CA gagné" value={caFormatted} color="bg-green-50 border-green-200 text-green-700" />
<KpiCard label="CA pipeline" value={pipelineFormatted} color="bg-amber-50 border-amber-200 text-amber-700" />

// Après :
<KpiCard label="Total collecté" value={total} topColor="border-t-2 border-ocean-cyan" />
<KpiCard label="Sources actives" value={sources} topColor="border-t-2 border-ocean-teal" />
<KpiCard label="CA gagné" value={caFormatted} topColor="border-t-2 border-ocean-teal" />
<KpiCard label="CA pipeline" value={pipelineFormatted} topColor="border-t-2 border-ocean-gold" />
```

- [ ] **Step 4 : Changer les conteneurs de graphiques et le skeleton**

```
// Avant (skeleton) :
className="h-20 rounded-lg bg-gray-100 animate-pulse"
// Après :
className="h-20 rounded-xl bg-ocean-panel/50 animate-pulse"

// Avant (skeleton graphique) :
className="h-56 rounded-lg bg-gray-100 animate-pulse"
// Après :
className="h-56 rounded-xl bg-ocean-panel/50 animate-pulse"

// Avant (chaque conteneur de graphique — 3 occurrences + top 5 sources) :
className="bg-white rounded-lg border border-gray-200 p-4"
// Après (remplacer les 4 occurrences) :
className="bg-ocean-panel border border-ocean-border rounded-xl p-4"
```

- [ ] **Step 5 : Changer les titres et textes des graphiques**

```
// Avant (4 occurrences de labels de graphique) :
className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-3"
// Après :
className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest mb-3"
```

- [ ] **Step 6 : Changer les axes et grilles Recharts**

Dans les 3 `<XAxis>` et `<YAxis>`, ajouter `stroke="rgba(0,200,255,0.1)"` et `tick={{ fill: 'rgba(150,200,240,0.4)', fontSize: 9 }}` :

```
// Avant :
<XAxis dataKey="week" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
<YAxis tick={{ fontSize: 10 }} />
// Après :
<XAxis dataKey="week" tick={{ fill: 'rgba(150,200,240,0.4)', fontSize: 9 }} interval="preserveStartEnd" stroke="rgba(0,200,255,0.1)" />
<YAxis tick={{ fill: 'rgba(150,200,240,0.4)', fontSize: 10 }} stroke="rgba(0,200,255,0.1)" />
```

Même chose pour le BarChart vertical et le PieChart.

- [ ] **Step 7 : Table top 5 sources**

```
// Avant :
<tr className="text-xs text-gray-500 border-b border-gray-200">
// Après :
<tr className="font-mono text-xs text-ocean-muted border-b border-ocean-border">

// Avant :
<tr key={source} className="border-b border-gray-50">
<td className="py-1.5 text-gray-700">{source}</td>
<td className="py-1.5 text-right font-semibold text-gray-800">{count}</td>
// Après :
<tr key={source} className="border-b border-ocean-border/50">
<td className="py-1.5 text-ocean-text/80 font-sans">{source}</td>
<td className="py-1.5 text-right font-mono font-semibold text-ocean-cyan">{count}</td>
```

- [ ] **Step 8 : Erreur et padding page**

```
// Avant :
<div className="p-5 space-y-4">  (loading)
<div className="p-5 space-y-6">  (main)
<p className="p-5 text-red-600 text-sm">
// Après :
<div className="p-6 space-y-4">  (loading)
<div className="p-6 space-y-6">  (main)
<p className="p-6 text-ocean-coral text-sm font-sans">
```

- [ ] **Step 9 : Commit**

```bash
git add frontend/src/pages/Analytics.jsx
git commit -m "feat(design): apply ocean theme to Analytics page and Recharts"
```

---

### Task 13 : Direction.jsx — Ocean theme

**Files:**
- Modify: `frontend/src/pages/Direction.jsx`

- [ ] **Step 1 : Changer le skeleton de chargement**

```
// Avant :
className="h-6 w-24 bg-gray-200 rounded animate-pulse"
// Après :
className="h-6 w-24 bg-ocean-panel/50 rounded animate-pulse"

// Avant :
className="h-24 bg-gray-100 rounded-lg animate-pulse"
// Après :
className="h-24 bg-ocean-panel/50 rounded-lg animate-pulse"
```

- [ ] **Step 2 : Changer le padding et texte info**

```
// Avant :
<div className="p-5 space-y-4">
<p className="text-xs text-gray-500">Marchés publics — score ≥ {GO_SCORE}</p>
// Après :
<div className="p-6 space-y-4">
<p className="font-mono text-xs text-ocean-muted">Marchés publics — score ≥ {GO_SCORE}</p>
```

- [ ] **Step 3 : Erreur**

```
// Avant :
<p className="p-5 text-red-600 text-sm">
// Après :
<p className="p-6 text-ocean-coral text-sm font-sans">
```

- [ ] **Step 4 : Commit**

```bash
git add frontend/src/pages/Direction.jsx
git commit -m "feat(design): apply ocean theme to Direction page"
```

---

### Task 14 : Guide.jsx — Typographie ocean

**Files:**
- Modify: `frontend/src/pages/Guide.jsx`

- [ ] **Step 1 : Changer Section et Table dans Guide.jsx**

```
// Avant :
className="text-base font-bold text-gray-800 mb-3"
// Après :
className="font-serif text-base font-bold text-ocean-text mb-3"

// Avant (table wrapper) :
className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden"
// Après :
className="w-full text-sm border border-ocean-border rounded-lg overflow-hidden"

// Avant (thead) :
<thead className="bg-gray-50">
// Après :
<thead className="bg-ocean-panel/50">

// Avant (th) :
className="text-left px-4 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wide border-b border-gray-200"
// Après :
className="text-left px-4 py-2 font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest border-b border-ocean-border"

// Avant (tr body) :
className="border-b border-gray-100 hover:bg-gray-50"
// Après :
className="border-b border-ocean-border/50 hover:bg-ocean-cyan/2 transition-colors"

// Avant (td) :
className="px-4 py-2.5 text-gray-700"
// Après :
className="px-4 py-2.5 text-ocean-text/80 font-sans"
```

- [ ] **Step 2 : Changer padding et fond de la page**

```
// Avant :
<div className="p-5 max-w-3xl space-y-8">
// Après :
<div className="p-6 max-w-3xl space-y-8">
```

- [ ] **Step 3 : Commit**

```bash
git add frontend/src/pages/Guide.jsx
git commit -m "feat(design): apply ocean theme to Guide page typography"
```

---

### Task 15 : Urgences.jsx — Ocean theme

**Files:**
- Modify: `frontend/src/pages/Urgences.jsx`

- [ ] **Step 1 : Remplacer le contenu de `frontend/src/pages/Urgences.jsx`**

```jsx
import UrgenceCard from '../components/UrgenceCard'
import { useUrgences } from '../hooks/useTenders'

export default function Urgences() {
  const { data: urgences = [], isLoading, isError } = useUrgences()

  if (isLoading) {
    return (
      <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-ocean-panel/50 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="p-6 text-ocean-coral text-sm font-sans">Impossible de charger les urgences.</p>
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="font-sans text-sm font-semibold text-ocean-text">Marchés à traiter en urgence</h2>
        {urgences.length > 0 && (
          <span className="bg-ocean-coral text-white font-mono text-xs font-bold rounded-full px-2 py-px shadow shadow-ocean-coral/40">
            {urgences.length}
          </span>
        )}
      </div>

      {urgences.length === 0 ? (
        <div className="text-center py-16 text-ocean-muted">
          <p className="text-3xl mb-2">✅</p>
          <p className="font-sans text-sm">Aucun marché urgent pour le moment.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {urgences.map((u) => {
            const jours = u.jours_restants ?? Math.ceil((new Date(u.deadline) - new Date()) / 86400000)
            return (
              <UrgenceCard
                key={u.id}
                title={u.title}
                jours_restants={jours}
                score={u.relevance_score}
                source={u.source}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2 : Commit**

```bash
git add frontend/src/pages/Urgences.jsx
git commit -m "feat(design): apply ocean theme to Urgences page"
```

---

### Task 16 : Parametres.jsx — Ocean theme

**Files:**
- Modify: `frontend/src/pages/Parametres.jsx`

- [ ] **Step 1 : Changer TabButton**

```
// Avant :
className={`relative px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
  active
    ? 'border-indigo-600 text-indigo-700'
    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
}`}

// Après :
className={`relative px-4 py-2 font-sans text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
  active
    ? 'border-ocean-cyan text-ocean-cyan'
    : 'border-transparent text-ocean-muted hover:text-ocean-text hover:border-ocean-border'
}`}
```

- [ ] **Step 2 : Changer le badge de TabButton**

```
// Avant :
className="ml-1.5 inline-flex items-center justify-center w-4 h-4 text-xs font-bold rounded-full bg-amber-500 text-white"
// Après :
className="ml-1.5 inline-flex items-center justify-center w-4 h-4 font-mono text-xs font-bold rounded-full bg-ocean-gold text-ocean-deep"
```

- [ ] **Step 3 : Changer statusBadge dans ConnexionTab**

```
// Avant :
return <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">● Configuré</span>
// Après :
return <span className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full bg-ocean-teal/15 text-ocean-teal font-medium">● Configuré</span>

// Avant :
return <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 font-medium">● Variable d'env</span>
// Après :
return <span className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full bg-ocean-cyan/15 text-ocean-cyan font-medium">● Variable d'env</span>

// Avant :
return <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">● Non configuré</span>
// Après :
return <span className="inline-flex items-center gap-1 font-mono text-xs px-2 py-0.5 rounded-full bg-ocean-coral/15 text-ocean-coral font-medium">● Non configuré</span>
```

- [ ] **Step 4 : Changer SiteRow dans ConnexionTab**

```
// Avant :
className="border border-gray-200 rounded-lg overflow-hidden"
// Après :
className="border border-ocean-border rounded-lg overflow-hidden"

// Avant :
className="w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-gray-50 transition-colors"
// Après :
className="w-full flex items-center justify-between px-4 py-3 font-sans text-sm hover:bg-ocean-panel/50 transition-colors"

// Avant :
className="font-medium text-gray-900"
// Après :
className="font-medium text-ocean-text"

// Avant :
className="text-xs text-gray-400 mt-0.5 truncate"
// Après :
className="font-mono text-xs text-ocean-muted mt-0.5 truncate"

// Avant (2e occurrence text-gray-400 pour URL) :
className="text-xs text-gray-400 truncate"
// Après :
className="font-mono text-xs text-ocean-muted truncate"

// Avant :
className="text-gray-400 text-xs flex-shrink-0 ml-2"
// Après :
className="text-ocean-muted text-xs flex-shrink-0 ml-2"
```

- [ ] **Step 5 : Changer le formulaire dans SiteRow (form expand)**

```
// Avant :
className="px-4 pb-4 pt-3 border-t border-gray-100 bg-gray-50"
// Après :
className="px-4 pb-4 pt-3 border-t border-ocean-border bg-ocean-navy/50"

// Avant :
className="block text-xs font-medium text-gray-600 mb-1"
// Après :
className="block font-sans text-xs font-medium text-ocean-muted mb-1"

// Avant (inputs — 2 occurrences) :
className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-400"
// Après :
className="w-full px-3 py-2 font-sans text-sm border border-ocean-border rounded-lg bg-ocean-navy text-ocean-text focus:outline-none focus:border-ocean-cyan/30 focus:ring-1 focus:ring-ocean-cyan/20"

// Avant (bouton toggle pwd) :
className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
// Après :
className="absolute right-2.5 top-1/2 -translate-y-1/2 text-ocean-muted hover:text-ocean-text transition-colors"
```

- [ ] **Step 6 : Changer les boutons d'action dans SiteRow**

```
// Avant (bouton Tester) :
className="px-3 py-1.5 bg-white text-gray-700 text-xs rounded-md border border-gray-300 hover:bg-gray-100 disabled:opacity-50 transition-colors"
// Après :
className="px-3 py-1.5 font-sans bg-ocean-navy text-ocean-muted text-xs rounded-lg border border-ocean-border hover:text-ocean-text hover:border-ocean-cyan/20 disabled:opacity-50 transition-colors"

// Avant (bouton Sauvegarder) :
className="px-3 py-1.5 bg-indigo-600 text-white text-xs rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
// Après :
className="px-3 py-1.5 font-sans bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan text-xs rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"

// Avant (bouton Supprimer) :
className="px-3 py-1.5 bg-red-50 text-red-700 text-xs rounded-md border border-red-300 hover:bg-red-100 disabled:opacity-50 transition-colors"
// Après :
className="px-3 py-1.5 font-sans bg-ocean-coral/10 border border-ocean-coral/20 text-ocean-coral text-xs rounded-lg hover:bg-ocean-coral/15 disabled:opacity-50 transition-colors"
```

- [ ] **Step 7 : Changer les messages de résultat et warning**

```
// Avant :
className={`text-xs mt-2 font-medium ${testResult.ok ? 'text-green-700' : 'text-red-600'}`}
// Après :
className={`font-mono text-xs mt-2 font-medium ${testResult.ok ? 'text-ocean-teal' : 'text-ocean-coral'}`}

// Avant :
className="text-xs mt-2 text-gray-400"  (2 occurrences)
// Après :
className="font-mono text-xs mt-2 text-ocean-muted"

// Avant (env_override expand) :
className="px-4 py-3 border-t border-gray-100 bg-blue-50"
<p className="text-xs text-blue-700">
// Après :
className="px-4 py-3 border-t border-ocean-border bg-ocean-cyan/5"
<p className="font-mono text-xs text-ocean-cyan">
```

- [ ] **Step 8 : Changer ConnexionTab — état erreur et conteneurs**

```
// Avant (erreur backend) :
className="p-4 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 space-y-2"
// Après :
className="p-4 bg-ocean-coral/8 border border-ocean-coral/20 rounded-lg font-sans text-sm text-ocean-coral space-y-2"

// Avant (bouton Réessayer) :
className="mt-2 px-3 py-1.5 bg-red-100 text-red-700 text-xs rounded border border-red-300 hover:bg-red-200"
// Après :
className="mt-2 px-3 py-1.5 font-sans bg-ocean-coral/10 text-ocean-coral text-xs rounded-lg border border-ocean-coral/20 hover:bg-ocean-coral/15"

// Avant (texte intro ConnexionTab) :
className="text-sm text-gray-600"
// Après :
className="font-sans text-sm text-ocean-muted"

// Avant (h3 sections) :
className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3"
// Après :
className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest mb-3"

// Avant (texte vide) :
className="text-sm text-gray-400 italic"
// Après :
className="font-sans text-sm text-ocean-muted italic"
```

- [ ] **Step 9 : Changer AnalyseTab**

```
// Avant :
className="text-sm text-gray-600"  (texte intro)
// Après :
className="font-sans text-sm text-ocean-muted"

// Avant (bouton analyser) :
className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
// Après :
className="px-4 py-2 font-sans bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"

// Avant (résultat succès) :
className="text-sm text-green-700"
// Après :
className="font-sans text-sm text-ocean-teal"
```

- [ ] **Step 10 : Changer MaintenanceTab**

```
// Avant (h3 doublons et DB) :
className="text-xs font-semibold text-gray-500 uppercase tracking-wide"
// Après :
className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest"

// Avant (textes états) :
className="text-sm text-gray-400"   (isLoading, aucun doublon)
// Après :
className="font-sans text-sm text-ocean-muted"

// Avant (detectResult count) :
className="text-sm text-gray-700"
// Après :
className="font-sans text-sm text-ocean-text/80"

// Avant (bouton détecter doublons) :
className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
// Après :
className="px-4 py-2 font-sans bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"

// Avant (bouton archiver) :
className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded border border-gray-300 hover:bg-gray-200 disabled:opacity-50 transition-colors"
// Après :
className="px-4 py-2 font-sans bg-ocean-navy border border-ocean-border text-ocean-muted text-sm rounded-lg hover:text-ocean-text hover:border-ocean-cyan/20 disabled:opacity-50 transition-colors"

// Avant (archiveResult texte) :
className="text-sm text-gray-600"
// Après :
className="font-sans text-sm text-ocean-muted"

// Avant (bouton réinitialiser) :
className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded border border-red-300 hover:bg-red-100 transition-colors"
// Après :
className="px-4 py-2 font-sans bg-ocean-coral/10 border border-ocean-coral/20 text-ocean-coral text-sm rounded-lg hover:bg-ocean-coral/15 transition-colors"

// Avant (confirm panel) :
className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg"
<p className="text-sm text-red-700 font-medium">
// Après :
className="flex items-center gap-3 p-3 bg-ocean-coral/8 border border-ocean-coral/20 rounded-lg"
<p className="font-sans text-sm text-ocean-coral font-medium">

// Avant (bouton oui réinitialiser) :
className="px-3 py-1.5 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
// Après :
className="px-3 py-1.5 font-sans bg-ocean-coral text-ocean-deep text-xs rounded-lg hover:bg-ocean-coral/80 disabled:opacity-50"

// Avant (bouton annuler) :
className="px-3 py-1.5 bg-white text-gray-700 text-xs rounded border border-gray-300 hover:bg-gray-100"
// Après :
className="px-3 py-1.5 font-sans bg-ocean-navy text-ocean-muted text-xs rounded-lg border border-ocean-border hover:text-ocean-text hover:border-ocean-cyan/20"
```

- [ ] **Step 11 : Changer la page principale Parametres**

```
// Avant :
<div className="p-5 max-w-4xl">
// Après :
<div className="p-6 max-w-4xl">

// Avant :
className="text-lg font-bold text-gray-900 mb-1"
// Après :
className="font-serif text-lg font-bold text-ocean-text mb-1"

// Avant :
className="text-sm text-gray-500"
// Après :
className="font-sans text-sm text-ocean-muted"

// Avant :
className="border-b border-gray-200 mb-6 flex gap-0 -mx-1 overflow-x-auto"
// Après :
className="border-b border-ocean-border mb-6 flex gap-0 -mx-1 overflow-x-auto"
```

- [ ] **Step 12 : Vérifier** — tabs actifs en cyan, inputs fond `ocean-navy`, badges statut en couleurs ocean.

- [ ] **Step 13 : Commit**

```bash
git add frontend/src/pages/Parametres.jsx
git commit -m "feat(design): apply ocean theme to Parametres page"
```

---

### Task 17 : Vérification finale

- [ ] **Step 1 : Naviguer dans toutes les pages** — ouvrir http://localhost:5173 et vérifier chacune :
  - `/` — Pipeline : KpiGrid + table + sidebar
  - `/analytics` — Analytics : graphiques cyan/teal
  - `/direction` — Direction : kanban navy
  - `/urgences` — Urgences : cartes avec accent coral/gold/teal
  - `/guide` — Guide : typographie Playfair + DM Sans
  - `/parametres` — Paramètres : tabs cyan, inputs navy

- [ ] **Step 2 : Vérifier les tests existants**

```bash
cd frontend && npm run test
```
Expected: tous les tests passent (les tests sont logiques, pas visuels).

- [ ] **Step 3 : Build de production**

```bash
cd frontend && npm run build
```
Expected: `dist/` créé sans erreur.
