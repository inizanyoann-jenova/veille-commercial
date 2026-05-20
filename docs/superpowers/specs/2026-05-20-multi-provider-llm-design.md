# Spec : Support multi-provider LLM (Anthropic + Mistral)

**Date :** 2026-05-20  
**Statut :** Approuvé

---

## Contexte

L'application analyse les appels d'offres via l'API Claude (Anthropic). L'utilisateur souhaite pouvoir utiliser à la place une clé API Mistral (plan gratuit : 1 milliard de tokens/mois, accès à tous les modèles dont `mistral-large-latest`). Une seule clé est nécessaire à la fois — l'utilisateur choisit son provider depuis la page Paramètres.

---

## Objectif

Permettre à l'utilisateur de choisir entre Anthropic (Claude) et Mistral comme moteur LLM pour l'analyse des marchés, sans obligation de configurer les deux.

---

## Architecture

### Flux d'analyse

```
analyze_tender(text)
    │
    ├─ lit LLM_PROVIDER depuis os.environ (défaut : "anthropic")
    ├─ "anthropic" → _claude_analyze()    (comportement actuel inchangé)
    ├─ "mistral"   → _mistral_analyze()   (nouveau)
    └─ clé absente / erreur → fallback analyse locale (règles métier)
```

Le fallback sur l'analyse locale est conservé dans tous les cas — l'app fonctionne sans aucune clé.

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `llm_analyzer.py` | Ajout `_mistral_analyze()`, `_get_mistral_client()`, routage dans `analyze_tender()` et `auto_analyze_claude()` |
| `pages/parametres.py` | Refonte section IA : sélecteur radio provider + section clé Mistral |
| `.env.example` | Ajout `MISTRAL_API_KEY=` et `LLM_PROVIDER=anthropic` |
| `requirements.txt` | Ajout `mistralai>=1.0.0` |

---

## Détail : `llm_analyzer.py`

### Nouvelle variable d'environnement

- `LLM_PROVIDER` : `"anthropic"` (défaut) ou `"mistral"`
- `MISTRAL_API_KEY` : clé API Mistral (format `...`)

### `_get_mistral_client()`

Crée et met en cache un client `mistralai.Mistral(api_key=...)`. Retourne `None` si la clé est absente.

### `_mistral_analyze(text: str) -> dict | None`

- Modèle : `mistral-large-latest`
- Envoie le même `SYSTEM_PROMPT` que Claude (format JSON identique demandé)
- Parse la réponse JSON (même logique de nettoyage des code fences)
- Gère les erreurs de quota (429) via `_LLMQuotaError`
- Gère `MistralAPIStatusException` pour auth invalide
- `_source` = `"mistral"` dans le résultat

### Routage dans `analyze_tender()`

```python
provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
if provider == "mistral":
    llm_result = _mistral_analyze(text)
else:
    llm_result = _claude_analyze(text)
```

### Routage dans `auto_analyze_claude()`

Même logique de routage. La fonction garde son nom actuel pour compatibilité (l'alias `auto_analyze_gemini` est conservé).

---

## Détail : `pages/parametres.py`

### Nouvelle section "🤖 Intelligence Artificielle"

Remplace la section actuelle "Clé API Claude".

**Sélecteur provider :**
- `st.radio("Fournisseur IA actif", ["Anthropic (Claude)", "Mistral"])` 
- Persisté dans `.env` via `set_key(".env", "LLM_PROVIDER", ...)`
- Mis à jour dans `os.environ` immédiatement sans redémarrage

**Sous-section Anthropic (toujours visible) :**
- Statut de la clé actuelle (configurée / non configurée)
- Champ saisie + boutons Enregistrer / Tester (comportement actuel conservé)
- Le test appelle `claude-haiku-4-5-20251001` avec `max_tokens=5` (idem actuel)

**Sous-section Mistral (toujours visible) :**
- Statut de la clé (configurée / non configurée)
- Champ saisie + boutons Enregistrer / Tester
- Format clé : commence par aucun préfixe particulier imposé (validation : longueur > 20)
- Le test appelle `mistral-small-latest` avec un message court pour limiter les tokens
- Persisté via `set_key(".env", "MISTRAL_API_KEY", ...)`

---

## Détail : dépendances

```
mistralai>=1.0.0
```

SDK officiel Mistral (pip). Interface : `mistralai.Mistral(api_key=...)`.  
Appel : `client.chat.complete(model=..., messages=[...])`.  
Réponse : `response.choices[0].message.content`.

---

## Compatibilité et rétrocompat

- Comportement actuel inchangé si `LLM_PROVIDER` absent (défaut `"anthropic"`)
- `auto_analyze_gemini` reste un alias de `auto_analyze_claude` (aucun code existant cassé)
- Les marchés déjà analysés via Claude ne sont pas ré-analysés

---

## Tests

- `tests/test_llm_analyzer.py` : ajouter tests pour `_mistral_analyze()` avec mock du client Mistral (quota error, auth error, réponse JSON valide, réponse non-JSON)
- `tests/test_credential_manager.py` : pas de changement nécessaire (les clés sont dans `.env`, pas en DB)
- Vérifier manuellement dans la page Paramètres : saisie clé Mistral → test → sélection provider → relance d'une analyse
