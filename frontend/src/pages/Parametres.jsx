import { useState } from 'react'
import ScraperRunsTable from '../components/ScraperRunsTable'
import DuplicatePair from '../components/DuplicatePair'
import {
  useSources,
  useCollectMutation,
  useAnalyzePending,
  useDuplicates,
  useDetectDuplicates,
  useResolveDuplicate,
  useArchiveOld,
  useResetDb,
} from '../hooks/useTenders'

function SectionTitle({ children }) {
  return (
    <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide border-b border-gray-200 pb-2 mb-4">
      {children}
    </h2>
  )
}

function CollectSection() {
  const { data: sources = [] } = useSources()
  const { mutate: collect, isPending, data: collectResult } = useCollectMutation()
  const enabled = sources.filter((s) => s.enabled && !s.is_manual)
  const [selected, setSelected] = useState(null)

  const toggle = (name) => {
    setSelected((prev) => {
      if (prev === null) {
        const all = enabled.map((s) => s.name).filter((n) => n !== name)
        return all.length === 0 ? null : all
      }
      if (prev.includes(name)) {
        const next = prev.filter((n) => n !== name)
        return next.length === 0 ? null : next
      }
      const next = [...prev, name]
      return next.length === enabled.length ? null : next
    })
  }

  const isChecked = (name) => selected === null || selected.includes(name)

  return (
    <div className="space-y-4">
      <SectionTitle>🔄 Collecte des sources</SectionTitle>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-2">
        {enabled.map((s) => (
          <label key={s.name} className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={isChecked(s.name)}
              onChange={() => toggle(s.name)}
              className="rounded"
            />
            <span className="text-gray-700">{s.name}</span>
          </label>
        ))}
      </div>
      <button
        onClick={() => collect(selected)}
        disabled={isPending}
        className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {isPending ? 'Collecte en cours…' : 'Lancer la collecte'}
      </button>
      {collectResult && Array.isArray(collectResult) && (
        <div className="space-y-1 mt-2">
          {collectResult.map((r) => (
            <div key={r.source} className="flex items-center gap-3 text-sm">
              <span className={r.status === 'ok' ? 'text-green-600' : 'text-red-600'}>
                {r.status === 'ok' ? '✓' : '✗'}
              </span>
              <span className="font-medium w-32 truncate">{r.source}</span>
              {r.status === 'ok' && <span className="text-gray-500">+{r.nb_new} nouveaux</span>}
              {r.status === 'error' && <span className="text-red-500 text-xs">{r.error}</span>}
            </div>
          ))}
        </div>
      )}
      <div className="mt-4">
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide mb-2">Historique des runs</p>
        <ScraperRunsTable />
      </div>
    </div>
  )
}

function AnalyseSection() {
  const { mutate: analyze, isPending, data } = useAnalyzePending()
  return (
    <div className="space-y-4">
      <SectionTitle>🤖 Analyse LLM</SectionTitle>
      <p className="text-sm text-gray-600">
        Lance l'analyse IA sur les marchés qui n'ont pas encore été analysés.
      </p>
      <button
        onClick={() => analyze()}
        disabled={isPending}
        className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
      >
        {isPending ? 'Analyse en cours…' : 'Analyser les marchés en attente'}
      </button>
      {data && (
        <p className="text-sm text-green-700">
          ✓ {data.message ?? 'Analyse lancée en arrière-plan.'}
        </p>
      )}
    </div>
  )
}

function DoublonsSection() {
  const { data: duplicates = [], isLoading } = useDuplicates()
  const { mutate: detect, isPending: detecting, data: detectResult } = useDetectDuplicates()
  const { mutate: resolve } = useResolveDuplicate()
  return (
    <div className="space-y-4">
      <SectionTitle>🔍 Détection des doublons</SectionTitle>
      <div className="flex items-center gap-4">
        <button
          onClick={() => detect()}
          disabled={detecting}
          className="px-4 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {detecting ? 'Détection en cours…' : 'Détecter les doublons'}
        </button>
        {detectResult !== undefined && (
          <p className="text-sm text-gray-700">
            {detectResult?.new_pairs ?? 0} nouvelle(s) paire(s) détectée(s).
          </p>
        )}
      </div>
      {isLoading && <p className="text-sm text-gray-400">Chargement…</p>}
      {!isLoading && duplicates.length === 0 && (
        <p className="text-sm text-gray-400">Aucun doublon non résolu.</p>
      )}
      <div className="space-y-3">
        {duplicates.map((pair) => (
          <DuplicatePair key={pair.id} pair={pair} onResolve={resolve} />
        ))}
      </div>
    </div>
  )
}

function MaintenanceSection() {
  const { mutate: archive, isPending: archiving, data: archiveResult } = useArchiveOld()
  const { mutate: reset, isPending: resetting } = useResetDb()
  const [showConfirm, setShowConfirm] = useState(false)
  return (
    <div className="space-y-4">
      <SectionTitle>🛠️ Maintenance</SectionTitle>
      <div className="flex flex-wrap gap-3 items-center">
        <button
          onClick={() => archive()}
          disabled={archiving}
          className="px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded border border-gray-300 hover:bg-gray-200 disabled:opacity-50 transition-colors"
        >
          {archiving ? 'Archivage…' : 'Archiver les marchés > 30 jours'}
        </button>
        {archiveResult && (
          <span className="text-sm text-gray-600">✓ {archiveResult.archived ?? 0} archivé(s)</span>
        )}
      </div>
      <div>
        {!showConfirm ? (
          <button
            onClick={() => setShowConfirm(true)}
            className="px-4 py-2 bg-red-50 text-red-700 text-sm rounded border border-red-300 hover:bg-red-100 transition-colors"
          >
            Réinitialiser la base de données
          </button>
        ) : (
          <div className="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700 font-medium">
              ⚠️ Cette action est irréversible. Confirmer ?
            </p>
            <button
              onClick={() => { reset(); setShowConfirm(false) }}
              disabled={resetting}
              className="px-3 py-1.5 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
            >
              Oui, réinitialiser
            </button>
            <button
              onClick={() => setShowConfirm(false)}
              className="px-3 py-1.5 bg-white text-gray-700 text-xs rounded border border-gray-300 hover:bg-gray-100"
            >
              Annuler
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Parametres() {
  return (
    <div className="p-5 space-y-10 max-w-4xl">
      <CollectSection />
      <AnalyseSection />
      <DoublonsSection />
      <MaintenanceSection />
    </div>
  )
}
