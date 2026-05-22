import { useQueryClient } from '@tanstack/react-query'
import KanbanColumn from '../components/KanbanColumn'
import { usePipeline, useUpdateStatus } from '../hooks/useTenders'

const GO_SCORE = 65

function enrichWithJours(items) {
  return (items || []).map((item) => ({
    ...item,
    jours_restants: item.deadline
      ? Math.ceil((new Date(item.deadline) - new Date()) / 86400000)
      : null,
  }))
}

export default function Direction() {
  const { data: pipeline = {}, isLoading, isError } = usePipeline()
  const { mutate: changeStatus } = useUpdateStatus()
  const qc = useQueryClient()

  const handleStatusChange = (id, status) => {
    changeStatus(
      { id, status },
      { onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline'] }) }
    )
  }

  if (isLoading) {
    return (
      <div className="p-5 grid grid-cols-3 gap-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="space-y-2">
            <div className="h-6 w-24 bg-gray-200 rounded animate-pulse" />
            {Array.from({ length: 3 }).map((_, j) => (
              <div key={j} className="h-24 bg-gray-100 rounded-lg animate-pulse" />
            ))}
          </div>
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="p-5 text-red-600 text-sm">Impossible de charger le pipeline.</p>
  }

  const goItems = enrichWithJours(
    [
      ...(pipeline['À qualifier'] || []),
      ...(pipeline['En cours'] || []),
    ].filter((t) => t.score >= GO_SCORE)
  )

  const soumisItems = enrichWithJours(pipeline['Soumis'] || [])

  const resultatsItems = enrichWithJours([
    ...(pipeline['Gagné'] || []),
    ...(pipeline['Perdu'] || []),
  ])

  return (
    <div className="p-5 space-y-4">
      <p className="text-xs text-gray-500">Marchés publics — score ≥ {GO_SCORE}</p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-start">
        <KanbanColumn
          title="✅ GO"
          items={goItems}
          actions={[{ label: 'Marquer Soumis', nextStatus: 'Soumis' }]}
          onStatusChange={handleStatusChange}
        />
        <KanbanColumn
          title="📤 Soumis"
          items={soumisItems}
          actions={[
            { label: 'Gagné 🏆', nextStatus: 'Gagné' },
            { label: 'Perdu', nextStatus: 'Perdu' },
          ]}
          onStatusChange={handleStatusChange}
        />
        <KanbanColumn
          title="🏆 Résultats"
          items={resultatsItems}
          actions={[]}
        />
      </div>
    </div>
  )
}
