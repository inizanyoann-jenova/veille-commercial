import streamlit as st
import pandas as pd

st.set_page_config(page_title="Guide — DEF OI", page_icon="📖", layout="wide")
st.title("📖 Guide utilisateur — DEF Océan Indien")
st.caption("Version 4.0 — Mise à jour mai 2026")

# ── 0. Procédure nouvel utilisateur ──────────────────────────────────────────
st.header("🚀 Procédure d'installation — Nouvel utilisateur")
st.success("Suivez ces étapes dans l'ordre si vous installez l'application pour la première fois sur un nouveau PC.")

st.markdown("""
### Prérequis
- **Python 3.10 ou supérieur** installé sur le PC ([python.org](https://www.python.org/downloads/))
- Le dossier de l'application copié sur le bureau (avec le fichier `def_oi_veille.db` si vous migrez depuis un autre poste)
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 1")
    st.markdown("**Ouvrir un terminal dans le dossier de l'application**")
with col2:
    st.markdown("""
Clic droit dans le dossier → **Ouvrir dans le terminal** (ou PowerShell).

Vérifiez que Python est bien installé :
```bash
python --version
```
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 2")
    st.markdown("**Installer les dépendances Python**")
with col2:
    st.markdown("""
```bash
pip install -r requirements.txt
```
Cette commande installe Streamlit, SQLAlchemy, Claude (anthropic), Playwright et toutes les autres librairies nécessaires.

⏳ Durée estimée : 1–3 minutes selon la connexion.
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 3")
    st.markdown("**Installer le navigateur Playwright**")
with col2:
    st.markdown("""
```bash
playwright install chromium
```
Playwright est le navigateur automatisé utilisé pour collecter les sources qui nécessitent un vrai navigateur (Marchés Sécurisés, Instao, etc.).

⏳ Durée estimée : 1–2 minutes.
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 4")
    st.markdown("**Lancer l'application**")
with col2:
    st.markdown("""
```bash
streamlit run app.py
```
L'application s'ouvre automatiquement dans votre navigateur à l'adresse `http://localhost:8501`.

> Si la page ne s'ouvre pas, tapez manuellement `http://localhost:8501` dans votre navigateur.
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 5")
    st.markdown("**Configurer la clé API Claude** *(obligatoire pour l'analyse IA)*")
with col2:
    st.markdown("""
1. Dans l'application, allez dans **⚙️ Paramètres** (menu latéral gauche)
2. Dépliez la section **🤖 Intelligence Artificielle**
3. Collez votre clé API (commence par `sk-ant-api03-…`)
4. Cliquez **💾 Enregistrer la clé**
5. Cliquez **🧪 Tester la clé** pour valider

> 📌 Vous obtenez une clé API sur **[console.anthropic.com](https://console.anthropic.com)** → API Keys → Create Key.
> La clé n'est affichée qu'une seule fois — copiez-la immédiatement.
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 6 *(optionnelle)*")
    st.markdown("**Configurer les identifiants des sources privées**")
with col2:
    st.markdown("""
Uniquement nécessaire si vous utilisez **Marchés Sécurisés**, **Instao** ou **Tenders Go** :

1. Allez dans **⚙️ Paramètres → 🔐 Identifiants des sources**
2. Dépliez la source souhaitée
3. Entrez email et mot de passe
4. Cliquez **💾 Enregistrer**
5. Optionnel : **🔌 Tester la connexion** pour valider

Les mots de passe sont chiffrés en base de données — ils ne sont jamais lisibles en clair.
""")

st.markdown("---")

col1, col2 = st.columns([1, 2])
with col1:
    st.markdown("### Étape 7")
    st.markdown("**Lancer votre première collecte**")
with col2:
    st.markdown("""
1. Revenez sur la page principale (🏠 dans le menu latéral)
2. Dans la barre latérale, sélectionnez vos sources (commencez par BOAMP, DECP, VAAO)
3. Choisissez la période **"Depuis 2 ans"** (recommandé pour un premier import)
4. Cliquez **⚡ Collecter la sélection**
5. Attendez la fin de la collecte (1–5 minutes selon les sources)
6. Cliquez **🤖 Analyser en lot (Claude)** pour enrichir les résultats avec l'IA
""")

st.info("✅ L'application est prête. Consultez les sections ci-dessous pour aller plus loin.", icon="✅")

st.markdown("---")

# ── 1. Présentation ───────────────────────────────────────────────────────────
st.header("1. Qu'est-ce que cette application ?")
st.markdown("""
Cette application est un **outil de veille automatique des marchés publics** conçu spécifiquement
pour les commerciaux de **DEF Océan Indien**.

### Ce qu'elle fait concrètement

Chaque jour, elle parcourt automatiquement **17 sources** (plateformes officielles, agrégateurs,
sites privés, banques de développement) et collecte tous les appels d'offres publiés sur
**La Réunion (974)** et **Mayotte (976)** — sans que vous ayez à vous connecter manuellement à chacune.

Elle filtre ensuite les résultats selon les **4 domaines métier de DEF OI** :

| Domaine | Exemples de marchés ciblés |
|---------|---------------------------|
| 🔥 SSI / CMSI | Systèmes de sécurité incendie, centrales de détection, désenfumage |
| 🔍 Détection incendie | Alarmes, détecteurs optiques, déclencheurs manuels, sprinklers |
| 📷 Vidéosurveillance | CCTV, caméras IP/PTZ, NVR, VMS, PC sécurité |
| ⚡ Courants faibles | Contrôle d'accès, interphonie, GTB, anti-intrusion |

### Ce qu'elle produit

- Un **score de pertinence (0–100)** pour chaque appel d'offres, calculé automatiquement
- Un **résumé en langage naturel** expliquant pourquoi le marché est (ou non) dans le périmètre DEF OI
- Une **fiche commerciale** complète avec domaine technique, budget estimé, type de travaux, lots identifiés
- Un **pipeline commercial** suivi statut par statut : À qualifier → En cours → Soumis → Gagné/Perdu
- Un **rapport Direction** exportable (Excel et PDF) pour les réunions commerciales
- Un **digest email quotidien** envoyé chaque matin avec les nouvelles opportunités

### Ce qu'elle remplace

Sans cet outil, un commercial devrait ouvrir manuellement 17 sites chaque matin, copier-coller
les marchés pertinents dans un tableur, et évaluer lui-même la pertinence de chacun.
Avec l'outil, cette veille quotidienne prend moins de **5 minutes** au lieu de 1 à 2 heures.
""")

# ── 2. Tableau de bord ────────────────────────────────────────────────────────
st.markdown("---")
st.header("2. Tableau de bord — lire les résultats")
st.markdown("""
### Les KPIs en haut de page
- **Total AO** : nombre total d'appels d'offres collectés
- **En cours** : AO avec statut "En cours" ou "Soumis"
- **Gagnés** : AO remportés
- **Score moyen** : pertinence moyenne des AO actifs

### Les statuts
Chaque AO suit ce cycle de vie :

```
À qualifier  →  En cours  →  Soumis  →  Gagné
                                    ↘  Perdu
```

- **À qualifier** : nouvel AO importé, à examiner
- **En cours** : vous travaillez sur ce dossier
- **Soumis** : offre déposée
- **Gagné / Perdu** : résultat connu

### Le score de pertinence (0–100)
Calculé par l'IA (Claude) à partir du titre, de la description et du contenu du DCE.

| Score | Signification | Action recommandée |
|-------|--------------|-------------------|
| 🟢 65–100 | **Très pertinent** — cœur de métier DEF OI | Préparer une offre |
| 🟡 35–64 | **À évaluer** — signal présent, à confirmer | Lire le CCTP |
| 🔴 0–34 | **Hors périmètre** — peu de chance de gain | Passer |

Le score combine **70 % analyse Claude** (compréhension sémantique du texte) +
**30 % règles métier DEF** (mots-clés SSI/CMSI/Vidéo/CF, géographie, type de prestation).

Si la clé API Claude n'est pas configurée, seul le moteur local (30 %) est utilisé.
""")

# ── 3. Configurer la clé API Claude ──────────────────────────────────────────
st.markdown("---")
st.header("3. Clé API Claude — avantages et configuration")
st.info("**Sans cette clé, l'analyse IA ne fonctionne pas.** La collecte et le filtrage de base restent disponibles, mais le score sera calculé uniquement par les règles locales (30 % de précision).", icon="⚠️")

st.markdown("""
### Pourquoi activer la clé API IA ?

L'application intègre deux moteurs d'analyse qui travaillent en parallèle :

| | Sans clé API | Avec clé API |
|--|--|--|
| **Précision du score** | 30 % (règles locales) | 100 % (70 % IA + 30 % règles) |
| **Compréhension du texte** | Mots-clés exacts uniquement | Compréhension sémantique complète |
| **Marchés détectés** | Les plus évidents | Y compris les marchés formulés indirectement |
| **Justification** | Aucune | 3 phrases expliquant le score en français |
| **Analyse structurée** | Non disponible | Budget estimé, lots, type de travaux, recommandation |
| **Historique acheteur** | Non disponible | Analyse automatique des marchés passés |
| **Coût** | Gratuit | Environ **0,50 € à 2 € / mois** selon le volume |

**En résumé :** sans clé API, l'outil collecte et filtre mais ne "comprend" pas les marchés.
Avec la clé, chaque appel d'offres est lu et analysé comme le ferait un ingénieur expérimenté.

---

### Compatibilité — quelle clé utiliser ?

> ⚠️ **Important :** cette application utilise exclusivement l'IA **Claude d'Anthropic**.
> Les clés OpenAI (ChatGPT), Google Gemini ou autres ne sont **pas compatibles**.
> Vous devez impérativement utiliser une clé qui commence par `sk-ant-api03-…`

---

### Où acheter des crédits API Anthropic ?

Toutes les offres sont sur la plateforme officielle Anthropic. Voici les liens directs :

| Lien | Description |
|------|-------------|
| 🔑 [console.anthropic.com](https://console.anthropic.com) | Console principale — créer un compte, gérer les clés |
| 💳 [console.anthropic.com/settings/billing](https://console.anthropic.com/settings/billing) | Ajouter des crédits (carte bancaire) |
| 💰 [anthropic.com/pricing](https://www.anthropic.com/pricing) | Tarifs officiels par modèle |
| 📘 [docs.anthropic.com](https://docs.anthropic.com) | Documentation et limites d'utilisation |
| 🏢 [anthropic.com/api](https://www.anthropic.com/api) | Offres entreprise et API overview |

**Tarif indicatif pour cette application :**
L'outil utilise le modèle *Claude Haiku* (le plus économique d'Anthropic) pour les analyses courantes.
Pour une utilisation typique (50 à 150 marchés analysés par mois), comptez **moins de 1 € / mois**.
Un rechargement de **5 $ (≈ 4,60 €)** couvre généralement plusieurs mois d'utilisation.

---

### Étape 1 — Créer un compte Anthropic
Rendez-vous sur **[console.anthropic.com](https://console.anthropic.com)** et créez un compte
avec l'adresse email de DEF OI (ou connectez-vous si vous avez déjà un compte).

### Étape 2 — Ajouter des crédits (si compte nouveau)
1. Cliquez **Settings** → **Billing**
2. Cliquez **Add credits**
3. Entrez un montant (5 $ minimum recommandé pour démarrer)
4. Payez par carte bancaire — les crédits sont disponibles immédiatement

### Étape 3 — Créer une clé API
1. Dans le menu de gauche, cliquez **API Keys**
2. Cliquez **Create Key**
3. Nommez-la (ex : *DEF OI Veille Marchés*)
4. **Copiez la clé immédiatement** — elle commence par `sk-ant-api03-…`
   > ⚠️ La clé n'est affichée **qu'une seule fois**. Si vous la perdez, il faudra en créer une nouvelle.

### Étape 4 — Saisir la clé dans l'application
Deux méthodes équivalentes :

**Méthode A — Directement dans l'interface (recommandée)**
1. Allez dans **⚙️ Paramètres** (menu latéral)
2. La section **🤖 Intelligence Artificielle** est en haut
3. Dépliez-la, collez votre clé dans le champ
4. Cliquez **💾 Enregistrer la clé**
5. Optionnel : cliquez **🧪 Tester la clé** pour vérifier

La clé est enregistrée dans le fichier `.env` et active **immédiatement**, sans redémarrage.

**Méthode B — Éditer le fichier `.env` manuellement**
Ouvrez le fichier `.env` à la racine du dossier projet avec Notepad et ajoutez :
```
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
```
Puis relancez l'application (`streamlit run app.py`).
""")

# ── 4. Sources de collecte ────────────────────────────────────────────────────
st.markdown("---")
st.header("4. Sources de collecte")
st.markdown("L'application collecte automatiquement sur ces sources :")

sources_data = [
    ("BOAMP — Journal Officiel", "Public", "✅ Automatique", "Non", "AO officiels France entière"),
    ("DECP / PLACE", "Public", "✅ Automatique", "Non", "Données essentielles commande publique"),
    ("TED Europe", "Public", "✅ Automatique", "Non", "AO européens (marchés > seuil)"),
    ("VAAO", "Public", "✅ Automatique", "Non", "Agrégateur AO Réunion/Mayotte"),
    ("Marché Online", "Public", "✅ Automatique", "Non", "Agrégateur AO par département"),
    ("Marchés Publics — Dép. 974", "Public", "✅ Automatique", "Non", "AO officiels Conseil Dép. Réunion"),
    ("Nukema", "Public", "✅ Automatique", "Optionnel", "Veille marchés publics France"),
    ("Marchés Public Info", "Public", "✅ Automatique", "Non", "Agrégateur marchés publics"),
    ("Permis de construire", "Public", "✅ Automatique", "Non", "Signaux avant-vente construction"),
    ("Presse & Institutions IO", "Public", "✅ Automatique", "Non", "Actualités locales Réunion"),
    ("Marchés Sécurisés", "Privé", "✅ Automatique", "Oui ⚠️", "Plateforme dématérialisée"),
    ("Instao", "Privé", "✅ Automatique", "Oui ⚠️", "IA marchés publics"),
    ("Banques Dev. (BAD/BEI/COI)", "International", "✅ Automatique", "Non", "Projets africains et insulaires"),
    ("AFD", "International", "✅ Automatique", "Non", "Projets Agence Française Développement"),
    ("Banque Mondiale", "International", "✅ Automatique", "Non", "Projets Banque Mondiale"),
    ("UNGM", "International", "✅ Automatique", "Non", "Marchés ONU"),
    ("Tenders Go", "International", "✅ Automatique", "Oui ⚠️", "Agrégateur mondial"),
]

df = pd.DataFrame(sources_data, columns=["Source", "Catégorie", "Collecte", "Compte requis", "Couverture"])
st.dataframe(df, use_container_width=True, hide_index=True)

st.info("⚠️ Les sources marquées 'Compte requis' nécessitent vos identifiants dans **⚙️ Paramètres → Identifiants des sources**.")

# ── 5. Lancer une collecte ────────────────────────────────────────────────────
st.markdown("---")
st.header("5. Lancer une collecte — pas à pas")
st.markdown("""
**Étape 1 — Cocher les sources**
Dans la barre latérale gauche, cochez les sources que vous voulez interroger.
Les sources sans identifiant configuré seront ignorées automatiquement.

**Étape 2 — Choisir la période**
Sélectionnez la période d'analyse :
- *Depuis cette année* : AO publiés depuis janvier
- *Depuis 2 ans* (défaut) : recommandé pour un premier import
- *Tout afficher* : tous les AO disponibles (peut être lent)

**Étape 3 — Cliquer "⚡ Collecter la sélection"**
La collecte démarre. Pour les sources Playwright (navigateur), cela peut prendre 1–3 minutes.

**Étape 4 — Analyser en lot avec Claude**
Après la collecte, cliquez **🤖 Analyser en lot (Claude)** dans la barre latérale.
Claude analyse les 10 marchés les plus prioritaires (ceux avec le meilleur score local) et
enrichit chacun avec une justification en langage naturel.

**Étape 5 — Consulter les résultats**
Les nouveaux AO apparaissent en haut du tableau avec le statut **"À qualifier"**.

**Étape 6 — Traiter les AO**
Changez le statut, ajoutez des notes, lancez une réanalyse individuelle si besoin.
""")

# ── 6. Analyse IA — fonctionnement détaillé ──────────────────────────────────
st.markdown("---")
st.header("6. Analyse IA — comment ça fonctionne ?")
st.markdown("""
### Deux moteurs en parallèle

**Moteur local (toujours actif, sans clé API)**
- Analyse par mots-clés : SSI, CMSI, vidéosurveillance, courants faibles, ERP...
- Détection géographique (974, 976, communes, codes postaux)
- Bonus maintenance, ERP, marques concurrentes
- Résultat instantané, aucun coût

**Moteur Claude (actif si clé API configurée)**
- Compréhension sémantique complète du texte
- Identifie les domaines DEF OI même quand les mots-clés sont absents
- Justification en 3 phrases : domaines techniques, territoire, type de prestation
- Résultat : score final = 70 % Claude + 30 % moteur local

### Analyse individuelle
Dans la **fiche commerciale** d'un AO, cliquez **🤖 Réanalyser avec Claude** pour forcer
une nouvelle analyse Claude, utile si vous avez enrichi la description.

### Analyse en lot
Le bouton **🤖 Analyser en lot (Claude)** dans la sidebar traite jusqu'à 10 marchés d'un coup,
en ciblant en priorité ceux qui ont le meilleur score local mais pas encore d'analyse Claude.

### Badge source
Sur chaque fiche, un badge indique l'origine du score :
- `🤖 Analyse Claude (70 % IA + 30 % règles métier)` — analyse complète
- `🔍 Analyse locale (règles métier DEF)` — clé API absente ou quota atteint
""")

# ── 7. Gérer les opportunités ─────────────────────────────────────────────────
st.markdown("---")
st.header("7. Gérer les opportunités")
st.markdown("""
### Changer le statut
Dans la colonne **Statut** de chaque ligne, utilisez le menu déroulant pour faire évoluer l'AO :
`À qualifier → En cours → Soumis → Gagné / Perdu`

### Ajouter des notes
Chaque AO dispose d'un champ de notes libre pour y consigner les éléments clés du dossier.

### Tags
Sur la fiche d'un AO, vous pouvez ajouter un ou plusieurs tags prédéfinis :
*Partenaire requis · En attente DCE · Budget bloqué · À voir avec DG · Offre déposée · Recours prévu*

Les tags sont filtrables depuis la sidebar et visibles directement sur les cartes.

### Score adaptatif
En plus du score de pertinence classique, un **score adaptatif** (badge 🧠) est calculé
à partir de vos décisions passées (GO / Soumis / Gagné / Perdu).
Plus vous utilisez l'outil, plus ce score devient précis.
Il est disponible une fois 10 décisions enregistrées.

### Supprimer un AO
Cliquez 🗑️ sur une ligne pour supprimer l'AO — il passe en "blacklist" et ne réapparaîtra
plus après une prochaine collecte.

### Exporter le rapport Excel
Le bouton **📊 Télécharger le Rapport Direction** génère un fichier Excel avec :
- Tous les AO actifs, scores et analyses
- Les statuts, dates, domaines et territoires
- Conçu pour être partagé en réunion commerciale
""")

# ── 8. Configurer les identifiants des sources ────────────────────────────────
st.markdown("---")
st.header("8. Configurer les identifiants des sources")
st.markdown("""
Deux méthodes pour les sources qui nécessitent un compte (Marchés Sécurisés, Instao, Tenders Go) :

### Méthode 1 — Via l'interface (recommandée)
1. Allez dans **⚙️ Paramètres** (menu latéral)
2. Section **🔐 Identifiants des sources**
3. Dépliez la source souhaitée
4. Entrez email et mot de passe
5. Cliquez **💾 Enregistrer**
6. Optionnel : cliquez **🔌 Tester la connexion** pour valider

Les mots de passe sont **chiffrés** en base de données.

### Méthode 2 — Via le fichier `.env`
Ouvrez `.env` à la racine du projet et ajoutez :
```
MARCHES_SEC_EMAIL=votre@email.com
MARCHES_SEC_PASSWORD=votre_mot_de_passe

INSTAO_EMAIL=votre@email.com
INSTAO_PASSWORD=votre_mot_de_passe

TENDERSGO_EMAIL=votre@email.com
TENDERSGO_PASSWORD=votre_mot_de_passe
```
Puis **relancez l'application**. Les variables `.env` ont toujours la priorité sur la base.
""")

# ── 8b. Digest email ─────────────────────────────────────────────────────────
st.markdown("---")
st.header("9. Digest email quotidien")
st.markdown("""
L'application peut envoyer chaque matin un email récapitulatif des nouvelles opportunités
détectées la veille, sans que vous ayez à ouvrir l'outil.

### Contenu de l'email
- **✅ GO (score ≥ 65)** — marchés qualifiés prêts à traiter, avec titre, domaine, territoire, score et deadline
- **🔍 À étudier (score 35–64)** — liste compacte pour décider si ça vaut un clic
- **⚠️ Urgences** — marchés GO avec deadline dans moins de 7 jours

Si aucun nouveau marché n'est détecté dans les 24h, l'email n'est pas envoyé.

### Configuration (fichier `.env`)
Ajoutez ces lignes dans votre fichier `.env` :
```
DIGEST_SMTP_HOST=smtp.gmail.com
DIGEST_SMTP_PORT=587
DIGEST_SMTP_USER=votre.email@gmail.com
DIGEST_SMTP_PASSWORD=mot_de_passe_app_gmail
DIGEST_TO=inizan.yoann@gmail.com
DIGEST_HOUR=7
```
> Pour Gmail : créez un **mot de passe d'application** dans votre compte Google
> (Sécurité → Connexion à Google → Mots de passe des applications).
> N'utilisez pas votre mot de passe Gmail habituel.

### Deux modes de déclenchement
**Mode automatique (recommandé)** — Script `send_digest.py` planifié via le Planificateur de tâches Windows :
- Fonctionne même si Streamlit est fermé
- Déclencheur : tous les jours à l'heure configurée (`DIGEST_HOUR`)

**Mode manuel** — Bouton **"📧 Envoyer le digest maintenant"** dans **⚙️ Paramètres → Digest email**
""")

st.info("💡 Pour planifier le script sous Windows : Planificateur de tâches → Créer une tâche → Action : `python C:\\chemin\\vers\\send_digest.py`")

# ── 10. Page Direction ─────────────────────────────────────────────────────────
st.markdown("---")
st.header("10. Page Direction — vue exécutive")
st.markdown("""
La page **📊 Direction** (menu latéral) est une vue synthétique conçue pour être montrée
directement à la Direction, sans les détails techniques de l'outil.

### Contenu
- **4 KPIs clés** : opportunités actives, CA prévisionnel, CA gagné, taux de conversion
- **Graphique activité 90 jours** : évolution du pipeline par semaine
- **Tableau pipeline en cours** : marchés GO + Soumis triés par deadline

### Export PDF
Le bouton **📄 Télécharger le rapport PDF** génère un document `Rapport_Direction_DEF_AAAAMMJJ.pdf`
avec les KPIs, le graphique et le tableau — prêt à envoyer ou présenter sans aucune manipulation.

> La page Analytics existante reste disponible pour les analyses techniques détaillées.
""")

# ── 11. Analyse structurée IA ──────────────────────────────────────────────────
st.markdown("---")
st.header("11. Analyse structurée IA")
st.markdown("""
En plus du résumé narratif Claude, chaque fiche marché peut afficher une **analyse structurée**
avec des champs exploitables pour décider plus vite :

| Champ | Exemple |
|---|---|
| Budget estimé | 150 000 € |
| Type de travaux | Installation neuve |
| Lots identifiés | Lot 1 — Détection · Lot 2 — SSI |
| Mots-clés techniques | ERP type J, SSI catégorie A, NF S 61-931 |
| Type d'acheteur | Établissement scolaire |
| Niveau de concurrence | Élevé |
| Recommandation IA | ✅ GO (confiance 78 %) |

Cette analyse est déclenchée automatiquement sur les marchés avec score ≥ 35 après chaque collecte.
Vous pouvez aussi cliquer **🔄 Ré-analyser** sur une fiche pour forcer le recalcul.

### Historique acheteur
Si l'acheteur a déjà publié des marchés similaires dans la base, une section
**"🏛️ Historique acheteur"** apparaît sur la fiche :
- Nombre de marchés publiés, nombre de GO, marchés gagnés, CA total gagné
- Les 3 derniers marchés cliquables pour consultation directe
""")

# ── 12. FAQ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("12. FAQ & Résolution de problèmes")

with st.expander("🤖 L'analyse Claude ne fonctionne pas / le badge affiche 'Analyse locale'"):
    st.markdown("""
    **Cause 1 — Clé API absente ou invalide**
    1. Allez dans **⚙️ Paramètres → 🤖 Intelligence Artificielle**
    2. Vérifiez que la clé est configurée (bandeau vert ✅)
    3. Si non, saisissez votre clé et cliquez **💾 Enregistrer la clé**
    4. Cliquez **🧪 Tester la clé** pour confirmer que la connexion fonctionne

    **Cause 2 — Package `anthropic` non installé**
    Dans le terminal, dans le dossier de l'application :
    ```bash
    pip install anthropic
    ```
    Puis relancez l'application.

    **Cause 3 — Quota atteint**
    Un bandeau jaune s'affiche avec un délai avant de réessayer.
    Sur un compte Enterprise, cela est très rare. Attendez quelques minutes et relancez.
    """)

with st.expander("Un scraper retourne une erreur 400 ou 500"):
    st.markdown("""
    - Vérifiez votre connexion internet
    - L'API ou le site peut être temporairement indisponible — relancez dans 10 minutes
    - Si l'erreur persiste, le format du site a peut-être changé (contacter le support)
    """)

with st.expander("Aucun résultat après une collecte"):
    st.markdown("""
    - Élargissez la période (passez à "2 ans" ou "Tout afficher")
    - Vérifiez que les sources sont bien cochées
    - Certaines sources (Marchés Sécurisés, Instao, Tenders Go) nécessitent un compte configuré
    """)

with st.expander("Les sources Playwright sont lentes"):
    st.markdown("""
    Un scraper Playwright (navigateur headless) prend 30–90 secondes par source.
    C'est normal — il simule un vrai navigateur pour accéder aux sites.
    Lancez la collecte et attendez la fin du spinner.
    """)

with st.expander("Identifiants incorrects — login échoué"):
    st.markdown("""
    1. Allez dans **⚙️ Paramètres → Identifiants des sources**
    2. Utilisez **🔌 Tester la connexion** pour vérifier
    3. Corrigez email/mot de passe et re-enregistrez
    4. Si le site a changé son formulaire de login, contactez le support
    """)

with st.expander("L'application ne démarre pas"):
    st.markdown("""
    Dans le terminal, dans le dossier de l'application :
    ```bash
    streamlit run app.py
    ```
    Si erreur `ModuleNotFoundError` :
    ```bash
    pip install -r requirements.txt
    pip install anthropic
    playwright install chromium
    ```
    """)

with st.expander("Comment sauvegarder mes données ?"):
    st.markdown("""
    Toutes les données sont dans le fichier `def_oi_veille.db` (SQLite).
    Faites une copie régulière de ce fichier pour sauvegarder vos AO et analyses.

    La clé API Claude et les identifiants sources sont dans le fichier `.env` —
    sauvegardez-le aussi (mais ne le partagez jamais : il contient vos mots de passe).
    """)

with st.expander("Comment savoir si l'analyse Claude a bien été faite ?"):
    st.markdown("""
    Sur chaque fiche commerciale, regardez le badge sous le score :
    - `🤖 Analyse Claude (70 % IA + 30 % règles métier)` → analyse Claude complète
    - `🔍 Analyse locale (règles métier DEF)` → analyse Claude non faite

    Dans la liste principale, la colonne **Source** indique `claude` ou `local`.
    Cliquez **🤖 Réanalyser avec Claude** sur la fiche pour forcer une (re)analyse.
    """)

with st.expander("Le digest email ne part pas"):
    st.markdown("""
    **Vérification 1 — Variables `.env` présentes**
    Ouvrez le fichier `.env` et confirmez que `DIGEST_SMTP_HOST`, `DIGEST_SMTP_USER`,
    `DIGEST_SMTP_PASSWORD` et `DIGEST_TO` sont tous renseignés.

    **Vérification 2 — Mot de passe d'application Gmail**
    N'utilisez pas votre mot de passe Gmail habituel.
    Créez un mot de passe d'application : compte Google → Sécurité → Mots de passe des applications.

    **Vérification 3 — Aucun nouveau marché**
    Si aucun GO ni "À étudier" n'est apparu dans les 24 dernières heures, l'email n'est pas envoyé.
    Utilisez le bouton **"📧 Envoyer maintenant"** dans Paramètres pour tester l'envoi.

    **Vérification 4 — Script non planifié**
    Si l'app Streamlit est fermée, seul le script `send_digest.py` peut envoyer l'email.
    Vérifiez que la tâche Windows est bien active (Planificateur de tâches).
    """)

with st.expander("Le score adaptatif n'apparaît pas"):
    st.markdown("""
    Le score adaptatif nécessite **au moins 10 décisions enregistrées** (marchés passés en
    Soumis, Gagné ou Perdu). Consultez **⚙️ Paramètres → Score adaptatif** pour voir
    le nombre de décisions disponibles et déclencher un recalcul manuel.
    """)
