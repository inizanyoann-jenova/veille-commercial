import { useScraperRuns } from '../hooks/useTenders'

function StatusBadge({ status }) {
  if (status === 'ok')
    return <span className="text-xs font-semibold text-green-700 bg-green-100 px-2 py-0.5 rounded-full">✓ ok</span>
  if (status === 'error')
    return <span className="text-xs font-semibold text-red-700 bg-red-100 px-2 py-0.5 rounded-full">✗ erreur</span>
  return <span className="text-xs font-semibold text-blue-700 bg-blue-100 px-2 py-0.5 rounded-full animate-pulse">⟳ en cours</span>
}

function formatDuration(started, finished) {
  if (!started || !finished) return '—'
  const s = Math.round((new Date(finished) - new Date(started)) / 1000)
  return s < 60 ? `${s}s` : `${Math.round(s / 60)}m`
}

function formatTime(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

export default function ScraperRunsTable() {
  const { data: runs = [], isLoading } = useScraperRuns()

  if (isLoading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="h-8 bg-gray-100 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (runs.length === 0) {
    return <p className="text-sm text-gray-400">Aucun historique disponible.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-gray-500 border-b border-gray-200">
            <th className="text-left py-2 pr-4 font-medium">Source</th>
            <th className="text-left py-2 pr-4 font-medium">Heure</th>
            <th className="text-left py-2 pr-4 font-medium">Durée</th>
            <th className="text-left py-2 pr-4 font-medium">Trouvés</th>
            <th className="text-left py-2 pr-4 font-medium">Nouveaux</th>
            <th className="text-left py-2 font-medium">Statut</th>
          </tr>
        </thead>
        <tbody>
          {runs.slice(0, 20).map((r) => (
            <tr key={r.id} className="border-b border-gray-100 hover:bg-gray-50">
              <td className="py-2 pr-4 font-medium text-gray-700">{r.source_name}</td>
              <td className="py-2 pr-4 text-gray-500">{formatTime(r.started_at)}</td>
              <td className="py-2 pr-4 text-gray-500">{formatDuration(r.started_at, r.finished_at)}</td>
              <td className="py-2 pr-4 text-gray-600">{r.nb_found ?? '—'}</td>
              <td className="py-2 pr-4 text-gray-600">{r.nb_new ?? '—'}</td>
              <td className="py-2">
                <StatusBadge status={r.status} />
                {r.error && <span className="ml-2 text-xs text-red-500">{r.error}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
