# Spec : Clé API Mistral, Filtre Date, OUI/NON, ERP

**Date :** 2026-05-22  
**Périmètre :** `app.py`, `llm_analyzer.py`, `scraper_utils.py`  
**Approche retenue :** A — modifications ciblées, architecture inchangée

---

## 1. Clé API Mistral dans la sidebar

### Comportement
- Bloc "🔑 Mistral API" ajouté dans `app.py` > `with st.sidebar`, juste avant la section "⚡ Collecte"
- `st.text_input(type="password")` pré-rempli avec `os.getenv("MISTRAL_API_KEY", "")`
- Bouton "💾 Sauvegarder" : écrit la clé dans `.env` (crée le fichier si absent), met à jour `os.environ["MISTRAL_API_KEY"]` immédiatement, appelle `llm_analyzer.reset_mistral_client()` pour invalider le singleton
- Indicateur visuel : `st.success("✓ Clé active")` si clé présente, `st.warning("⚠ Clé manquante")` sinon

### Fonction `_save_api_key_to_env(key: str)` dans `app.py`
- Lit le `.env` existant ligne par ligne
- Remplace la ligne `MISTRAL_API_KEY=...` si présente, sinon l'ajoute en fin de fichier
- Écrit atomiquement (écrit dans un buffer, remplace le fichier)

### Fonction `reset_mistral_client()` dans `llm_analyzer.py`
- Remet `_mistral_client = None` (thread-safe avec lock si nécessaire)
- Exportée publiquement pour être appelée depuis `app.py`

---

## 2. Prompt Mistral — OUI/NON + ERP + Date obligatoire

### Champ `decision` (nouveau)
Ajouté au JSON de réponse demandé dans `SYSTEM_PROMPT` :

```json
"decision": "OUI" | "NON"
```

**Règle instruite à Mistral :**
- `"OUI"` si `score_pertinence >= 45` ET territoire Réunion/Mayotte/Océan Indien
- `"OUI"` aussi si ERP détecté + contexte sécurité, même score < 45
- En cas de doute sur le périmètre technique : préférer `"OUI"` (le commercial ne doit louper aucune affaire)
- `"NON"` uniquement si exclusion formelle (gardiennage, génie civil, hors zone confirmé)

### Champ `alerte_erp` (nouveau)
```json
"alerte_erp": "⚠️ ERP DÉTECTÉ — [type bâtiment] : SSI catégorie [X] obligatoire" | null
```

**Règle instruite à Mistral :**
- Dès qu'un bâtiment ERP est identifié avec contexte sécurité, renseigner ce champ
- ERP = signal d'alerte prioritaire : force `decision` à `"OUI"` sauf exclusion formelle
- Exemples : hôpital, école, mairie, hôtel, centre commercial, gymnase, IGH

### Champ `date_publication` (renforcé, existant)
```json
"date_publication": "YYYY-MM-DD" | null
```

**Instruction renforcée dans le prompt :**
> Cherche IMPÉRATIVEMENT une date dans le texte (date de parution, date de publication, date d'avis, date de mise en ligne…). Extrais-la au format YYYY-MM-DD. Si aucune date n'est trouvée dans le texte : retourner `null`.

### Nettoyage nommage "Claude" dans l'UI
- Dans `app.py`, la variable `claude_ok` → `llm_ok`
- Le message `"🤖 X analysé(s) par IA"` → `"🤖 X analysé(s) par Mistral"`
- La vérification `_source in ("claude", "gemini")` → `_source in ("mistral", "claude", "gemini")` (rétrocompat)
- Les noms internes (`auto_analyze_claude`, `_claude_analyze`) ne changent pas pour éviter les régressions

---

## 3. Filtre temporel strict à la collecte

**Fichier :** `scraper_utils.py` — fonction `insert_if_new()`

### Changement
Ajouter le rejet des offres sans date **avant** le check de l'âge (qui existe déjà) :

```python
def insert_if_new(db, tender_obj, seen_ids: set[str]) -> bool:
    if tender_obj.id in seen_ids:
        return False
    # NOUVEAU : rejet si date absente
    if not tender_obj.publication_date:
        _log.debug("insert_if_new: article ignoré (date absente) — %s", tender_obj.id)
        return False
    # Existant : rejet si trop ancien (> 31 jours)
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=_MAX_ARTICLE_AGE_DAYS)
    if tender_obj.publication_date.replace(tzinfo=None) < cutoff:
        _log.debug("insert_if_new: article ignoré (trop ancien) — %s", tender_obj.id)
        return False
    seen_ids.add(tender_obj.id)
    db.add(tender_obj)
    return True
```

**`_MAX_ARTICLE_AGE_DAYS = 31`** — déjà présent, inchangé.

---

## Fichiers modifiés

| Fichier | Nature du changement |
|---------|---------------------|
| `app.py` | + bloc API sidebar + `_save_api_key_to_env()` + renommage `claude_ok` → `llm_ok` |
| `llm_analyzer.py` | + `reset_mistral_client()` + `SYSTEM_PROMPT` : `decision`, `alerte_erp`, date renforcée |
| `scraper_utils.py` | + 3 lignes dans `insert_if_new()` |

## Fichiers non touchés
`scraper_afd.py`, `scraper_decp.py`, `scraper_permis.py`, `scraper_worldbank.py`, `models.py`, `database.py`, `fiche_logic.py`

---

## Critères de succès
1. La clé API saisie dans la sidebar est sauvegardée dans `.env` et active immédiatement sans redémarrer l'app
2. Chaque réponse Mistral contient `decision: OUI/NON` et `alerte_erp` (null ou texte d'alerte)
3. Aucune offre sans date de publication n'est insérée en base lors de la collecte
4. Les offres > 31 jours continuent d'être rejetées (comportement existant préservé)
5. L'UI affiche "Mistral" au lieu de "IA" générique dans les messages de collecte
