# Validation des sources avant apparition dans la sidebar — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Les sources n'apparaissent dans la sidebar de collecte que si elles ont passé un test de connexion (Playwright pour les sources avec identifiants, HTTP ping pour les sources publiques).

**Architecture:** Nouveau champ `is_validated` sur le modèle `Source` persisté en base via migration `ALTER TABLE`. Le test de connexion existant dans `pages/parametres.py` appelle un helper `validate_source()` après succès. Une nouvelle section "📡 Sources automatiques" dans Paramètres lance un HTTP ping pour les sources sans identifiant. La sidebar filtre sur `s.enabled AND s.is_validated`.

**Tech Stack:** SQLAlchemy · Streamlit · requests · SQLite (ALTER TABLE migration pattern déjà en place dans `database.py`)

---

## Fichiers impactés

| Fichier | Changement |
|---|---|
| `source_registry.py` | Colonne `is_validated` sur `Source` + fonction `validate_source()` |
| `database.py` | Migration `ALTER TABLE sources ADD COLUMN is_validated` |
| `tests/test_source_registry.py` | Tests pour `validate_source()` + valeur par défaut |
| `app.py` | Filtre sidebar (`and s.is_validated`) + badge dans "Gérer les sources" |
| `pages/parametres.py` | Chargement sources en DB + badges expanders + callback Playwright + section HTTP ping |

---

## Task 1 — Champ `is_validated` + `validate_source()` dans `source_registry.py`

**Files:**
- Modify: `source_registry.py:14-18` (classe `Source`, après `display_order`)
- Modify: `source_registry.py:160-169` (après `toggle_enabled`)
- Test: `tests/test_source_registry.py`

- [ ] **Étape 1 : Écrire les tests qui échouent**

Ajouter à la fin de `tests/test_source_registry.py` :

```python
def test_sources_default_not_validated(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    sources = list_sources(db)
    assert all(s.is_validated is False for s in sources)


def test_validate_source(db):
    from source_registry import init_sources, list_sources, validate_source
    init_sources(db)
    source = list_sources(db)[0]
    assert source.is_validated is False
    validate_source(db, source.id)
    db.refresh(source)
    assert source.is_validated is True


def test_validate_source_unknown_id_noop(db):
    from source_registry import validate_source
    validate_source(db, 99999)  # ne doit pas lever d'exception
```

- [ ] **Étape 2 : Lancer les tests pour confirmer qu'ils échouent**

```bash
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
python -m pytest tests/test_source_registry.py::test_sources_default_not_validated tests/test_source_registry.py::test_validate_source tests/test_source_registry.py::test_validate_source_unknown_id_noop -v
```

Attendu : `FAILED` — `AttributeError: type object 'Source' has no attribute 'is_validated'`

- [ ] **Étape 3 : Ajouter `is_validated` à la classe `Source`**

Dans `source_registry.py`, remplacer la ligne `display_order` par :

```python
    display_order = Column(Integer, default=99)
    is_validated = Column(Boolean, default=False)
```

- [ ] **Étape 4 : Ajouter la fonction `validate_source()`**

Dans `source_registry.py`, ajouter après `toggle_enabled` (ligne ~169) :

```python
def validate_source(db, source_id: int) -> None:
    """Marque une source comme validée (test de connexion réussi)."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if s:
        s.is_validated = True
        db.commit()
```

- [ ] **Étape 5 : Lancer les tests et vérifier qu'ils passent**

```bash
python -m pytest tests/test_source_registry.py -v
```

Attendu : tous les tests PASS (anciens + nouveaux).

- [ ] **Étape 6 : Commit**

```bash
git add source_registry.py tests/test_source_registry.py
git commit -m "feat: champ is_validated + validate_source() sur Source"
```

---

## Task 2 — Migration `database.py`

**Files:**
- Modify: `database.py:19-33`

- [ ] **Étape 1 : Ajouter la migration `is_validated` sur la table `sources`**

Dans `database.py`, le bloc `with engine.connect() as conn:` existant gère la table `tenders`. Ajouter un bloc identique juste après pour la table `sources` :

```python
    # Migration colonne sources
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE sources ADD COLUMN is_validated BOOLEAN DEFAULT 0"))
            conn.commit()
        except OperationalError as e:
            if "already exists" not in str(e) and "duplicate column" not in str(e):
                raise
```

Le bloc complet de `init_db()` ressemble alors à :

```python
def init_db():
    from source_registry import Source, init_sources  # noqa

    Base.metadata.create_all(bind=engine)

    # Migrations table tenders
    with engine.connect() as conn:
        for col_name, col_def in [
            ("secteur", "VARCHAR"),
            ("type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
            ("amount", "INTEGER"),
            ("is_blacklisted", "BOOLEAN DEFAULT 0"),
            ("is_saved", "BOOLEAN DEFAULT 0"),
            ("notes", "TEXT"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE tenders ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except OperationalError as e:
                if "already exists" not in str(e) and "duplicate column" not in str(e):
                    raise

    # Migration table sources
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE sources ADD COLUMN is_validated BOOLEAN DEFAULT 0"))
            conn.commit()
        except OperationalError as e:
            if "already exists" not in str(e) and "duplicate column" not in str(e):
                raise

    db = SessionLocal()
    try:
        init_sources(db)
    finally:
        db.close()
```

- [ ] **Étape 2 : Vérifier que l'import fonctionne sans erreur**

```bash
python -c "from database import init_db; init_db(); print('OK')"
```

Attendu : `OK` (si la base existait déjà avec la colonne, l'OperationalError est silencieusement ignorée).

- [ ] **Étape 3 : Vérifier l'ensemble des tests source_registry**

```bash
python -m pytest tests/test_source_registry.py -v
```

Attendu : tous PASS.

- [ ] **Étape 4 : Commit**

```bash
git add database.py
git commit -m "feat: migration is_validated sur table sources"
```

---

## Task 3 — Filtre sidebar dans `app.py`

**Files:**
- Modify: `app.py:930`

- [ ] **Étape 1 : Modifier le filtre de la sidebar**

Dans `app.py`, repérer le bloc (environ ligne 930) :

```python
        cat_sources = [s for s in all_sources if s.category == cat and s.enabled]
```

Le remplacer par :

```python
        cat_sources = [s for s in all_sources if s.category == cat and s.enabled and s.is_validated]
```

- [ ] **Étape 2 : Vérifier manuellement**

Lancer l'app :
```bash
streamlit run app.py
```

Ouvrir la sidebar → aucune source ne doit apparaître dans les cases à cocher (toutes à `is_validated = False` si la base est existante et vient d'être migrée).

Si vous voulez tester l'affichage d'une source validée : dans un terminal Python, valider manuellement une source :
```python
from database import SessionLocal
from source_registry import list_sources, validate_source
db = SessionLocal()
s = list_sources(db)[0]
validate_source(db, s.id)
db.close()
```
Recharger l'app → cette source doit apparaître dans la sidebar.

- [ ] **Étape 3 : Commit**

```bash
git add app.py
git commit -m "feat: sidebar — filtre is_validated sur les sources"
```

---

## Task 4 — Badge ✅/⬜ dans l'expander "Gérer les sources" (`app.py`)

**Files:**
- Modify: `app.py:1677`

- [ ] **Étape 1 : Ajouter le badge dans la colonne nom**

Dans `app.py`, repérer le bloc (environ ligne 1676-1677) :

```python
        with col_name:
            st.markdown(f"**{s.name}**")
```

Le remplacer par :

```python
        with col_name:
            _valid_badge = "✅" if s.is_validated else "⬜"
            st.markdown(f"{_valid_badge} **{s.name}**")
```

- [ ] **Étape 2 : Vérifier visuellement**

Dans l'app, dérouler l'expander "⚙️ Gérer les sources de veille". Chaque source doit afficher ⬜ (non validée) ou ✅ (validée). La source validée manuellement à l'étape précédente doit afficher ✅.

- [ ] **Étape 3 : Commit**

```bash
git add app.py
git commit -m "feat: badge is_validated dans l'expander Gérer les sources"
```

---

## Task 5 — Chargement sources en DB + badges dans les expanders credentials (`pages/parametres.py`)

**Files:**
- Modify: `pages/parametres.py:102-111` (début de la section identifiants)

- [ ] **Étape 1 : Charger les sources par nom en début de section**

Dans `pages/parametres.py`, repérer le bloc (environ ligne 102-108) :

```python
st.markdown("---")
st.header("🔐 Identifiants des sources")
st.caption("Les mots de passe sont chiffrés en base de données. Les variables `.env` ont la priorité.")

configured = {c["site"]: c for c in CredentialManager.list_configured()}
```

Le remplacer par :

```python
st.markdown("---")
st.header("🔐 Identifiants des sources")
st.caption("Les mots de passe sont chiffrés en base de données. Les variables `.env` ont la priorité.")

configured = {c["site"]: c for c in CredentialManager.list_configured()}

from database import SessionLocal as _SL_cred
from source_registry import Source as _SrcCred

_SITE_TO_SOURCE_NAME = {
    "vaao":               "VAAO",
    "marcheonline":       "Marché Online",
    "dept974":            "Marchés Publics — Dép. 974",
    "nukema":             "Nukema",
    "marchespublicsinfo": "Marchés Public Info",
    "marches_securises":  "Marchés Sécurisés",
    "instao":             "Instao",
    "tendersgo":          "Tenders Go",
}

_db_cred = _SL_cred()
try:
    _sources_by_name = {s.name: s for s in _db_cred.query(_SrcCred).all()}
finally:
    _db_cred.close()
```

- [ ] **Étape 2 : Mettre à jour le titre de chaque expander**

Repérer la boucle (environ ligne 108) :

```python
for site_key, (site_label, category) in _SITE_LABELS.items():
    cred = configured.get(site_key)
    icon = "✅" if cred else "⬜"
    with st.expander(f"{icon} {site_label} — {category}"):
```

La remplacer par :

```python
for site_key, (site_label, category) in _SITE_LABELS.items():
    cred = configured.get(site_key)
    _src_obj = _sources_by_name.get(_SITE_TO_SOURCE_NAME.get(site_key, ""))
    _is_validated = _src_obj.is_validated if _src_obj else False
    if cred and _is_validated:
        icon = "✅"
    elif cred:
        icon = "🔌"
    else:
        icon = "⬜"
    with st.expander(f"{icon} {site_label} — {category}"):
```

- [ ] **Étape 3 : Vérifier visuellement**

Ouvrir Paramètres → Section "🔐 Identifiants des sources". Les expanders doivent afficher :
- `⬜` si aucun identifiant configuré
- `🔌` si identifiants configurés mais pas encore testés
- `✅` si identifiants configurés ET connexion validée

- [ ] **Étape 4 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat: badges is_validated dans les expanders credentials"
```

---

## Task 6 — Mise à jour du callback Playwright après succès (`pages/parametres.py`)

**Files:**
- Modify: `pages/parametres.py:191-192`

- [ ] **Étape 1 : Appeler `validate_source()` après un test Playwright réussi**

Repérer le bloc (environ ligne 191-192) :

```python
                                        if diag.get("ok"):
                                            st.success(f"✅ Connexion réussie — redirigé vers `{diag.get('url_finale', '—')}`")
```

Le remplacer par :

```python
                                        if diag.get("ok"):
                                            st.success(f"✅ Connexion réussie — redirigé vers `{diag.get('url_finale', '—')}`")
                                            _src_name = _SITE_TO_SOURCE_NAME.get(site_key)
                                            if _src_name:
                                                from database import SessionLocal as _SL2
                                                from source_registry import validate_source as _val_src
                                                _db_val = _SL2()
                                                try:
                                                    _src = _db_val.query(_SrcCred).filter(_SrcCred.name == _src_name).first()
                                                    if _src:
                                                        _val_src(_db_val, _src.id)
                                                finally:
                                                    _db_val.close()
                                            st.rerun()
```

- [ ] **Étape 2 : Tester le flux complet**

Dans Paramètres, pour une source avec identifiants (ex. Nukema ou Marchés Sécurisés) :
1. Saisir email + mot de passe valides
2. Cliquer "🔌 Tester la connexion"
3. Si connexion OK → le badge de l'expander passe à ✅, la page se recharge
4. Ouvrir l'app principale → cette source doit apparaître dans la sidebar

- [ ] **Étape 3 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat: validate_source() après test Playwright réussi"
```

---

## Task 7 — Section HTTP ping pour sources automatiques (`pages/parametres.py`)

**Files:**
- Modify: `pages/parametres.py:210` (juste avant la section "🔑 Sécurité")

- [ ] **Étape 1 : Ajouter la section "📡 Sources automatiques"**

Dans `pages/parametres.py`, repérer le commentaire (environ ligne 210) :

```python
# ── Section sécurité ──────────────────────────────────────────────────────────
st.markdown("---")
st.header("🔑 Sécurité")
```

Insérer le bloc suivant AVANT ce commentaire :

```python
# ── Section sources automatiques (HTTP ping) ──────────────────────────────────
st.markdown("---")
st.header("📡 Sources automatiques")
st.caption("Un test HTTP vérifie que chaque source est accessible. Valider une source la fait apparaître dans la sidebar de collecte.")

import requests as _req
from database import SessionLocal as _SL3
from source_registry import Source as _Src3, validate_source as _val3

_db_auto = _SL3()
try:
    _auto_sources = (
        _db_auto.query(_Src3)
        .filter(_Src3.is_manual == False)
        .order_by(_Src3.display_order, _Src3.name)
        .all()
    )
finally:
    _db_auto.close()

for _s in _auto_sources:
    _badge = "✅" if _s.is_validated else "⬜"
    _col_badge, _col_name, _col_btn = st.columns([1, 6, 2])
    with _col_badge:
        st.markdown(_badge)
    with _col_name:
        st.markdown(f"**{_s.name}**")
        st.caption(_s.url)
    with _col_btn:
        if st.button("🔌 Tester", key=f"ping_{_s.id}"):
            with st.spinner(f"Test {_s.name}…"):
                try:
                    _resp = _req.get(_s.url, timeout=8, allow_redirects=True)
                    if _resp.status_code < 400:
                        _db_v3 = _SL3()
                        try:
                            _val3(_db_v3, _s.id)
                        finally:
                            _db_v3.close()
                        st.success(f"✅ Accessible (HTTP {_resp.status_code})")
                        st.rerun()
                    else:
                        st.error(f"❌ HTTP {_resp.status_code}")
                except Exception as _exc:
                    st.error(f"❌ Inaccessible — {_exc}")

```

- [ ] **Étape 2 : Vérifier visuellement**

Ouvrir Paramètres → Section "📡 Sources automatiques". Chaque source auto doit apparaître avec son badge ✅/⬜, son URL en caption, et un bouton "🔌 Tester".

Cliquer "🔌 Tester" sur BOAMP → doit afficher `✅ Accessible (HTTP 200)` et recharger la page avec le badge ✅.

Vérifier dans la sidebar de l'app principale que BOAMP apparaît maintenant.

- [ ] **Étape 3 : Tester toutes les sources publiques**

Cliquer "🔌 Tester" pour chaque source. Sources attendues OK : BOAMP, DECP, TED, AFD, Banque Mondiale, UNGM, Permis, Presse IO, Banques Dev. Certaines peuvent échouer si elles sont derrière un WAF (status 403/429) — noter lesquelles pour suivi.

- [ ] **Étape 4 : Commit final**

```bash
git add pages/parametres.py
git commit -m "feat: section HTTP ping sources automatiques dans Paramètres"
```

---

## Vérification finale

- [ ] Lancer tous les tests :
  ```bash
  python -m pytest tests/test_source_registry.py -v
  ```
  Attendu : tous PASS.

- [ ] Vérifier le flux complet :
  1. Ouvrir l'app → sidebar vide (aucune source validée)
  2. Aller dans Paramètres → Section "📡 Sources automatiques"
  3. Tester BOAMP → ✅ → BOAMP apparaît dans la sidebar
  4. Pour une source avec identifiants (ex. Nukema) : saisir identifiants → Tester → ✅ → Nukema apparaît dans la sidebar
  5. Les sources non testées restent absentes de la sidebar
