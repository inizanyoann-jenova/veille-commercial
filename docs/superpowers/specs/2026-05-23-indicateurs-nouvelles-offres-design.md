# Spec — Indicateurs nouvelles offres & fraîcheur

**Date :** 2026-05-23  
**Statut :** Approuvé

---

## Contexte et problème

Trois problèmes identifiés dans l'état actuel :

1. **Barres de progression fausses dans la Sidebar** : les barres "Collecte" et "Mots-clés" affichent toujours 100% (`value = total = nb_new`). Elles ne reflètent aucune réalité mesurable.
2. **KpiGrid non rafraîchi après collecte** : `useCollectMutation.onSuccess` n'invalide pas `['kpis']`, donc le Dashboard ne se met pas à jour après une collecte.
3. **Aucun indicateur de fraîcheur** : impossible de savoir combien de nouvelles offres ont été collectées récemment sans aller dans l'historique des runs.

## Objectif

- Afficher un indicateur fiable du nombre de nouvelles offres (24h) sur le Dashboard.
- Rafraîchir automatiquement les KPIs du Dashboard après chaque collecte.
- Nettoyer la Sidebar : supprimer les barres fausses, garder seulement la barre Analyse IA.

---

## Architecture

### 1. Backend — `backend/main.py` : `/api/kpis/public`

Ajouter deux champs à la réponse JSON existante :

- `new_24h` : count des tenders avec `collected_at >= now() - 24h`, non blacklistés
- `new_7d` : count des tenders avec `collected_at >= now() - 7j`, non blacklistés

Implémentation : deux requêtes SQL supplémentaires dans `get_kpis_public()`, utilisant `datetime.utcnow()` et le filtre `Tender.collected_at >= cutoff`. Pas de nouveau endpoint, pas de nouveau modèle.

**Hypothèse :** le champ `Tender.collected_at` existe et est alimenté à l'insertion. Si ce champ s'appelle autrement (ex. `created_at`, `date_collecte`), adapter le nom.

### 2. Frontend — `frontend/src/components/KpiGrid.jsx`

Ajouter une 6ème card dans `KPI_CARDS` :

```js
{ key: 'new_24h', label: 'Nouvelles 24h', icon: '🆕', topColor: 'border-t-2 border-ocean-cyan/50' }
```

La grille passe de `md:grid-cols-5` à `md:grid-cols-6`. La valeur provient directement du même endpoint déjà consommé (`useKpisPublic`), aucun nouveau hook nécessaire.

### 3. Frontend — `frontend/src/hooks/useTenders.js` : `useCollectMutation`

Dans `onSuccess`, ajouter l'invalidation des queries KPIs :

```js
onSuccess: () => {
  qc.invalidateQueries({ queryKey: ['scraper-runs'] })
  qc.invalidateQueries({ queryKey: ['kpis'] })
  qc.invalidateQueries({ queryKey: ['tenders'] })
}
```

Ainsi, dès qu'une collecte se termine, le Dashboard recharge les KPIs (total, à qualifier, en cours, soumis, gagnés, nouvelles 24h).

### 4. Frontend — `frontend/src/components/Sidebar.jsx`

Dans la section `showResults` :

- **Supprimer** les deux `<StepBar>` avec `label="Collecte"` et `label="Mots-clés"`.
- **Garder** la `<StepBar>` avec `label="Analyse IA"`.
- **Ajouter** un résumé texte en tête de la section résultats :
  ```jsx
  <p className="text-sm font-semibold text-ocean-cyan font-mono">+{totalNew} nouvelles offres</p>
  ```

---

## Données

| Champ | Source | Fiabilité |
|---|---|---|
| `new_24h` | `COUNT` SQL sur `collected_at` | Fiable — directement depuis la DB |
| `new_7d` | `COUNT` SQL sur `collected_at` | Fiable — directement depuis la DB |
| `totalNew` sidebar | Somme des `nb_new` par source retournés par `/api/collect` | Fiable — calculé avant/après run |
| Barre Analyse IA | `min(totalNew, 10)` / `totalNew` | Approximatif mais cohérent avec la logique IA |

---

## Ce qui n'est pas dans cette spec

- Tracking du `nb_found` réel (nécessiterait de modifier l'interface des scrapers).
- Indicateur `new_7d` dans le KpiGrid (jugé non prioritaire pour l'instant, mais disponible en backend).
- Barre de progression en temps réel pendant la collecte.

---

## Fichiers modifiés

| Fichier | Nature du changement |
|---|---|
| `backend/main.py` | Ajout `new_24h`, `new_7d` dans `get_kpis_public()` |
| `frontend/src/components/KpiGrid.jsx` | Ajout card "Nouvelles 24h", grille 6 colonnes |
| `frontend/src/hooks/useTenders.js` | `useCollectMutation.onSuccess` invalide `['kpis']` et `['tenders']` |
| `frontend/src/components/Sidebar.jsx` | Suppression barres "Collecte" + "Mots-clés", ajout résumé texte |
