// frontend/src/components/TendersTable.jsx
import { useMemo } from 'react'
import { useTenders } from '../hooks/useTenders'

const STATUTS = ['Tous', 'À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']
const SECTEURS = ['Public', 'Privé', 'International']

function GonogoBadge({ gonogo }) {
  if (!gonogo) return <span className="text-gray-400 text-xs">—</span>
  if (gonogo === 'GO')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-green-100 text-green-800">
        🟢 GO
      </span>
    )
  if (gonogo === 'Étudier')
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-800">
        🟡 Étudier
      </span>
    )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-800">
      🔴 Passer
    </span>
  )
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

export default function TendersTable({
  status,
  secteur,
  searchText,
  onStatusChange,
  onSecteurChange,
  onSearchChange,
  onRowClick,
}) {
  const { data: tenders = [], isLoading, isError } = useTenders({ status, secteur })

  const filtered = useMemo(() => {
    if (!searchText) return tenders
    const q = searchText.toLowerCase()
    return tenders.filter((t) =>
      `${t.title} ${t.domaine} ${t.territoire}`.toLowerCase().includes(q)
    )
  }, [tenders, searchText])

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Filtres */}
      <div className="flex flex-wrap gap-3 items-center p-4 border-b border-gray-100 bg-gray-50">
        <select
          value={status}
          onChange={(e) => onStatusChange(e.target.value)}
          aria-label="Filtrer par statut"
          className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white"
        >
          {STATUTS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          value={secteur}
          onChange={(e) => onSecteurChange(e.target.value)}
          aria-label="Filtrer par secteur"
          className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white"
        >
          {SECTEURS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <input
          type="text"
          value={searchText}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Rechercher un marché…"
          aria-label="Rechercher un marché"
          className="text-sm border border-gray-300 rounded px-2 py-1.5 flex-1 min-w-[200px]"
        />
      </div>

      {/* Corps */}
      {isLoading && (
        <div className="space-y-2 p-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-gray-100 rounded animate-pulse" />
          ))}
        </div>
      )}

      {isError && (
        <p className="p-4 text-red-600 text-sm">Impossible de charger les marchés.</p>
      )}

      {!isLoading && !isError && filtered.length === 0 && (
        <p className="p-8 text-center text-gray-400 text-sm">Aucun marché trouvé.</p>
      )}

      {!isLoading && !isError && filtered.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 text-xs uppercase text-gray-500 bg-gray-50">
                <th className="text-left px-4 py-3 font-medium">Titre</th>
                <th className="text-left px-4 py-3 font-medium">Domaine</th>
                <th className="text-left px-4 py-3 font-medium">Territoire</th>
                <th className="text-left px-4 py-3 font-medium">Deadline</th>
                <th className="text-left px-4 py-3 font-medium">Score</th>
                <th className="text-left px-4 py-3 font-medium">GO/NO-GO</th>
                <th className="text-left px-4 py-3 font-medium">Statut</th>
                <th className="text-left px-4 py-3 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((t) => (
                <tr
                  key={t.id}
                  onClick={() => onRowClick?.(t.id)}
                  className="border-b border-gray-50 hover:bg-gray-50 transition-colors cursor-pointer"
                >
                  <td className="px-4 py-3 font-medium text-gray-900 max-w-xs truncate">
                    {t.title}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.domaine || '—'}</td>
                  <td className="px-4 py-3 text-gray-600">{t.territoire || '—'}</td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {formatDate(t.deadline)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="bg-indigo-500 h-1.5 rounded-full"
                          style={{ width: `${Math.min(t.relevance_score ?? 0, 100)}%` }}
                        />
                      </div>
                      <span className="text-gray-700 tabular-nums">{t.relevance_score ?? 0}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <GonogoBadge gonogo={t.gonogo} />
                  </td>
                  <td className="px-4 py-3 text-gray-600">{t.status}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{t.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
