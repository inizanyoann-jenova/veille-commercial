# Nouvelles Sources OI + Distinction Auto/Manuel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter 11 nouvelles sources gratuites sans auth pour Réunion/Mayotte/Madagascar/Maurice, enrichir scraper_presse.py avec L'Éco Austral, et afficher une distinction visuelle automatique/manuel dans la page Paramètres.

**Architecture:** `scraper_presse.py` gère déjà tous les flux RSS OI via `feedparser` — on lui ajoute juste L'Éco Austral. Les nouveaux portails marchés publics (8) et banques de développement (3) sont ajoutés comme sources manuelles dans `_DEFAULT_SOURCES`. L'UI `parametres.py` est refactorisée pour sous-grouper auto vs manuel avec un bouton "Ouvrir" sur les manuelles.

**Tech Stack:** Python, SQLAlchemy, Streamlit, feedparser (déjà installé)

---

## Fichiers impactés

| Fichier | Changement |
|---|---|
| `scraper_presse.py` | Ajout de L'Éco Austral dans `FLUX_PRESSE` |
| `source_registry.py` | +11 entrées dans `_DEFAULT_SOURCES` |
| `pages/parametres.py` | Refactor boucle "Sources à collecter" (lignes 31–56) |
| `tests/test_source_registry.py` | +1 test vérifiant la présence des nouvelles sources |

---

## Task 1 — Ajouter L'Éco Austral dans scraper_presse.py

**Files:**
- Modify: `scraper_presse.py:20-41` (liste `FLUX_PRESSE`)
- Test: `tests/test_source_registry.py` (test existant passe toujours — pas de fichier test dédié ici)

- [ ] **Step 1 : Ouvrir `scraper_presse.py` et localiser `FLUX_PRESSE`**

  La liste commence ligne 20. Chaque entrée est un tuple `(territoire, nom, url_rss)`.

- [ ] **Step 2 : Ajouter L'Éco Austral à la fin du bloc `FLUX_PRESSE`**

  Remplacer la fin de `FLUX_PRESSE` (après `"Batiactu DOM"`, avant `]`) :

  ```python
      ("La Réunion", "Batiactu DOM",        "https://www.batiactu.com/rss/rss_actualites.xml"),
      ("OI",         "L'Éco Austral",        "https://www.ecoaustral.com/feed/"),
  ]
  ```

- [ ] **Step 3 : Vérifier que le scraper tourne sans erreur**

  ```
  python -c "from scraper_presse import fetch_presse_io; print('import OK')"
  ```

  Résultat attendu : `import OK`

- [ ] **Step 4 : Commit**

  ```bash
  git add scraper_presse.py
  git commit -m "feat: ajouter L'Éco Austral dans FLUX_PRESSE"
  ```

---

## Task 2 — Ajouter les sources manuelles marchés publics locaux

**Files:**
- Modify: `source_registry.py:95-109` (bloc `# ── Manuelles`)
- Test: `tests/test_source_registry.py`

- [ ] **Step 1 : Écrire le test en premier**

  Ajouter dans `tests/test_source_registry.py` à la fin du fichier :

  ```python
  def test_nouvelles_sources_oi_presentes():
      from sqlalchemy import create_engine
      from sqlalchemy.orm import sessionmaker
      from models import Base
      from source_registry import init_sources, list_sources
      engine = create_engine("sqlite:///:memory:")
      Base.metadata.create_all(engine)
      Session = sessionmaker(bind=engine)
      db = Session()
      init_sources(db)
      names = {s.name for s in list_sources(db)}
      expected = [
          "Région Réunion — Marchés publics",
          "CINOR — Marchés publics",
          "TCO — Marchés publics",
          "CHU Réunion — Marchés publics",
          "Département de Mayotte — Marchés",
          "CADEMA — Marchés publics",
          "ARMP Madagascar",
          "CPB Mauritius — Procurement",
          "IFC — Projets Afrique / OI",
          "AIIB — Projets approuvés",
          "COI — Commission Océan Indien",
      ]
      for name in expected:
          assert name in names, f"Source manquante : {name}"
      db.close()
  ```

- [ ] **Step 2 : Lancer le test pour vérifier qu'il échoue**

  ```
  pytest tests/test_source_registry.py::test_nouvelles_sources_oi_presentes -v
  ```

  Résultat attendu : `FAILED` — "Source manquante : Région Réunion — Marchés publics"

- [ ] **Step 3 : Ajouter les 8 sources marchés publics locaux dans `source_registry.py`**

  Dans `_DEFAULT_SOURCES`, après la ligne `{"name": "PLACE — Portail commandes publiques", ...}` (ligne ~97), insérer :

  ```python
      # ── Manuelles locales OI ──────────────────────────────────────────────────
      {"name": "Région Réunion — Marchés publics",
       "url": "https://regionreunion.com/region/marches-publics",
       "category": "Public", "is_manual": True, "display_order": 31},
      {"name": "CINOR — Marchés publics",
       "url": "https://www.cinor.re/marches-publics",
       "category": "Public", "is_manual": True, "display_order": 32},
      {"name": "TCO — Marchés publics",
       "url": "https://www.tco.re/commande-publique",
       "category": "Public", "is_manual": True, "display_order": 33},
      {"name": "CHU Réunion — Marchés publics",
       "url": "https://www.chu-reunion.fr/appels-offres",
       "category": "Public", "is_manual": True, "display_order": 34},
      {"name": "Département de Mayotte — Marchés",
       "url": "https://www.departement976.fr/appels-d-offres",
       "category": "Public", "is_manual": True, "display_order": 35},
      {"name": "CADEMA — Marchés publics",
       "url": "https://www.cadema.yt/appels-d-offres",
       "category": "Public", "is_manual": True, "display_order": 36},
      {"name": "ARMP Madagascar",
       "url": "https://www.armp.mg/appels-offres",
       "category": "International", "is_manual": True, "display_order": 26},
      {"name": "CPB Mauritius — Procurement",
       "url": "https://procurement.govmu.org",
       "category": "International", "is_manual": True, "display_order": 27},
  ```

- [ ] **Step 4 : Lancer le test (échouera encore — IFC/AIIB/COI manquants)**

  ```
  pytest tests/test_source_registry.py::test_nouvelles_sources_oi_presentes -v
  ```

  Résultat attendu : `FAILED` — "Source manquante : IFC — Projets Afrique / OI"

---

## Task 3 — Ajouter les 3 sources banques de développement

**Files:**
- Modify: `source_registry.py` (même `_DEFAULT_SOURCES`)
- Test: `tests/test_source_registry.py::test_nouvelles_sources_oi_presentes`

- [ ] **Step 1 : Ajouter les 3 sources banques dans `source_registry.py`**

  Dans `_DEFAULT_SOURCES`, après `{"name": "DG Market", ...}` (dernière entrée), ajouter :

  ```python
      # ── Banques de développement — OI ────────────────────────────────────────
      {"name": "IFC — Projets Afrique / OI",
       "url": "https://projects.ifc.org",
       "category": "International", "is_manual": True, "display_order": 52},
      {"name": "AIIB — Projets approuvés",
       "url": "https://www.aiib.org/en/projects/approved/index.html",
       "category": "International", "is_manual": True, "display_order": 53},
      {"name": "COI — Commission Océan Indien",
       "url": "https://www.commissionoceanindien.org/appels-doffres/",
       "category": "International", "is_manual": True, "display_order": 54},
  ```

- [ ] **Step 2 : Lancer le test — il doit passer**

  ```
  pytest tests/test_source_registry.py::test_nouvelles_sources_oi_presentes -v
  ```

  Résultat attendu : `PASSED`

- [ ] **Step 3 : Lancer toute la suite test_source_registry**

  ```
  pytest tests/test_source_registry.py -v
  ```

  Résultat attendu : tous les tests passent (notamment `test_init_sources_populates_table` — il vérifie `len(sources) == len(_DEFAULT_SOURCES)`, ce qui est toujours vrai).

- [ ] **Step 4 : Commit**

  ```bash
  git add source_registry.py tests/test_source_registry.py
  git commit -m "feat: ajouter 11 sources OI gratuites (marchés locaux + banques dev)"
  ```

---

## Task 4 — Refactorer l'UI parametres.py : distinction auto / manuel

**Files:**
- Modify: `pages/parametres.py:31-56` (boucle "Sources à collecter")

- [ ] **Step 1 : Remplacer le bloc d'affichage des sources (lignes 31–56)**

  Remplacer ce bloc entier :

  ```python
  _CAT_ICONS = {"Public": "📋 Public", "Privé": "🏗️ Privé", "International": "🌍 International"}
  for _cat in ["Public", "Privé", "International"]:
      _cat_src = [s for s in _all_sources_p if s.category == _cat]
      if not _cat_src:
          continue
      st.subheader(_CAT_ICONS[_cat])
      for _s in _cat_src:
          _col_toggle, _col_label = st.columns([1, 9])
          with _col_toggle:
              _new_enabled = st.toggle(
                  "Activée",
                  value=bool(_s.enabled),
                  key=f"src_enabled_{_s.id}",
                  label_visibility="collapsed",
              )
          with _col_label:
              _status_icon = "✅" if _s.is_validated else ("📋" if _s.is_manual else "⚠️")
              st.markdown(f"{_status_icon} **{_s.name}**")
          if _new_enabled != bool(_s.enabled):
              _db_tog = _SL_src()
              try:
                  _toggle_enabled(_db_tog, _s.id)
              finally:
                  _db_tog.close()
              _action = "activée" if _new_enabled else "désactivée"
              st.toast(f"Source '{_s.name}' {_action} ✓")
              st.rerun()  # obligatoire — _s est stale après toggle
  ```

  Par ce nouveau bloc :

  ```python
  _CAT_ICONS = {"Public": "📋 Public", "Privé": "🏗️ Privé", "International": "🌍 International"}

  def _render_source_row(s):
      """Affiche une ligne source avec toggle. Retourne True si toggle modifié."""
      is_manual = bool(s.is_manual)
      if is_manual:
          _col_toggle, _col_label, _col_open = st.columns([1, 7, 2])
      else:
          _col_toggle, _col_label = st.columns([1, 9])
      with _col_toggle:
          new_enabled = st.toggle(
              "Activée",
              value=bool(s.enabled),
              key=f"src_enabled_{s.id}",
              label_visibility="collapsed",
          )
      with _col_label:
          if is_manual:
              st.markdown(f"📋 **{s.name}**")
          else:
              _icon = "✅" if s.is_validated else "⚠️"
              st.markdown(f"{_icon} **{s.name}**")
      if is_manual:
          with _col_open:
              st.link_button("🔗 Ouvrir", url=s.url)
      if new_enabled != bool(s.enabled):
          _db_tog = _SL_src()
          try:
              _toggle_enabled(_db_tog, s.id)
          finally:
              _db_tog.close()
          _action = "activée" if new_enabled else "désactivée"
          st.toast(f"Source '{s.name}' {_action} ✓")
          st.rerun()

  for _cat in ["Public", "Privé", "International"]:
      _cat_src = [s for s in _all_sources_p if s.category == _cat]
      if not _cat_src:
          continue
      st.subheader(_CAT_ICONS[_cat])

      _auto_src = [s for s in _cat_src if not s.is_manual]
      _manual_src = [s for s in _cat_src if s.is_manual]

      if _auto_src:
          st.markdown("**🤖 Automatiques**")
          st.caption("Collecte déclenchée via le pipeline — aucune action requise")
          for _s in _auto_src:
              _render_source_row(_s)

      if _manual_src:
          if _auto_src:
              st.markdown("")
          st.markdown("**👆 Manuelles** *(consultation guidée)*")
          st.caption("À consulter manuellement — cliquez Ouvrir pour accéder au site")
          for _s in _manual_src:
              _render_source_row(_s)
  ```

- [ ] **Step 2 : Vérifier que l'application démarre sans erreur**

  ```
  python -c "import ast, sys; ast.parse(open('pages/parametres.py').read()); print('Syntaxe OK')"
  ```

  Résultat attendu : `Syntaxe OK`

- [ ] **Step 3 : Lancer l'application et vérifier visuellement**

  ```
  streamlit run app.py
  ```

  Aller sur la page "Paramètres" → section "Sources à collecter". Vérifier :
  - Chaque catégorie a une sous-section "🤖 Automatiques" et "👆 Manuelles"
  - Les sources manuelles ont un bouton "🔗 Ouvrir" cliquable
  - Les sources automatiques montrent ✅ ou ⚠️ selon `is_validated`
  - Les toggles fonctionnent (activer/désactiver affiche un toast)

- [ ] **Step 4 : Commit**

  ```bash
  git add pages/parametres.py
  git commit -m "feat: distinction visuelle auto/manuel dans Sources à collecter"
  ```

---

## Task 5 — Vérification finale

- [ ] **Step 1 : Lancer toute la suite de tests**

  ```
  pytest tests/ -v --tb=short
  ```

  Résultat attendu : tous les tests passent (ou échecs identiques à avant ces changements).

- [ ] **Step 2 : Vérifier que `init_sources` ajoute bien les nouvelles sources**

  ```python
  python -c "
  from sqlalchemy import create_engine
  from sqlalchemy.orm import sessionmaker
  from models import Base
  from source_registry import init_sources, list_sources
  engine = create_engine('sqlite:///:memory:')
  Base.metadata.create_all(engine)
  db = sessionmaker(bind=engine)()
  init_sources(db)
  manual = [s for s in list_sources(db) if s.is_manual]
  print(f'{len(manual)} sources manuelles :')
  for s in manual: print(f'  [{s.category}] {s.name}')
  "
  ```

  Résultat attendu : 17 sources manuelles listées incluant "Région Réunion — Marchés publics", "ARMP Madagascar", "IFC — Projets Afrique / OI", etc.

- [ ] **Step 3 : Commit final si non-déjà commité**

  ```bash
  git add -p
  git commit -m "chore: vérification finale nouvelles sources OI"
  ```

---

## Note sur les URLs

Les URLs des portails marchés publics locaux sont à vérifier manuellement après déploiement — les collectivités déplacent souvent leurs pages marchés. Utiliser le bouton "🔗 Ouvrir" pour tester chaque lien et corriger dans `source_registry.py` si nécessaire. Les URLs de référence à vérifier en priorité :

| Source | URL à vérifier |
|---|---|
| Région Réunion | https://regionreunion.com/region/marches-publics |
| CINOR | https://www.cinor.re/marches-publics |
| TCO | https://www.tco.re/commande-publique |
| CADEMA | https://www.cadema.yt |
| Département 976 | https://www.departement976.fr |
| ARMP Madagascar | https://www.armp.mg |
