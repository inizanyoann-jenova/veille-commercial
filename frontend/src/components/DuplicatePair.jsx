function TenderCard({ tender, highlighted }) {
  return (
    <div className={`flex-1 rounded-lg border p-3 ${highlighted ? 'ring-2 ring-indigo-400 bg-indigo-50' : 'bg-gray-50'}`}>
      {highlighted && (
        <span className="text-xs text-indigo-600 font-semibold mb-1 block">Recommandé ✓</span>
      )}
      <p className="text-sm font-semibold text-gray-800 mb-2">{tender.title}</p>
      <div className="flex gap-3 text-xs text-gray-500 flex-wrap">
        <span>Score : <strong>{tender.relevance_score}</strong></span>
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
    <div className="border border-gray-200 rounded-lg p-4 bg-white space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500">Similarité :</span>
        <span className="text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
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
          className="text-xs px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 transition-colors"
        >
          Garder A — archiver B
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'keep', archiveId: pair.tender_a.id })}
          className="text-xs px-3 py-1.5 rounded border border-indigo-300 text-indigo-700 hover:bg-indigo-50 transition-colors"
        >
          Garder B — archiver A
        </button>
        <button
          onClick={() => onResolve({ pairId: pair.id, action: 'ignore', archiveId: null })}
          className="text-xs px-3 py-1.5 rounded border border-gray-300 text-gray-600 hover:bg-gray-100 transition-colors"
        >
          Ignorer
        </button>
      </div>
    </div>
  )
}
