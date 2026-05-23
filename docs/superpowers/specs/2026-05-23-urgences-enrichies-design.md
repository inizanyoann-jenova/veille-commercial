# Spec — Urgences enrichies : raison + lien annonce

**Date :** 2026-05-23
**Statut :** Approuvé

## Contexte

L'onglet Urgences affiche des cartes de marchés à traiter en priorité (deadline < 30j, score ≥ 65). Actuellement les cartes sont quasi-vides à cause de :
1. Bug de nommage : `load_urgences` retourne `score`/`jours` mais le frontend attend `relevance_score`/`jours_restants`
2. `source` non retourné par le backend
3. Aucun contenu explicatif sur pourquoi c'est urgent
4. Pas de lien vers l'annonce originale

## Objectif

Enrichir chaque carte d'urgence avec :
- La raison de l'urgence (description + résumé LLM + secteur + montant)
- Le lien vers l'annonce (URL stockée en DB)

## Approche retenue

**Carte enrichie verticale** — grille maintenue, cartes plus hautes.

---

## Changements Backend

### 1. `models.py` — Ajout colonne `url`

```python
url = Column(String, nullable=True)
```
Ajouté dans la classe `Tender`, après `adaptive_score`.

### 2. `database.py` — Migration

```python
("tenders", "url", "VARCHAR DEFAULT NULL"),
```
Ajouté dans `_MIGRATIONS`.

### 3. `database.py:load_urgences` — Fix + nouveaux champs

Remplacer le dict retourné par :
```python
{
    "id": t.id,
    "title": t.title,
    "relevance_score": t.relevance_score,
    "jours_restants": (t.deadline.replace(tzinfo=None) - today).days,
    "source": t.source,
    "url": t.url,
    "description": (t.description or "")[:300] if t.description else None,
    "secteur": t.secteur,
    "amount": t.amount,
    "llm_resume": (t.llm_analysis or {}).get("resume") if t.llm_analysis else None,
}
```

**Note :** les scrapers peuplent déjà `url` dans leur dict de résultat (ex: `scraper_devbanks.py`, `scraper_isdb.py`). Il faut vérifier comment ces dicts sont convertis en objets `Tender` pour s'assurer que `url` est bien propagé.

---

## Changements Frontend

### 4. `UrgenceCard.jsx` — Props étendus

**Nouveaux props :** `url`, `description`, `secteur`, `amount`, `llm_resume`

**Contenu texte :** `llm_resume` en priorité, sinon `description` tronqué.

**Maquette de la carte :**
```
┌─────────────────────────────────────────────┐
│  🔴 J-3          [87]           [🔗 Annonce] │
│                                             │
│  Titre du marché (2 lignes max)             │
│                                             │
│  Résumé LLM ou description courte           │  ← line-clamp-3, italic, ocean-muted
│  (3 lignes max)                             │
│                                             │
│  [SSI]              💰 45 000 €             │  ← secteur badge + montant
│  BOAMP                                      │  ← source
└─────────────────────────────────────────────┘
```

**Détails d'implémentation :**
- Lien annonce : `<a href={url} target="_blank" rel="noopener">` visible uniquement si `url` non null
- Secteur : badge `ocean-cyan/10 text-ocean-cyan` si `secteur` non null
- Montant : `new Intl.NumberFormat('fr-FR', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 }).format(amount)` si `amount` non null
- Contenu : `llm_resume ?? description`, `line-clamp-3`, style `italic text-ocean-muted text-xs`

### 5. `Urgences.jsx` — Passer les nouveaux props

```jsx
<UrgenceCard
  key={u.id}
  title={u.title}
  jours_restants={u.jours_restants}
  score={u.relevance_score}
  source={u.source}
  url={u.url}
  description={u.description}
  secteur={u.secteur}
  amount={u.amount}
  llm_resume={u.llm_resume}
/>
```

---

## Tests à mettre à jour

- `tests/test_urgences_pipeline.py` — vérifier que `load_urgences` retourne les nouveaux champs
- `frontend/src/components/UrgenceCard.test.jsx` — tester l'affichage du lien, du secteur, du montant et du fallback description/LLM

---

## Hors périmètre

- Migration des données existantes (url null pour les tenders déjà en DB — acceptable)
- Modification des scrapers pour peupler `url` (à vérifier si déjà connecté)
- Changement du layout grille (reste grid 4 colonnes)
