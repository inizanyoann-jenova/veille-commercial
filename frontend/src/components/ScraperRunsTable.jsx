import { useScraperRuns } from '../hooks/useTenders'

function StatusBadge({ status }) {
  if (status === 'ok')
    return <span className="text-xs font-semibold text-ocean-teal bg-ocean-teal/10 px-2 py-0.5 rounded-full">✓ ok</span>
  if (status === 'error')
    return <span className="text-xs font-semibold text-ocean-coral bg-ocean-coral/10 px-2 py-0.5 rounded-full">✗ erreur</span>
  return <span className="text-xs font-semibold text-ocean-cyan bg-ocean-cyan/10 px-2 py-0.5 rounded-full animate-pulse">⟳ en cours</span>
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
          <div key={i} className="h-8 bg-ocean-panel/50 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (runs.length === 0) {
    return <p className="text-sm text-ocean-muted">Aucun historique disponible.</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs uppercase text-ocean-muted border-b border-ocean-border">
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
            <tr key={r.id} className="border-b border-ocean-border hover:bg-ocean-cyan/4">
              <td className="py-2 pr-4 font-medium text-ocean-text">{r.source_name}</td>
              <td className="py-2 pr-4 text-ocean-muted">{formatTime(r.started_at)}</td>
              <td className="py-2 pr-4 text-ocean-muted">{formatDuration(r.started_at, r.finished_at)}</td>
              <td className="py-2 pr-4 text-ocean-text/80">{r.nb_found ?? '—'}</td>
              <td className="py-2 pr-4 text-ocean-text/80">{r.nb_new ?? '—'}</td>
              <td className="py-2">
                <StatusBadge status={r.status} />
                {r.error && <span className="ml-2 text-xs text-ocean-coral">{r.error}</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
