# Design — Marché Online : enrichissement par fiche détail

**Date :** 2026-05-19  
**Statut :** Approuvé

---

## Contexte et problème

Le scraper Marché Online (`scraper_marcheonline.py`) ne remonte aucun résultat dans l'app malgré des AOs pertinents visibles sur le site. Trois causes combinées :

1. **Description quasi-vide** : la description envoyée à `classify_relevance` est `"{dept} — {publisher}"`, trop pauvre pour filtrer correctement.
2. **Filtre trop strict sur titre seul** : `classify_relevance` élimine tout AO dont le titre ne contient pas explicitement un mot-clé SSI/CMSI/incendie ou une combinaison construction + ERP.
3. **Le scraper ne visite jamais les fiches détail** : la vraie description n'est accessible qu'en cliquant sur chaque AO.

Les URLs de collecte sont déjà filtrées géographiquement (`/reunion-D101`, `/mayotte-D976`), donc tout AO retourné est géographiquement pertinent.

---

## Architecture — Deux phases

### Phase 1 : Collecte de liste (identique à l'actuel)

Parcourir les pages de liste avec Playwright (authentifié). Extraire depuis les commentaires HTML :
- URL de la fiche (`/appels-offres/avis/...`)
- Titre
- Date de publication
- Date limite de remise
- Éditeur / département

Limite : **10 pages** par URL (contre 5 actuellement).

**Sortie** : liste de `dict` avec `{url, title, date, deadline, description_courte}`.

### Phase 2 : Enrichissement par fiche détail (nouveau)

Pour chaque fiche dont l'URL n'est **pas dans `existing_ids`** :

1. Naviguer vers la page de détail avec la même session Playwright (authentifiée).
2. Extraire la description complète avec CSS selectors (ordre de priorité / fallback) :
   - `[itemprop="description"]`
   - `.ao-objet`, `.objet-marche`, `.description-lot`
   - `article p` (fallback générique)
3. Concaténer `titre + description_complète` et appliquer `classify_relevance`.
4. Insérer en base uniquement si `relevant == True`.
5. En cas d'erreur sur une fiche (timeout, sélecteur manquant) : logger un warning et continuer — ne pas crasher la collecte.

**Comportement dégradé** : si aucun sélecteur ne retourne de texte, utiliser le titre seul (identique au comportement actuel). Garantit la non-régression.

---

## Impact sur les performances

- **Première exécution** : visite de toutes les fiches récentes (~100–200 pages). Durée estimée : 5–15 min selon la latence réseau.
- **Exécutions suivantes** : seuls les nouveaux AOs (absents de `existing_ids`) sont visités. Surcoût marginal.
- `existing_ids` est chargé **avant** la phase 2 pour éviter les re-visites.

---

## Fichiers modifiés

| Fichier | Nature du changement |
|---|---|
| `scraper_marcheonline.py` | Refactoring en deux phases, ajout extraction détail |

---

## Ce qui ne change pas

- `scraper_ted.py` : comportement normal (AOs = format dominant sur TED Europe). Aucune modification.
- `filters.py` : `classify_relevance` inchangée.
- `database.py`, `models.py`, `scraper_utils.py` : inchangés.

---

## Tests

- Test unitaire sur `_extract_detail` avec un HTML mocké contenant chaque sélecteur ciblé.
- Vérifier que si aucun sélecteur ne matche, le fallback sur le titre est bien utilisé.
- Vérifier que `existing_ids` empêche une re-visite lors d'un deuxième appel.
