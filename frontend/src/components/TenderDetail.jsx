// frontend/src/components/TenderDetail.jsx
import { useEffect, useState } from 'react'
import { useTender, useUpdateStatus, useUpdateSaved } from '../hooks/useTenders'

const STATUTS = ['À qualifier', 'En cours', 'Soumis', 'Gagné', 'Perdu']

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('fr-FR')
}

function formatAmount(amount) {
  if (!amount) return '—'
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency', currency: 'EUR', maximumFractionDigits: 0,
  }).format(amount)
}

function GonogoBadge({ gonogo }) {
  if (!gonogo) return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-gray-100 text-gray-500">—</span>
  if (gonogo === 'GO')
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-green-100 text-green-800">🟢 GO</span>
  if (gonogo === 'Étudier')
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-yellow-100 text-yellow-800">🟡 Étudier</span>
  return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-red-100 text-red-800">🔴 Passer</span>
}

function ScoreBar({ label, value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-600">
        <span>{label}</span>
        <span className="tabular-nums font-medium">{value}/{max}</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full">
        <div className="h-2 bg-indigo-500 rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-16 bg-gray-100 rounded animate-pulse" />
      ))}
    </div>
  )
}

function TenderDetailHeader({ tender }) {
  return (
    <div className="space-y-3">
      <GonogoBadge gonogo={tender.gonogo} />
      <h2 className="text-base font-semibold text-gray-900 line-clamp-2">{tender.title}</h2>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500">
        <span>
          Score : <strong className="text-gray-700">{tender.relevance_score ?? 0}</strong>/100
        </span>
        <span>
          Deadline : <strong className="text-gray-700">{formatDate(tender.deadline)}</strong>
          {tender.jours_restants != null && (
            <span className={`ml-1 ${
              tender.jours_restants <= 7
                ? 'text-red-600 font-bold'
                : tender.jours_restants <= 30
                ? 'text-orange-500'
                : ''
            }`}>
              ({tender.jours_restants} j)
            </span>
          )}
        </span>
        <span>Montant : <strong className="text-gray-700">{formatAmount(tender.amount)}</strong></span>
        <span>Secteur : <strong className="text-gray-700">{tender.secteur || '—'}</strong></span>
        <span>Source : <strong className="text-gray-700">{tender.source || '—'}</strong></span>
      </div>
    </div>
  )
}

function TenderDetailActionPlan({ ficheData }) {
  if (!ficheData) return null
  return (
    <div className="space-y-3">
      <h3 className="font-semibold text-gray-800">{ficheData.label_action}</h3>
      <ol className="space-y-1.5 pl-5">
        {ficheData.steps.map((step, i) => (
          <li key={i} className="text-sm text-gray-700 list-decimal">{step}</li>
        ))}
      </ol>
      {ficheData.risques.length > 0 && (
        <div className="space-y-1">
          {ficheData.risques.map((r, i) => (
            <div key={i} className="text-sm px-3 py-2 bg-orange-50 border border-orange-200 rounded text-orange-800">
              {r}
            </div>
          ))}
        </div>
      )}
      {ficheData.atouts.length > 0 && (
        <div className="space-y-1">
          {ficheData.atouts.map((a, i) => (
            <div key={i} className="text-sm px-3 py-2 bg-green-50 border border-green-200 rounded text-green-800">
              {a}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function TenderDetailTechnical({ tender }) {
  const [open, setOpen] = useState(false)
  const fd = tender.fiche_data
  return (
    <div className="border border-gray-200 rounded">
      <button
        className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span>📊 Détail du score & mots-clés</span>
        <span className="text-gray-400 text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && fd && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-100">
          <p className="text-xs font-semibold text-gray-500 uppercase pt-3">Décomposition du score</p>
          <ScoreBar label="Pertinence métier" value={fd.sm} max={45} />
          <ScoreBar label="Proximité géographique" value={fd.sg} max={30} />
          <ScoreBar label="Mots-clés dans le titre" value={fd.sk} max={15} />
          <ScoreBar label="Maintenance / Récurrence" value={fd.smaint} max={10} />
          <div className="pt-2 space-y-1 text-xs text-gray-600 border-t border-gray-100">
            <div><span className="font-medium">Type : </span>{tender.type_marche || tender.type_opportunite || '—'}</div>
            <div><span className="font-medium">Territoire : </span>{tender.territoire || '—'}</div>
            <div><span className="font-medium">Domaine : </span>{tender.domaine || '—'}</div>
            {tender.concurrents && (
              <div><span className="font-medium">Concurrents : </span>{tender.concurrents}</div>
            )}
          </div>
          {tender.description && (
            <div className="pt-2 border-t border-gray-100">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-1">Description</p>
              <p className="text-xs text-gray-600 whitespace-pre-wrap line-clamp-6">{tender.description}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function TenderDetailAI({ llmStructured }) {
  const s = llmStructured
  const recoBadge =
    s.recommandation === 'GO' ? (
      <span className="text-green-700 font-semibold">✅ GO</span>
    ) : s.recommandation === 'NON' ? (
      <span className="text-red-700 font-semibold">🔴 NON</span>
    ) : (
      <span>—</span>
    )
  return (
    <div className="border border-gray-200 rounded px-4 py-3 space-y-2">
      <p className="text-xs font-semibold text-gray-500 uppercase">🤖 Analyse IA</p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-xs text-gray-700">
        <div><span className="font-medium">Budget estimé</span><br />{s.budget_estime || '—'}</div>
        <div><span className="font-medium">Type de travaux</span><br />{s.type_travaux || '—'}</div>
        <div><span className="font-medium">Acheteur</span><br />{s.acheteur_type || '—'}</div>
        <div><span className="font-medium">Concurrence</span><br />{s.niveau_concurrence || '—'}</div>
        <div>
          <span className="font-medium">Confiance IA</span><br />
          {s.score_confiance != null ? `${s.score_confiance} %` : '—'}
        </div>
        <div><span className="font-medium">Recommandation</span><br />{recoBadge}</div>
      </div>
      {s.lots && s.lots.length > 0 && (
        <p className="text-xs text-gray-600">
          <span className="font-medium">Lots : </span>{s.lots.join(' · ')}
        </p>
      )}
      {s.justification && (
        <p className="text-xs text-gray-500 italic">{s.justification}</p>
      )}
    </div>
  )
}

function TenderDetailActions({ tender }) {
  const updateStatus = useUpdateStatus()
  const updateSaved = useUpdateSaved()
  return (
    <div className="flex items-center gap-3 pt-2 border-t border-gray-100">
      <select
        value={tender.status}
        onChange={(e) => updateStatus.mutate({ id: tender.id, status: e.target.value })}
        disabled={updateStatus.isPending}
        aria-label="Qualifier le marché"
        className="text-sm border border-gray-300 rounded px-2 py-1.5 bg-white flex-1"
      >
        {STATUTS.map((s) => <option key={s}>{s}</option>)}
      </select>
      <button
        onClick={() => updateSaved.mutate({ id: tender.id, is_saved: !tender.is_saved })}
        disabled={updateSaved.isPending}
        aria-label={tender.is_saved ? 'Retirer des favoris' : 'Sauvegarder'}
        className={`text-xl px-2 py-1 rounded transition-colors ${
          tender.is_saved
            ? 'text-yellow-500 hover:text-yellow-600'
            : 'text-gray-300 hover:text-yellow-400'
        }`}
      >
        {tender.is_saved ? '⭐' : '☆'}
      </button>
    </div>
  )
}

export default function TenderDetail({ tenderId, onClose }) {
  useEffect(() => {
    if (!tenderId) return
    const handler = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [tenderId, onClose])

  const { data: tender, isLoading, isError } = useTender(tenderId)

  if (!tenderId) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        role="dialog"
        aria-label="Fiche marché"
        className="fixed right-0 top-0 bottom-0 w-[480px] z-50 bg-white overflow-y-auto shadow-xl flex flex-col"
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 shrink-0">
          <span className="text-sm font-medium text-gray-500">Fiche marché</span>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="text-gray-400 hover:text-gray-600 text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {isLoading && <LoadingSkeleton />}
        {isError && (
          <p className="p-6 text-red-600 text-sm">Impossible de charger ce marché.</p>
        )}
        {tender && (
          <div className="p-4 space-y-5">
            <TenderDetailHeader tender={tender} />
            <hr className="border-gray-100" />
            <TenderDetailActionPlan ficheData={tender.fiche_data} />
            <TenderDetailTechnical tender={tender} />
            {tender.llm_structured && (
              <TenderDetailAI llmStructured={tender.llm_structured} />
            )}
            <TenderDetailActions tender={tender} />
          </div>
        )}
      </div>
    </>
  )
}
