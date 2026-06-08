import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  useUrgences, useSources, useCollectMutation,
  useCredentials, useAnalyzePending,
} from '../hooks/useTenders'

const NAV_ITEMS = [
  { to: '/', icon: '📋', label: 'Marchés', end: true },
  { to: '/pipeline', icon: '🎯', label: 'Pipeline' },
  { to: '/analytics', icon: '📊', label: 'Analytics' },
  { to: '/direction', icon: '🏆', label: 'Direction' },
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
  const aiAnalyzed = totalNew
  const aiPending = 0
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
            <span className="font-serif font-bold text-ocean-cyan text-sm">AT</span>
          </div>
          <div>
            <p className="font-serif font-bold text-ocean-text text-sm leading-tight">ATEXIA</p>
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
