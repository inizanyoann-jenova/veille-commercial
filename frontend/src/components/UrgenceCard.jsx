function urgenceStyle(jours) {
  if (jours < 7) return { accent: 'border-l-2 border-ocean-coral', badge: 'bg-ocean-coral/10 text-ocean-coral', emoji: '🔴' }
  if (jours <= 15) return { accent: 'border-l-2 border-ocean-gold', badge: 'bg-ocean-gold/10 text-ocean-gold', emoji: '🟡' }
  return { accent: 'border-l-2 border-ocean-teal', badge: 'bg-ocean-teal/10 text-ocean-teal', emoji: '🟢' }
}

const EUR = new Intl.NumberFormat('fr-FR', {
  style: 'currency',
  currency: 'EUR',
  maximumFractionDigits: 0,
})

export default function UrgenceCard({
  title,
  jours_restants,
  score,
  source,
  url,
  description,
  secteur,
  amount,
  llm_resume,
}) {
  const style = urgenceStyle(jours_restants)
  const contenu = llm_resume ?? description

  return (
    <div className={`bg-ocean-panel border border-ocean-border rounded-xl p-4 flex flex-col gap-3 ${style.accent}`}>
      {/* Ligne 1 : badge J-X + score + lien annonce */}
      <div className="flex items-center justify-between gap-2">
        <span className={`font-mono text-xs font-bold px-2 py-1 rounded-full flex-shrink-0 ${style.badge}`}>
          <span>{style.emoji}</span> <span>J-{jours_restants}</span>
        </span>
        <div className="flex items-center gap-2 ml-auto">
          <span className="font-mono text-xs bg-ocean-cyan/8 text-ocean-cyan font-semibold rounded px-1.5 py-0.5">
            {score}
          </span>
          {url && (
            <a
              href={url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-xs text-ocean-muted hover:text-ocean-cyan underline underline-offset-2"
              aria-label="Voir l'annonce"
            >
              Annonce
            </a>
          )}
        </div>
      </div>

      {/* Ligne 2 : titre */}
      <p className="font-sans text-sm font-semibold text-ocean-text line-clamp-2">{title}</p>

      {/* Ligne 3 : résumé LLM ou description */}
      {contenu && (
        <p
          className="font-sans text-xs italic text-ocean-muted line-clamp-3"
          data-testid="card-content"
        >
          {contenu}
        </p>
      )}

      {/* Ligne 4 : secteur + montant */}
      {(secteur || amount != null) && (
        <div className="flex items-center gap-2 flex-wrap">
          {secteur && (
            <span
              className="font-mono text-xs bg-ocean-cyan/10 text-ocean-cyan rounded px-1.5 py-0.5"
              data-testid="secteur-badge"
            >
              {secteur}
            </span>
          )}
          {amount != null && (
            <span className="font-mono text-xs text-ocean-muted" data-testid="amount">
              💰 {EUR.format(amount)}
            </span>
          )}
        </div>
      )}

      {/* Ligne 5 : source */}
      <p className="font-mono text-xs text-ocean-muted">{source}</p>
    </div>
  )
}
