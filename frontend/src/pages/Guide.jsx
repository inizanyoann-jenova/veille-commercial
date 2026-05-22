function Section({ title, children }) {
  return (
    <section>
      <h2 className="text-base font-bold text-gray-800 mb-3">{title}</h2>
      {children}
    </section>
  )
}

function Table({ headers, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border border-gray-200 rounded-lg overflow-hidden">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((h) => (
              <th key={h} className="text-left px-4 py-2 text-xs font-semibold text-gray-600 uppercase tracking-wide border-b border-gray-200">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-gray-100 hover:bg-gray-50">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 text-gray-700">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function Guide() {
  return (
    <div className="p-5 max-w-3xl space-y-8">
      <Section title="📋 Workflow — Comment utiliser l'app">
        <ol className="space-y-3">
          {[
            ['1 — Collecte', 'Aller dans Paramètres → Lancer la collecte. Les scrapers récupèrent les marchés depuis les sources configurées.'],
            ['2 — Qualification', "Dans Pipeline, chaque marché est \"À qualifier\". Ouvrez la fiche, lisez l'analyse IA, et choisissez un statut."],
            ['3 — Suivi', 'Les marchés "En cours" apparaissent dans le kanban Direction. Mettez à jour le statut à chaque étape.'],
            ['4 — Clôture', 'Marquez le marché Gagné ou Perdu depuis le kanban. Les marchés Gagnés alimentent le CA pipeline.'],
          ].map(([step, desc]) => (
            <li key={step} className="flex gap-3">
              <span className="font-semibold text-gray-800 w-32 flex-shrink-0">{step}</span>
              <span className="text-gray-600">{desc}</span>
            </li>
          ))}
        </ol>
      </Section>

      <Section title="🎯 Scores de pertinence">
        <Table
          headers={['Score', 'Décision', 'Signification']}
          rows={[
            ['≥ 65', '🟢 GO', 'Marché dans notre cœur de métier, territoire prioritaire. À traiter en priorité.'],
            ['35 – 64', '🟡 Étudier', 'Marché potentiellement intéressant. Analyse approfondie recommandée.'],
            ['< 35', '🔴 Passer', 'Hors périmètre ou faible probabilité de succès. Archiver.'],
          ]}
        />
      </Section>

      <Section title="📊 Statuts des marchés">
        <Table
          headers={['Statut', 'Signification']}
          rows={[
            ['À qualifier', "Marché fraîchement collecté, non encore analysé par l'équipe."],
            ['En cours', 'En cours d\'analyse ou de préparation de réponse.'],
            ['Soumis', 'Offre déposée, en attente de résultat.'],
            ['Gagné', 'Marché remporté ✅'],
            ['Perdu', 'Marché non remporté ❌'],
            ['Archivé', 'Ancien marché retiré de la vue active.'],
          ]}
        />
      </Section>

      <Section title="🌐 Sources surveillées">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {[
            { cat: '🏛️ Marchés publics France', sources: ['BOAMP', 'DECP', 'Marchés Publics Info', 'Marchés Sécurisés'] },
            { cat: '🌍 Banques de développement', sources: ['Banque Mondiale', 'AFD', 'BID', 'ISDB'] },
            { cat: '🏝️ Sources locales OI', sources: ['Département 974', 'SEMADER', 'NUKEMA', 'Presse locale'] },
            { cat: '🏗️ Signaux privés', sources: ['Permis de construire', 'Presse économique', 'Instao'] },
          ].map(({ cat, sources }) => (
            <div key={cat} className="bg-gray-50 rounded-lg p-3 border border-gray-200">
              <p className="text-xs font-semibold text-gray-700 mb-2">{cat}</p>
              <ul className="space-y-1">
                {sources.map((s) => (
                  <li key={s} className="text-sm text-gray-600">• {s}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </Section>
    </div>
  )
}
