import { useState } from 'react'
import { useTender } from '../hooks/useTenders'

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
    <span className={`font-mono text-xs ${color}`}>
      J-{jours_restants}
    </span>
  )
}

function KanbanCardDetail({ id }) {
  const { data: tender, isLoading } = useTender(id)

  if (isLoading) {
    return (
      <div className="pt-2 border-t border-ocean-border space-y-2">
        <div className="h-3 bg-ocean-panel/60 rounded animate-pulse w-full" />
        <div className="h-3 bg-ocean-panel/60 rounded animate-pulse w-3/4" />
        <div className="h-3 bg-ocean-panel/60 rounded animate-pulse w-5/6" />
      </div>
    )
  }
  if (!tender) return null

  const resume = tender.llm_resume || tender.description

  return (
    <div className="pt-2 border-t border-ocean-border space-y-2" onClick={(e) => e.stopPropagation()}>
      {resume && (
        <p className="font-sans text-xs text-ocean-text/70 leading-relaxed line-clamp-5">
          {resume}
        </p>
      )}
      <div className="flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs text-ocean-muted">
        {tender.secteur && <span>{tender.secteur}</span>}
        {tender.source && <span>{tender.source}</span>}
        {tender.amount && (
          <span className="text-ocean-gold">
            {new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(tender.amount)}
          </span>
        )}
      </div>
      {tender.llm_structured?.justification && (
        <p className="font-sans text-xs italic text-ocean-muted/80 leading-snug line-clamp-3">
          {tender.llm_structured.justification}
        </p>
      )}
      {tender.url && (
        <a
          href={tender.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-mono text-ocean-cyan hover:text-ocean-teal underline underline-offset-2 transition-colors"
        >
          Voir l'annonce ↗
        </a>
      )}
    </div>
  )
}

export default function KanbanColumn({ title, items = [], actions = [], onStatusChange }) {
  const [expandedId, setExpandedId] = useState(null)

  return (
    <div className="flex flex-col gap-2 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-sans text-sm font-semibold text-ocean-text">{title}</span>
        <span className="font-mono bg-ocean-cyan/8 text-ocean-cyan text-xs font-bold rounded-full px-2 py-px">
          {items.length}
        </span>
      </div>

      {items.length === 0 && (
        <p className="font-sans text-xs text-ocean-muted text-center py-6">Aucun marché</p>
      )}

      {items.map((item) => {
        const isExpanded = expandedId === item.id
        return (
          <article
            key={item.id}
            onClick={() => setExpandedId(isExpanded ? null : item.id)}
            className={`bg-ocean-panel rounded-lg border p-3 flex flex-col gap-2 cursor-pointer transition-colors ${
              isExpanded
                ? 'border-ocean-cyan/40'
                : 'border-ocean-border hover:border-ocean-cyan/20'
            }`}
          >
            <div className="flex items-start justify-between gap-2">
              <p className="font-sans text-sm font-medium text-ocean-text leading-snug flex-1">
                {item.title.length > 60 ? item.title.slice(0, 60) + '…' : item.title}
              </p>
              <span className="text-ocean-muted text-xs shrink-0 mt-0.5">
                {isExpanded ? '▲' : '▼'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs bg-ocean-cyan/8 text-ocean-cyan font-semibold rounded px-1.5 py-0.5">
                {item.score}
              </span>
              <DeadlineBadge jours_restants={item.jours_restants} />
            </div>

            {isExpanded && <KanbanCardDetail id={item.id} />}

            {actions.length > 0 && (
              <div
                className="flex gap-1 flex-wrap mt-1"
                onClick={(e) => e.stopPropagation()}
              >
                {actions.map(({ label, nextStatus }) => (
                  <button
                    key={nextStatus}
                    onClick={() => onStatusChange?.(item.id, nextStatus)}
                    className="font-sans text-xs px-2 py-1 rounded-lg border border-ocean-border text-ocean-muted hover:text-ocean-text hover:bg-ocean-cyan/4 transition-colors"
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
          </article>
        )
      })}
    </div>
  )
}
