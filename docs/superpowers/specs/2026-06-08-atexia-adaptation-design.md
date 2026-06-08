# Design — Adaptation ATEXIA Veille Marchés Publics

**Date :** 2026-06-08  
**Statut :** Approuvé  
**Auteur :** Brainstorming Claude Code

---

## 1. Contexte et objectif

Adapter l'application de veille marchés publics initialement développée pour DEF OI (DEF Océan Indien) à la société **ATEXIA**. Les objectifs sont :

1. Supprimer toute référence à DEF OI / DEF Océan Indien et appliquer le branding ATEXIA (bleu + rouge)
2. Recentrer la veille sur **La Réunion (974)** uniquement — suppression des sources Mayotte
3. Étendre les mots-clés aux secteurs d'ATEXIA (courants forts, IRVE, photovoltaïque, énergie, etc.)
4. Ajouter les agrégateurs du document Word "agregateur sites publics.docx" comme sources manuelles
5. Packager l'application en **EXE autonome Windows** (PyInstaller) ne nécessitant ni Python ni Node.js sur le poste cible

---

## 2. Périmètre géographique

### Supprimé (Mayotte uniquement)
- `source_registry.py` : retirer les entrées suivantes
  - Centre Hospitalier de Mayotte (`scraper_chm`)
  - Département de Mayotte — Marchés
  - CADEMA — Marchés publics
  - ARMP Madagascar
  - CPB Mauritius

### Conservé
- Toutes les sources La Réunion existantes (BOAMP filtré 974, DECP, TED, Nukema, dept974, VAAO, marcheonline, marchessecurises, marchespublicsinfo, instao, permis, presse)
- Toutes les sources manuelles locales (Région Réunion, CINOR, TCO, CHU Réunion, PLACE, France Marchés, Achatpublic.com, Dematis, Deepbloo, DG Market, etc.)
- Toutes les sources internationales (AFD, Banque Mondiale, UNGM, TED Europe, IsDB, TendersGo, IFC, AIIB, COI)

### Filtre géographique dans `filters.py`
Remplacer `"974" or "976" or "réunion" or "mayotte"` par `"974" or "réunion"` dans la logique `classify_relevance`.

---

## 3. Sources à ajouter (agrégateurs Word)

### Catégorie Freemium
| Nom | URL | Description |
|-----|-----|-------------|
| e-marchespublics.com | https://www.e-marchespublics.com | Un des plus importants en volume — couvre une part considérable des acheteurs de La Réunion |
| J360 | https://www.j360.info | Réseau social professionnel de la commande publique — veille cartographiée par mots-clés |
| Bidding Source | https://www.biddingsource.com | Plateforme internationale avec bonne déclinaison des flux français et ultra-marins |

*(marchesonline.com et BOAMP déjà présents)*

### Catégorie Premium / Expert
| Nom | URL | Description |
|-----|-----|-------------|
| Vecteur Plus | https://www.vecteurplus.com | Leader BTP et second œuvre technique — détecte marchés privés et publics |
| Libel | https://www.libel.fr | Centralisation exhaustive web + presse locale — IA pour analyser les DCE |
| Explore | https://www.explore.fr | Cartographie projets immobiliers et d'aménagement avant la sortie officielle AO |
| DoubleTrade | https://www.doubletrade.com | Business Intelligence marchés publics et privés — excellents filtres de tri |
| Wanao | https://www.wanao.com | Veille automatique avec segmentation sectorielle très fine |
| Klekoon | https://www.klekoon.com | Veille payante + plateforme d'envoi de candidatures sécurisées |
| MPF — Marchés Publics France | https://www.mpfrance.fr | Plateforme EASY — alertes dédoublonnées avec analyse rapide du DCE |
| Centrale des Marchés | https://www.centraledesmarches.com | Détection et envoi ciblé d'opportunités d'affaires publiques |
| First AO | https://www.firstao-appel-offre.fr | Prospection commerciale via la commande publique |
| TendersPage | https://www.tenderspage.com | Un des plus grands moteurs de recherche mondiaux — couverture outre-mer |

Toutes ces sources sont ajoutées en `is_manual=True` dans `source_registry.py`.

---

## 4. Mots-clés ATEXIA — `filters.py`

### Familles à ajouter à `INCLUSION_KEYWORDS`

#### Courants forts / génie électrique
```
courants forts, génie électrique, installation électrique, travaux électriques,
TGBT, tableau général basse tension, armoire électrique, distribution basse tension,
coffret électrique, disjoncteur, tableau divisionnaire
```

#### Continuité d'énergie
```
groupe électrogène, onduleur, UPS, continuité d'énergie, alimentation sans interruption,
ASI, secours électrique
```

#### Éclairage
```
relamping, éclairage intérieur, éclairage LED, LED, mise aux normes électriques,
NF C 15-100, éclairage de sécurité, balisage lumineux, éclairage de balisage
```

#### IRVE (bornes de recharge)
```
IRVE, borne de recharge, bornes de recharge, recharge véhicule électrique,
infrastructure de recharge, point de charge, station de recharge
```

#### Énergie renouvelable / photovoltaïque
```
photovoltaïque, panneaux solaires, centrale solaire, autoconsommation,
stockage énergie, batterie solaire, ombrière photovoltaïque, ENR
```

#### Efficacité énergétique / réglementaire
```
décret tertiaire, OPERAT, performance énergétique, audit énergétique,
bilan énergétique, rénovation énergétique, efficacité énergétique, CEE
```

#### Réseau / infrastructures numériques
```
fibre optique, réseau informatique, baie informatique, réseau local, LAN,
câblage réseau, infrastructure réseau
```

#### Acteurs locaux La Réunion (ajout dans `classify_relevance`)
```
SHLMR, SIDR, SEMADER, SEDRE, CHU Réunion, CHOR, Cinor, TCO, Civis, Cirest
```

### Suppression du filtre `976` / `mayotte` dans la logique de scoring géographique

---

## 5. Branding ATEXIA

### Fichiers backend à modifier
- `backend/main.py` : titre de l'app FastAPI (`"DEF OI Veille"` → `"ATEXIA Veille"`)
- `email_digest.py` : expéditeur, objet des emails
- `source_registry.py` : User-Agent `"DEF-OI-Monitor/1.0"` → `"ATEXIA-Monitor/1.0"`
- `health_check.py` : références au nom

### Fichiers frontend à modifier
- `frontend/src/components/Sidebar.jsx` ou équivalent : logo, nom affiché
- `frontend/src/pages/Guide.jsx` : contenu de la page guide
- `frontend/index.html` : `<title>` de la page
- `frontend/src/utils/theme.js` : couleurs Ocean Deep → palette ATEXIA
- `frontend/package.json` : `name` du projet

### Palette ATEXIA
```css
--atexia-blue:    #003087    /* Bleu marine ATEXIA */
--atexia-red:     #E30613    /* Rouge ATEXIA */
--atexia-blue-light: #0057B8 /* Bleu secondaire */
--atexia-gray:    #F4F5F7    /* Fond clair */
```
Remplace le thème "Ocean Deep" (teal/cyan) actuel.

---

## 6. Architecture EXE autonome (PyInstaller)

### Prérequis de build (une seule fois, sur une machine avec Python + Node.js)
```powershell
# 1. Build frontend
cd frontend && npm run build  # produit frontend/dist/

# 2. Build exe
pip install pyinstaller
python build_exe.py           # script à créer
```

### Script `build_exe.py`
- Spécification PyInstaller : `--onefile` ou `--onedir` (onedir recommandé pour performances)
- Inclut `frontend/dist/` comme datas
- Inclut tous les scrapers et modules Python
- Exclut playwright Chromium du bundle (téléchargement automatique au 1er lancement)

### Fichier `atexia_launcher.py` (point d'entrée)
```python
# Lance uvicorn + ouvre le navigateur
import uvicorn, webbrowser, threading, time

def open_browser():
    time.sleep(2)
    webbrowser.open("http://localhost:8000")

threading.Thread(target=open_browser, daemon=True).start()
uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
```

### Stockage des données
- Base SQLite : `%APPDATA%\ATEXIA\atexia_veille.db` (persiste entre les mises à jour)
- Playwright Chromium : `%APPDATA%\ATEXIA\chromium\`
- `.env` : `%APPDATA%\ATEXIA\.env`

### Résultat
- `dist/atexia_veille/` (dossier) ou `dist/atexia_veille.exe` (fichier unique)
- Taille : ~150-200 Mo (sans Chromium embarqué)
- Chromium téléchargé au 1er lancement : ~130 Mo supplémentaires dans `%APPDATA%`

---

## 7. Fichiers impactés

| Fichier | Type de modification |
|---------|---------------------|
| `filters.py` | Refonte complète INCLUSION_KEYWORDS + suppression 976/Mayotte |
| `source_registry.py` | Suppression sources Mayotte + ajout agrégateurs Word |
| `backend/main.py` | Branding + chemin DB APPDATA |
| `database.py` | Chemin DB → APPDATA |
| `email_digest.py` | Branding expéditeur |
| `health_check.py` | Branding User-Agent |
| `frontend/index.html` | Titre page |
| `frontend/src/utils/theme.js` | Palette couleurs ATEXIA |
| `frontend/src/components/Sidebar.jsx` | Logo + nom ATEXIA |
| `frontend/src/pages/Guide.jsx` | Contenu guide ATEXIA |
| `frontend/package.json` | Nom projet |
| `atexia_launcher.py` | Nouveau — point d'entrée EXE |
| `build_exe.py` | Nouveau — script PyInstaller |
| `build_exe.ps1` | Nouveau — script PowerShell de build complet |

---

## 8. Ce qui ne change pas

- Architecture backend FastAPI + SQLite + SQLAlchemy
- Tous les scrapers existants (hors scraper_chm supprimé)
- Logique LLM Mistral, scoring adaptatif
- Interface utilisateur (structure, composants, pages)
- Tests pytest et Vitest
- Pipeline collect → analyze → export

---

## 9. Ordre d'implémentation recommandé

1. `filters.py` — nouveaux mots-clés ATEXIA + suppression Mayotte
2. `source_registry.py` — suppression sources Mayotte + ajout agrégateurs
3. Branding backend (`main.py`, `email_digest.py`, `health_check.py`, `source_registry.py`)
4. Branding frontend (`theme.js`, `index.html`, `Sidebar.jsx`, `Guide.jsx`, `package.json`)
5. Chemin DB `%APPDATA%\ATEXIA\` dans `database.py` + `main.py`
6. `atexia_launcher.py` + `build_exe.py` + `build_exe.ps1`
7. Build de test + vérification
