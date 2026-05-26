// frontend/src/components/TenderDetail.jsx
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
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
  if (!gonogo) return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-white/5 text-ocean-muted">—</span>
  if (gonogo === 'GO')
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-ocean-teal/10 text-ocean-teal">🟢 GO</span>
  if (gonogo === 'Étudier')
    return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-ocean-gold/10 text-ocean-gold">🟡 Étudier</span>
  return <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold bg-ocean-coral/10 text-ocean-coral">🔴 Passer</span>
}

function ScoreBar({ label, value, max }) {
  const pct = max > 0 ? Math.round((value / max) * 100) : 0
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-ocean-muted">
        <span>{label}</span>
        <span className="tabular-nums font-medium text-ocean-text/80">{value}/{max}</span>
      </div>
      <div className="h-1.5 bg-white/6 rounded-full">
        <div className="h-1.5 bg-gradient-to-r from-ocean-cyan to-ocean-teal rounded-full" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="p-4 space-y-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="h-16 bg-ocean-panel/50 rounded-xl animate-pulse" />
      ))}
    </div>
  )
}

function TenderDetailHeader({ tender }) {
  return (
    <div className="space-y-3">
      <GonogoBadge gonogo={tender.gonogo} />
      <h2 className="font-serif text-base font-semibold text-ocean-text line-clamp-2">{tender.title}</h2>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ocean-muted">
        <span>
          Score : <strong className="text-ocean-text/80">{tender.relevance_score ?? 0}</strong>/100
        </span>
        <span>
          Deadline : <strong className="text-ocean-text/80">{formatDate(tender.deadline)}</strong>
          {tender.jours_restants != null && (
            <span className={`ml-1 ${
              tender.jours_restants <= 7
                ? 'text-ocean-coral font-bold'
                : tender.jours_restants <= 30
                ? 'text-ocean-gold'
                : ''
            }`}>
              ({tender.jours_restants} j)
            </span>
          )}
        </span>
        <span>Montant : <strong className="text-ocean-text/80">{formatAmount(tender.amount)}</strong></span>
        <span>Secteur : <strong className="text-ocean-text/80">{tender.secteur || '—'}</strong></span>
        <span>Source : <strong className="text-ocean-text/80">{tender.source || '—'}</strong></span>
      </div>
      {tender.url && (
        <a
          href={tender.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-ocean-cyan hover:text-ocean-teal underline underline-offset-2 transition-colors"
        >
          Voir l'annonce ↗
        </a>
      )}
    </div>
  )
}

function TenderDetailActionPlan({ ficheData }) {
  if (!ficheData) return null
  return (
    <div className="space-y-3">
      <h3 className="font-serif font-semibold text-ocean-text">{ficheData.label_action}</h3>
      <ol className="space-y-1.5 pl-5">
        {ficheData.steps.map((step, i) => (
          <li key={i} className="font-sans text-sm text-ocean-text/80 list-decimal">{step}</li>
        ))}
      </ol>
      {ficheData.risques.length > 0 && (
        <div className="space-y-1">
          {ficheData.risques.map((r, i) => (
            <div key={i} className="font-sans text-sm px-3 py-2 bg-ocean-coral/8 border border-ocean-coral/20 rounded text-ocean-coral">
              {r}
            </div>
          ))}
        </div>
      )}
      {ficheData.atouts.length > 0 && (
        <div className="space-y-1">
          {ficheData.atouts.map((a, i) => (
            <div key={i} className="font-sans text-sm px-3 py-2 bg-ocean-teal/8 border border-ocean-teal/20 rounded text-ocean-teal">
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
    <div className="border border-ocean-border rounded-xl">
      <button
        className="w-full flex items-center justify-between px-4 py-2.5 font-sans text-sm font-medium text-ocean-text/80 hover:text-ocean-text hover:bg-ocean-cyan/4 transition-colors rounded-xl"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span>📊 Détail du score & mots-clés</span>
        <span className="text-ocean-muted text-xs">{open ? '▲' : '▼'}</span>
      </button>
      {open && fd && (
        <div className="px-4 pb-4 space-y-3 border-t border-ocean-border">
          <p className="font-mono text-xs font-semibold text-ocean-muted uppercase pt-3">Décomposition du score</p>
          <ScoreBar label="Pertinence métier" value={fd.sm} max={45} />
          <ScoreBar label="Proximité géographique" value={fd.sg} max={30} />
          <ScoreBar label="Mots-clés dans le titre" value={fd.sk} max={15} />
          <ScoreBar label="Maintenance / Récurrence" value={fd.smaint} max={10} />
          <div className="pt-2 space-y-1 font-mono text-xs text-ocean-text/80 border-t border-ocean-border">
            <div><span className="text-ocean-muted">Type : </span>{tender.type_marche || tender.type_opportunite || '—'}</div>
            <div><span className="text-ocean-muted">Territoire : </span>{tender.territoire || '—'}</div>
            <div><span className="text-ocean-muted">Domaine : </span>{tender.domaine || '—'}</div>
            {tender.concurrents && (
              <div><span className="text-ocean-muted">Concurrents : </span>{tender.concurrents}</div>
            )}
          </div>
          {tender.description && (
            <div className="pt-2 border-t border-ocean-border">
              <p className="font-mono text-xs text-ocean-muted uppercase mb-1">Description</p>
              <p className="font-sans text-xs text-ocean-text/80 whitespace-pre-wrap line-clamp-6">{tender.description}</p>
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
      <span className="text-ocean-teal font-semibold">✅ GO</span>
    ) : s.recommandation === 'NON' ? (
      <span className="text-ocean-coral font-semibold">🔴 NON</span>
    ) : (
      <span>—</span>
    )
  return (
    <div className="border border-ocean-border rounded-xl px-4 py-3 space-y-2">
      <p className="font-mono text-xs text-ocean-muted uppercase">🤖 Analyse IA</p>
      <div className="grid grid-cols-2 gap-x-6 gap-y-2 font-sans text-xs text-ocean-text/80">
        <div><span className="text-ocean-muted">Budget estimé</span><br />{s.budget_estime || '—'}</div>
        <div><span className="text-ocean-muted">Type de travaux</span><br />{s.type_travaux || '—'}</div>
        <div><span className="text-ocean-muted">Acheteur</span><br />{s.acheteur_type || '—'}</div>
        <div><span className="text-ocean-muted">Concurrence</span><br />{s.niveau_concurrence || '—'}</div>
        <div>
          <span className="text-ocean-muted">Confiance IA</span><br />
          {s.score_confiance != null ? `${s.score_confiance} %` : '—'}
        </div>
        <div><span className="text-ocean-muted">Recommandation</span><br />{recoBadge}</div>
      </div>
      {s.lots && s.lots.length > 0 && (
        <p className="font-sans text-xs text-ocean-text/80">
          <span className="text-ocean-muted">Lots : </span>{s.lots.join(' · ')}
        </p>
      )}
      {s.justification && (
        <p className="font-sans text-xs text-ocean-muted italic">{s.justification}</p>
      )}
    </div>
  )
}

function TenderDetailActions({ tender }) {
  const updateStatus = useUpdateStatus()
  const updateSaved = useUpdateSaved()
  return (
    <div className="flex items-center gap-3 pt-2 border-t border-ocean-border">
      <select
        value={tender.status}
        onChange={(e) => updateStatus.mutate({ id: tender.id, status: e.target.value })}
        disabled={updateStatus.isPending}
        aria-label="Qualifier le marché"
        className="font-sans text-sm border border-ocean-border rounded-lg px-2 py-1.5 bg-ocean-navy text-ocean-text flex-1 focus:border-ocean-cyan/20 focus:outline-none"
      >
        {STATUTS.map((s) => <option key={s}>{s}</option>)}
      </select>
      <button
        onClick={() => updateSaved.mutate({ id: tender.id, is_saved: !tender.is_saved })}
        disabled={updateSaved.isPending}
        aria-label={tender.is_saved ? 'Retirer des favoris' : 'Sauvegarder'}
        className={`text-xl px-2 py-1 rounded transition-colors ${
          tender.is_saved
            ? 'text-ocean-gold hover:text-ocean-gold/80'
            : 'text-ocean-muted hover:text-ocean-gold'
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

  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-black/60"
      onClick={onClose}
      aria-hidden="true"
    >
      <div
        role="dialog"
        aria-label="Fiche marché"
        className="w-full max-w-[640px] max-h-[88vh] bg-ocean-panel border border-ocean-border rounded-2xl overflow-y-auto shadow-2xl flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-ocean-border shrink-0 bg-ocean-navy rounded-t-2xl">
          <span className="font-sans text-sm font-medium text-ocean-muted">Fiche marché</span>
          <button
            onClick={onClose}
            aria-label="Fermer"
            className="text-ocean-muted hover:text-ocean-text transition-colors text-lg leading-none"
          >
            ✕
          </button>
        </div>

        {isLoading && <LoadingSkeleton />}
        {isError && (
          <p className="p-6 text-ocean-coral text-sm">Impossible de charger ce marché.</p>
        )}
        {tender && (
          <div className="p-4 space-y-5">
            <TenderDetailHeader tender={tender} />
            <hr className="border-ocean-border" />
            <TenderDetailActionPlan ficheData={tender.fiche_data} />
            <TenderDetailTechnical tender={tender} />
            {tender.llm_structured && (
              <TenderDetailAI llmStructured={tender.llm_structured} />
            )}
            <TenderDetailActions tender={tender} />
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}
