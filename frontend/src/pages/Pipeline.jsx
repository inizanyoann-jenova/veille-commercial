import { usePipeline, useUpdateStatus } from '../hooks/useTenders'
import KanbanColumn from '../components/KanbanColumn'

function daysDiff(deadline) {
  if (!deadline) return null
  return Math.ceil((new Date(deadline) - Date.now()) / 86400000)
}

function enrich(items) {
  return items.map((t) => ({ ...t, jours_restants: daysDiff(t.deadline) }))
}

function KpiChip({ label, value, color = 'cyan' }) {
  const colors = {
    cyan: 'bg-ocean-cyan/8 text-ocean-cyan border-ocean-cyan/20',
    teal: 'bg-ocean-teal/8 text-ocean-teal border-ocean-teal/20',
    gold: 'bg-ocean-gold/8 text-ocean-gold border-ocean-gold/20',
    coral: 'bg-ocean-coral/8 text-ocean-coral border-ocean-coral/20',
  }
  return (
    <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-mono text-sm ${colors[color]}`}>
      <span className="font-bold">{value}</span>
      <span className="text-xs opacity-70">{label}</span>
    </div>
  )
}

export default function Pipeline() {
  const { data, isLoading } = usePipeline()
  const { mutate: changeStatus } = useUpdateStatus()

  const go     = enrich(data?.go ?? [])
  const soumis = enrich(data?.soumis ?? [])
  const gagnes = enrich((data?.resultats ?? []).filter((t) => t.status === 'Gagné'))
  const perdus = enrich((data?.resultats ?? []).filter((t) => t.status === 'Perdu'))

  const onStatusChange = (id, status) => changeStatus({ id, status })

  if (isLoading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-5 bg-ocean-panel/60 rounded animate-pulse w-48" />
        <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-3 bg-ocean-panel/60 rounded animate-pulse w-24" />
              {[...Array(3)].map((_, j) => (
                <div key={j} className="h-20 bg-ocean-panel/40 rounded animate-pulse" />
              ))}
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="font-serif text-xl font-bold text-ocean-text">Pipeline commercial</h1>
        <div className="flex flex-wrap gap-2">
          <KpiChip label="à soumettre" value={go.length} color="cyan" />
          <KpiChip label="soumis" value={soumis.length} color="gold" />
          <KpiChip label="gagné" value={gagnes.length} color="teal" />
          <KpiChip label="perdu" value={perdus.length} color="coral" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 items-start">
        <KanbanColumn
          title="À soumettre"
          items={go}
          actions={[{ label: 'Soumettre →', nextStatus: 'Soumis' }]}
          onStatusChange={onStatusChange}
        />
        <KanbanColumn
          title="Soumis"
          items={soumis}
          actions={[
            { label: 'Gagné ✓', nextStatus: 'Gagné' },
            { label: 'Perdu ✗', nextStatus: 'Perdu' },
          ]}
          onStatusChange={onStatusChange}
        />
        <KanbanColumn
          title="Gagné"
          items={gagnes}
          actions={[]}
        />
        <KanbanColumn
          title="Perdu"
          items={perdus}
          actions={[]}
        />
      </div>
    </div>
  )
}
