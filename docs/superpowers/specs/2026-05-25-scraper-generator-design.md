# Spec — Générateur de scrapers via IA

**Date :** 2026-05-25
**Statut :** Approuvé

## Contexte

L'app DEF OI gère 20+ scrapers manuellement codés. L'objectif est de permettre à l'utilisateur d'ajouter n'importe quel site de marchés publics en collant son URL, et que l'app génère automatiquement un scraper fonctionnel via Mistral AI.

## Approche retenue

**Code Python complet généré par Mistral** — Mistral reçoit le HTML de la page cible + des exemples de scrapers existants, génère un fichier `scraper_custom_[domaine].py` complet, qui est testé puis activé automatiquement si ≥ 1 résultat valide.

## Architecture

### Nouveau module : `scraper_factory.py`

Fichier à la racine du projet, contient toute la logique de génération.

```python
# Interface publique
generate(url: str, source_name: str, category: str, db) -> GenerationResult
```

`GenerationResult` est un dataclass avec : `status` ("ok" | "failed"), `scraper_module`, `nb_results`, `preview` (liste des 5 premiers items), `reason` (message d'erreur si failed).

### Flux de génération

```text
POST /api/sources/generate { url, name, category }
  1. Fetch HTML de l'URL
       → requests.get() avec User-Agent DEF-OI
       → si JS détecté (body vide ou < 500 chars) → fallback Playwright headless
  2. Tronquer le HTML à 8 000 tokens (≈ 32 000 chars)
  3. Construire le prompt Mistral avec :
       - Schema obligatoire (clés name, url, source, date_found, publication_date, deadline, description)
       - 2 exemples de scrapers existants (CHM + marchespublicsinfo, tronqués)
       - HTML de la page cible
       - Instruction : retourner uniquement le code Python sans markdown
  4. Appel Mistral (modèle mistral-large-latest)
  5. Extraction du bloc de code (regex entre ```python ... ``` ou premier def fetch())
  6. Validation syntaxique (ast.parse())
  7. Sauvegarde scraper_custom_[domaine_slug].py à la racine
  8. Test automatique dans un thread avec timeout=30s
       → importlib.import_module() + fetch()
       → vérifier : isinstance(result, list) et len > 0 et result[0].get("name")
  9. Si succès → créer Source en BDD (is_manual=False, is_validated=True)
     Si échec → supprimer le fichier, retourner erreur avec traceback
```

### Nommage du fichier scraper

```python
import re
slug = re.sub(r'[^a-z0-9]', '_', domain.lower()).strip('_')
filename = f"scraper_custom_{slug}.py"
```

Exemples :

- `chu-reunion.fr` → `scraper_custom_chu_reunion.py`
- `marches.mairie-stpierre.re` → `scraper_custom_marches_mairie_stpierre_re.py`

### Endpoint backend

```text
POST /api/sources/generate
Body : { "url": str, "name": str, "category": "Public" | "Privé" | "International" }
Response 200 : { "status": "ok", "scraper_module": str, "nb_results": int, "preview": [...] }
Response 400/422 : { "detail": str }

DELETE /api/sources/{id}
Response 200 : { "deleted": true }
```

### Gestion des erreurs

| Cas | Code | Message |
| --- | ---- | ------- |
| Mistral non configuré | 400 | "Clé Mistral manquante — configurez-la dans Paramètres > Intégrations" |
| Site inaccessible | 400 | "Impossible de télécharger la page : [erreur HTTP]" |
| Mistral ne retourne pas de code | 422 | "Code non extractible — reformulez ou essayez une autre URL" |
| ast.parse() échoue | 422 | "Code généré invalide syntaxiquement" |
| fetch() lève une exception | 422 | "Scraper testé mais erreur : [traceback court]" |
| fetch() retourne 0 résultats | 422 | "Scraper testé mais 0 résultats — page peut-être dynamique ou structure non reconnue" |

## Frontend

### Emplacement

Nouvel onglet **"Sources"** dans `frontend/src/pages/Parametres.jsx`, inséré entre "Connexion" et "Intégrations".

### Composant `SourceGenerator.jsx`

```text
┌────────────────────────────────────────────────────────┐
│  Ajouter un site de veille                             │
│                                                        │
│  Nom du site   [________________________]              │
│  URL           [https://________________]              │
│  Catégorie     [Public ▾]                              │
│                                                        │
│  [  Générer le scraper  ]                              │
└────────────────────────────────────────────────────────┘
```

**États visuels (durant la génération) :**

1. `Analyse de la page en cours...` — spinner
2. `Génération du code par Mistral...` — spinner
3. `Test du scraper...` — spinner
4. ✅ Badge vert : `Scraper actif — X annonces trouvées` + tableau preview
5. ❌ Badge rouge : `Échec — [raison courte]` + détail dépliable

**Liste des sources personnalisées :**

- Tableau en dessous du formulaire
- Colonnes : Nom | URL | Statut | Annonces | Actions
- Badge statut : "actif" (vert) / "échec" (rouge)
- Bouton "🗑 Supprimer" par ligne (DELETE /api/sources/{id})

### Hooks TanStack Query (dans `useTenders.js`)

```js
useGenerateScraper()   // mutation POST /api/sources/generate
useSources()           // query GET /api/sources (filtre is_manual=false et custom)
useDeleteSource()      // mutation DELETE /api/sources/{id}
```

## Contraintes techniques

- Les fichiers `scraper_custom_*.py` sont créés à la racine du projet (même niveau que les autres scrapers existants) — `importlib` les trouve automatiquement grâce au `sys.path`.
- Le `scraper_factory.py` importe `_get_mistral_client` depuis `llm_analyzer` pour accéder au singleton Mistral déjà initialisé (évite de dupliquer la gestion de la clé API). Modèle utilisé : `mistral-large-latest`.
- Timeout du test scraper : 30 secondes via `concurrent.futures.ThreadPoolExecutor`.
- Le HTML envoyé à Mistral est tronqué à 32 000 caractères pour rester dans les limites de contexte.

## Tests

- **Backend** : `tests/test_scraper_factory.py` — tests unitaires avec HTML mockés, vérifie extraction du code, validation syntaxique, gestion des erreurs.
- **Frontend** : test du composant `SourceGenerator.jsx` — vérifie les 3 états (loading, success, error) avec des mutations mockées.
