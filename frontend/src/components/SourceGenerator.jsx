// frontend/src/components/SourceGenerator.jsx
import { useState } from 'react'
import { useGenerateScraper, useDeleteSource, useSources } from '../hooks/useTenders'

export default function SourceGenerator() {
  const [form, setForm] = useState({ name: '', url: '', category: 'Public' })
  const {
    mutate: generate,
    isPending,
    isSuccess,
    isError,
    error,
    data,
    reset,
  } = useGenerateScraper()
  const { mutate: removeSource } = useDeleteSource()
  const { data: sources = [] } = useSources()

  const customSources = sources.filter((s) =>
    s.scraper_module?.startsWith('scraper_custom_')
  )

  const handleSubmit = () => {
    reset()
    generate({ url: form.url, name: form.name, category: form.category })
  }

  const canSubmit = form.name.trim() && form.url.trim() && !isPending

  return (
    <div className="space-y-6">
      <div className="p-4 bg-ocean-panel border border-ocean-border rounded-lg space-y-4">
        <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest">
          ➕ Ajouter un site de veille
        </h3>
        <p className="font-sans text-sm text-ocean-muted">
          Collez l'URL d'une page listant des appels d'offres. Mistral AI analyse la page et génère
          automatiquement le scraper.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">
              Nom du site
            </label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
              placeholder="Ex: CHU Réunion — Appels d'offres"
              className="w-full px-3 py-2 font-sans text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text placeholder:text-ocean-muted focus:outline-none focus:border-ocean-cyan/30"
            />
          </div>

          <div>
            <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">
              URL
            </label>
            <input
              type="url"
              value={form.url}
              onChange={(e) => setForm((p) => ({ ...p, url: e.target.value }))}
              placeholder="https://..."
              className="w-full px-3 py-2 font-mono text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text placeholder:text-ocean-muted focus:outline-none focus:border-ocean-cyan/30"
            />
          </div>

          <div>
            <label className="block font-sans text-xs font-medium text-ocean-muted mb-1">
              Catégorie
            </label>
            <select
              value={form.category}
              onChange={(e) => setForm((p) => ({ ...p, category: e.target.value }))}
              className="w-full px-3 py-2 font-sans text-sm border border-ocean-border rounded-md bg-ocean-deep text-ocean-text focus:outline-none focus:border-ocean-cyan/30"
            >
              <option value="Public">Public</option>
              <option value="Privé">Privé</option>
              <option value="International">International</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleSubmit}
          disabled={!canSubmit}
          className="px-4 py-2 bg-ocean-cyan/12 border border-ocean-cyan/20 text-ocean-cyan font-sans text-sm rounded-lg hover:bg-ocean-cyan/18 disabled:opacity-50 transition-colors"
        >
          {isPending ? '⏳ Génération en cours…' : '🤖 Générer le scraper'}
        </button>

        {isPending && (
          <p className="font-sans text-xs text-ocean-muted animate-pulse">
            Analyse de la page, génération du code et test en cours — cela peut prendre 30–60 secondes…
          </p>
        )}

        {isSuccess && (
          <div className="space-y-2">
            <p className="font-mono text-xs text-ocean-teal">
              ✅ Scraper actif — {data.nb_results} annonces trouvées
            </p>
            {data.preview?.length > 0 && (
              <div className="border border-ocean-border rounded-md overflow-hidden">
                <table className="w-full text-xs font-sans">
                  <thead>
                    <tr className="bg-ocean-panel/50">
                      <th className="px-3 py-2 text-left text-ocean-muted font-medium">Titre</th>
                      <th className="px-3 py-2 text-left text-ocean-muted font-medium hidden sm:table-cell">
                        Date
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.preview.map((item, i) => (
                      <tr key={i} className="border-t border-ocean-border">
                        <td className="px-3 py-2 text-ocean-text truncate max-w-xs">{item.name}</td>
                        <td className="px-3 py-2 text-ocean-muted hidden sm:table-cell">
                          {item.publication_date || item.date_found}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {isError && (
          <p className="font-mono text-xs text-ocean-coral">
            ✗ {error?.response?.data?.detail ?? 'Erreur lors de la génération'}
          </p>
        )}
      </div>

      {customSources.length > 0 && (
        <div className="space-y-3">
          <h3 className="font-mono text-xs font-semibold text-ocean-muted uppercase tracking-widest">
            Sites personnalisés ({customSources.length})
          </h3>
          <div className="space-y-2">
            {customSources.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between p-3 bg-ocean-panel border border-ocean-border rounded-lg"
              >
                <div className="min-w-0 flex-1 mr-3">
                  <div className="font-sans text-sm font-medium text-ocean-text truncate">
                    {s.name}
                  </div>
                  <div className="font-mono text-xs text-ocean-muted truncate">{s.url}</div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span className="font-mono text-xs text-ocean-teal bg-ocean-teal/10 px-2 py-0.5 rounded-full">
                    actif
                  </span>
                  <button
                    onClick={() => removeSource(s.id)}
                    className="px-2 py-1 text-ocean-coral font-sans text-xs rounded border border-ocean-coral/20 hover:bg-ocean-coral/10 transition-colors"
                  >
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
