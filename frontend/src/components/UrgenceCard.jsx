function urgenceStyle(jours) {
  if (jours < 7) return { accent: 'border-l-2 border-ocean-coral', badge: 'bg-ocean-coral/10 text-ocean-coral', emoji: '🔴' }
  if (jours <= 15) return { accent: 'border-l-2 border-ocean-gold', badge: 'bg-ocean-gold/10 text-ocean-gold', emoji: '🟡' }
  return { accent: 'border-l-2 border-ocean-teal', badge: 'bg-ocean-teal/10 text-ocean-teal', emoji: '🟢' }
}

export default function UrgenceCard({ title, jours_restants, score, source }) {
  const style = urgenceStyle(jours_restants)
  return (
    <div className={`bg-ocean-panel border border-ocean-border rounded-xl p-4 flex flex-col gap-3 ${style.accent}`}>
      <div className="flex items-start justify-between gap-2">
        <span className={`font-mono text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 ${style.badge}`}>
          <span>{style.emoji}</span> <span>J-{jours_restants}</span>
        </span>
        <span className="font-mono text-xs bg-ocean-cyan/8 text-ocean-cyan font-semibold rounded px-1.5 py-0.5">
          {score}
        </span>
      </div>
      <p className="font-sans text-sm font-semibold text-ocean-text line-clamp-2">{title}</p>
      <p className="font-mono text-xs text-ocean-muted">{source}</p>
    </div>
  )
}
