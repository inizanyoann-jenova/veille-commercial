# Design — Lot 1 : Recherche plein texte + Vue urgences + Résumé collecte
**Date :** 2026-05-14
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** 3 améliorations rapides dans `app.py` uniquement — zéro nouveau fichier

---

## Contexte

Suite au Lot 0 (cartes post-collecte + tableau enrichi), ce lot apporte trois améliorations de workflow quotidien : trouver rapidement un marché par mot-clé, voir les délais critiques d'un coup d'œil, et avoir un bilan structuré après chaque collecte.

---

## Architecture

Tout dans `app.py`. Trois zones indépendantes :
1. Sidebar — deux nouveaux widgets (search input + checkbox urgences)
2. Filtrage post-chargement — appliqué sur `rows_pub` / `rows_priv` après `load_tenders()`
3. Fin de `_collect_selected_sources()` — remplacement du `st.success` simple

---

## Feature 1 — Recherche plein texte

### Emplacement
Dans `with st.sidebar:`, **juste au-dessus** du widget "Période" (premier filtre existant).

### Widget
```python
search_query = st.text_input("🔍 Rechercher", placeholder="Titre, source…", key="search_query")
```

### Filtrage
Appliqué après `load_tenders()`, avant les filtres territoire/domaine/décision existants :
```python
if search_query:
    q = search_query.lower()
    rows_pub  = [r for r in rows_pub  if q in r["Titre"].lower() or q in r["Source"].lower()]
    rows_priv = [r for r in rows_priv if q in r["Titre"].lower() or q in r["Source"].lower()]
```

### Comportement
- Recherche insensible à la casse
- Champs couverts : Titre + Source (les deux champs visibles dans le tableau)
- Aucun impact sur la DB ni sur le cache — filtrage pur en mémoire
- Compatible avec tous les autres filtres (s'applique en plus)

---

## Feature 2 — Vue urgences délais courts

### Emplacement
Dans `with st.sidebar:`, juste après `only_recent = st.checkbox("🆕 Nouveaux (24h)")`.

### Widget
```python
urgent_only = st.checkbox("🚨 Délais < 14 jours")
```

### Filtrage
Appliqué après `load_tenders()` et après le filtre search_query :
```python
if urgent_only:
    today = datetime.now().date()
    def _is_urgent(r: dict) -> bool:
        dl = r["Date Limite"]
        if dl == "—":
            return False
        try:
            d = datetime.strptime(dl, "%d/%m/%Y").date()
            return (d - today).days <= 14
        except ValueError:
            return False
    rows_pub  = [r for r in rows_pub  if _is_urgent(r)]
    rows_priv = [r for r in rows_priv if _is_urgent(r)]
```

### Comportement
- Inclut les marchés dont la deadline est **dépassée** (jours restants < 0) — c'est intentionnel, ils sont également urgents à archiver
- Seuil fixe à 14 jours — pas configurable (YAGNI)
- `_is_urgent` défini localement dans le scope principal (pas une fonction de module)

---

## Feature 3 — Résumé de collecte enrichi

### Emplacement
Dans `_collect_selected_sources()`, en remplacement du bloc `if total: st.success(...)` final.

### Logique
Après la collecte, requête DB sur les nouveaux IDs pour comptabiliser les scores :

```python
if total and st.session_state.get("new_tender_ids"):
    _db_res = new_db()
    try:
        _new_tenders = _db_res.query(Tender).filter(
            Tender.id.in_(st.session_state["new_tender_ids"])
        ).all()
    finally:
        _db_res.close()

    _go    = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("score_pertinence", t.relevance_score or 0) >= 65)
    _etude = sum(1 for t in _new_tenders if 35 <= (t.llm_analysis or {}).get("score_pertinence", t.relevance_score or 0) < 65)
    _pass  = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("score_pertinence", t.relevance_score or 0) < 35)
    _claude_analyzed = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("_source") in ("claude", "gemini"))

    st.success(
        f"✅ {total} nouveau(x) marché(s) importé(s) — "
        f"🟢 {_go} GO · 🟡 {_etude} À étudier · 🔴 {_pass} Passer"
        + (f" · 🤖 {_claude_analyzed} analysé(s) par Claude" if _claude_analyzed else "")
    )
elif total:
    st.success(f"✅ {total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
elif not errors:
    st.info("Aucune nouvelle offre trouvée pour les sources sélectionnées.")
for err in errors:
    st.warning(err)
```

### Comportement
- Si `total == 0` : comportement inchangé (`st.info` "Aucune nouvelle offre")
- Les erreurs scraper restent affichées via `st.warning` comme avant
- Le résumé remplace le `st.success` simple — pas d'affichage en double

---

## Ce qui n'est PAS dans ce périmètre
- Recherche dans la description complète (trop lente sans index full-text)
- Seuil de délai configurable par l'utilisateur
- Persistance de la recherche entre sessions
- Tri des résultats urgents par délai restant (le tableau existant est déjà trié par deadline)
