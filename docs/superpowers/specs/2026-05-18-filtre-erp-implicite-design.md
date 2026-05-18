# Design — Capture des opportunités SSI implicites (ERP sans mot-clé direct)

**Date :** 2026-05-18  
**Statut :** Approuvé

---

## Problème

12 scrapers de marchés publics utilisent `is_relevant_def()` qui n'accepte que les mots-clés
explicites DEF OI (SSI, CMSI, vidéosurveillance…). Des opportunités pertinentes — comme la
réhabilitation d'une école — sont ignorées alors qu'elles impliquent une obligation SSI sans
le mentionner dans l'intitulé du marché. Seul `scraper_presse.py` utilisait déjà la logique
élargie via `is_prive_relevant()`.

## Solution retenue : `classify_relevance()` centralisée (Option A)

Remplacer `is_relevant_def()` dans tous les scrapers par une fonction unique qui retourne
un tuple `(pertinent: bool, tags: list[str])`. Quand la capture est via la logique
construction + type ERP (et non via mot-clé direct), elle ajoute le tag `"Potentiel SSI implicite"`.

---

## Architecture

### 1. `filters.py`

Nouvelle fonction `classify_relevance(text: str) -> tuple[bool, list[str]]` :

```
1. Exclusions absolues → (False, [])
2. Mot-clé DEF OI explicite (SSI, CMSI, etc.) → (True, [])
3. Construction + type ERP (école, hôpital, mairie…) → (True, ["Potentiel SSI implicite"])
4. Sinon → (False, [])
```

`is_relevant_def()` devient un wrapper : `return classify_relevance(text)[0]`  
`is_prive_relevant()` idem : conservée, devient un wrapper.

### 2. Les 12 scrapers concernés

`scraper_marcheonline`, `scraper_boamp`, `scraper_decp`, `scraper_marchespublicsinfo`,
`scraper_instao`, `scraper_dept974`, `scraper_ted`, `scraper_ungm`, `scraper_vaao`,
`scraper_marchessecurises`, `scraper_nukema`, `scraper_tendersgo`

Pattern de changement uniforme par scraper :

```python
# AVANT
if not is_relevant_def(f"{title} {desc}"):
    continue
t = Tender(..., tags=[])

# APRÈS
relevant, extra_tags = classify_relevance(f"{title} {desc}")
if not relevant:
    continue
t = Tender(..., tags=extra_tags)
```

Scrapers qui ne passent pas `tags=` : l'ajouter explicitement avec `extra_tags`.

### 3. `app.py`

- **`TENDER_TAGS`** (ligne 37) : ajouter `"Potentiel SSI implicite"` en tête de liste.
- **Fiche** : afficher un bandeau `⚠️ Potentiel SSI implicite` en haut de la fiche
  quand `"Potentiel SSI implicite" in (t.tags or [])`, avant l'expander Tags.

---

## Comportement attendu

| Intitulé marché | Résultat avant | Résultat après |
|---|---|---|
| "SSI — Lycée Paul Vergès" | ✅ capturé | ✅ capturé, pas de tag |
| "Réhabilitation école primaire Sainte-Marie" | ❌ ignoré | ✅ capturé + tag "Potentiel SSI implicite" |
| "Fournitures scolaires 2026" | ❌ ignoré | ❌ ignoré (exclusion "scolaires") |
| "Construction EHPAD — Lot électricité" | ❌ ignoré | ✅ capturé + tag "Potentiel SSI implicite" |

---

## Tests

- Mettre à jour `tests/test_filters.py` : cas ERP implicite → `classify_relevance` retourne `(True, ["Potentiel SSI implicite"])`
- Cas mot-clé direct → retourne `(True, [])`
- Cas exclusion → retourne `(False, [])`
- Cas ERP sans construction → retourne `(False, [])`

---

## Ce qui ne change pas

- La logique d'exclusion absolue (gardiennage, fournitures scolaires, etc.)
- Le pipeline et les statuts existants
- La possibilité pour l'utilisateur de retirer manuellement le tag
- `scraper_presse.py` (déjà sur `is_prive_relevant()`)
