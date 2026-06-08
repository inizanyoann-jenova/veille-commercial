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

function KeywordGroup({ title, keywords }) {
  return (
    <div className="space-y-1.5">
      <p className="font-mono text-xs font-semibold text-ocean-muted uppercase">{title}</p>
      <div className="flex flex-wrap gap-1.5">
        {keywords.map((kw) => (
          <span key={kw} className="font-mono text-xs px-2 py-0.5 bg-ocean-cyan/8 border border-ocean-cyan/15 rounded text-ocean-cyan/80">
            {kw}
          </span>
        ))}
      </div>
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
            ['🎯 Direction', "Kanban des marchés GO : de la qualification jusqu'au résultat (Gagné / Perdu)."],
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
          Elle interroge en parallèle toutes les sources sélectionnées et insère les nouveaux marchés en base.
          Le backend retourne immédiatement un <strong>identifiant de job</strong> et exécute les scrapers en arrière-plan ;
          la sidebar interroge l'état toutes les 2 secondes et met à jour le résumé en temps réel jusqu'à la fin.
        </P>

        <H3>Pipeline de collecte — étape par étape</H3>
        <ol className="space-y-3 mb-4">
          {[
            {
              n: '1',
              title: 'Appel des scrapers',
              desc: "Chaque source active exécute sa fonction fetch() qui retourne une liste de marchés bruts (titre, URL, date de publication, description, deadline). Les sources nécessitant une connexion (Nukema, Instao…) utilisent un navigateur automatique Playwright avec les identifiants chiffrés.",
            },
            {
              n: '2',
              title: 'Déduplication par empreinte MD5',
              desc: "Avant insertion, un identifiant unique est calculé : MD5(source + titre + date_publication). Si cet ID existe déjà en base, le marché est ignoré silencieusement — il n'est pas re-inséré même si son contenu a changé.",
            },
            {
              n: '3',
              title: 'Rejet sans date de publication',
              desc: "Un marché sans date de publication est systématiquement rejeté et compté dans nb_rejected_no_date. Cette règle évite d'insérer des marchés expirés ou mal parsés dont on ne saurait pas dater l'ancienneté.",
            },
            {
              n: '4',
              title: 'Score initial (50 ou 0)',
              desc: "À l'insertion, le système applique le filtre par mots-clés (voir section ci-dessous). Si le marché est pertinent pour ATEXIA, relevance_score = 50. Sinon = 0. Ce score provisoire sera écrasé par Mistral si une clé est configurée.",
            },
            {
              n: '5',
              title: 'Analyse IA post-collecte',
              desc: "Après l'insertion des nouveaux marchés, deux passes d'analyse se déclenchent automatiquement : Mistral analyse les marchés sans score IA (jusqu'à LLM_BATCH_SIZE par collecte, défaut 10). L'analyse produit le score définitif 0-100 et le rapport structuré.",
            },
          ].map(({ n, title, desc }) => (
            <li key={n} className="flex gap-4">
              <span className="font-mono text-xs font-bold text-ocean-cyan bg-ocean-cyan/10 border border-ocean-cyan/20 rounded-lg px-2 py-1 h-fit flex-shrink-0 mt-0.5">
                {n}
              </span>
              <div>
                <p className="font-sans text-sm font-semibold text-ocean-text mb-0.5">{title}</p>
                <p className="font-sans text-sm text-ocean-text/80 leading-relaxed">{desc}</p>
              </div>
            </li>
          ))}
        </ol>

        <H3>Résumé affiché après collecte</H3>
        <Table
          headers={['Compteur', 'Signification']}
          rows={[
            ['Trouvés', 'Nombre total de marchés retournés par le scraper de cette source.'],
            ['Nouveaux', "Marchés effectivement insérés en base (inconnus et avec date valide)."],
            ['Rejetés sans date', "Marchés ignorés car la date de publication était absente ou non parsable."],
          ]}
        />

        <div className="bg-ocean-gold/8 border border-ocean-gold/20 rounded-lg px-4 py-3">
          <p className="font-sans text-xs text-ocean-gold leading-relaxed">
            <strong>Avertissement identifiants manquants :</strong> si un message ⚠ apparaît en jaune avant le bouton de collecte,
            certaines sources authentifiées sont désactivées. Cliquez sur le lien <em>configurer ↗</em> pour aller dans Paramètres → Connexion.
          </p>
        </div>
      </section>

      {/* ── COMMENT FONCTIONNE LA DÉTECTION ────────────────────────────────── */}
      <section>
        <H2>Comment fonctionne la détection des marchés</H2>
        <P>
          Avant même d'attribuer un score, le système doit décider si un marché collecté est
          potentiellement pertinent pour ATEXIA. Ce filtrage se fait en deux passes successives.
        </P>

        <H3>Passe 1 — Exclusions absolues</H3>
        <P>
          Si le texte contient l'un de ces termes, le marché est écarté immédiatement, quelle que soit la suite :
        </P>
        <div className="flex flex-wrap gap-1.5 mb-4">
          {['gardiennage', 'agents de sécurité', 'ssiap', 'maître-chien', 'espaces verts', 'voirie', 'assainissement', 'livres scolaires', 'offre d\'emploi'].map((kw) => (
            <span key={kw} className="font-mono text-xs px-2 py-0.5 bg-ocean-coral/8 border border-ocean-coral/20 rounded text-ocean-coral/80">{kw}</span>
          ))}
        </div>
        <P>Ces exclusions évitent les faux positifs évidents (gardiennage, sécurité humaine, fournitures scolaires, etc.).</P>

        <H3>Passe 2 — Mots-clés d'inclusion (160 termes)</H3>
        <P>
          Si le marché n'est pas exclu, le système cherche l'un des 160 mots-clés métier ATEXIA.
          Un seul match suffit pour qualifier le marché comme pertinent.
        </P>
        <div className="space-y-4 mb-4">
          <KeywordGroup
            title="🔥 SSI — détection & équipements"
            keywords={['ssi', 'système de sécurité incendie', 'alarme incendie', 'sécurité incendie', 'centrale incendie', 'détection incendie', 'détecteur de fumée', 'détecteur thermique', 'déclencheur manuel', 'diffuseur sonore', 'porte coupe-feu', 'compartimentage', 'extinction incendie', 'sprinkler', 'ria', 'baas', 'bloc autonome alarme']}
          />
          <KeywordGroup
            title="💨 CMSI — désenfumage"
            keywords={['cmsi', 'désenfumage', 'centrale de mise en sécurité', 'volet de désenfumage', 'trappe de désenfumage', 'exutoire de fumée', 'extracteur de fumée', 'désenfumage naturel', 'désenfumage mécanique', 'denfc', 'dmfc']}
          />
          <KeywordGroup
            title="📷 Vidéo — CCTV & contrôle d'accès"
            keywords={['cctv', 'vidéosurveillance', 'vidéoprotection', 'caméra ip', 'caméra thermique', 'télésurveillance', 'nvr', 'dvr', "contrôle d'accès", 'lecteur de badge', 'interphonie', 'visiophone', 'portier vidéo', 'alarme intrusion', 'sécurité électronique']}
          />
          <KeywordGroup
            title="⚡ Courants faibles & GTB"
            keywords={['courants faibles', 'gtb', 'gtc', 'bms', 'vdi', 'câblage structuré', 'voix données images', 'gestion technique bâtiment', 'building management', 'domotique', 'tableau de communication']}
          />
          <KeywordGroup
            title="🔧 Maintenance & réglementaire"
            keywords={['mco', 'mco ssi', 'maintenance ssi', 'contrat de maintenance', 'maintenance préventive', 'maintien en condition opérationnelle', 'vérification annuelle', 'vérification réglementaire', 'mise en conformité', 'dta', 'télémaintenance']}
          />
        </div>

        <H3>Passe 3 — Signal implicite (construction + ERP)</H3>
        <P>
          Si aucun mot-clé direct n'est trouvé mais que le texte mentionne à la fois un <strong>projet de
          construction</strong> (travaux, réhabilitation, chantier…) <strong>et</strong> un type de bâtiment ERP
          (hôpital, école, ehpad, crèche, mairie, piscine, hôtel, musée…), le marché est conservé avec le
          tag <Chip color="gold">Potentiel SSI implicite</Chip>. Ces bâtiments ont une obligation réglementaire SSI/CMSI.
        </P>
        <P>
          Tout projet de construction dans le <strong>974</strong> (La Réunion) est également
          conservé même sans ERP identifié, car ATEXIA est le principal opérateur local qualifié.
        </P>
      </section>

      {/* ── SCORING ────────────────────────────────────────────────────────── */}
      <section>
        <H2>Scores de pertinence et GO/NO-GO</H2>
        <P>
          Chaque marché possède un score de <strong>0 à 100</strong> qui évolue en trois phases successives,
          du plus rudimentaire au plus précis.
        </P>

        <H3>Phase 1 — Score initial à l'insertion (50 ou 0)</H3>
        <P>
          Dès qu'un marché est inséré en base, le système applique le filtre par mots-clés décrit dans
          la section précédente. Si le texte contient un mot-clé d'inclusion (sans mot d'exclusion), le
          marché reçoit <strong>relevance_score = 50</strong>. Sinon <strong>0</strong>.
          C'est un score binaire provisoire — il confirme uniquement que le marché a passé le filtre automatique,
          pas sa qualité réelle.
        </P>
        <div className="bg-ocean-gold/8 border border-ocean-gold/20 rounded-lg px-4 py-3 mb-4">
          <p className="font-sans text-xs text-ocean-gold leading-relaxed">
            Avec un score de 50, le marché apparaît en <strong>🟡 Étudier</strong> (35–64).
            Ce n'est pas un signal fort : presque tous les marchés filtrés démarrent à 50.
            C'est l'analyse Mistral qui affine ce chiffre.
          </p>
        </div>

        <H3>Phase 2 — Score Mistral (0 à 100, définitif)</H3>
        <P>
          Quand Mistral analyse un marché, il lit <strong>titre + description complète</strong> et retourne
          un <code>score_pertinence</code> de 0 à 100 basé sur le contenu réel.
          Ce score <strong>écrase</strong> le 50 initial dans <code>relevance_score</code> et devient la valeur affichée.
          C'est ce score qui détermine le GO/NO-GO.
        </P>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <div className="bg-ocean-panel border border-ocean-gold/30 rounded-xl p-4 space-y-2">
            <p className="font-mono text-xs font-semibold text-ocean-gold uppercase">Sans analyse IA</p>
            <p className="font-sans text-xs text-ocean-text/70 leading-relaxed">
              Score = <strong className="text-ocean-text">50</strong> ou <strong className="text-ocean-text">0</strong>.
              Le panneau "Détail du score" affiche une décomposition (domaine, territoire, titre) calculée à la volée
              pour donner un repère visuel, mais ce n'est pas ce chiffre qui détermine le score stocké.
            </p>
            <p className="font-mono text-xs text-ocean-gold">Icône ▶ dans le tableau = non encore analysé</p>
          </div>
          <div className="bg-ocean-panel border border-ocean-teal/30 rounded-xl p-4 space-y-2">
            <p className="font-mono text-xs font-semibold text-ocean-teal uppercase">Après analyse Mistral</p>
            <p className="font-sans text-xs text-ocean-text/70 leading-relaxed">
              Score Mistral <strong className="text-ocean-text">0–100</strong> enregistré en base.
              La décomposition en 4 barres reste affichée pour expliquer le contexte, mais c'est
              le score Mistral qui fait foi pour le GO/NO-GO.
            </p>
            <p className="font-mono text-xs text-ocean-teal">Icône ✓ dans le tableau = analysé par IA</p>
          </div>
        </div>

        <H3>Phase 3 — Score adaptatif (apprentissage sur vos décisions)</H3>
        <P>
          En parallèle, le système apprend de vos décisions passées (GO, Perdu) pour calculer un
          <strong> score adaptatif</strong> complémentaire, recalculé automatiquement chaque semaine.
        </P>
        <ul className="space-y-1.5 mb-4">
          <Li>
            <strong>Données d'entraînement :</strong> le système lit tous les marchés en statut
            Soumis/Gagné (positifs) et Perdu (négatifs). Il faut au moins <strong>10 décisions</strong> au total pour que le calcul s'active.
          </Li>
          <Li>
            <strong>Méthode :</strong> chaque mot significatif du titre et de la description est tokenisé.
            Le système calcule la fréquence de chaque token dans les marchés positifs vs négatifs.
            Un token fréquent dans les GO et rare dans les Perdus a un poids positif — et inversement.
          </Li>
          <Li>
            <strong>Score final :</strong> la somme pondérée des tokens de chaque marché non décidé est normalisée
            en 0–100 via une formule sigmoïde. Ce score adaptatif est visible dans l'API (<code>adaptive_score</code>)
            et reflète la similarité textuelle avec vos marchés remportés.
          </Li>
          <Li>
            Plus vous enregistrez de résultats (Gagné / Perdu), plus le score adaptatif devient pertinent
            pour votre activité spécifique à La Réunion.
          </Li>
        </ul>

        <H3>Décomposition affichée dans la fiche (repère visuel)</H3>
        <P>
          La fiche marché affiche 4 barres pour expliquer d'où vient la pertinence estimée.
          Ces barres sont <strong>recalculées à l'affichage</strong> depuis le domaine et territoire détectés —
          elles n'impactent pas le score stocké, elles servent à comprendre pourquoi un marché a été retenu.
        </P>
        <Table
          headers={['Composante', 'Max', 'Ce que ça mesure']}
          rows={[
            ['Pertinence métier', '45', "SSI direct = 45 · CMSI/Vidéo = 40 · Courants faibles = 30 · Signal implicite = 5"],
            ['Proximité géographique', '30', "La Réunion = 30 · Madagascar / Maurice = 22 · Comores = 18 · France = 10"],
            ['Mots-clés dans le titre', '15', "3+ mots-clés métier dans le titre = 15 · 2 = 10 · 1 = 6 · aucun = 0"],
            ['Maintenance / Récurrence', '10', "10 si le marché est identifié comme un contrat de maintenance, sinon 0"],
          ]}
        />

        <H3>Seuils GO/NO-GO</H3>
        <Table
          headers={['Score', 'Recommandation', 'Que faire ?']}
          rows={[
            ['≥ 65', '🟢 GO', "Dans notre cœur de métier sur territoire prioritaire. Basculer en « En cours », ouvrir une affaire, télécharger le DCE."],
            ['35 – 64', '🟡 Étudier', "Potentiellement intéressant. Lire l'analyse IA, vérifier le CCTP, décision GO/NO-GO à remonter sous 48 h."],
            ['< 35', '🔴 Passer', 'Hors périmètre ou faible probabilité. Archiver sans mobiliser de ressources commerciales.'],
          ]}
        />

        <H3>Analyse IA — ce que Mistral produit</H3>
        <P>
          Quand Mistral analyse un marché, il lit tout le texte disponible et produit un rapport structuré visible
          dans la section <strong>Analyse IA</strong> de la fiche marché :
        </P>
        <Table
          headers={['Champ IA', 'Description']}
          rows={[
            ['Score de pertinence', 'Note 0–100 basée sur le contenu complet. Remplace le score provisoire 50/0.'],
            ['Type de travaux', 'Installation neuve, réhabilitation, maintenance, fourniture, mixte…'],
            ['Budget estimé', 'Estimation du montant si non précisé dans le marché.'],
            ['Type acheteur', 'Collectivité, établissement de santé, bailleur social, entreprise privée…'],
            ['Niveau de concurrence', 'Estimation du nombre et type de concurrents probables sur ce marché.'],
            ['Concurrents nommés', 'Marques ou entreprises citées dans le DCE (Notifier, Hikvision, Tyco…).'],
            ['Recommandation', "GO / NON — jugement global de Mistral sur l'opportunité pour ATEXIA."],
            ['Justification', 'Explication synthétique du raisonnement IA.'],
          ]}
        />

        <H3>Déclencher l'analyse IA manuellement</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>Dans le tableau Pipeline, le bouton <strong>▶ Analyser</strong> apparaît sur les marchés non encore analysés.</Li>
          <Li>Dans la fiche marché, le bouton d'analyse est disponible en bas si le marché n'a pas encore été traité par Mistral.</Li>
          <Li>Le bouton <strong>Analyser les en attente</strong> (Paramètres → Intégrations) relance l'analyse sur tous les marchés sans score IA.</Li>
          <Li>Sans clé Mistral configurée, aucune analyse IA n'est possible — le score reste à 50 ou 0.</Li>
        </ul>
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
            ['Secteur', 'Public / Privé / International', "Bascule entre marchés publics, signaux privés et appels d'offres internationaux."],
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
            ['Territoire', 'La Réunion, France métropole, International, etc.'],
            ['Deadline', "Date limite de remise de l'offre."],
            ['Score', 'Note de pertinence de 0 à 100. Provisoire (50) avant analyse IA, définitif après.'],
            ['GO/NO-GO', '🟢 GO ≥ 65 · 🟡 Étudier 35–64 · 🔴 Passer < 35'],
            ['Statut', 'Statut actuel dans le cycle de vie du marché.'],
            ['Source', "Nom de la plateforme source — cliquable pour ouvrir l'annonce originale."],
            ['IA', '✓ Analysé · ▶ Analyser (déclencher manuellement) · barre de chargement en cours.'],
          ]}
        />
      </section>

      {/* ── FICHE DETAIL ───────────────────────────────────────────────────── */}
      <section>
        <H2>Fiche marché (détail)</H2>
        <P>Cliquez sur une ligne du tableau pour ouvrir le panneau de détail.</P>

        <H3>Informations affichées</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>Badge GO/NO-GO + score/100 en haut de la fiche.</Li>
          <Li>Deadline avec compteur J-X coloré (rouge si ≤ 7 jours, orange si ≤ 30 jours).</Li>
          <Li>Montant estimé du marché, secteur, source.</Li>
          <Li>Lien direct vers l'annonce originale (<strong>Voir l'annonce ↗</strong>).</Li>
          <Li>Plan d'action commercial contextuel selon le score et l'urgence.</Li>
          <Li>Décomposition du score en 4 barres (pertinence métier, géographie, titre, maintenance).</Li>
          <Li>Bloc Analyse IA si Mistral a traité le marché : type de travaux, budget, concurrents, recommandation.</Li>
        </ul>

        <H3>Actions disponibles</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>
            <strong>Changer le statut</strong> — menu déroulant (À qualifier → En cours → Soumis → Gagné / Perdu).
          </Li>
          <Li>
            <strong>Étoile (favori)</strong> — sauvegardez un marché pour le retrouver facilement.
          </Li>
        </ul>
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
      </section>

      {/* ── URGENCES ───────────────────────────────────────────────────────── */}
      <section>
        <H2>Urgences</H2>
        <P>
          La page Urgences liste les marchés GO (score ≥ 65) dont l'échéance est dans moins de 30 jours.
          Le badge rouge en sidebar indique combien d'urgences sont en cours.
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
          <Li><strong>Publications / semaine</strong> — histogramme des 30 dernières semaines.</Li>
          <Li><strong>Par territoire</strong> — donut La Réunion / autres.</Li>
          <Li><strong>Par domaine</strong> — SSI, CMSI, Vidéo, Courants faibles.</Li>
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
          L'analyse IA utilise Mistral. Sans clé valide, les marchés ne sont pas analysés automatiquement
          et le score reste provisoire (50 ou 0).
        </P>
        <ul className="space-y-1.5 mb-4">
          <Li>Collez votre clé API Mistral dans le champ prévu.</Li>
          <Li>Cliquez <strong>Sauvegarder</strong> — la clé est écrite dans le fichier <code>.env</code> et rechargée à chaud, sans redémarrer le serveur.</Li>
          <Li>Le badge <Chip color="teal">● Clé active</Chip> / <Chip color="coral">● Non configurée</Chip> indique l'état en temps réel.</Li>
          <Li>Une fois la clé configurée, cliquez <strong>Analyser les en attente</strong> pour traiter tous les marchés non encore scorés par l'IA.</Li>
        </ul>

        <H3>Apparence</H3>
        <ul className="space-y-1.5 mb-4">
          <Li><strong>Curseur de luminosité</strong> — ajuste la clarté globale de l'interface. Le réglage est sauvegardé dans le navigateur.</Li>
        </ul>

        <H3>Doublons</H3>
        <ul className="space-y-1.5 mb-4">
          <Li>Cliquez <strong>Détecter les doublons</strong> pour lancer l'analyse de similarité entre marchés.</Li>
          <Li>
            L'algorithme calcule une empreinte <strong>SimHash 64 bits</strong> sur le titre de chaque marché,
            puis utilise un <strong>bucketing LSH 4 bandes</strong> pour regrouper les candidats proches sans comparer toutes les paires.
            Deux marchés sont signalés doublons si leur <strong>distance de Hamming ≤ 12</strong> (titres quasi-identiques)
            ou ≤ 20 (titres similaires).
          </Li>
          <Li>Les paires détectées s'affichent avec le score de similarité et les deux titres côte à côte.</Li>
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
            { cat: '🏝️ Sources locales Océan Indien', sources: ['Département 974', 'NUKEMA', 'VAAO', 'Instao', 'Tenders Go'] },
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
        </p>
      </section>

      {/* ── WORKFLOW QUOTIDIEN ─────────────────────────────────────────────── */}
      <section>
        <H2>Workflow quotidien recommandé</H2>
        <ol className="space-y-4">
          {[
            {
              step: '1 — Collecte',
              desc: "Depuis la sidebar, cliquez ⟳ Lancer la collecte. La collecte tourne en arrière-plan (job asynchrone) — la sidebar affiche la progression en temps réel et un résumé apparaît à la fin. Les nouveaux marchés sont analysés par Mistral automatiquement si la clé est configurée.",
            },
            {
              step: '2 — Triage GO',
              desc: "Dans Pipeline, filtrez sur GO/NO-GO = GO. Parcourez les marchés en À qualifier. Pour chaque GO pertinent, passez en En cours.",
            },
            {
              step: '3 — Lecture fiches',
              desc: "Cliquez sur un marché En cours pour lire l'analyse IA. Vérifiez le délai (J-X), le montant, le domaine, les concurrents éventuels.",
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
          <Li>Le badge 🔔 en sidebar indique le nombre de marchés GO urgents (échéance &lt; 30 j).</Li>
        </ul>
      </section>

    </div>
  )
}
