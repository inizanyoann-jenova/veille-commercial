import UrgenceCard from '../components/UrgenceCard'
import { useUrgences } from '../hooks/useTenders'

export default function Urgences() {
  const { data: urgences = [], isLoading, isError } = useUrgences()

  if (isLoading) {
    return (
      <div className="p-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-gray-100 rounded-lg animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="p-5 text-red-600 text-sm">Impossible de charger les urgences.</p>
  }

  return (
    <div className="p-5 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-sm font-semibold text-gray-700">Marchés à traiter en urgence</h2>
        {urgences.length > 0 && (
          <span className="bg-red-500 text-white text-xs font-bold rounded-full px-2 py-px">
            {urgences.length}
          </span>
        )}
      </div>

      {urgences.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          <p className="text-3xl mb-2">✅</p>
          <p className="text-sm">Aucun marché urgent pour le moment.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {urgences.map((u) => {
            const jours = u.jours_restants ?? Math.ceil((new Date(u.deadline) - new Date()) / 86400000)
            return (
              <UrgenceCard
                key={u.id}
                title={u.title}
                jours_restants={jours}
                score={u.relevance_score}
                source={u.source}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
