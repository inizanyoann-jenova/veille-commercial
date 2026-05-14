# Design — Validation des sources avant apparition dans la sidebar

**Date :** 2026-05-14
**Projet :** DEF Océan Indien — Veille Marchés
**Périmètre :** `source_registry.py` · `database.py` · `pages/parametres.py` · `app.py`
**Problème résolu :** La sidebar affiche toutes les sources activées, même celles dont les identifiants n'ont jamais été testés. L'opérateur peut lancer une collecte sur une source inaccessible sans le savoir.
**Approche retenue :** Champ `is_validated` sur `Source` — une source n'apparaît dans la sidebar que si elle a passé un test de connexion (Playwright pour les sources avec identifiants, HTTP ping pour les sources publiques).

---

## Architecture cible

### Fichiers impactés

| Fichier | Changement |
|---|---|
| `source_registry.py` | Ajout `is_validated` sur `Source` + helper `validate_source()` |
| `database.py` | Migration `ALTER TABLE sources ADD COLUMN is_validated` |
| `pages/parametres.py` | Mise à jour `is_validated` après test Playwright réussi + nouvelle section HTTP ping |
| `app.py` | Filtre sidebar sur `is_validated` + badge dans l'expander "Gérer les sources" |

### Ce qui ne change pas

- La logique des scrapers — non touchée
- Le credential manager — non touché
- Les fiches marchés, analytics, pipeline — non touchés
- Le CSS existant — conservé

---

## Bloc 1 — Modèle de données (`source_registry.py`)

### Nouveau champ

```python
is_validated = Column(Boolean, default=False)
```

Ajouté dans la classe `Source`, après `display_order`.

### Nouvelle fonction helper

```python
def validate_source(db, source_id: int) -> None:
    """Marque une source comme validée (test de connexion réussi)."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if s:
        s.is_validated = True
        db.commit()
```

### Sources par défaut (`_DEFAULT_SOURCES`)

Aucun changement — elles démarrent toutes à `is_validated = False` (valeur par défaut du champ). L'opérateur valide chaque source depuis Paramètres.

---

## Bloc 2 — Migration (`database.py`)

Ajout dans le bloc `for col_name, col_def in [...]` de `init_db()` :

```python
# Table sources
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE sources ADD COLUMN is_validated BOOLEAN DEFAULT 0"))
        conn.commit()
    except OperationalError as e:
        if "already exists" not in str(e) and "duplicate column" not in str(e):
            raise
```

Ce bloc est idempotent — exécuté à chaque démarrage, ignoré si la colonne existe déjà.

---

## Bloc 3 — Paramètres (`pages/parametres.py`)

### 3a — Sources avec identifiants (Playwright)

Mapping local `site_key → source.name` :

```python
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
```

Après le bloc `if diag.get("ok"):` (test Playwright réussi), ajouter :

```python
# Marquer la source comme validée en base
_src_name = _SITE_TO_SOURCE_NAME.get(site_key)
if _src_name:
    from database import SessionLocal as _SL2
    from source_registry import Source as _Src, validate_source as _val_src
    _db_val = _SL2()
    try:
        _src = _db_val.query(_Src).filter(_Src.name == _src_name).first()
        if _src:
            _val_src(_db_val, _src.id)
    finally:
        _db_val.close()
    st.rerun()
```

Le badge dans l'expander reflète le statut : `✅ Connexion réussie` → la source apparaît désormais dans la sidebar.

### 3b — Sources automatiques (HTTP ping)

Nouvelle section dans `pages/parametres.py`, après la section "🔐 Identifiants des sources" :

```
st.markdown("---")
st.header("📡 Sources automatiques")
st.caption("Un test HTTP vérifie que chaque source est accessible. Les sources avec identifiants bénéficient également du test de connexion ci-dessus.")
```

Charger toutes les sources en DB au début de la section :
```python
from database import SessionLocal as _SL3
from source_registry import Source as _Src2, validate_source as _val2
_db_ping = _SL3()
try:
    _auto_sources = _db_ping.query(_Src2).filter(_Src2.is_manual == False).order_by(_Src2.display_order).all()
finally:
    _db_ping.close()
```

**Filtre : `not s.is_manual`** — toutes les sources avec un scraper automatique, y compris celles qui ont aussi des identifiants (VAAO, Nukema…). Pour ces dernières, le ping HTTP est un test minimal ; le test Playwright (section 3a) offre une validation plus complète.

Pour chaque source, afficher une ligne :

```
[badge ✅/⬜]  Nom de la source (url)    [🔌 Tester]
```

Au clic sur "🔌 Tester" :

```python
import requests as _req
_db_v2 = _SL3()
try:
    resp = _req.get(source.url, timeout=8, allow_redirects=True)
    if resp.status_code < 400:
        _val2(_db_v2, source.id)
        st.success(f"✅ {source.name} accessible (HTTP {resp.status_code})")
        st.rerun()
    else:
        st.error(f"❌ {source.name} — réponse HTTP {resp.status_code}")
except Exception as exc:
    st.error(f"❌ {source.name} inaccessible — {exc}")
finally:
    _db_v2.close()
```

### 3c — Titre des expanders de credentials

Charger les sources en DB en début de section pour accéder à `is_validated` :

```python
from database import SessionLocal as _SL_cred
from source_registry import Source as _SrcCred
_db_cred = _SL_cred()
try:
    _sources_by_name = {s.name: s for s in _db_cred.query(_SrcCred).all()}
finally:
    _db_cred.close()
```

Le titre de chaque expander reflète le statut de validation :

```python
_src_obj = _sources_by_name.get(_SITE_TO_SOURCE_NAME.get(site_key, ""))
_is_validated = _src_obj.is_validated if _src_obj else False
icon = "✅" if (cred and _is_validated) else ("🔌" if cred else "⬜")
```

- `✅` : identifiants configurés ET connexion testée
- `🔌` : identifiants configurés, pas encore testés
- `⬜` : pas d'identifiants

---

## Bloc 4 — Sidebar (`app.py`)

### Filtre de la sidebar

Ligne 930 (actuelle) :
```python
cat_sources = [s for s in all_sources if s.category == cat and s.enabled]
```

Devient :
```python
cat_sources = [s for s in all_sources if s.category == cat and s.enabled and s.is_validated]
```

Une seule ligne modifiée. Toute la logique d'affichage (checkboxes, boutons link) est inchangée.

### Badge dans l'expander "Gérer les sources"

Dans la liste affichée par `st.expander("⚙️ Gérer les sources de veille")`, le nom de la source est précédé d'un badge :

```python
valid_icon = "✅" if s.is_validated else "⬜"
st.markdown(f"{valid_icon} **{s.name}**")
```

Pas de bouton de validation ici — l'opérateur va dans Paramètres pour tester.

---

## Comportement complet

1. L'opérateur ajoute ou réinitialise les sources → toutes à `is_validated = False`
2. Il ouvre Paramètres :
   - Pour les sources avec identifiants : saisit email/mot de passe → "🔌 Tester la connexion" → si OK → `is_validated = True`
   - Pour les sources publiques : clique "🔌 Tester" → si HTTP < 400 → `is_validated = True`
3. La sidebar affiche uniquement les sources validées
4. L'expander "Gérer les sources" montre le badge ✅/⬜ pour identifier ce qui reste à tester

---

## Critères de succès

1. La sidebar n'affiche aucune source non validée
2. Un test Playwright réussi dans Paramètres → la source apparaît immédiatement dans la sidebar (après `st.rerun()`)
3. Un test HTTP réussi → même comportement
4. La migration `is_validated` est idempotente (démarrage sans erreur si colonne existe)
5. Les sources sans identifiant et sans test HTTP ne polluent pas la sidebar
