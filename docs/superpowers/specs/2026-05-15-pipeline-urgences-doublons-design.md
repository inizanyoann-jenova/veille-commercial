# Design — Pipeline, Urgences & Doublons

**Date :** 2026-05-15
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** `app.py` · `pages/pipeline.py` (nouveau) · `pages/parametres.py` · `database.py` · `models.py`

---

## Vue d'ensemble

Trois améliorations indépendantes :

| ID | Feature | Fichiers principaux |
|---|---|---|
| B | Vue Pipeline Kanban par statut | `pages/pipeline.py` (nouveau) |
| C | Widget Urgences délais | `app.py` |
| D | Détection et fusion de doublons | `database.py`, `models.py`, `pages/parametres.py` |

---

## B — Pipeline Kanban

### Page

Nouveau fichier `pages/pipeline.py`.

### Colonnes

| Colonne | Critère | Tri |
|---|---|---|
| GO ✅ | `relevance_score >= 65` AND `status NOT IN ["Soumis", "Gagné", "Perdu"]` | deadline croissante |
| Soumis | `status == "Soumis"` | deadline croissante |
| Résultats | `status IN ["Gagné", "Perdu"]` | date décroissante |

La colonne Résultats affiche Gagné et Perdu en deux sous-groupes visuels distincts.

### Cartes

Chaque carte affiche :
- Titre (tronqué à 60 caractères)
- Score de pertinence
- Jours restants avant deadline, coloré :
  - 🔴 rouge si < 7 jours
  - 🟡 orange si 7–30 jours
  - ⚫ gris si deadline absente

### Transitions de statut

Boutons sur la carte, inline :

```
GO      → [Marquer Soumis]
Soumis  → [Gagné 🏆]  [Perdu]
```

Après un changement : `db.commit()` + `st.cache_data.clear()` + `st.rerun()`.

### Données

```python
@st.cache_data(ttl=120)
def _load_pipeline() -> dict:
    # Retourne {"go": [...], "soumis": [...], "resultats": [...]}
```

### Ce qui ne change pas

- La logique de scoring — inchangée
- La fiche marché existante — inchangée

---

## C — Widget Urgences délais

### Placement

Bandeau inséré dans `app.py`, **au-dessus de la barre de recherche**, avant la liste principale. Masqué automatiquement si la requête retourne zéro marché.

### Requête

```python
@st.cache_data(ttl=300)
def _load_urgences() -> list:
    # Tenders avec relevance_score >= 65
    # ET is_blacklisted != True
    # ET deadline BETWEEN today AND today+30j
    # ET status NOT IN ["Gagné", "Perdu"]
    # Triés par deadline croissante
```

### Affichage

Cartes horizontales via `st.columns(min(len(urgences), 4))`. Couleur par urgence :

| Plage | Couleur |
|---|---|
| < 7 jours | 🔴 rouge |
| 7–15 jours | 🟡 orange |
| 15–30 jours | 🟢 vert |

Contenu de chaque carte : titre + jours restants + score.

### Ce qui ne change pas

- La liste principale et ses filtres — inchangés
- Le comportement des filtres sidebar — inchangé

---

## D — Détection et fusion de doublons

### Nouvelle table `duplicate_candidates`

```python
class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    tender_id_a     = Column(String, nullable=False)
    tender_id_b     = Column(String, nullable=False)
    similarity_score = Column(Float, nullable=False)
    detected_at     = Column(DateTime, nullable=False)
    resolved        = Column(Boolean, default=False)
```

Migration idempotente dans `init_db()`.

### Algorithme de détection

Lancé par un bouton "🔍 Détecter les doublons" dans `pages/parametres.py`.

```python
from difflib import SequenceMatcher

def detect_duplicates(db) -> int:
    """Scanne tous les marchés non blacklistés, retourne le nb de paires nouvelles détectées."""
    tenders = db.query(Tender).filter(Tender.is_blacklisted != True).all()
    new_pairs = 0
    for i, a in enumerate(tenders):
        for b in tenders[i+1:]:
            if a.source == b.source:
                continue  # jamais doublon intra-source
            ratio = SequenceMatcher(None, a.title.lower(), b.title.lower()).ratio()
            if ratio < 0.80:
                continue
            # deadline à ±3 jours ou les deux nulles
            if a.deadline and b.deadline:
                if abs((a.deadline - b.deadline).days) > 3:
                    continue
            elif a.deadline or b.deadline:
                continue  # l'un a une deadline, l'autre non → pas doublon
            # vérifier qu'on n'a pas déjà cette paire
            existing = db.query(DuplicateCandidate).filter(
                or_(
                    and_(DuplicateCandidate.tender_id_a == a.id, DuplicateCandidate.tender_id_b == b.id),
                    and_(DuplicateCandidate.tender_id_a == b.id, DuplicateCandidate.tender_id_b == a.id),
                )
            ).first()
            if not existing:
                db.add(DuplicateCandidate(
                    tender_id_a=a.id, tender_id_b=b.id,
                    similarity_score=round(ratio, 3),
                    detected_at=datetime.utcnow(),
                ))
                new_pairs += 1
    db.commit()
    return new_pairs
```

### UI dans Paramètres

Nouvelle section "🔍 Doublons détectés" dans `pages/parametres.py` :

- Bouton de lancement de la détection, affiche le nombre de paires trouvées
- Pour chaque paire non résolue : affichage côte-à-côte (deux colonnes)
  - Le tender avec le `relevance_score` le plus élevé est mis en évidence (fond coloré) — c'est le candidat recommandé à conserver
  - En cas d'égalité de score, favoriser le tender ayant le plus de champs non nuls
- Boutons par paire :
  - `[Garder A — archiver B]` → `b.is_blacklisted = True` + `pair.resolved = True`
  - `[Garder B — archiver A]` → `a.is_blacklisted = True` + `pair.resolved = True`
  - `[Ignorer]` → `pair.resolved = True` sans archivage

### Performances

L'algorithme est O(n²) sur le titre. Acceptable jusqu'à ~5 000 marchés. Au-delà, un index sur les 3 premiers mots du titre permettrait de pré-filtrer — hors scope pour l'instant.

---

## Migrations requises

Toutes idempotentes, dans `init_db()` de `database.py` :

```sql
CREATE TABLE IF NOT EXISTS duplicate_candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id_a TEXT NOT NULL,
    tender_id_b TEXT NOT NULL,
    similarity_score REAL NOT NULL,
    detected_at DATETIME NOT NULL,
    resolved INTEGER DEFAULT 0
)
```

---

## Dépendances

| Package | Usage | Déjà présent ? |
|---|---|---|
| `difflib` | Similarité de titres (D) | Oui (stdlib) |

Aucune nouvelle dépendance externe.

---

## Critères de succès

1. **B** — La page Pipeline affiche les 3 colonnes, les boutons de transition changent le statut en base et la vue se met à jour immédiatement
2. **C** — Le widget apparaît uniquement quand des marchés GO ont une deadline dans les 30 prochains jours ; il est absent sinon
3. **D** — La détection identifie correctement les paires titre-similaire + deadline proche ; la fusion archive bien le perdant (is_blacklisted=True) et marque la paire resolved

---

## Ce qui ne change pas

- Les scrapers existants
- La logique de scoring et de détection de domaine/territoire
- Le CSS et le layout des pages existantes
- Le credential manager
