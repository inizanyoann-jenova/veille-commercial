import UrgenceCard from '../components/UrgenceCard'
import { useUrgences } from '../hooks/useTenders'

export default function Urgences() {
  const { data: urgences = [], isLoading, isError } = useUrgences()

  if (isLoading) {
    return (
      <div className="p-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-32 bg-ocean-panel/50 rounded-xl animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <p className="p-6 text-ocean-coral text-sm">Impossible de charger les urgences.</p>
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="font-sans text-sm font-semibold text-ocean-text">Marchés à traiter en urgence</h2>
        {urgences.length > 0 && (
          <span className="bg-ocean-coral text-white font-mono text-xs font-bold rounded-full px-2 py-px shadow shadow-ocean-coral/40">
            {urgences.length}
          </span>
        )}
      </div>

      {urgences.length === 0 ? (
        <div className="text-center py-16 text-ocean-muted">
          <p className="text-3xl mb-2">✅</p>
          <p className="font-sans text-sm">Aucun marché urgent pour le moment.</p>
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
                score={u.relevance_score ?? u.score}
                source={u.source}
                url={u.url}
                description={u.description}
                secteur={u.secteur}
                amount={u.amount}
                llm_resume={u.llm_resume}
              />
            )
          })}
        </div>
      )}
    </div>
  )
}
