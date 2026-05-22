function urgenceStyle(jours) {
  if (jours < 7) return { bg: 'bg-red-100 border-red-300', badge: 'bg-red-100 text-red-700', emoji: '🔴' }
  if (jours <= 15) return { bg: 'bg-orange-50 border-orange-300', badge: 'bg-orange-100 text-orange-700', emoji: '🟡' }
  return { bg: 'bg-green-50 border-green-300', badge: 'bg-green-100 text-green-700', emoji: '🟢' }
}

export default function UrgenceCard({ title, jours_restants, score, source }) {
  const style = urgenceStyle(jours_restants)
  return (
    <div className={`rounded-lg border p-4 flex flex-col gap-3 ${style.bg}`}>
      <div className="flex items-start justify-between gap-2">
        <span className={`text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 ${style.badge}`}>
          <span>{style.emoji}</span> <span>J-{jours_restants}</span>
        </span>
        <span className="text-xs bg-indigo-100 text-indigo-700 font-semibold rounded px-1.5 py-0.5">
          {score}
        </span>
      </div>
      <p className="text-sm font-semibold text-gray-800 line-clamp-2">{title}</p>
      <p className="text-xs text-gray-500">{source}</p>
    </div>
  )
}
