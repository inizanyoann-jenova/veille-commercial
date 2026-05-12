# Design — Nouveaux scrapers + Paramètres + Guide utilisateur
**Date :** 2026-05-12  
**Périmètre :** DEF Océan Indien — Veille Marchés Publics  
**Statut :** Approuvé

---

## Contexte

L'application existante collecte des appels d'offres (AO) pertinents pour la défense/sécurité
(SSI, CMSI, incendie, vidéosurveillance…) sur La Réunion (974) et Mayotte (976).

8 sources importantes avaient été retirées par erreur (marquées "défuntes") :
- VAAO, Marché Online, Département 974, Marchés Public Info *(publiques)*
- Marchés Sécurisés, Instao, Tenders Go, Nukema *(compte requis)*

Ce spec couvre leur ré-intégration avec :
- Scrapers Playwright (robustesse maximale)
- Gestion des identifiants (`.env` + SQLite chiffré)
- Page Paramètres Streamlit
- Page Guide utilisateur in-app

---

## Architecture

### Nouveaux fichiers

```
playwright_base.py              # navigateur Playwright partagé + helpers
credential_manager.py           # lecture .env → SQLite chiffré (Fernet)
scraper_vaao.py                 # public, sans auth
scraper_marcheonline.py         # public, sans auth
scraper_dept974.py              # public, sans auth
scraper_nukema.py               # public + compte optionnel
scraper_marchespublicsinfo.py   # à confirmer URL au lancement
scraper_marchessecurises.py     # auth requise
scraper_instao.py               # auth requise
scraper_tendersgo.py            # auth requise
pages/parametres.py             # page Streamlit Paramètres
pages/guide.py                  # page Streamlit Guide utilisateur
```

### Fichiers modifiés

```
source_registry.py   # ajout 8 sources, retrait de _DEFUNCT_URLS
models.py            # ajout modèle Credential
database.py          # init table credentials
app.py               # navigation vers Paramètres + Guide
```

---

## Composant 1 — `playwright_base.py`

### Responsabilité
Fournit une interface unique pour lancer Playwright et interagir avec les pages web.
Tous les scrapers l'importent — aucun n'instancie Playwright directement.

### Interface publique

```python
def get_browser() -> Browser
    # Lance Chromium headless. Une nouvelle instance est créée par run de collecte
    # et fermée automatiquement via context manager à la fin de la collecte.

def login(page: Page, url: str, email: str, password: str, selectors: dict) -> bool
    # Navigue vers url, remplit email/password avec les sélecteurs CSS fournis,
    # soumet le formulaire. Retourne True si login réussi.
    # selectors = {"email": "#email", "password": "#password", "submit": "button[type=submit]"}

def extract_cards(page: Page, card_selector: str, field_map: dict) -> list[dict]
    # Extrait une liste de dicts depuis les cartes AO de la page.
    # field_map = {"title": ".title", "date": ".date", "url": "a@href"}
    # Supporte l'attribut via la notation "selector@attribute"

def paginate(page: Page, next_selector: str, max_pages: int = 5) -> bool
    # Clique sur "page suivante" si présent. Retourne False quand plus de pages.
```

### Comportement erreur
- Timeout 15s par navigation, retry x2 automatique
- Si login échoue → log warning ; scrapers publics continuent sans auth, scrapers auth-only sont skippés
- Si page introuvable (404/500) → lève `ScraperError` catchée dans `_collect_selected_sources`

---

## Composant 2 — `credential_manager.py`

### Responsabilité
Abstraction unique pour lire/écrire les identifiants. Les scrapers ne lisent jamais
`.env` ou la DB directement — ils appellent `CredentialManager.get()`.

### Interface publique

```python
class CredentialManager:
    @staticmethod
    def get(site: str) -> tuple[str, str] | None
        # Priorité : 1) variable d'env  2) SQLite déchiffré  3) None
        # site = "marches_securises" | "instao" | "tendersgo" | ...

    @staticmethod
    def save(site: str, email: str, password: str) -> None
        # Chiffre password avec Fernet, stocke en DB

    @staticmethod
    def delete(site: str) -> None

    @staticmethod
    def list_configured() -> list[dict]
        # Retourne [{site, email, has_env_override}] — jamais le mot de passe en clair
```

### Nommage des variables d'environnement

| Site | Variable email | Variable password |
|------|---------------|-------------------|
| VAAO | `VAAO_EMAIL` | `VAAO_PASSWORD` |
| Marchés Sécurisés | `MARCHES_SEC_EMAIL` | `MARCHES_SEC_PASSWORD` |
| Instao | `INSTAO_EMAIL` | `INSTAO_PASSWORD` |
| Tenders Go | `TENDERSGO_EMAIL` | `TENDERSGO_PASSWORD` |
| Nukema | `NUKEMA_EMAIL` | `NUKEMA_PASSWORD` |
| Marché Online | `MARCHEONLINE_EMAIL` | `MARCHEONLINE_PASSWORD` |

### Clé de chiffrement
- Variable `CREDENTIAL_KEY` dans `.env`
- Si absente : générée automatiquement au 1er lancement, écrite dans `.env`
- Régénérer la clé efface tous les mots de passe stockés en DB (ils deviennent illisibles)

### Modèle SQLite `credentials`
```python
class Credential(Base):
    __tablename__ = "credentials"
    id       = Column(Integer, primary_key=True)
    site     = Column(String, unique=True, nullable=False)
    email    = Column(String, nullable=False)
    password = Column(String, nullable=False)  # chiffré Fernet, jamais en clair
```

---

## Composant 3 — Les 8 scrapers

### Interface commune (identique aux scrapers existants)

```python
def fetch_xxx_tenders() -> int:
    """Collecte les AO, insère les nouveaux en DB. Retourne le nombre d'insérés."""
    creds = CredentialManager.get("xxx")       # None si non configuré
    browser = get_browser()
    page = browser.new_page()
    if creds:
        login(page, LOGIN_URL, *creds, SELECTORS)
    # ... navigation, extraction, filtrage, insertion
    return inserted
```

### Sites publics

**`scraper_vaao.py`**
- URLs : `https://www.vaao.fr/departement/la-reunion` + `/mayotte`
- Extraction : cartes AO listées sur la page, pagination "suivant"
- Auth : optionnelle (mode public suffit pour la liste)

**`scraper_marcheonline.py`**
- URL : `https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101`
- Extraction : tableau d'AO, pagination numérique
- Auth : non requise

**`scraper_dept974.py`**
- URL : `https://cg974.e-marchespublics.com/`
- Extraction : liste des avis de marchés publiés par le Conseil Départemental
- Auth : non requise

**`scraper_nukema.py`**
- URL : `https://marches-publics.nukema.com/seo/consultation/departement?departement=974` + `976`
- Extraction : cartes de consultations listées publiquement
- Auth : optionnelle (compte débloque les détails complets)

### Sites avec authentification

**`scraper_marchessecurises.py`**
- Login : `https://www.marches-securises.fr` → formulaire email/password
- Recherche : filtre département 974/976 + mots-clés DEF
- Sans credentials → scraper skippé avec warning

**`scraper_instao.py`**
- Login : `https://www.instao.fr` → formulaire email/password
- Recherche : `/bids?l=974,976` + keywords SSI/CMSI/incendie
- Bonus : récupère le score de pertinence IA si présent dans la réponse
- Sans credentials → scraper skippé avec warning

**`scraper_tendersgo.py`**
- Login : `https://app.tendersgo.com` → formulaire email/password
- Recherche : filtre pays France + DOM + mots-clés DEF
- Orientation internationale (Mayotte, COM, TAAF)
- Sans credentials → scraper skippé avec warning

**`scraper_marchespublicsinfo.py`**
- URL à confirmer au 1er lancement (domaine à vérifier)
- Scraper générique activable une fois l'URL validée
- Même pattern que les sites publics

### Filtrage et déduplication
- `is_relevant_def(titre + description)` appliqué sur chaque AO extrait
- Déduplication par `hashlib.md5(f"{titre}{url_source}{date}".encode())`
- Tous insérés avec `status="À qualifier"`, `relevance_score=0`

---

## Composant 4 — Page Paramètres (`pages/parametres.py`)

### Structure UI

```
⚙️ Paramètres
│
├── 🔐 Identifiants des sources
│   ├── Tableau : Site | Email configuré | Source (env/.env/DB) | Actions
│   ├── Bouton "Tester connexion" → ✅ Connexion réussie / ❌ Échec
│   └── Formulaire ajout/modification (expander par site)
│       ├── Email
│       ├── Mot de passe (champ masqué)
│       └── Boutons Enregistrer / Supprimer
│
├── 🔑 Sécurité
│   ├── Statut clé Fernet : "Active — générée le JJ/MM/AAAA"
│   └── Bouton "Régénérer la clé" (confirmation requise — efface les mots de passe DB)
│
└── 🧹 Maintenance
    ├── Bouton "Vider le cache Streamlit"
    └── Bouton "Réinitialiser les sources par défaut"
```

### Règles UI
- Les mots de passe ne sont jamais affichés en clair dans l'interface
- Si une variable `.env` est détectée pour un site : badge "via .env" en vert, champs désactivés
- "Tester connexion" lance un Playwright headless rapide (timeout 10s) sans collecter

---

## Composant 5 — Page Guide (`pages/guide.py`)

### Sections

1. **Qu'est-ce que cette application ?**
   - Veille automatique AO pour La Réunion (974) et Mayotte (976)
   - Domaines : SSI, CMSI, détection incendie, vidéosurveillance, courants faibles
   - Destinée aux commerciaux DEF Océan Indien

2. **Tableau de bord — lire les résultats**
   - KPIs (total AO, en cours, soumis, gagnés)
   - Statuts possibles : À qualifier → En cours → Soumis → Gagné/Perdu
   - Score de pertinence (0–100) et analyse IA

3. **Sources de collecte**
   - Tableau complet : Source | Catégorie | Automatique | Compte requis | Couverture
   - Explication : sources publiques vs sources avec compte

4. **Lancer une collecte — pas à pas**
   - Étape 1 : Cocher les sources souhaitées dans la sidebar
   - Étape 2 : Choisir la période (cette année / 2 ans / tout)
   - Étape 3 : Cliquer "⚡ Collecter la sélection"
   - Étape 4 : Attendre la collecte (barre de progression)
   - Étape 5 : Consulter les nouveaux AO "À qualifier"

5. **Gérer les opportunités**
   - Changer le statut d'un AO
   - Déclencher l'analyse IA (score + résumé)
   - Exporter le rapport Excel Direction

6. **Configurer les identifiants**
   - Via `.env` : modifier le fichier, relancer l'app
   - Via l'interface : ⚙️ Paramètres → Identifiants
   - Tableau des variables d'environnement disponibles

7. **FAQ & résolution de problèmes**
   - "Un scraper retourne une erreur" → vérifier identifiants + connexion internet
   - "Aucun résultat" → élargir la période ou vérifier les mots-clés
   - "L'application ne démarre pas" → relancer `streamlit run app.py`

---

## Mise à jour `source_registry.py`

### Supprimer de `_DEFUNCT_URLS`
```python
# Retirer ces entrées (sites actifs) :
"https://www.vaao.fr"
"https://www.instao.fr"
"https://www.nukema.fr"          # → remplacer par marches-publics.nukema.com
"https://www.marcheonline.com"   # → remplacer par marchesonline.com
"https://www.marches-publics.info"
"https://www.tendersgo.com"
```

### Ajouter dans `_DEFAULT_SOURCES`
```python
{"name": "VAAO",            "url": "https://www.vaao.fr",
 "category": "Public",      "scraper_module": "scraper_vaao",
 "scraper_func": "fetch_vaao_tenders", "is_manual": False, "display_order": 4},

{"name": "Marché Online",   "url": "https://www.marchesonline.com",
 "category": "Public",      "scraper_module": "scraper_marcheonline",
 "scraper_func": "fetch_marcheonline_tenders", "is_manual": False, "display_order": 5},

{"name": "Marchés Publics — Dép. 974", "url": "https://cg974.e-marchespublics.com",
 "category": "Public",      "scraper_module": "scraper_dept974",
 "scraper_func": "fetch_dept974_tenders", "is_manual": False, "display_order": 6},

{"name": "Nukema",          "url": "https://marches-publics.nukema.com",
 "category": "Public",      "scraper_module": "scraper_nukema",
 "scraper_func": "fetch_nukema_tenders", "is_manual": False, "display_order": 7},

{"name": "Marchés Public Info", "url": "https://www.marches-publics.info",
 "category": "Public",      "scraper_module": "scraper_marchespublicsinfo",
 "scraper_func": "fetch_marchespublicsinfo_tenders", "is_manual": False, "display_order": 8},

{"name": "Marchés Sécurisés", "url": "https://www.marches-securises.fr",
 "category": "Privé",       "scraper_module": "scraper_marchessecurises",
 "scraper_func": "fetch_marchessecurises_tenders", "is_manual": False, "display_order": 12},

{"name": "Instao",          "url": "https://www.instao.fr",
 "category": "Privé",       "scraper_module": "scraper_instao",
 "scraper_func": "fetch_instao_tenders", "is_manual": False, "display_order": 13},

{"name": "Tenders Go",      "url": "https://www.tendersgo.com",
 "category": "International", "scraper_module": "scraper_tendersgo",
 "scraper_func": "fetch_tendersgo_tenders", "is_manual": False, "display_order": 24},
```

---

## Gestion des erreurs

| Situation | Comportement |
|-----------|-------------|
| Site inaccessible (réseau) | Warning affiché dans sidebar, collecte continue sur autres sources |
| Login échoué (mauvais identifiants) | Warning "Identifiants incorrects pour X — vérifiez Paramètres" |
| Page structure changée (sélecteur CSS invalide) | Warning "Scraper X nécessite une mise à jour" |
| Timeout Playwright (>15s) | Retry x2, puis warning si toujours en échec |
| Site sans credentials configurés | Skippé silencieusement si `is_manual=False` et scraper attend auth |

---

## Navigation dans `app.py`

Streamlit multi-pages : ajout de `pages/parametres.py` et `pages/guide.py`.
Liens d'accès rapide dans la sidebar :
```
---
[⚙️ Paramètres]  [📖 Guide]
```

---

## Dépendances à ajouter

```
playwright>=1.44.0
cryptography>=42.0.0   # pour Fernet
```

Commande post-install : `playwright install chromium`

---

## Ce qui est hors périmètre

- Scraping de sites nécessitant un CAPTCHA (non couvert)
- Notifications email/Slack sur nouveaux AO (future itération)
- Scraping en tâche de fond planifiée (future itération)
- Support multi-utilisateurs (app locale mono-utilisateur)
