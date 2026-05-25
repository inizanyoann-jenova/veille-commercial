function H2({ children }) {
  return (
    <h2 className="font-serif text-sm font-bold text-ocean-cyan uppercase tracking-widest border-b border-ocean-border pb-2 mb-4">
      {children}
    </h2>
  )
}

function H3({ children }) {
  return (
    <h3 className="font-sans text-sm font-semibold text-ocean-text mb-2 mt-4">{children}</h3>
  )
}

function P({ children }) {
  return <p className="font-sans text-sm text-ocean-text/80 leading-relaxed mb-2">{children}</p>
}

function Li({ children }) {
  return (
    <li className="flex gap-2 font-sans text-sm text-ocean-text/80 leading-relaxed">
      <span className="text-ocean-cyan flex-shrink-0 mt-0.5">›</span>
      <span>{children}</span>
    </li>
  )
}

function Chip({ children, color = 'cyan' }) {
  const colors = {
    cyan: 'bg-ocean-cyan/10 text-ocean-cyan border-ocean-cyan/20',
    teal: 'bg-ocean-teal/10 text-ocean-teal border-ocean-teal/20',
    gold: 'bg-ocean-gold/10 text-ocean-gold border-ocean-gold/20',
    coral: 'bg-ocean-coral/10 text-ocean-coral border-ocean-coral/20',
    muted: 'bg-white/5 text-ocean-muted border-white/10',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border ${colors[color]}`}>
      {children}
    </span>
  )
}

function Table({ headers, rows }) {
  return (
    <div className="overflow-x-auto mb-4">
      <table className="w-full text-sm border border-ocean-border rounded-lg overflow-hidden">
        <thead className="bg-ocean-panel/60">
          <tr>
            {headers.map((h) => (
              <th key={h} className="text-left px-4 py-2 font-mono text-xs text-ocean-muted uppercase tracking-widest border-b border-ocean-border">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-ocean-cyan/4 last:border-0 hover:bg-ocean-cyan/2">
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-2.5 font-sans text-sm text-ocean-text/80">{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Block({ icon, title, children }) {
  return (
    <div className="bg-ocean-panel border border-ocean-border rounded-xl p-4 space-y-2">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-base">{icon}</span>
        <span className="font-sans text-sm font-semibold text-ocean-text">{title}</span>
      </div>
      {children}
    </div>
  )
}

export default function Guide() {
  return (
    <div className="p-6 max-w-3xl space-y-10">

      {/* ── NAVIGATION ─────────────────────────────────────────────────────── */}
      <section>
        <H2>Navigation générale</H2>
        <P>
          La barre latérale gauche donne accès à toutes les sections de l'application.
          En bas de la sidebar se trouve le bloc <strong>Collecte</strong> pour déclencher la récupération des marchés.
          Le bouton <strong>Paramètres</strong> (⚙️) est en bas de la sidebar.
        </P>
        <Table
          headers={['Page', 'Rôle']}
          rows={[
            ['📋 Pipeline', "Tableau principal des marchés avec filtres, scores et analyse IA. Point d'entrée quotidien."],
            ['📊 Analytics', 'Graphiques : publications par semaine, répartition par territoire et domaine, top sources, CA.'],
            ['🎯 Direction', 'Kanban des marchés GO : de la qualification jusqu\'au résultat (Gagné / Perdu).'],
            ['🔔 Urgences', 'Marchés GO avec échéance < 30 jours. Badge rouge en sidebar si des urgences existent.'],
            ['📖 Guide', 'Ce document.'],
            ['⚙️ Paramètres', 'Identifiants, clé Mistral, apparence, doublons, export Excel.'],
          ]}
        />
      </section>

      {/* ── COLLECTE ───────────────────────────────────────────────────────── */}
      <section>
        <H2>Collecte des marchés</H2>
        <P>
          La collecte se lance depuis le bloc <strong>Collecte</strong> en bas de la sidebar, visible depuis toutes les pages.
        </P>

        <H3>Comment ça marche</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>Les sources actives sont listées sous forme de cases à cocher. Décochez celles que vous voulez exclure.</Li>
          <Li>Les sources grisées avec 🔒 nécessitent des identifiants non encore configurés (voir Paramètres → Connexion).</Li>
          <Li>Cliquez sur <strong>⟳ Lancer la collecte</strong>. L'opération peut prendre plusieurs minutes.</Li>
          <Li>Après la collecte, un résumé par source s'affiche : nombre de marchés trouvés et nouveaux insérés.</Li>
          <Li>Une analyse IA (Mistral) se déclenche automatiquement sur <strong>tous</strong> les nouveaux marchés après chaque collecte.</Li>
        </ul>

        <div className="bg-ocean-gold/8 border border-ocean-gold/20 rounded-lg px-4 py-3">
          <p className="font-sans text-xs text-ocean-gold leading-relaxed">
            <strong>Avertissement identifiants manquants :</strong> si un message ⚠ apparaît en jaune avant le bouton de collecte,
            certaines sources authentifiées sont désactivées. Cliquez sur le lien <em>configurer ↗</em> pour aller dans Paramètres → Connexion.
          </p>
        </div>
      </section>

      {/* ── PIPELINE / DASHBOARD ───────────────────────────────────────────── */}
      <section>
        <H2>Pipeline (page principale)</H2>

        <H3>Compteurs KPI</H3>
        <P>La rangée de 6 indicateurs en haut du Dashboard affiche en temps réel :</P>
        <ul className="space-y-1.5 mb-4">
          <Li><strong>Total marchés</strong> — tous les marchés publics actifs en base.</Li>
          <Li><strong>À qualifier</strong> — marchés nouvellement collectés, non encore traités.</Li>
          <Li><strong>En cours</strong> — marchés en analyse ou préparation de réponse.</Li>
          <Li><strong>Soumis</strong> — offres déposées en attente de résultat.</Li>
          <Li><strong>Gagnés</strong> — marchés remportés.</Li>
          <Li><strong>Nouvelles 24h</strong> — marchés extraits dans les dernières 24 heures.</Li>
        </ul>

        <H3>Filtres du tableau</H3>
        <Table
          headers={['Filtre', 'Options', 'Effet']}
          rows={[
            ['Statut', 'Tous / À qualifier / En cours / Soumis / Gagné / Perdu', 'Affiche uniquement les marchés du statut choisi.'],
            ['Secteur', 'Public / Privé / International', 'Bascule entre marchés publics, signaux privés et appels d\'offres internationaux.'],
            ['GO/NO-GO', 'Tous / GO / Étudier / Passer', 'Filtre par recommandation de pertinence calculée depuis le score.'],
            ['Recherche', 'Texte libre', 'Filtre en temps réel sur le titre, le domaine et le territoire.'],
          ]}
        />

        <H3>Colonnes du tableau</H3>
        <Table
          headers={['Colonne', 'Description']}
          rows={[
            ['Titre', 'Intitulé du marché. Cliquez sur la ligne pour ouvrir la fiche détail.'],
            ['Domaine', 'SSI, CMSI, Vidéosurveillance, Courants faibles — détecté automatiquement dans le titre.'],
            ['Territoire', 'La Réunion, Mayotte, France métropole, International, etc.'],
            ['Deadline', "Date limite de remise de l'offre."],
            ['Score', 'Note de pertinence de 0 à 100 calculée par l\'IA.'],
            ['GO/NO-GO', '🟢 GO ≥ 65 · 🟡 Étudier 35–64 · 🔴 Passer < 35'],
            ['Statut', 'Statut actuel dans le cycle de vie du marché.'],
            ['Source', 'Nom de la plateforme source — cliquable pour ouvrir l\'annonce originale.'],
            ['IA', '✓ Analysé (IA faite) · ▶ Analyser (déclencher manuellement) · barre de chargement en cours.'],
          ]}
        />
      </section>

      {/* ── FICHE DETAIL ───────────────────────────────────────────────────── */}
      <section>
        <H2>Fiche marché (détail)</H2>
        <P>Cliquez sur une ligne du tableau pour ouvrir le panneau de détail sur la droite.</P>

        <H3>Informations affichées</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>Badge GO/NO-GO + score/100 en haut de la fiche.</Li>
          <Li>Deadline avec compteur J-X coloré (rouge si ≤ 7 jours, orange si ≤ 30 jours).</Li>
          <Li>Montant estimé du marché, secteur, source.</Li>
          <Li>Lien direct vers l'annonce originale (<strong>Voir l'annonce</strong>).</Li>
          <Li>Résumé de l'analyse IA Mistral : type de marché, domaines couverts, recommandation.</Li>
          <Li>Scores détaillés (pertinence territoriale, sectorielle, etc.) sous forme de barres.</Li>
          <Li>Champ notes libre pour annoter le marché.</Li>
        </ul>

        <H3>Actions disponibles</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>
            <strong>Changer le statut</strong> — menu déroulant (À qualifier → En cours → Soumis → Gagné / Perdu).
          </Li>
          <Li>
            <strong>Déclencher l'analyse IA</strong> — si le bouton ▶ Analyser est visible, cliquez pour lancer Mistral sur ce marché spécifiquement.
          </Li>
          <Li>
            <strong>Étoile (favori)</strong> — sauvegardez un marché pour le retrouver facilement.
          </Li>
        </ul>
      </section>

      {/* ── SCORES ─────────────────────────────────────────────────────────── */}
      <section>
        <H2>Scores de pertinence et GO/NO-GO</H2>
        <P>
          Chaque marché reçoit un score de 0 à 100 calculé par l'analyse IA Mistral, croisant
          domaine technique, territoire et type de marché. Ce score détermine automatiquement la recommandation GO/NO-GO.
        </P>
        <Table
          headers={['Score', 'Recommandation', 'Que faire ?']}
          rows={[
            ['≥ 65', '🟢 GO', "Marché dans notre cœur de métier sur territoire prioritaire. À traiter en priorité. Basculez en « En cours » et passez en Direction."],
            ['35 – 64', '🟡 Étudier', "Potentiellement intéressant. Lisez l'analyse IA et décidez si cela mérite une réponse."],
            ['< 35', '🔴 Passer', 'Hors périmètre ou faible probabilité de succès. Archivez.'],
          ]}
        />
        <P>
          Le filtre GO/NO-GO dans le tableau permet d'afficher uniquement les marchés d'une catégorie pour traiter
          rapidement les GO en priorité.
        </P>
      </section>

      {/* ── STATUTS ────────────────────────────────────────────────────────── */}
      <section>
        <H2>Cycle de vie d'un marché</H2>
        <Table
          headers={['Statut', 'Déclenchement', 'Signification']}
          rows={[
            ['À qualifier', 'Automatique à la collecte', "Marché entré en base, non encore traité par l'équipe."],
            ['En cours', 'Manuel (fiche ou Direction)', "Analyse ou préparation de la réponse en cours."],
            ['Soumis', 'Manuel', "Offre déposée, en attente de résultat."],
            ['Gagné', 'Manuel (kanban Direction)', 'Marché remporté ✅ — alimente le CA pipeline.'],
            ['Perdu', 'Manuel (kanban Direction)', 'Marché non remporté ❌'],
            ['Archivé', 'Automatique après 30 jours sans action', 'Retiré de la vue active. Récupérable depuis le filtre de statut.'],
          ]}
        />
      </section>

      {/* ── DIRECTION ──────────────────────────────────────────────────────── */}
      <section>
        <H2>Direction (kanban)</H2>
        <P>
          Vue kanban réservée aux marchés publics avec un score ≥ 65 (GO).
          Elle présente trois colonnes pour suivre la progression commerciale.
        </P>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          {[
            { col: '✅ GO', desc: "Marchés À qualifier et En cours avec score GO. Action : cliquer « Marquer Soumis » après dépôt de l'offre." },
            { col: '📤 Soumis', desc: "Offres déposées. Actions : « Gagné 🏆 » ou « Perdu » selon le résultat de l'appel d'offres." },
            { col: '🏆 Résultats', desc: "Historique des marchés Gagnés et Perdus. Lecture seule." },
          ].map(({ col, desc }) => (
            <div key={col} className="bg-ocean-panel border border-ocean-border rounded-xl p-3">
              <p className="font-sans text-xs font-semibold text-ocean-text mb-1">{col}</p>
              <p className="font-sans text-xs text-ocean-muted leading-relaxed">{desc}</p>
            </div>
          ))}
        </div>
        <P>
          Chaque carte affiche le titre, le montant estimé, la deadline et le score.
          Le changement de statut se fait directement par les boutons d'action sur la carte.
        </P>
      </section>

      {/* ── URGENCES ───────────────────────────────────────────────────────── */}
      <section>
        <H2>Urgences</H2>
        <P>
          La page Urgences liste les marchés GO (score ≥ 65) dont l'échéance est dans moins de 30 jours.
          Le badge rouge en sidebar indique combien d'urgences sont en cours.
        </P>
        <P>
          Chaque carte affiche : le badge <strong>J-X</strong> (jours restants, coloré selon l'urgence),
          le score, le secteur, le montant, un résumé IA, et un lien direct vers l'annonce.
        </P>
        <Table
          headers={['Couleur J-X', 'Signification']}
          rows={[
            ['Rouge vif', '≤ 7 jours — traitement immédiat requis'],
            ['Orange', '8 à 14 jours — à prioriser cette semaine'],
            ['Jaune', '15 à 30 jours — à planifier'],
          ]}
        />
      </section>

      {/* ── ANALYTICS ──────────────────────────────────────────────────────── */}
      <section>
        <H2>Analytics</H2>
        <P>Tableau de bord graphique donnant une vue macro de l'activité de veille.</P>
        <ul className="space-y-1.5 mb-4">
          <Li><strong>Total collecté</strong> et <strong>Sources actives</strong> — volume global de la base.</Li>
          <Li><strong>CA gagné</strong> — somme des montants des marchés remportés.</Li>
          <Li><strong>CA pipeline</strong> — somme des montants En cours + Soumis (potentiel commercial).</Li>
          <Li><strong>Publications / semaine</strong> — histogramme des 30 dernières semaines pour détecter les pics d'activité.</Li>
          <Li><strong>Par territoire</strong> — donut La Réunion / Mayotte / autres, pour évaluer la concentration géographique.</Li>
          <Li><strong>Par domaine</strong> — SSI, CMSI, Vidéo, Courants faibles — barres horizontales.</Li>
          <Li><strong>Top 5 sources</strong> — les plateformes qui génèrent le plus de marchés pertinents.</Li>
        </ul>
      </section>

      {/* ── PARAMETRES ─────────────────────────────────────────────────────── */}
      <section>
        <H2>Paramètres</H2>

        <H3>Connexion — identifiants des sites authentifiés</H3>
        <P>
          Certaines sources (Nukema, Marché Online, Instao, Marchés Sécurisés, Tenders Go…) nécessitent
          un compte pour accéder aux annonces. Configurez vos identifiants ici pour débloquer ces sources lors de la collecte.
        </P>
        <ul className="space-y-1.5 mb-4">
          <Li>Cliquez sur un site pour déplier le formulaire email / mot de passe.</Li>
          <Li>Cliquez sur <strong>🔌 Tester la connexion</strong> — un navigateur automatique (Playwright) vérifie les identifiants en temps réel.</Li>
          <Li>Si le test réussit (✓), le bouton <strong>💾 Sauvegarder</strong> se déverrouille.</Li>
          <Li>Les identifiants sont chiffrés (Fernet) et stockés localement. Ils ne transitent jamais en clair.</Li>
          <Li>Badge <Chip color="teal">● Configuré</Chip> = identifiants enregistrés · <Chip color="muted">● Non configuré</Chip> = source verrouillée à la collecte.</Li>
        </ul>

        <H3>Intégrations — clé API Mistral</H3>
        <P>
          L'analyse IA utilise Mistral. Sans clé valide, les marchés ne sont pas analysés automatiquement.
        </P>
        <ul className="space-y-1.5 mb-4">
          <Li>Collez votre clé API Mistral dans le champ prévu.</Li>
          <Li>Cliquez <strong>Sauvegarder</strong> — la clé est écrite dans le fichier <code>.env</code> et rechargée à chaud, sans redémarrer le serveur.</Li>
          <Li>Le badge <Chip color="teal">● Clé active</Chip> / <Chip color="coral">● Non configurée</Chip> indique l'état en temps réel.</Li>
        </ul>

        <H3>Apparence</H3>
        <ul className="space-y-1.5 mb-4">
          <Li><strong>Curseur de luminosité</strong> — ajuste la clarté globale de l'interface. Le réglage est sauvegardé dans le navigateur.</Li>
          <Li><strong>Couleurs du thème</strong> — personnalisez les teintes principales (Ocean Deep par défaut).</Li>
        </ul>

        <H3>Doublons</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>Cliquez <strong>Détecter les doublons</strong> pour lancer l'analyse de similarité entre marchés.</Li>
          <Li>Les paires détectées s'affichent avec un score de similarité.</Li>
          <Li><strong>Conserver</strong> résout la paire sans action · <strong>Ignorer</strong> la marque comme résolue.</Li>
        </ul>

        <H3>Export</H3>
        <P>
          Le bouton <strong>Télécharger le rapport Excel</strong> génère un fichier <code>.xlsx</code> avec
          tous les marchés actifs, leurs scores, statuts et données IA — utilisable pour des rapports commerciaux.
        </P>
      </section>

      {/* ── SOURCES ────────────────────────────────────────────────────────── */}
      <section>
        <H2>Sources surveillées</H2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            { cat: '🏛️ Marchés publics France', sources: ['BOAMP', 'DECP', 'TED (Europe)', 'Marchés Publics Info', 'Marchés Sécurisés', 'Marché Online'] },
            { cat: '🏝️ Sources locales Océan Indien', sources: ['Département 974', 'SEMADER', 'NUKEMA', 'VAAO', 'CHM (Mayotte)', 'Instao', 'Tenders Go'] },
            { cat: '🌍 Banques de développement', sources: ['AFD', 'Banque Mondiale / IDA', 'BID (Amériques)', 'ISDB (islamique)'] },
            { cat: '🏗️ Signaux privés', sources: ['Permis de construire', 'Presse économique locale'] },
          ].map(({ cat, sources }) => (
            <div key={cat} className="bg-ocean-panel border border-ocean-border rounded-xl p-3">
              <p className="font-sans text-xs font-semibold text-ocean-text mb-2">{cat}</p>
              <ul className="space-y-0.5">
                {sources.map((s) => (
                  <li key={s} className="font-sans text-sm text-ocean-muted">· {s}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="font-sans text-xs text-ocean-muted mt-3">
          Les sources avec 🔒 dans la sidebar nécessitent des identifiants configurés dans Paramètres → Connexion.
          Les sources désactivées peuvent être réactivées dans Paramètres → Sources.
        </p>
      </section>

      {/* ── WORKFLOW QUOTIDIEN ─────────────────────────────────────────────── */}
      <section>
        <H2>Workflow quotidien recommandé</H2>
        <ol className="space-y-4">
          {[
            {
              step: '1 — Collecte',
              desc: 'Depuis la sidebar, cliquez ⟳ Lancer la collecte. Patientez jusqu\'au résumé. Tous les nouveaux marchés sont analysés par Mistral automatiquement.',
            },
            {
              step: '2 — Triage GO',
              desc: 'Dans Pipeline, filtrez sur GO/NO-GO = GO. Parcourez les marchés en À qualifier. Pour chaque GO pertinent, passez en En cours.',
            },
            {
              step: '3 — Lecture fiches',
              desc: "Cliquez sur un marché En cours pour lire l'analyse IA. Vérifiez le délai (J-X), le montant, le domaine. Annotez dans le champ Notes si besoin.",
            },
            {
              step: '4 — Direction',
              desc: "Après dépôt d'une offre, passez le marché en Soumis depuis la fiche ou le kanban Direction. À l'attribution, marquez Gagné ou Perdu.",
            },
            {
              step: '5 — Urgences',
              desc: 'Consultez la page Urgences si le badge rouge apparaît en sidebar. Traitez en priorité les marchés J ≤ 7 (rouge).',
            },
          ].map(({ step, desc }) => (
            <li key={step} className="flex gap-4">
              <span className="font-mono text-xs font-bold text-ocean-cyan bg-ocean-cyan/10 border border-ocean-cyan/20 rounded-lg px-2 py-1 h-fit flex-shrink-0 mt-0.5">
                {step.split(' — ')[0]}
              </span>
              <div>
                <p className="font-sans text-sm font-semibold text-ocean-text mb-0.5">{step.split(' — ')[1]}</p>
                <p className="font-sans text-sm text-ocean-text/80 leading-relaxed">{desc}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* ── RACCOURCIS ─────────────────────────────────────────────────────── */}
      <section>
        <H2>Liens utiles</H2>
        <ul className="space-y-1.5">
          <Li>API REST documentée : <code className="font-mono text-ocean-cyan text-xs">http://localhost:8000/docs</code></Li>
          <Li>La colonne <strong>Source</strong> dans le tableau est un lien cliquable vers l'annonce originale.</Li>
          <Li>Le titre dans la fiche marché est un lien direct vers l'annonce source.</Li>
          <Li>Le badge 🔔 en sidebar indique le nombre de marchés GO urgents (échéance &lt; 30 j).</Li>
        </ul>
      </section>

    </div>
  )
}
