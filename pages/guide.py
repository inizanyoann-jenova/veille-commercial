import streamlit as st

st.set_page_config(page_title="Guide — DEF OI", page_icon="📖", layout="wide")
st.title("📖 Guide utilisateur — DEF Océan Indien")
st.caption("Version 2.0 — Mise à jour mai 2026")

# ── 1. Présentation ───────────────────────────────────────────────────────────
st.header("1. Qu'est-ce que cette application ?")
st.markdown("""
Cette application est un **outil de veille automatique des marchés publics** pour les
commerciaux de DEF Océan Indien.

Elle surveille en continu les appels d'offres publiés sur **La Réunion (974)** et
**Mayotte (976)** dans les domaines :

| Domaine | Exemples |
|---------|---------|
| SSI / CMSI | Systèmes de sécurité incendie, centrales |
| Détection incendie | Alarmes, détecteurs, désenfumage |
| Vidéosurveillance | CCTV, caméras, contrôle d'accès |
| Courants faibles | Câblage, réseaux, domotique |

L'IA analyse chaque opportunité et lui attribue un **score de pertinence** (0–100).
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
Calculé par l'IA (Gemini) sur le titre et la description.
- **80–100** : très pertinent, à traiter en priorité
- **50–79** : pertinent, à examiner
- **0–49** : faible pertinence, probablement hors périmètre
""")

# ── 3. Sources ────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("3. Sources de collecte")
st.markdown("""
L'application collecte automatiquement sur ces sources :
""")

sources_data = [
    ("BOAMP — Journal Officiel", "Public", "✅ Automatique", "Non", "AO officiels France entière"),
    ("DECP / PLACE", "Public", "✅ Automatique", "Non", "Données essentielles commande publique"),
    ("TED Europe", "Public", "✅ Automatique", "Non", "AO européens (marchés > seuil)"),
    ("VAAO", "Public", "✅ Automatique", "Non", "Agrégateur AO Réunion/Mayotte"),
    ("Marché Online", "Public", "✅ Automatique", "Non", "Agrégateur AO par département"),
    ("Marchés Publics — Dép. 974", "Public", "✅ Automatique", "Non", "AO officiels Conseil Dép. Réunion"),
    ("Nukema", "Public", "✅ Automatique", "Optionnel", "Veille marchés publics France"),
    ("Marchés Public Info", "Public", "✅ Automatique", "Non", "Agrégateur marchés publics"),
    ("Permis de construire", "Privé", "✅ Automatique", "Non", "Signaux avant-vente construction"),
    ("Presse & Institutions IO", "Privé", "✅ Automatique", "Non", "Actualités locales Réunion"),
    ("Marchés Sécurisés", "Privé", "✅ Automatique", "Oui ⚠️", "Plateforme dématérialisée"),
    ("Instao", "Privé", "✅ Automatique", "Oui ⚠️", "IA marchés publics"),
    ("Banques Dev. (BAD/BEI/COI)", "International", "✅ Automatique", "Non", "Projets africains et insulaires"),
    ("AFD", "International", "✅ Automatique", "Non", "Projets Agence Française Développement"),
    ("Banque Mondiale", "International", "✅ Automatique", "Non", "Projets Banque Mondiale"),
    ("UNGM", "International", "✅ Automatique", "Non", "Marchés ONU"),
    ("Tenders Go", "International", "✅ Automatique", "Oui ⚠️", "Agrégateur mondial"),
]

import pandas as pd
df = pd.DataFrame(sources_data, columns=["Source", "Catégorie", "Collecte", "Compte requis", "Couverture"])
st.dataframe(df, use_container_width=True, hide_index=True)

st.info("⚠️ Les sources marquées 'Compte requis' nécessitent vos identifiants dans **⚙️ Paramètres**.")

# ── 4. Lancer une collecte ────────────────────────────────────────────────────
st.markdown("---")
st.header("4. Lancer une collecte — pas à pas")
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

**Étape 4 — Consulter les résultats**
Les nouveaux AO apparaissent en haut du tableau avec le statut **"À qualifier"**.
L'analyse IA se déclenche automatiquement après la collecte.

**Étape 5 — Traiter les AO**
Changez le statut, ajoutez des notes, lancez une analyse IA manuelle si besoin.
""")

# ── 5. Gérer les opportunités ─────────────────────────────────────────────────
st.markdown("---")
st.header("5. Gérer les opportunités")
st.markdown("""
### Changer le statut
Dans la colonne **Statut** de chaque ligne, utilisez le menu déroulant pour faire évoluer l'AO.

### Déclencher l'analyse IA
Cliquez sur **🤖 Analyser** sur un AO pour obtenir :
- Un résumé en quelques lignes
- Un score de pertinence (0–100)
- Les domaines concernés (SSI, CMSI, vidéo…)
- Une justification du score

### Exporter le rapport Excel
Le bouton **📊 Télécharger le Rapport Direction** génère un fichier Excel avec :
- Tous les AO actifs
- Les scores et analyses
- Les statuts et dates

Ce rapport est conçu pour être partagé en réunion commerciale.
""")

# ── 6. Configurer les identifiants ────────────────────────────────────────────
st.markdown("---")
st.header("6. Configurer les identifiants")
st.markdown("""
Deux méthodes pour configurer les identifiants des sources qui le nécessitent :

### Méthode 1 — Via l'interface (recommandée)
1. Allez dans **⚙️ Paramètres** (menu latéral)
2. Dépliez la source souhaitée
3. Entrez email et mot de passe
4. Cliquez **💾 Enregistrer**

### Méthode 2 — Via le fichier `.env`
Ouvrez le fichier `.env` à la racine du projet et ajoutez :
```
MARCHES_SEC_EMAIL=votre@email.com
MARCHES_SEC_PASSWORD=votre_mot_de_passe

INSTAO_EMAIL=votre@email.com
INSTAO_PASSWORD=votre_mot_de_passe

TENDERSGO_EMAIL=votre@email.com
TENDERSGO_PASSWORD=votre_mot_de_passe

NUKEMA_EMAIL=votre@email.com
NUKEMA_PASSWORD=votre_mot_de_passe
```
Puis **relancez l'application**. Les variables `.env` ont toujours la priorité sur la base de données.
""")

# ── 7. FAQ ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("7. FAQ & Résolution de problèmes")

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
    1. Allez dans **⚙️ Paramètres**
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
    playwright install chromium
    ```
    """)

with st.expander("Comment sauvegarder mes données ?"):
    st.markdown("""
    Toutes les données sont dans le fichier `def_oi_veille.db` (SQLite).
    Faites une copie régulière de ce fichier pour sauvegarder vos AO et analyses.
    """)
