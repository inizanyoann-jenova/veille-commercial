/* eslint-disable react-hooks/set-state-in-effect */
import { useMemo, useState, useCallback, useEffect } from 'react'
import { useTenders, useAnalyzeTender } from '../hooks/useTenders'

const EMPTY_PAGE = []

const STATUTS = ['Tous', 'À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']
const SECTEURS = ['Public', 'Privé', 'International']
const GONOGOS = ['Tous', 'GO', 'Étudier', 'Passer']

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
      <div role="progressbar" aria-label={`Analyse de ${tender.title} en cours`} className="w-16 bg-white/6 rounded-full h-2 overflow-hidden">
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
  gonogo,
  onStatusChange,
  onSecteurChange,
  onSearchChange,
  onGonogoChange,
  onRowClick,
}) {
  const LIMIT = 200
  const [offset, setOffset] = useState(0)
  const [allTenders, setAllTenders] = useState([])
  const [lastPageSize, setLastPageSize] = useState(0)

  useEffect(() => {
    setOffset(0)
    setAllTenders([])
    setLastPageSize(0)
  }, [status, secteur])

  const { data: page = EMPTY_PAGE, isLoading, isFetching, isError } = useTenders({
    status,
    secteur,
    limit: LIMIT,
    offset,
  })

  useEffect(() => {
    setAllTenders((prev) => {
      if (page.length === 0 && offset === 0) return prev.length === 0 ? prev : []
      if (offset === 0) return page
      const existingIds = new Set(prev.map((t) => t.id))
      const newItems = page.filter((t) => !existingIds.has(t.id))
      return newItems.length === 0 ? prev : [...prev, ...newItems]
    })
    if (!isFetching) setLastPageSize(page.length)
  }, [page, offset, isFetching])

  const hasMore = lastPageSize === LIMIT

  const [analyzingIds, setAnalyzingIds] = useState(new Set())
  const { mutate: triggerAnalysis } = useAnalyzeTender()

  const filtered = useMemo(() => {
    let result = allTenders
    if (gonogo && gonogo !== 'Tous') {
      if (gonogo === 'GO') result = result.filter((t) => t.gonogo === 'GO')
      else if (gonogo === 'Étudier') result = result.filter((t) => t.gonogo === 'Étudier')
      else if (gonogo === 'Passer') result = result.filter((t) => t.gonogo != null && t.gonogo !== 'GO' && t.gonogo !== 'Étudier')
    }
    if (!searchText) return result
    const q = searchText.toLowerCase()
    return result.filter((t) =>
      `${t.title} ${t.domaine} ${t.territoire}`.toLowerCase().includes(q)
    )
  }, [allTenders, searchText, gonogo])

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
        <select
          value={gonogo ?? 'Tous'}
          onChange={(e) => onGonogoChange?.(e.target.value)}
          aria-label="Filtrer par GO/NO-GO"
          className="font-sans text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text focus:border-ocean-cyan/20 focus:outline-none"
        >
          {GONOGOS.map((g) => (
            <option key={g}>{g}</option>
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
                <th className="text-left px-4 py-3 font-medium">Date</th>
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
                  <td className="px-4 py-3 font-sans font-medium text-ocean-text max-w-xs">
                    <div className="flex items-start gap-1.5">
                      <span className="truncate">{t.title}</span>
                      {t.url && (
                        <a
                          href={t.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          title="Voir l'annonce"
                          className="shrink-0 text-ocean-cyan hover:text-ocean-teal transition-colors mt-0.5"
                        >
                          ↗
                        </a>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80">{t.domaine || '—'}</td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80">{t.territoire || '—'}</td>
                  <td className="px-4 py-3 font-sans text-xs text-ocean-text/80 whitespace-nowrap">
                    {t.deadline
                      ? <span title="Date limite de remise">{formatDate(t.deadline)}</span>
                      : t.publication_date
                        ? <span className="text-ocean-muted" title="Date de publication">{formatDate(t.publication_date)}</span>
                        : '—'}
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
          {hasMore && (
            <div className="flex justify-center py-3 border-t border-ocean-border">
              <button
                onClick={() => setOffset((o) => o + LIMIT)}
                disabled={isFetching}
                className="px-4 py-2 bg-ocean-cyan/10 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
              >
                {isFetching ? 'Chargement…' : 'Charger 200 de plus'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
