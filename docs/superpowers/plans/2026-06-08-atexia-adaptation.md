# ATEXIA Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adapter l'application DEF OI en ATEXIA — branding bleu/rouge, mots-clés métier étendus, suppression Mayotte, ajout agrégateurs du Word, packaging EXE autonome Windows.

**Architecture:** Backend FastAPI + SQLite inchangé. Les modifications sont (1) les mots-clés de filtrage dans `filters.py`, (2) le catalogue de sources dans `source_registry.py`, (3) le branding dans les fichiers backend et frontend, (4) le chemin DB adaptatif pour fonctionner en exe PyInstaller, (5) les scripts de build PyInstaller.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, SQLite, React 19, Vite, Tailwind CSS, PyInstaller, Vitest, pytest

---

## Fichiers impactés

| Fichier | Rôle de la modification |
|---------|------------------------|
| `filters.py` | Nouveaux mots-clés ATEXIA + suppression référence 976/Mayotte |
| `source_registry.py` | Suppression sources Mayotte + ajout 12 agrégateurs du Word |
| `backend/main.py` | Branding titre app FastAPI |
| `health_check.py` | Branding commentaire module |
| `email_digest.py` | Pas de texte DEF OI visible — aucun changement nécessaire |
| `database.py` | Chemin DB adaptatif : `%APPDATA%\ATEXIA\` quand frozen |
| `frontend/index.html` | Titre `<title>` |
| `frontend/tailwind.config.js` | Couleurs hardcodées → palette ATEXIA |
| `frontend/src/utils/theme.js` | DEFAULTS couleurs CSS vars → palette ATEXIA |
| `frontend/src/components/Sidebar.jsx` | Texte "DEF Océan Indien" → "ATEXIA", logo "OI" → "AT" |
| `frontend/src/components/Sidebar.test.jsx` | Mise à jour assertion branding |
| `frontend/src/components/Layout.jsx` | Fallback titre "DEF OI" → "ATEXIA" |
| `frontend/src/components/Layout.test.jsx` | Mise à jour assertion |
| `frontend/src/pages/Guide.jsx` | Remplacement toutes références DEF OI |
| `frontend/src/pages/Analytics.jsx` | `COULEUR_DEF` → couleur bleue ATEXIA |
| `frontend/package.json` | Nom du projet |
| `atexia_launcher.py` | **Nouveau** — point d'entrée exe (uvicorn + navigateur) |
| `build_exe.py` | **Nouveau** — spec PyInstaller |
| `build_exe.ps1` | **Nouveau** — script PowerShell de build complet |

---

## Task 1 : Mots-clés ATEXIA dans `filters.py`

**Files:**
- Modify: `filters.py`
- Test: `tests/test_filters_atexia.py` (nouveau)

- [ ] **Step 1 : Créer le fichier de test**

```python
# tests/test_filters_atexia.py
import pytest
from filters import classify_relevance, is_relevant_def


# ── Nouveaux secteurs ATEXIA ──────────────────────────────────────────────────

def test_courants_forts_est_pertinent():
    result, _ = classify_relevance("Travaux de courants forts bâtiment tertiaire")
    assert result is True


def test_tgbt_est_pertinent():
    result, _ = classify_relevance("Fourniture et pose TGBT armoire électrique")
    assert result is True


def test_irve_est_pertinent():
    result, _ = classify_relevance("Installation IRVE borne de recharge véhicule électrique")
    assert result is True


def test_photovoltaique_est_pertinent():
    result, _ = classify_relevance("Centrale photovoltaïque autoconsommation 50 kWc")
    assert result is True


def test_decret_tertiaire_est_pertinent():
    result, _ = classify_relevance("Audit énergétique décret tertiaire OPERAT")
    assert result is True


def test_groupe_electrogene_est_pertinent():
    result, _ = classify_relevance("Location groupe électrogène continuité d'énergie")
    assert result is True


def test_nf_c_15_100_est_pertinent():
    result, _ = classify_relevance("Mise aux normes électriques NF C 15-100")
    assert result is True


def test_fibre_optique_est_pertinent():
    result, _ = classify_relevance("Déploiement fibre optique réseau informatique")
    assert result is True


def test_acteur_local_shlmr_est_pertinent():
    """SHLMR dans le texte + mot construction → potentiel SSI implicite."""
    result, tags = classify_relevance("Construction logements sociaux SHLMR Saint-Denis Réunion")
    assert result is True


def test_relamping_est_pertinent():
    result, _ = classify_relevance("Relamping éclairage LED intérieur bâtiment")
    assert result is True


# ── Suppression Mayotte du filtre géographique ───────────────────────────────

def test_mayotte_seul_ne_declenche_plus():
    """Un texte mentionnant uniquement Mayotte + construction ne doit plus matcher."""
    result, _ = classify_relevance("Construction école Mamoudzou Mayotte département 976")
    assert result is False


def test_reunion_seule_declenche_toujours():
    """Un texte mentionnant La Réunion + construction doit toujours matcher."""
    result, _ = classify_relevance("Construction école Saint-Denis La Réunion")
    assert result is True


def test_974_declenche_toujours():
    result, _ = classify_relevance("Travaux extension hôpital 974")
    assert result is True


# ── Secteurs historiques DEF OI toujours actifs ───────────────────────────────

def test_ssi_toujours_pertinent():
    result, _ = classify_relevance("Système de sécurité incendie SSI catégorie A")
    assert result is True


def test_videosurveillance_toujours_pertinent():
    result, _ = classify_relevance("Installation vidéosurveillance CCTV parking")
    assert result is True
```

- [ ] **Step 2 : Lancer le test — vérifier l'échec**

```powershell
cd "c:\Users\Utilisateur\Desktop\ATEXIA veille commercial\commercial et opportunité def OI"
pytest tests/test_filters_atexia.py -v 2>&1 | head -40
```

Attendu : la plupart des tests échouent (courants forts, TGBT, IRVE, etc. non reconnus ; test Mayotte passe peut-être car 976 peut matcher).

- [ ] **Step 3 : Réécrire `filters.py`**

Remplacer le contenu complet du fichier par :

```python
import re as _re

# Mots déclencheurs directs — équipements ATEXIA
INCLUSION_KEYWORDS = [
    # ── SSI — signaux directs ──────────────────────────────────────────────────
    "ssi",
    "système de sécurité incendie",
    "alarme incendie",
    "alarme anti-incendie",
    "système incendie",
    "sécurité incendie",
    "protection incendie",
    "centrale incendie",
    "tableau de signalisation",
    # Détecteurs
    "détection incendie",
    "détecteur de fumée",
    "détecteurs de fumée",
    "détecteur thermique",
    "détecteurs thermiques",
    "détecteur incendie",
    "détecteurs incendie",
    "tête de détection",
    "têtes de détection",
    # Déclencheurs / diffuseurs
    "déclencheur manuel",
    "déclencheurs manuels",
    "diffuseur sonore",
    "diffuseurs sonores",
    "flash lumineux",
    "flash incendie",
    # Extinction / compartimentage
    "extinction incendie",
    "extinction automatique",
    "sprinkler",
    "porte coupe-feu",
    "portes coupe-feu",
    "compartimentage",
    "compartimentage incendie",
    "évacuation incendie",
    # Équipements complémentaires SSI
    "ria",
    "robinet incendie arm",
    "robinets incendie arm",
    "baas",
    "bloc autonome alarme",
    "blocs autonomes alarme",
    # ── CMSI / Désenfumage ─────────────────────────────────────────────────────
    "cmsi",
    "désenfumage",
    "centrale de mise en sécurité",
    "mise en sécurité incendie",
    "volet de désenfumage",
    "volets de désenfumage",
    "trappe de désenfumage",
    "trappes de désenfumage",
    "exutoire de fumée",
    "exutoires de fumée",
    "extracteur de fumée",
    "extracteurs de fumée",
    "désenfumage naturel",
    "désenfumage mécanique",
    "denfc",
    "dmfc",
    # ── Vidéosurveillance / CCTV ───────────────────────────────────────────────
    "cctv",
    "vidéosurveillance",
    "vidéo surveillance",
    "vidéoprotection",
    "vidéo protection",
    "système de vidéosurveillance",
    "système de vidéoprotection",
    "caméras de sécurité",
    "caméra de surveillance",
    "caméras de surveillance",
    "caméra ip",
    "caméras ip",
    "caméra thermique",
    "caméras thermiques",
    "télésurveillance",
    "nvr",
    "dvr",
    # Contrôle d'accès
    "contrôle d'accès",
    "controle d'acces",
    "système de contrôle d'accès",
    "lecteur de badge",
    "lecteurs de badge",
    "badge d'accès",
    "interphonie",
    "interphone",
    "visiophone",
    "portier vidéo",
    "vidéo portier",
    "sûreté électronique",
    "sureté électronique",
    "sécurité électronique",
    # Intrusion
    "alarme intrusion",
    "détection intrusion",
    "anti-intrusion",
    "système anti-intrusion",
    "système d'alarme",
    # ── Courants faibles / GTB ─────────────────────────────────────────────────
    "courants faibles",
    "courant faible",
    "gtb",
    "gtc",
    "bms",
    "gestion technique bâtiment",
    "gestion technique du bâtiment",
    "building management",
    "câblage structuré",
    "cablage structure",
    "vdi",
    "voix données images",
    "réseau de communication",
    "domotique",
    "automatisme bâtiment",
    "tableau de communication",
    "armoire de brassage",
    "baie de brassage",
    # ── Courants forts / Génie électrique ────────────────────────────────────
    "courants forts",
    "génie électrique",
    "genie electrique",
    "installation électrique",
    "installations électriques",
    "travaux électriques",
    "tgbt",
    "tableau général basse tension",
    "armoire électrique",
    "armoires électriques",
    "distribution basse tension",
    "coffret électrique",
    "coffrets électriques",
    "tableau divisionnaire",
    "tableaux divisionnaires",
    "disjoncteur",
    "câblage électrique",
    "cablage electrique",
    # ── Continuité d'énergie ─────────────────────────────────────────────────
    "groupe électrogène",
    "groupes électrogènes",
    "onduleur",
    "onduleurs",
    "ups",
    "asi",
    "alimentation sans interruption",
    "continuité d'énergie",
    "secours électrique",
    "alimentation de secours",
    # ── Éclairage ────────────────────────────────────────────────────────────
    "relamping",
    "éclairage intérieur",
    "éclairage led",
    "mise aux normes électriques",
    "nf c 15-100",
    "nfc 15-100",
    "éclairage de sécurité",
    "balisage lumineux",
    "éclairage de balisage",
    "luminaire",
    "luminaires",
    # ── IRVE — bornes de recharge ────────────────────────────────────────────
    "irve",
    "borne de recharge",
    "bornes de recharge",
    "recharge véhicule électrique",
    "infrastructure de recharge",
    "point de charge",
    "station de recharge",
    # ── Énergie renouvelable / photovoltaïque ────────────────────────────────
    "photovoltaïque",
    "photovoltaique",
    "panneaux solaires",
    "panneau solaire",
    "centrale solaire",
    "autoconsommation",
    "stockage énergie",
    "batterie solaire",
    "ombrière photovoltaïque",
    "ombriere photovoltaique",
    "enr",
    # ── Efficacité énergétique / réglementaire ───────────────────────────────
    "décret tertiaire",
    "decret tertiaire",
    "operat",
    "performance énergétique",
    "audit énergétique",
    "audit energetique",
    "bilan énergétique",
    "rénovation énergétique",
    "efficacité énergétique",
    "cee",
    # ── Réseau / infrastructures numériques ──────────────────────────────────
    "fibre optique",
    "réseau informatique",
    "baie informatique",
    "réseau local",
    "lan",
    "câblage réseau",
    "infrastructure réseau",
    # ── Maintenance SSI / réglementaire ──────────────────────────────────────
    "mco ssi",
    "mco",
    "maintenance ssi",
    "contrat de maintenance ssi",
    "contrat de maintenance",
    "maintien en condition opérationnelle",
    "maintenance préventive",
    "maintenance corrective",
    "vérification annuelle",
    "vérification réglementaire",
    "vérification périodique",
    "vérification et maintenance",
    "maintenance et vérification",
    "télémaintenance",
    # Conformité réglementaire
    "mise en conformité",
    "dta",
    "dossier technique amiante",
]

# Exclusions absolues — hors périmètre ATEXIA
EXCLUSION_KEYWORDS = [
    # Sécurité humaine (gardiens, agents)
    "gardiennage",
    "agents de sécurité",
    "agent de sécurité",
    "agent de surveillance",
    "rondes de surveillance",
    "surveillance humaine",
    "maître-chien",
    "ssiap",
    "sécurité civile",
    # Contenu scolaire/culturel sans lien avec la construction
    "livres scolaires",
    "manuels scolaires",
    "fournitures scolaires",
    "rentrée scolaire",
    "prix littéraire",
    "concours littéraire",
    # RH / social
    "offre d'emploi",
    "aide sociale",
    "allocation",
    "bourse scolaire",
    # Environnement / voirie (sans lien avec bâtiment)
    "espaces verts",
    "voirie",
    "assainissement",
    "eau potable",
    "collecte des déchets",
    "déchèterie",
]

KEYWORDS_CONSTRUCTION = [
    "construction",
    "chantier",
    "travaux",
    "permis de construire",
    "réhabilitation",
    "rénovation",
    "extension",
    "restructuration",
    "aménagement",
    "programme immobilier",
    "promotion immobilière",
    "lotissement",
    "inauguration",
    "pose de la première pierre",
    "mise en service",
    "nouveau bâtiment",
    "nouvelle construction",
    "projet de construction",
    "maître d'ouvrage",
    "maîtrise d'ouvrage",
    "financement construction",
    "investissement immobilier",
    "bâtiment neuf",
    "immeuble neuf",
    "opération immobilière",
    "programme de construction",
    "zac",
]

KEYWORDS_ERP_CIBLES = [
    # Santé
    "hôpital", "hopital", "clinique", "ehpad", "maison de retraite",
    "résidence seniors", "établissement de santé", "maison de santé",
    "centre de soins", "centre médical", "dispensaire",
    # Hébergement / hôtellerie
    "hôtel", "hotel", "résidence hôtelière", "resort", "résidence de tourisme",
    # Enseignement
    "école", "ecole", "lycée", "lycee", "collège", "college",
    "université", "universite", "résidence étudiante", "campus",
    "internat", "crèche", "creche", "halte-garderie", "halte garderie",
    # Commerce / logistique
    "centre commercial", "mall", "galerie marchande", "marché couvert",
    "entrepôt logistique", "entrepot", "usine",
    # Sport / loisirs
    "salle de sport", "gymnase", "stade", "arena", "piscine",
    "centre aquatique", "base nautique",
    # Culture
    "centre culturel", "théâtre", "theatre", "cinéma", "cinema",
    "musée", "musee", "bibliothèque", "bibliotheque",
    "médiathèque", "mediatheque", "salle des fêtes", "salle polyvalente",
    # Bureaux / administration
    "immeuble de bureaux", "siège social", "bâtiment administratif",
    "mairie", "préfecture", "sous-préfecture", "tribunal",
    "commissariat", "caserne", "foyer",
    # Logement social
    "logement social", "hlm", "office hlm", "résidence sociale",
    # Transport / data
    "aéroport", "aeroport", "gare", "port maritime",
    "centre de données", "data center",
]

# Acteurs locaux La Réunion — renforcent le score géographique
_ACTEURS_LOCAUX_974 = [
    "shlmr", "sidr", "semader", "sedre", "chu réunion", "chu reunion",
    "chor", "cinor", "tco", "civis", "cirest",
]

_WORD_BOUNDARY_KW = {
    "ssi", "cmsi", "cctv", "ria", "gtb", "gtc", "bms", "mco", "vdi",
    "nvr", "dvr", "ups", "asi", "irve", "enr", "cee", "lan", "tgbt",
}

_COMPILED_BOUNDARY = {
    kw: _re.compile(r"\b" + _re.escape(kw) + r"\b") for kw in _WORD_BOUNDARY_KW
}


def classify_relevance(text: str) -> tuple[bool, list[str]]:
    """Retourne (pertinent, tags).

    tags contient ["Potentiel SSI implicite"] quand la capture est via
    la logique construction+ERP, sans mot-clé ATEXIA direct.
    """
    text_lower = text.lower()

    for kw in INCLUSION_KEYWORDS:
        if kw in _WORD_BOUNDARY_KW:
            if _COMPILED_BOUNDARY[kw].search(text_lower):
                return True, []
        elif kw in text_lower:
            return True, []

    for kw in EXCLUSION_KEYWORDS:
        if kw in text_lower:
            return False, []

    has_chantier = any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)
    has_erp = any(kw in text_lower for kw in KEYWORDS_ERP_CIBLES)
    has_acteur_local = any(kw in text_lower for kw in _ACTEURS_LOCAUX_974)

    if has_chantier:
        if has_erp:
            return True, ["Potentiel SSI implicite"]
        if (
            "974" in text_lower
            or "réunion" in text_lower
            or has_acteur_local
        ):
            return True, ["Potentiel SSI implicite"]

    return False, []


def is_relevant_def(text: str) -> bool:
    return classify_relevance(text)[0]


def is_construction_relevant(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in KEYWORDS_CONSTRUCTION)


def is_prive_relevant(text: str) -> bool:
    return classify_relevance(text)[0]
```

- [ ] **Step 4 : Lancer les tests — vérifier qu'ils passent**

```powershell
pytest tests/test_filters_atexia.py -v
```

Attendu : tous les tests PASS.

- [ ] **Step 5 : Lancer les tests existants pour vérifier aucune régression**

```powershell
pytest tests/ -v --ignore=tests/test_filters_atexia.py 2>&1 | tail -20
```

- [ ] **Step 6 : Commit**

```powershell
git add filters.py tests/test_filters_atexia.py
git commit -m "feat(filters): mots-clés ATEXIA — courants forts, IRVE, photovoltaïque, énergie + suppression filtre Mayotte"
```

---

## Task 2 : Sources dans `source_registry.py`

**Files:**
- Modify: `source_registry.py`

- [ ] **Step 1 : Supprimer les sources Mayotte de `_DEFAULT_SOURCES`**

Dans `source_registry.py`, retirer les blocs correspondant à ces 5 entrées :
- `"Centre Hospitalier de Mayotte"` (avec `scraper_module: "scraper_chm"`)
- `"Département de Mayotte — Marchés"`
- `"CADEMA — Marchés publics"`
- `"ARMP Madagascar"`
- `"CPB Mauritius — Procurement"`

- [ ] **Step 2 : Supprimer le module `scraper_chm` de `_old_func_names`**

Retirer `"fetch_chm_tenders"` de la liste `_old_func_names` dans `init_sources()`.

- [ ] **Step 3 : Ajouter les agrégateurs du Word**

À la fin de `_DEFAULT_SOURCES`, avant le commentaire `# ── Banques de développement`, ajouter le bloc suivant :

```python
    # ── Agrégateurs freemium ──────────────────────────────────────────────────
    {
        "name": "e-marchespublics.com",
        "url": "https://www.e-marchespublics.com",
        "category": "Public",
        "is_manual": True,
        "display_order": 60,
        "notes": "Freemium — important en volume, couvre les acheteurs de La Réunion. Compte gratuit pour les alertes.",
    },
    {
        "name": "J360",
        "url": "https://www.j360.info",
        "category": "Public",
        "is_manual": True,
        "display_order": 61,
        "notes": "Freemium — réseau social professionnel de la commande publique. Veille cartographiée par mots-clés.",
    },
    {
        "name": "Bidding Source",
        "url": "https://www.biddingsource.com",
        "category": "International",
        "is_manual": True,
        "display_order": 62,
        "notes": "Freemium — bonne déclinaison des flux français et ultra-marins.",
    },
    # ── Agrégateurs premium / experts ────────────────────────────────────────
    {
        "name": "Vecteur Plus",
        "url": "https://www.vecteurplus.com",
        "category": "Privé",
        "is_manual": True,
        "display_order": 70,
        "notes": "Premium — leader BTP et second œuvre technique. Détecte marchés privés et publics, analyses amont.",
    },
    {
        "name": "Libel",
        "url": "https://www.libel.fr",
        "category": "Privé",
        "is_manual": True,
        "display_order": 71,
        "notes": "Premium — centralisation exhaustive web + presse locale. IA pour analyser les DCE.",
    },
    {
        "name": "Explore",
        "url": "https://www.explore.fr",
        "category": "Privé",
        "is_manual": True,
        "display_order": 72,
        "notes": "Premium — cartographie projets immobiliers et d'aménagement avant la sortie officielle de l'AO.",
    },
    {
        "name": "DoubleTrade",
        "url": "https://www.doubletrade.com",
        "category": "Privé",
        "is_manual": True,
        "display_order": 73,
        "notes": "Premium — Business Intelligence marchés publics et privés, excellents filtres de tri.",
    },
    {
        "name": "Deepbloo",
        "url": "https://www.deepbloo.com",
        "category": "International",
        "is_manual": True,
        "display_order": 74,
        "notes": "Premium — spécialisé énergie, électricité, infrastructures de réseaux. Idéal pour ATEXIA.",
    },
    {
        "name": "Wanao",
        "url": "https://www.wanao.com",
        "category": "Privé",
        "is_manual": True,
        "display_order": 75,
        "notes": "Premium — veille automatique avec segmentation sectorielle très fine.",
    },
    {
        "name": "Klekoon",
        "url": "https://www.klekoon.com",
        "category": "Privé",
        "is_manual": True,
        "display_order": 76,
        "notes": "Premium — veille payante + plateforme d'envoi de candidatures sécurisées.",
    },
    {
        "name": "MPF — Marchés Publics France",
        "url": "https://www.mpfrance.fr",
        "category": "Public",
        "is_manual": True,
        "display_order": 77,
        "notes": "Premium — plateforme EASY, alertes dédoublonnées avec analyse rapide du DCE.",
    },
    {
        "name": "Centrale des Marchés",
        "url": "https://www.centraledesmarches.com",
        "category": "Public",
        "is_manual": True,
        "display_order": 78,
        "notes": "Premium — détection et envoi ciblé d'opportunités d'affaires publiques.",
    },
    {
        "name": "First AO",
        "url": "https://www.firstao-appel-offre.fr",
        "category": "Public",
        "is_manual": True,
        "display_order": 79,
        "notes": "Premium — prospection commerciale via la commande publique.",
    },
    {
        "name": "TendersPage",
        "url": "https://www.tenderspage.com",
        "category": "International",
        "is_manual": True,
        "display_order": 80,
        "notes": "Premium — un des plus grands moteurs de recherche mondiaux, couverture outre-mer.",
    },
```

- [ ] **Step 4 : Mettre à jour le User-Agent**

Dans `_ping_source()`, remplacer :
```python
headers={"User-Agent": "DEF-OI-Monitor/1.0"},
```
par :
```python
headers={"User-Agent": "ATEXIA-Monitor/1.0"},
```

- [ ] **Step 5 : Vérifier que les tests passent**

```powershell
pytest tests/ -v 2>&1 | tail -15
```

- [ ] **Step 6 : Commit**

```powershell
git add source_registry.py
git commit -m "feat(sources): suppression sources Mayotte + ajout 12 agrégateurs (J360, Vecteur Plus, Libel, etc.)"
```

---

## Task 3 : Branding backend

**Files:**
- Modify: `backend/main.py` (ligne 3)
- Modify: `health_check.py` (ligne 3)

- [ ] **Step 1 : Modifier `backend/main.py`**

Remplacer la ligne :
```python
FastAPI backend — DEF OI Veille Marchés
```
par :
```python
FastAPI backend — ATEXIA Veille Marchés
```

C'est la docstring en ligne 3 du fichier. Trouver aussi l'instanciation FastAPI dans ce fichier et remplacer le titre :

```powershell
grep -n "DEF OI\|DEF Océan\|def.oi" backend/main.py
```

Remplacer chaque occurrence trouvée par "ATEXIA".

- [ ] **Step 2 : Modifier `health_check.py`**

Remplacer ligne 3 :
```python
Module de health check — DEF OI Veille Commerciale.
```
par :
```python
Module de health check — ATEXIA Veille Commerciale.
```

- [ ] **Step 3 : Vérifier aucune occurrence résiduelle**

```powershell
grep -rn "DEF OI\|DEF Océan\|def_oi\|DEF-OI" backend/ health_check.py email_digest.py
```

Attendu : aucun résultat (ou seulement dans des commentaires historiques non affichés à l'utilisateur).

- [ ] **Step 4 : Commit**

```powershell
git add backend/main.py health_check.py
git commit -m "feat(branding): remplacement DEF OI → ATEXIA dans les modules backend"
```

---

## Task 4 : Chemin DB adaptatif dans `database.py`

**Files:**
- Modify: `database.py` (lignes 1-18)

- [ ] **Step 1 : Ajouter les imports en haut de `database.py`**

Après la ligne `from datetime import timezone`, ajouter :
```python
import os as _os
import sys as _sys
```

- [ ] **Step 2 : Remplacer le bloc DATABASE_URL (lignes ~11-17)**

Remplacer :
```python
DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)
```
par :
```python
def _get_db_path() -> str:
    if getattr(_sys, "frozen", False):
        # Exécution en tant qu'exe PyInstaller — stocker dans %APPDATA%\ATEXIA
        data_dir = _os.path.join(_os.environ.get("APPDATA", "."), "ATEXIA")
        _os.makedirs(data_dir, exist_ok=True)
        return _os.path.join(data_dir, "atexia_veille.db")
    return _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "atexia_veille.db")

DATABASE_URL = f"sqlite:///{_get_db_path()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)
```

- [ ] **Step 2 : Vérifier que les tests DB passent toujours**

```powershell
pytest tests/test_database_helpers.py tests/test_insert_if_new.py -v
```

Attendu : PASS (les tests utilisent une DB in-memory via conftest, non affectée).

- [ ] **Step 3 : Commit**

```powershell
git add database.py
git commit -m "feat(database): chemin DB adaptatif — APPDATA\ATEXIA quand exécuté en exe PyInstaller"
```

---

## Task 5 : Couleurs ATEXIA dans le frontend

**Files:**
- Modify: `frontend/src/utils/theme.js`
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/index.html`
- Modify: `frontend/package.json`

**Palette ATEXIA :**
- Bleu marine foncé (fond) : `#001441` → RGB `0 20 65`
- Bleu primaire (accent) : `#0057B8` → RGB `0 87 184`
- Rouge ATEXIA (badges, urgences) : `#E30613` → RGB `227 6 19`
- Texte clair : `#DDE6FF` → RGB `221 230 255`

- [ ] **Step 1 : Modifier `frontend/src/utils/theme.js`**

Remplacer le bloc `DEFAULTS` :
```js
export const DEFAULTS = {
  deep:  '4 13 26',
  cyan:  '0 200 255',
  coral: '255 107 107',
  text:  '221 238 255',
}
```
par :
```js
export const DEFAULTS = {
  deep:  '0 20 65',
  cyan:  '0 87 184',
  coral: '227 6 19',
  text:  '221 230 255',
}
```

- [ ] **Step 2 : Modifier `frontend/tailwind.config.js`**

Remplacer le contenu complet :
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        sidebar: '#001441',
        accent:  '#E30613',
        ocean: {
          deep:   'rgb(var(--color-ocean-deep) / <alpha-value>)',
          navy:   '#00082A',
          panel:  '#000C36',
          border: 'rgba(0,87,184,0.12)',
          glow:   'rgba(0,87,184,0.20)',
          cyan:   'rgb(var(--color-ocean-cyan) / <alpha-value>)',
          teal:   '#4A90D9',
          coral:  'rgb(var(--color-ocean-coral) / <alpha-value>)',
          gold:   '#ffd700',
          text:   'rgb(var(--color-ocean-text) / <alpha-value>)',
          muted:  'rgba(140,175,230,0.45)',
        },
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'serif'],
        sans:  ['DM Sans', 'system-ui', 'sans-serif'],
        mono:  ['DM Mono', 'Inconsolata', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3 : Modifier `frontend/index.html`**

Remplacer :
```html
<title>DEF Océan Indien — Veille Marchés</title>
```
par :
```html
<title>ATEXIA — Veille Marchés</title>
```

- [ ] **Step 4 : Modifier `frontend/package.json`**

Changer la propriété `"name"` de l'objet JSON :
```json
"name": "atexia-veille",
```

- [ ] **Step 5 : Mettre à jour `Parametres.apparence.test.jsx`**

Ce fichier hardcode les anciennes valeurs RGB. Remplacer dans `frontend/src/pages/Parametres.apparence.test.jsx` :

```js
DEFAULTS: { deep: '4 13 26', cyan: '0 200 255', coral: '255 107 107', text: '221 238 255' },
```

par :

```js
DEFAULTS: { deep: '0 20 65', cyan: '0 87 184', coral: '227 6 19', text: '221 230 255' },
```

- [ ] **Step 6 : Vérifier les tests thème**

```powershell
cd frontend && npm test -- --reporter=verbose src/utils/theme.test.js src/pages/Parametres.apparence.test.jsx
```

Attendu : PASS. Les tests vérifient le comportement des fonctions `applyTheme`, `loadSavedTheme`, etc.

- [ ] **Step 6 : Commit**

```powershell
cd ..
git add frontend/src/utils/theme.js frontend/tailwind.config.js frontend/index.html frontend/package.json
git commit -m "feat(theme): palette couleurs ATEXIA — bleu #0057B8 et rouge #E30613 en remplacement du thème Ocean Deep"
```

---

## Task 6 : Branding Sidebar ATEXIA

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/components/Sidebar.test.jsx`

- [ ] **Step 1 : Mettre à jour le test Sidebar**

Dans `frontend/src/components/Sidebar.test.jsx`, remplacer :
```js
it('affiche le logo DEF OI', () => {
  // ...
  expect(screen.getByText('DEF Océan Indien')).toBeInTheDocument()
```
par :
```js
it('affiche le logo ATEXIA', () => {
  // ...
  expect(screen.getByText('ATEXIA')).toBeInTheDocument()
```

- [ ] **Step 2 : Lancer le test pour confirmer l'échec**

```powershell
cd frontend && npm test -- --reporter=verbose src/components/Sidebar.test.jsx
```

Attendu : FAIL — `"ATEXIA"` introuvable dans le DOM.

- [ ] **Step 3 : Modifier `Sidebar.jsx` — logo et nom**

Localiser les lignes autour de la ligne 279 (bloc logo) et remplacer :
```jsx
<span className="font-serif font-bold text-ocean-cyan text-sm">OI</span>
```
par :
```jsx
<span className="font-serif font-bold text-ocean-cyan text-sm">AT</span>
```

Et remplacer :
```jsx
<p className="font-serif font-bold text-ocean-text text-sm leading-tight">DEF Océan Indien</p>
```
par :
```jsx
<p className="font-serif font-bold text-ocean-text text-sm leading-tight">ATEXIA</p>
```

- [ ] **Step 4 : Lancer les tests pour confirmer le PASS**

```powershell
npm test -- --reporter=verbose src/components/Sidebar.test.jsx
```

- [ ] **Step 5 : Commit**

```powershell
cd ..
git add frontend/src/components/Sidebar.jsx frontend/src/components/Sidebar.test.jsx
git commit -m "feat(sidebar): branding ATEXIA — logo AT et nom ATEXIA en remplacement de DEF Océan Indien"
```

---

## Task 7 : Branding Layout et Analytics

**Files:**
- Modify: `frontend/src/components/Layout.jsx`
- Modify: `frontend/src/components/Layout.test.jsx`
- Modify: `frontend/src/pages/Analytics.jsx`

- [ ] **Step 1 : Mettre à jour le test Layout**

Dans `frontend/src/components/Layout.test.jsx` ligne 31, remplacer :
```js
expect(screen.getByText('DEF Océan Indien')).toBeInTheDocument()
```
par :
```js
expect(screen.getByText('ATEXIA')).toBeInTheDocument()
```

- [ ] **Step 2 : Modifier `Layout.jsx`**

Trouver la ligne :
```js
const title = PAGE_TITLES[pathname] ?? 'DEF OI'
```
Remplacer par :
```js
const title = PAGE_TITLES[pathname] ?? 'ATEXIA'
```

Vérifier s'il existe une référence `'DEF Océan Indien'` dans le rendu JSX de Layout et la remplacer par `'ATEXIA'`.

- [ ] **Step 3 : Modifier `Analytics.jsx`**

Remplacer :
```js
const COULEUR_DEF = '#00c8ff'
```
par :
```js
const COULEUR_DEF = '#0057B8'
```

- [ ] **Step 4 : Lancer les tests**

```powershell
cd frontend && npm test -- --reporter=verbose src/components/Layout.test.jsx
```

Attendu : PASS.

- [ ] **Step 5 : Commit**

```powershell
cd ..
git add frontend/src/components/Layout.jsx frontend/src/components/Layout.test.jsx frontend/src/pages/Analytics.jsx
git commit -m "feat(branding): Layout et Analytics — remplacement références DEF OI par ATEXIA"
```

---

## Task 8 : Guide.jsx — remplacement des références DEF OI

**Files:**
- Modify: `frontend/src/pages/Guide.jsx`

- [ ] **Step 1 : Identifier toutes les occurrences**

```powershell
grep -n "DEF OI\|DEF Océan\|Mayotte\|CHM\|976" frontend/src/pages/Guide.jsx
```

- [ ] **Step 2 : Remplacer chaque occurrence**

Pour chaque ligne identifiée, faire les remplacements suivants :

| Texte original | Remplacement |
|---|---|
| `"DEF OI"` | `"ATEXIA"` |
| `"pour DEF OI"` | `"pour ATEXIA"` |
| `"mots-clés métier DEF OI"` | `"mots-clés métier ATEXIA"` |
| `"DEF OI est le principal opérateur local qualifié"` | `"ATEXIA est le principal opérateur local qualifié"` |
| `"CHM (Mayotte)"` | *(supprimer de la liste sources)* |
| `"Océan Indien"` dans le contexte DEF | `"La Réunion"` |
| `125 mots-clés` | `160 mots-clés` (le nouveau fichier en contient plus) |

- [ ] **Step 3 : Vérifier visuellement le résultat**

```powershell
grep -n "DEF OI\|DEF Océan" frontend/src/pages/Guide.jsx
```

Attendu : aucun résultat.

- [ ] **Step 4 : Commit**

```powershell
git add frontend/src/pages/Guide.jsx
git commit -m "feat(guide): remplacement toutes références DEF OI par ATEXIA + mise à jour liste sources"
```

---

## Task 9 : EXE autonome PyInstaller

**Files:**
- Create: `atexia_launcher.py`
- Create: `build_exe.py`
- Create: `build_exe.ps1`

- [ ] **Step 1 : Créer `atexia_launcher.py`**

```python
"""
Point d'entrée ATEXIA Veille — EXE PyInstaller.
Lance uvicorn sur localhost:8000 et ouvre le navigateur par défaut.
"""
import os
import sys
import threading
import time
import webbrowser

# Ajouter le répertoire du launcher au sys.path
# PyInstaller extrait les fichiers dans sys._MEIPASS
if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _base)

# Configurer le répertoire de données persistantes
_appdata = os.path.join(os.environ.get("APPDATA", "."), "ATEXIA")
os.makedirs(_appdata, exist_ok=True)

# Playwright Chromium dans APPDATA
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(_appdata, "playwright"),
)

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _open_browser():
    time.sleep(2.5)
    webbrowser.open(URL)


if __name__ == "__main__":
    print(f"ATEXIA Veille — démarrage sur {URL}")
    threading.Thread(target=_open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )
```

- [ ] **Step 2 : Créer `build_exe.py`**

```python
"""
Script de build PyInstaller pour ATEXIA Veille.
Exécuter depuis la racine du projet :
    python build_exe.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(ROOT, "frontend", "dist")
DIST_NAME = "atexia_veille"


def check_frontend_built():
    if not os.path.isdir(FRONTEND_DIST):
        print("❌ frontend/dist/ introuvable. Lancez d'abord : cd frontend && npm run build")
        sys.exit(1)
    print("✓ frontend/dist/ trouvé")


def run_pyinstaller():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name", DIST_NAME,
        "--add-data", f"{FRONTEND_DIST}{os.pathsep}frontend/dist",
        # Modules Python de la racine
        "--add-data", f"{ROOT}{os.pathsep}.",
        # Données statiques nécessaires
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "apscheduler",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "mistralai",
        "--collect-all", "playwright",
        "atexia_launcher.py",
    ]
    print("Lancement PyInstaller…")
    subprocess.run(cmd, check=True, cwd=ROOT)
    print(f"\n✓ Build terminé → dist/{DIST_NAME}/")


if __name__ == "__main__":
    check_frontend_built()
    run_pyinstaller()
```

- [ ] **Step 3 : Créer `build_exe.ps1`**

```powershell
<#
.SYNOPSIS
    Build complet ATEXIA Veille — frontend + exe PyInstaller
.DESCRIPTION
    1. Installe les dépendances npm et compile le frontend React
    2. Installe PyInstaller si absent
    3. Lance le build PyInstaller
    4. Affiche le chemin de l'exe final
.EXAMPLE
    .\build_exe.ps1
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== BUILD ATEXIA VEILLE ===" -ForegroundColor Cyan
Write-Host ""

# 1. Build frontend
Write-Host ">> Etape 1/3 : Build frontend React..." -ForegroundColor Yellow
Set-Location "$Root\frontend"
npm install --silent
npm run build
if (-not (Test-Path "$Root\frontend\dist\index.html")) {
    Write-Error "Echec du build frontend — dist\index.html introuvable"
    exit 1
}
Write-Host "   Frontend build OK" -ForegroundColor Green
Set-Location $Root

# 2. Installer PyInstaller si absent
Write-Host ""
Write-Host ">> Etape 2/3 : Verification PyInstaller..." -ForegroundColor Yellow
python -m pip install pyinstaller --quiet
Write-Host "   PyInstaller OK" -ForegroundColor Green

# 3. Build exe
Write-Host ""
Write-Host ">> Etape 3/3 : Build PyInstaller (peut prendre 2-5 minutes)..." -ForegroundColor Yellow
python build_exe.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Echec PyInstaller"
    exit 1
}

Write-Host ""
Write-Host "=== BUILD TERMINE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Executable : $Root\dist\atexia_veille\" -ForegroundColor Cyan
Write-Host "Double-cliquez sur dist\atexia_veille\atexia_veille.exe pour lancer l'application." -ForegroundColor White
Write-Host ""
Write-Host "Note : Au premier lancement, Playwright telecharge Chromium (~130 Mo)" -ForegroundColor DarkYellow
Write-Host "       dans %APPDATA%\ATEXIA\playwright\" -ForegroundColor DarkYellow
```

- [ ] **Step 4 : Mettre à jour `backend/main.py` pour servir le frontend compilé**

Chercher dans `backend/main.py` s'il existe déjà un montage de fichiers statiques. Sinon, ajouter après les imports :

```python
from fastapi.staticfiles import StaticFiles
import pathlib as _pathlib

# Chemin vers le frontend compilé (fonctionne en dev et en exe PyInstaller)
def _find_frontend_dist() -> str | None:
    candidates = [
        # En exe PyInstaller (sys._MEIPASS)
        _pathlib.Path(getattr(sys, "_MEIPASS", "")) / "frontend" / "dist",
        # En développement
        _pathlib.Path(__file__).parent.parent / "frontend" / "dist",
    ]
    for p in candidates:
        if p.is_dir():
            return str(p)
    return None
```

Puis après la création de `app = FastAPI(...)`, ajouter :

```python
_frontend_dist = _find_frontend_dist()
if _frontend_dist:
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
```

> **Important :** Ce montage doit être le dernier ajouté pour ne pas masquer les routes `/api/`.

- [ ] **Step 5 : Vérifier les tests backend**

```powershell
pytest tests/ -v 2>&1 | tail -20
```

Attendu : PASS (le montage statique est conditionnel — en test il n'y a pas de dist/).

- [ ] **Step 6 : Commit fichiers EXE**

```powershell
git add atexia_launcher.py build_exe.py build_exe.ps1 backend/main.py
git commit -m "feat(exe): packaging PyInstaller — atexia_launcher, build_exe.py, build_exe.ps1 + montage frontend statique"
```

---

## Task 10 : Vérification finale et tests complets

**Files:** aucun fichier nouveau

- [ ] **Step 1 : Lancer tous les tests Python**

```powershell
cd "c:\Users\Utilisateur\Desktop\ATEXIA veille commercial\commercial et opportunité def OI"
pytest tests/ -v 2>&1 | tail -30
```

Attendu : tous PASS.

- [ ] **Step 2 : Lancer tous les tests frontend**

```powershell
cd frontend && npm test 2>&1 | tail -30
```

Attendu : tous PASS.

- [ ] **Step 3 : Vérifier aucune référence DEF OI résiduelle dans le code affiché à l'utilisateur**

```powershell
cd ..
grep -rn "DEF OI\|DEF Océan\|Océan Indien" `
  backend/main.py health_check.py email_digest.py `
  frontend/src/components/Sidebar.jsx `
  frontend/src/components/Layout.jsx `
  frontend/src/pages/Guide.jsx `
  frontend/index.html
```

Attendu : aucun résultat (ou uniquement dans des commentaires non visibles par l'utilisateur).

- [ ] **Step 4 : Test de démarrage du backend**

```powershell
cd backend
python -m uvicorn main:app --port 8000 &
Start-Sleep -Seconds 3
Invoke-WebRequest http://localhost:8000/api/health -UseBasicParsing | Select-Object StatusCode
```

Attendu : `StatusCode: 200`.

- [ ] **Step 5 : (Optionnel) Test du build EXE si une machine avec Python + Node.js est disponible**

```powershell
cd ..
.\build_exe.ps1
```

Attendu : `dist\atexia_veille\atexia_veille.exe` créé, taille ~150-200 Mo.

---

## Récapitulatif des commits attendus

1. `feat(filters)` — mots-clés ATEXIA + suppression Mayotte
2. `feat(sources)` — Mayotte supprimé + 12 agrégateurs
3. `feat(branding)` — backend
4. `feat(database)` — chemin DB adaptatif
5. `feat(theme)` — couleurs ATEXIA
6. `feat(sidebar)` — branding ATEXIA
7. `feat(branding)` — Layout + Analytics
8. `feat(guide)` — Guide.jsx
9. `feat(exe)` — packaging PyInstaller
