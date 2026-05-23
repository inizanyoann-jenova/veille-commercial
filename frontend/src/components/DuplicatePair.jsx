function TenderCard({ tender, highlighted }) {
  return (
    <div className={`flex-1 rounded-xl border p-3 ${highlighted ? 'ring-1 ring-ocean-cyan/40 bg-ocean-cyan/5 border-ocean-cyan/30' : 'bg-ocean-panel border-ocean-border'}`}>
      {highlighted && (
        <span className="font-mono text-xs text-ocean-cyan font-semibold mb-1 block">Recommandé ✓</span>
      )}
      <p className="font-sans text-sm font-semibold text-ocean-text mb-2">{tender.title}</p>
      <div className="flex gap-3 font-mono text-xs text-ocean-muted flex-wrap">
        <span>Score : <strong className="text-ocean-text/80">{tender.relevance_score}</strong></span>
        <span>Source : {tender.source}</span>
        {tender.deadline && (
          <span>Deadline : {new Date(tender.deadline).toLocaleDateString('fr-FR')}</span>
        )}
      </div>
    </div>
  )
}

export default function DuplicatePair({ pair, onResolve }) {
  const aIsHigher = pair.tender_a.relevance_score >= pair.tender_b.relevance_score

  return (
    <div className="border border-ocean-border rounded-xl p-4 bg-ocean-panel space-y-3">
      <div className="flex items-center gap-2">
        <span className="font-sans text-xs text-ocean-muted">Similarité :</span>
        <span className="font-mono text-xs font-bold text-ocean-gold bg-ocean-gold/10 px-2 py-0.5 rounded-full">
          {Math.round(pair.similarity_score * 100)}%
        </span>
      </div>

      <div className="flex gap-3">
        <TenderCard tender={pair.tender_a} highlighted={aIsHigher} />
        <TenderCard tender={pair.tender_b} highlighted={!aIsHigher} />
      </div>

      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', archiveId: pair.tender_b.id })}
          className="font-sans text-xs px-3 py-1.5 rounded-lg border border-ocean-cyan/20 text-ocean-cyan hover:bg-ocean-cyan/8 transition-colors"
        >
          Garder A — archiver B
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', archiveId: pair.tender_a.id })}
          className="font-sans text-xs px-3 py-1.5 rounded-lg border border-ocean-cyan/20 text-ocean-cyan hover:bg-ocean-cyan/8 transition-colors"
        >
          Garder B — archiver A
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'ignore', archiveId: null })}
          className="font-sans text-xs px-3 py-1.5 rounded-lg border border-ocean-border text-ocean-muted hover:bg-white/4 transition-colors"
        >
          Ignorer
        </button>
      </div>
    </div>
  )
}
