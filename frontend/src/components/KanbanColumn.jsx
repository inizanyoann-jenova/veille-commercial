function DeadlineBadge({ jours_restants }) {
  if (jours_restants === null || jours_restants === undefined) {
    return <span className="text-xs text-gray-400">Pas de deadline</span>
  }
  const color =
    jours_restants < 7
      ? 'text-red-600'
      : jours_restants <= 30
      ? 'text-orange-500'
      : 'text-gray-500'
  return (
    <span className={`text-xs font-medium ${color}`}>
      J-{jours_restants}
    </span>
  )
}

export default function KanbanColumn({ title, items = [], actions = [], onStatusChange }) {
  return (
    <div className="flex flex-col gap-2 min-w-0">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm font-semibold text-gray-700">{title}</span>
        <span className="bg-gray-200 text-gray-600 text-xs font-bold rounded-full px-2 py-px">
          {items.length}
        </span>
      </div>

      {items.length === 0 && (
        <p className="text-xs text-gray-400 text-center py-6">Aucun marché</p>
      )}

      {items.map((item) => (
        <article
          key={item.id}
          className="bg-white rounded-lg border border-gray-200 p-3 flex flex-col gap-2 shadow-sm"
        >
          <p className="text-sm font-medium text-gray-800 leading-snug">
            {item.title.length > 60 ? item.title.slice(0, 60) + '…' : item.title}
          </p>
          <div className="flex items-center justify-between">
            <span className="text-xs bg-indigo-100 text-indigo-700 font-semibold rounded px-1.5 py-0.5">
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
                  className="text-xs px-2 py-1 rounded border border-gray-300 hover:bg-gray-100 transition-colors"
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
