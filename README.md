# DEF Océan Indien — Outil de Veille Marchés Publics

Outil de qualification commerciale pour les départements **974 (La Réunion)** et **976 (Mayotte)**.  
Métiers couverts : SSI, CMSI, Détection incendie, Désenfumage, Vidéosurveillance, Courants faibles.

---

## Installation (première fois)

```bash
pip install -r requirements.txt
```

Copiez `.env.example` en `.env` et renseignez votre clé OpenAI :

```
OPENAI_API_KEY=sk-...
```

---

## Lancement

```bash
streamlit run app.py
```

L'application s'ouvre dans le navigateur à l'adresse `http://localhost:8501`.

---

## Guide d'utilisation rapide

| Action | Où |
|---|---|
| Lancer la collecte | Sidebar → **⚡ Collecter la sélection** |
| Filtrer par statut / domaine / territoire | Sidebar — filtres |
| Changer le statut d'un marché | Tableau interactif → colonne **Statut** |
| Lancer l'analyse IA (Claude) | Sidebar → **🤖 Analyser en lot (Claude)** |
| Voir les urgences du jour | Bandeau en haut de la page principale |
| Vue pipeline Kanban | Menu latéral → **📋 Pipeline** |
| Envoyer le digest email | **⚙️ Paramètres → Digest email → Envoyer maintenant** |
| Rapport Direction PDF | Menu latéral → **📊 Direction → Télécharger le rapport PDF** |
| Détecter les doublons | **⚙️ Paramètres → Doublons → Détecter** |
| Recalculer le score adaptatif | **⚙️ Paramètres → Score adaptatif → Recalculer** |

---

## Export pour la Direction

### Rapport Excel
Cliquez sur le bouton **📊 Télécharger le Rapport Direction (Excel)** en haut de la page.

Un fichier `Rapport_Direction_DEF_AAAAMMJJ_HHMM.xlsx` est téléchargé immédiatement.  
Il contient :
- **Onglet "Opportunités DEF OI"** — tous les marchés sauf ceux au statut "Perdu", avec colonnes renommées et code couleur par statut.
- **Onglet "Infos Rapport"** — métadonnées (date de génération, périmètre).

### Page Direction (PDF)
La page **📊 Direction** (menu latéral) offre une vue exécutive avec KPIs, graphique d'activité 90 jours et tableau pipeline. Le bouton **📄 Télécharger le rapport PDF** génère un fichier `Rapport_Direction_DEF_AAAAMMJJ.pdf` prêt à présenter.

## Digest email quotidien

Configurez dans `.env` :
```
DIGEST_SMTP_HOST=smtp.gmail.com
DIGEST_SMTP_PORT=587
DIGEST_SMTP_USER=votre.email@gmail.com
DIGEST_SMTP_PASSWORD=mot_de_passe_app_gmail
DIGEST_TO=inizan.yoann@gmail.com
DIGEST_HOUR=7
```

Puis planifiez `python send_digest.py` via le Planificateur de tâches Windows pour recevoir chaque matin les nouveaux marchés GO sans ouvrir l'application.
