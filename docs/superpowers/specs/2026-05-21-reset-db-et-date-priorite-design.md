# Spec : Reset base de données + Date priorité LLM

**Date :** 2026-05-21  
**Statut :** Validé par l'utilisateur

---

## Contexte

L'application accumule des marchés anciens ou sans date de publication. L'utilisateur veut repartir de zéro et s'assurer que chaque marché analysé par le LLM porte toujours une date de publication extraite du texte.

---

## Fonctionnalité 1 — Bouton "Remise à zéro de la base"

### Emplacement
Page `pages/parametres.py`, nouvelle section **"⚠️ Zone Danger"** tout en bas de la page.

### Comportement
1. L'utilisateur coche une checkbox : *"Je confirme vouloir supprimer tous les marchés et l'historique de collecte"*
2. Un bouton rouge "🗑️ Remettre la base à zéro" devient actif
3. Au clic : appel à `reset_tenders_db(db)` dans `database.py`
4. Message de confirmation : *"Base remise à zéro — X marchés supprimés."*
5. `st.rerun()` pour rafraîchir la page

### Tables vidées
- `tenders` — tous les marchés
- `scraper_runs` — historique des collectes
- `duplicate_candidates` — doublons détectés

### Tables préservées (ne pas toucher)
- `sources` — configuration des sources
- `credentials` — identifiants chiffrés
- `score_weights` — poids d'apprentissage du scoring

### Nouvelle fonction `database.py`
```python
def reset_tenders_db(db) -> int:
    """Vide tenders, scraper_runs et duplicate_candidates. Retourne le nb de marchés supprimés."""
```
Utilise `db.query(Model).delete()` pour chaque table dans l'ordre :
1. `DuplicateCandidate` (dépend de tenders)
2. `ScraperRun`
3. `Tender`

---

## Fonctionnalité 2 — Date de publication en priorité absolue dans le LLM

### Problème actuel
Le prompt système contient :
```
"date_publication": "date de publication au format YYYY-MM-DD si trouvée dans le texte, sinon null"
```
Cette instruction est trop passive — le LLM peut l'ignorer ou ne pas chercher activement.

### Solution : réécriture de l'instruction `date_publication` dans `SYSTEM_PROMPT`

Remplacer l'instruction passive par un bloc d'instruction critique :

```
"date_publication": "PRIORITÉ ABSOLUE — cherche la date de publication dans TOUTES les parties
du texte : titre, corps, entête, référence, pied de page. Patterns à détecter :
'publié le', 'date de parution', 'mis en ligne le', 'date d\\'avis', 'paru le',
'date de publication', 'publié en', ainsi que tout format de date explicite
(JJ/MM/AAAA, AAAA-MM-JJ, mois AAAA). Retourne la date au format YYYY-MM-DD.
Si aucune date n\\'est trouvable nulle part dans le texte, retourne null."
```

### Ce qui ne change pas
- La logique `auto_analyze_claude` qui écrit `llm_result.get("date_publication")` → `t.publication_date` est déjà correcte, on ne la touche pas
- Aucun fallback `date_extraction` — la date vient du texte ou est nulle

### Fichiers concernés
- `llm_analyzer.py` : modification du `SYSTEM_PROMPT` (variable `SYSTEM_PROMPT` ou constante équivalente), ligne ~598

---

## Fichiers à modifier

| Fichier | Modification |
|---|---|
| `database.py` | Ajouter `reset_tenders_db(db) -> int` |
| `pages/parametres.py` | Ajouter section "Zone Danger" avec double confirmation |
| `llm_analyzer.py` | Renforcer l'instruction `date_publication` dans le prompt système |

---

## Critères de succès

- Après clic sur le bouton reset, `SELECT COUNT(*) FROM tenders` retourne 0
- Après une analyse LLM sur un marché avec date dans le texte, `publication_date` est renseigné
- Le bouton reset ne peut pas être déclenché sans la checkbox cochée
- Sources et credentials sont intacts après le reset
