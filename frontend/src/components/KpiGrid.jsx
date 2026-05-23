import { useKpisPublic } from '../hooks/useTenders'

const KPI_CARDS = [
  { key: 'total',       label: 'Total marchés', icon: '📋', topColor: 'border-t-2 border-ocean-cyan' },
  { key: 'a_qualifier', label: 'À qualifier',   icon: '🔍', topColor: 'border-t-2 border-ocean-muted' },
  { key: 'en_cours',   label: 'En cours',       icon: '⚙️', topColor: 'border-t-2 border-ocean-teal' },
  { key: 'soumis',     label: 'Soumis',         icon: '📤', topColor: 'border-t-2 border-ocean-gold' },
  { key: 'gagnes',     label: 'Gagnés',         icon: '✅', topColor: 'border-t-2 border-ocean-teal' },
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
        <div key={key} className={`bg-ocean-panel border border-ocean-border rounded-xl p-5 flex flex-col gap-1 hover:-translate-y-0.5 hover:shadow-lg hover:shadow-ocean-cyan/6 transition-all duration-200 ${topColor}`}>
          <span className="font-sans text-xs uppercase tracking-widest text-ocean-muted">{icon} {label}</span>
          <span className="font-serif text-4xl font-bold text-ocean-text">{data?.[key] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}
