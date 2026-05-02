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
| Importer les marchés BOAMP | Sidebar → bouton **🔄 Lancer la collecte** |
| Filtrer par statut / maintenance | Sidebar — filtres |
| Changer le statut d'un marché | Tableau interactif → colonne **Statut** (double-clic) |
| Lancer l'analyse IA (GPT) | Bas de page → sélectionner un marché → **▶ Lancer l'analyse GPT** |

---

## Export pour la Direction

Cliquez sur le bouton **📊 Télécharger le Rapport Direction (Excel)** en haut de la page.

Un fichier `Rapport_Direction_DEF_AAAAMMJJ_HHMM.xlsx` est téléchargé immédiatement.  
Il contient :
- **Onglet "Opportunités DEF OI"** — tous les marchés sauf ceux au statut "Perdu", avec colonnes renommées et code couleur par statut.
- **Onglet "Infos Rapport"** — métadonnées (date de génération, périmètre).

Ce fichier peut être envoyé directement à la Direction sans aucune manipulation supplémentaire.
