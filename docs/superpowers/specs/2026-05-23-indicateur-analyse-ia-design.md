# Spec — Indicateur d'analyse IA + déclenchement manuel

## Contexte

L'application collecte des appels d'offres (tenders) via des scrapers. L'IA Mistral analyse chaque tender et stocke le résultat dans les colonnes `llm_analysis` (JSON) et `llm_structured` (JSON) de la table `tenders`. Actuellement, il n'y a aucun moyen visuel de savoir quels marchés ont été analysés, ni de déclencher manuellement l'analyse sur une ligne précise.

## Objectif

Ajouter dans le tableau des marchés une colonne "IA" permettant de :
- **Voir** lesquels ont été analysés par Mistral
- **Déclencher manuellement** l'analyse sur un marché non encore analysé

## Choix de design

- **Emplacement** : colonne dédiée "IA" dans `TendersTable` (visible en permanence, pas au survol ni dans le panneau détail)
- **Re-analyse** : non — une fois analysé, le badge vert est verrouillé
- **État de chargement** : barre de progression bleue animée dans la colonne pendant l'appel Mistral
- **Approche réseau** : requête synchrone `POST /api/tenders/{id}/analyze` (Mistral répond en 3-8s, pas besoin de tâche en arrière-plan)

## Architecture

### Backend — `app.py`

Nouveau endpoint :

```
POST /api/tenders/{id}/analyze
```

Comportement :
1. Récupère le tender par `id` en base (404 si introuvable)
2. Appelle le LLM analyzer existant (`llm_analyzer.py`)
3. Sauvegarde `llm_analysis` et `llm_structured` sur le tender
4. Retourne le tender mis à jour en JSON (500 si Mistral échoue)

Aucun nouveau champ en base : `llm_analysis is not None` suffit à dériver le statut "analysé".

### Frontend — 3 fichiers touchés

#### `frontend/src/services/api.js`

Nouvelle fonction :

```js
analyzeTender(id)  // POST /api/tenders/{id}/analyze
```

#### `frontend/src/hooks/useTenders.js`

Nouveau hook :

```js
useAnalyzeTender()
```

Mutation React Query. Au succès : invalide le cache de la liste des tenders pour rafraîchir automatiquement la ligne concernée.

#### `frontend/src/components/TendersTable.jsx`

- Ajout d'une colonne `IA` à droite du tableau
- État local `analyzingIds` (Set) pour tracker les lignes en cours
- Trois états visuels par ligne :

| Condition | Affichage |
|---|---|
| `llm_analysis === null` et ID absent de `analyzingIds` | Bouton rouge `▶ Analyser` |
| ID présent dans `analyzingIds` | Barre bleue animée (désactivé) |
| `llm_analysis !== null` | Badge vert `✓ Analysé` |

- Au clic "▶ Analyser" : ajout dans `analyzingIds` → mutation → retrait de `analyzingIds` (succès ou erreur)

## Flux complet

```
Utilisateur clique ▶ Analyser
  → ID ajouté à analyzingIds (barre animée s'affiche)
  → POST /api/tenders/{id}/analyze
  → Backend appelle Mistral, sauvegarde llm_analysis
  → Réponse 200 + tender mis à jour
  → React Query invalide le cache
  → ID retiré de analyzingIds
  → Ligne se rafraîchit → badge vert ✓ Analysé
```

## Fichiers modifiés

| Fichier | Nature de la modification |
|---|---|
| `app.py` | Ajout endpoint `POST /api/tenders/{id}/analyze` |
| `frontend/src/services/api.js` | Ajout fonction `analyzeTender` |
| `frontend/src/hooks/useTenders.js` | Ajout hook `useAnalyzeTender` |
| `frontend/src/components/TendersTable.jsx` | Ajout colonne IA avec 3 états visuels |
