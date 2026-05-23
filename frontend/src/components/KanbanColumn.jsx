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

export default function KanbanColumn({ title, items = [], actions = [], onStatusChange }) {
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

      {items.map((item) => (
        <article
          key={item.id}
          className="bg-ocean-panel rounded-lg border border-ocean-border p-3 flex flex-col gap-2"
        >
          <p className="font-sans text-sm font-medium text-ocean-text leading-snug">
            {item.title.length > 60 ? item.title.slice(0, 60) + '…' : item.title}
          </p>
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs bg-ocean-cyan/8 text-ocean-cyan font-semibold rounded px-1.5 py-0.5">
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
                  className="font-sans text-xs px-2 py-1 rounded-lg border border-ocean-border text-ocean-muted hover:text-ocean-text hover:bg-ocean-cyan/4 transition-colors"
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
