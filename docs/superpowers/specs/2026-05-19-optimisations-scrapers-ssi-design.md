# Spec : Optimisations scrapers SSI — DEF Océan Indien

**Date :** 2026-05-19  
**Scope :** `filters.py`, `scraper_ted.py`, `scraper_decp.py`, `scraper_boamp.py`, `.env.example`  
**Approche retenue :** Option A — modifications atomiques fichier par fichier, pas de nouveau module.

---

## Contexte

L'application collecte des marchés publics SSI pour DEF OI (La Réunion 974, Mayotte 976, Océan Indien).  
Cinq optimisations de précision et de performance ont été identifiées :

1. Corriger l'endpoint TED + ajouter codes CPV + filtrage date + variantes géographiques Mayotte
2. Compléter les mots-clés SSI dans `filters.py`
3. Ajouter le filtrage CPV dans `scraper_decp.py`
4. Étendre les variantes géographiques Mayotte (TED uniquement)
5. Fenêtre temporelle glissante 90 j via `SCRAPER_WINDOW_DAYS` dans `.env`

---

## 1. `scraper_ted.py`

### 1.1 Correction URL
- **Avant :** `https://api.ted.europa.eu/v3/notices/search`
- **Après :** `https://ted.europa.eu/api/v3.0/notices/search`

### 1.2 Filtrage date
Ajout d'un paramètre `publicationDate` dans le payload de requête :

```python
from datetime import datetime, timedelta
import os

_WINDOW_DAYS = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
date_from = (datetime.now() - timedelta(days=_WINDOW_DAYS)).strftime("%Y%m%d")
# Injecté dans le payload : "publicationDate": f">={date_from}"
```

### 1.3 Variantes géographiques Mayotte
La requête `QUERIES["Mayotte"]` est étendue :

```python
_MAYOTTE_GEO = (
    "FT~Mayotte OR FT~Mahorais OR FT~Mamoudzou"
    " OR FT~Kaweni OR FT~Dzaoudzi OR FT~Koungou"
    " OR FT~Bandraboua OR FT~PetiteTerre OR FT~GrandeTerre"
)
"Mayotte": f"({_MAYOTTE_GEO}) AND ({_PUBLIC_SEARCH})"
```

### 1.4 Codes CPV
Ajout dans `_METIERS` d'une branche CPV via le champ `CPV~` de l'API TED :

```python
_CPV = (
    "CPV~45312100 OR CPV~35111300 OR CPV~50610000"
    " OR CPV~45312200 OR CPV~42961000 OR CPV~35111000"
)
_PUBLIC_SEARCH = f"({_METIERS}) OR ({_IMPLICITE_ERP}) OR ({_CPV})"
```

---

## 2. `filters.py`

### 2.1 Nouveaux mots-clés dans `INCLUSION_KEYWORDS`
Quatre groupes, tous en minuscules :

```python
# SSI direct — équipements complémentaires
"ria", "robinet incendie armé", "baas", "bloc autonome alarme",

# Déclencheurs travaux SSI (conformité réglementaire)
"dta", "dossier technique amiante", "mise en conformité",
"vérification réglementaire", "vérification périodique",

# Courants faibles / GTB
"gtb", "gtc", "bms", "gestion technique bâtiment", "building management",

# Maintenance SSI
"mco ssi", "contrat de maintenance ssi", "vérification annuelle",
```

### 2.2 Word-boundary pour les nouveaux acronymes
`_WORD_BOUNDARY_KW` étendu avec : `"gtb"`, `"gtc"`, `"bms"`, `"ria"`  
(même traitement que `ssi`, `cmsi`, `cctv` — évite les faux positifs sur sous-chaînes).

---

## 3. `scraper_decp.py`

### 3.1 Filtre CPV
Nouveau `_CPV_FILTER` OR-é avec le filtre existant :

```python
_CPV_FILTER = (
    'search(codeCPV, "45312100")'
    ' OR search(codeCPV, "35111300")'
    ' OR search(codeCPV, "50610000")'
    ' OR search(codeCPV, "45312200")'
    ' OR search(codeCPV, "42961000")'
    ' OR search(codeCPV, "35111000")'
)
_PUBLIC_SEARCH_FILTER = (
    f"({_KEYWORD_FILTER}) OR ({_CPV_FILTER})"
    f" OR (({_CONSTRUCTION_FILTER}) AND ({_ERP_FILTER}))"
)
```

> **Note :** si l'API DECP retourne un 400 sur `codeCPV`, le champ de repli est `search(objetmarche, "45312100")`.

### 3.2 Fenêtre temporelle
`years_back=3` remplacé par `days_back` :

```python
import os
def fetch_decp_tenders(days_back: int | None = None) -> int:
    if days_back is None:
        days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
    date_min = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
```

La signature garde rétro-compatibilité avec les callers existants (valeur par défaut).

---

## 4. `scraper_boamp.py`

Même traitement que DECP pour la fenêtre temporelle :

```python
def fetch_boamp_tenders(departments=None, days_back: int | None = None) -> int:
    if days_back is None:
        days_back = int(os.getenv("SCRAPER_WINDOW_DAYS", "90"))
    date_min = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
```

Le paramètre `years_back` est supprimé (non utilisé dans les tests existants).

---

## 5. `.env.example`

Ajout en fin de fichier :

```
# Fenêtre glissante de collecte active (jours). Défaut : 90.
# Augmenter pour un premier import historique, réduire pour accélérer les runs quotidiens.
SCRAPER_WINDOW_DAYS=90
```

---

## Fichiers non modifiés

- `app.py` — aucune raison de le toucher
- `scraper_boamp.py` (filtres keyword/ERP) — inchangés
- `scraper_decp.py` (filtres keyword/ERP) — seuls le CPV et la fenêtre changent
- `llm_analyzer.py` — scoring hybride inchangé

---

## Tests

Les tests existants dans `/tests/` ne sont pas cassés :
- `test_fetch_decp_returns_zero_on_empty_response` — pas de dépendance à `years_back`
- `test_fetch_decp_inserts_relevant_record` — toujours vrai avec les nouveaux filtres
- `test_fetch_decp_inserts_public_erp_implicit_record` — le `where_clause` assert `"construction"` et `"collège"` qui restent présents

Aucun test TED ou BOAMP existant ne vérifie les paramètres de date ou d'URL — les modifications sont sans risque pour la suite de tests.
