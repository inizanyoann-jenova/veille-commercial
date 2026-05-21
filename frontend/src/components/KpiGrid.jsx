import { useKpisPublic } from '../hooks/useTenders'

const KPI_CARDS = [
  { key: 'total',       label: 'Total marchés', icon: '📋', colorClass: 'bg-blue-50 border-blue-200 text-blue-700'   },
  { key: 'a_qualifier', label: 'À qualifier',   icon: '🔍', colorClass: 'bg-slate-50 border-slate-200 text-slate-700'  },
  { key: 'en_cours',   label: 'En cours',       icon: '⚙️', colorClass: 'bg-indigo-50 border-indigo-200 text-indigo-700' },
  { key: 'soumis',     label: 'Soumis',         icon: '📤', colorClass: 'bg-amber-50 border-amber-200 text-amber-700'  },
  { key: 'gagnes',     label: 'Gagnés',         icon: '✅', colorClass: 'bg-green-50 border-green-200 text-green-700'  },
]

export default function KpiGrid() {
  const { data, isLoading, isError } = useKpisPublic()

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-20 rounded-lg border bg-gray-100 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="text-red-600 text-sm">Impossible de charger les KPIs.</p>
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
      {KPI_CARDS.map(({ key, label, icon, colorClass }) => (
        <div key={key} className={`rounded-lg border p-4 flex flex-col gap-1 ${colorClass}`}>
          <span className="text-xs font-medium uppercase tracking-wide opacity-70">
            {icon} {label}
          </span>
          <span className="text-3xl font-bold">{data?.[key] ?? 0}</span>
        </div>
      ))}
    </div>
  )
}
