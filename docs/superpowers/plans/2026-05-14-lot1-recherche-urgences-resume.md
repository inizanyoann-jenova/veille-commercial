# Lot 1 — Recherche + Urgences + Résumé collecte : Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter une recherche plein texte, un filtre délais urgents et un résumé de collecte enrichi dans l'app de veille marchés.

**Architecture:** Trois modifications indépendantes dans `app.py` uniquement — deux nouveaux widgets sidebar + leurs filtres post-chargement, et remplacement du message de fin de collecte.

**Tech Stack:** Streamlit, Python 3.11+, SQLAlchemy, pytest

---

## Fichiers modifiés

- Modify: `app.py` — sidebar (widgets), filtrage rows_pub/rows_priv, `_collect_selected_sources`
- Modify: `tests/test_filters.py` — tests pour la logique de filtrage

---

### Task 1 : Recherche plein texte

**Files:**
- Modify: `app.py:966-985` (sidebar — widget search_query)
- Modify: `app.py:1418-1447` (filtrage rows_pub et rows_priv)
- Modify: `tests/test_filters.py`

- [ ] **Step 1 : Écrire les tests de filtrage**

Ouvrir `tests/test_filters.py` et ajouter à la fin :

```python
# ── Tests recherche plein texte ───────────────────────────────────────────────

def _make_row(titre: str, source: str = "") -> dict:
    return {"Titre": titre, "Source": source, "Date Limite": "—", "Go/No-Go": "🟢 GO"}


def test_search_query_titre():
    rows = [_make_row("Maintenance SSI CHU"), _make_row("Vidéosurveillance port")]
    q = "ssi"
    result = [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 1
    assert result[0]["Titre"] == "Maintenance SSI CHU"


def test_search_query_source():
    rows = [_make_row("Marché 1", source="boamp.fr"), _make_row("Marché 2", source="ted.europa.eu")]
    q = "boamp"
    result = [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 1


def test_search_query_empty_returns_all():
    rows = [_make_row("A"), _make_row("B")]
    q = ""
    result = rows if not q else [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 2


def test_search_query_case_insensitive():
    rows = [_make_row("Alarme INCENDIE")]
    q = "incendie"
    result = [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 1
```

- [ ] **Step 2 : Vérifier que les tests passent déjà (ils ne testent que la logique Python)**

```bash
cd "c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI"
python -m pytest tests/test_filters.py -v -k "search_query"
```

Expected: 4 tests PASS (logique pure Python, pas de dépendance Streamlit)

- [ ] **Step 3 : Ajouter le widget `search_query` dans la sidebar**

Dans `app.py`, trouver le bloc `with st.sidebar:` (ligne ~966). Juste après `st.markdown("---")` (la ligne de séparation après "Veille Marchés Publics") et **avant** `_now = datetime.now()`, insérer :

```python
    search_query = st.text_input("🔍 Rechercher", placeholder="Titre, source…", key="search_query")
```

Le bloc doit ressembler à :
```python
with st.sidebar:
    st.markdown("## 🔥 DEF Océan Indien")
    st.markdown("**Veille Marchés Publics**")
    st.markdown("---")

    search_query = st.text_input("🔍 Rechercher", placeholder="Titre, source…", key="search_query")

    _now = datetime.now()
    ...
```

- [ ] **Step 4 : Appliquer le filtre sur rows_pub et rows_priv**

Trouver le bloc de filtrage rows_pub (ligne ~1418) :
```python
rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public", only_recent=only_recent)
if terr_actifs:
    rows_pub = [r for r in rows_pub if any(terr in r["Territoire"] for terr in terr_actifs)]
```

Insérer le filtre search_query **juste après** `rows_pub = load_tenders(...)` et **avant** le filtre `terr_actifs` :

```python
rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_pub = [r for r in rows_pub if _sq in r["Titre"].lower() or _sq in r["Source"].lower()]
if terr_actifs:
    rows_pub = [r for r in rows_pub if any(terr in r["Territoire"] for terr in terr_actifs)]
```

Faire de même pour rows_priv (ligne ~1441) :

```python
rows_priv = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Privé", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_priv = [r for r in rows_priv if _sq in r["Titre"].lower() or _sq in r["Source"].lower()]
if terr_actifs:
    rows_priv = [r for r in rows_priv if any(terr in r["Territoire"] for terr in terr_actifs)]
```

- [ ] **Step 5 : Vérifier manuellement**

```bash
streamlit run app.py
```

- Taper "SSI" dans la barre de recherche → seuls les marchés contenant "SSI" dans le titre ou la source restent
- Vider la recherche → tous les marchés réapparaissent
- Combiner avec un filtre territoire → les deux filtres s'appliquent ensemble

- [ ] **Step 6 : Commit**

```bash
git add app.py tests/test_filters.py
git commit -m "feat: recherche plein texte sidebar"
```

---

### Task 2 : Vue urgences délais courts

**Files:**
- Modify: `app.py:1005-1006` (sidebar — widget urgent_only)
- Modify: `app.py:1418-1447` (filtrage rows_pub et rows_priv)
- Modify: `tests/test_filters.py`

- [ ] **Step 1 : Écrire les tests de filtrage urgences**

Ajouter à la fin de `tests/test_filters.py` :

```python
# ── Tests filtre urgences ─────────────────────────────────────────────────────

from datetime import datetime, timedelta


def _urgent_row(days_remaining: int) -> dict:
    d = (datetime.now() + timedelta(days=days_remaining)).strftime("%d/%m/%Y")
    return {"Titre": "Test", "Source": "", "Date Limite": d, "Go/No-Go": "🟢 GO"}


def _is_urgent(r: dict) -> bool:
    dl = r["Date Limite"]
    if dl == "—":
        return False
    try:
        d = datetime.strptime(dl, "%d/%m/%Y").date()
        return (d - datetime.now().date()).days <= 14
    except ValueError:
        return False


def test_urgent_within_14_days():
    row = _urgent_row(7)
    assert _is_urgent(row) is True


def test_urgent_exactly_14_days():
    row = _urgent_row(14)
    assert _is_urgent(row) is True


def test_urgent_15_days_not_urgent():
    row = _urgent_row(15)
    assert _is_urgent(row) is False


def test_urgent_overdue_is_urgent():
    row = _urgent_row(-3)
    assert _is_urgent(row) is True


def test_urgent_no_deadline_not_urgent():
    row = {"Titre": "Test", "Source": "", "Date Limite": "—", "Go/No-Go": "🟢 GO"}
    assert _is_urgent(row) is False
```

- [ ] **Step 2 : Vérifier que les tests passent**

```bash
python -m pytest tests/test_filters.py -v -k "urgent"
```

Expected: 5 tests PASS

- [ ] **Step 3 : Ajouter le widget `urgent_only` dans la sidebar**

Dans `app.py`, trouver :
```python
    maintenance_only = st.checkbox("Maintenance uniquement")
    only_recent = st.checkbox("🆕 Nouveaux (24h)")
```

Ajouter `urgent_only` juste après `only_recent` :

```python
    maintenance_only = st.checkbox("Maintenance uniquement")
    only_recent = st.checkbox("🆕 Nouveaux (24h)")
    urgent_only = st.checkbox("🚨 Délais < 14 jours")
```

- [ ] **Step 4 : Appliquer le filtre urgent_only sur rows_pub et rows_priv**

Dans le bloc de filtrage rows_pub, après le filtre `search_query` et avant `terr_actifs`, ajouter :

```python
if urgent_only:
    def _is_urgent(r: dict) -> bool:
        dl = r["Date Limite"]
        if dl == "—":
            return False
        try:
            d = datetime.strptime(dl, "%d/%m/%Y").date()
            return (d - datetime.now().date()).days <= 14
        except ValueError:
            return False
    rows_pub = [r for r in rows_pub if _is_urgent(r)]
```

Pour rows_priv, réutiliser `_is_urgent` (défini ci-dessus dans le même scope) :

```python
if urgent_only:
    rows_priv = [r for r in rows_priv if _is_urgent(r)]
```

Le bloc complet autour de rows_pub doit ressembler à :

```python
rows_pub = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Public", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_pub = [r for r in rows_pub if _sq in r["Titre"].lower() or _sq in r["Source"].lower()]
if urgent_only:
    def _is_urgent(r: dict) -> bool:
        dl = r["Date Limite"]
        if dl == "—":
            return False
        try:
            d = datetime.strptime(dl, "%d/%m/%Y").date()
            return (d - datetime.now().date()).days <= 14
        except ValueError:
            return False
    rows_pub = [r for r in rows_pub if _is_urgent(r)]
if terr_actifs:
    rows_pub = [r for r in rows_pub if any(terr in r["Territoire"] for terr in terr_actifs)]
if selected_domaines:
    rows_pub = [r for r in rows_pub if any(d in r["Domaine"] for d in selected_domaines)]
if selected_decisions:
    rows_pub = [r for r in rows_pub if r["Go/No-Go"] in selected_decisions]
```

Et pour rows_priv (après son bloc `if search_query`) :

```python
rows_priv = load_tenders(selected_status, maintenance_only, date_from, strict_date, secteur="Privé", only_recent=only_recent)
if search_query:
    _sq = search_query.lower()
    rows_priv = [r for r in rows_priv if _sq in r["Titre"].lower() or _sq in r["Source"].lower()]
if urgent_only:
    rows_priv = [r for r in rows_priv if _is_urgent(r)]
if terr_actifs:
    rows_priv = [r for r in rows_priv if any(terr in r["Territoire"] for terr in terr_actifs)]
if selected_domaines:
    rows_priv = [r for r in rows_priv if any(d in r["Domaine"] for d in selected_domaines)]
if selected_decisions:
    rows_priv = [r for r in rows_priv if r["Go/No-Go"] in selected_decisions]
```

- [ ] **Step 5 : Vérifier manuellement**

```bash
streamlit run app.py
```

- Cocher "🚨 Délais < 14 jours" → seuls les marchés avec deadline dans moins de 14 jours (ou dépassée) restent
- Si aucun marché urgent : le tableau affiche "Aucun résultat."
- Combiner avec la recherche plein texte → les deux filtres s'appliquent ensemble

- [ ] **Step 6 : Commit**

```bash
git add app.py tests/test_filters.py
git commit -m "feat: filtre urgences délais < 14 jours"
```

---

### Task 3 : Résumé de collecte enrichi

**Files:**
- Modify: `app.py:856-872` (fin de `_collect_selected_sources`)

Pas de test automatisé pour cette tâche — la logique dépend de `Tender` SQLAlchemy et du `st.session_state`, qui nécessitent un environnement Streamlit pour être testés. La vérification est manuelle.

- [ ] **Step 1 : Remplacer le bloc final de `_collect_selected_sources`**

Trouver dans `_collect_selected_sources` (ligne ~867) :

```python
    if total:
        st.success(f"{total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée pour les sources sélectionnées.")
    for err in errors:
        st.warning(err)
```

Remplacer par :

```python
    if total and st.session_state.get("new_tender_ids"):
        _db_res = new_db()
        try:
            _new_tenders = _db_res.query(Tender).filter(
                Tender.id.in_(st.session_state["new_tender_ids"])
            ).all()
        finally:
            _db_res.close()

        def _sc(t) -> int:
            return (t.llm_analysis or {}).get("score_pertinence", t.relevance_score or 0)

        _go    = sum(1 for t in _new_tenders if _sc(t) >= 65)
        _etude = sum(1 for t in _new_tenders if 35 <= _sc(t) < 65)
        _pass  = sum(1 for t in _new_tenders if _sc(t) < 35)
        _claude_ok = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("_source") in ("claude", "gemini"))

        st.success(
            f"✅ {total} nouveau(x) marché(s) importé(s) — "
            f"🟢 {_go} GO · 🟡 {_etude} À étudier · 🔴 {_pass} Passer"
            + (f" · 🤖 {_claude_ok} analysé(s) par Claude" if _claude_ok else "")
        )
    elif total:
        st.success(f"✅ {total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée pour les sources sélectionnées.")
    for err in errors:
        st.warning(err)
```

- [ ] **Step 2 : Vérifier manuellement**

```bash
streamlit run app.py
```

Lancer une collecte avec au moins une source active. Le message de succès doit afficher :
`✅ N nouveau(x) marché(s) importé(s) — 🟢 X GO · 🟡 Y À étudier · 🔴 Z Passer`

Si Claude a analysé certains marchés pendant la collecte, ajouter : `· 🤖 N analysé(s) par Claude`

Si aucun nouveau marché : `Aucune nouvelle offre trouvée…` inchangé.

- [ ] **Step 3 : Commit**

```bash
git add app.py
git commit -m "feat: résumé collecte enrichi GO/Étudier/Passer"
```

---

## Vérification finale

- [ ] `python -m pytest tests/test_filters.py -v` — tous les tests passent
- [ ] Recherche "ssi" filtre correctement les deux tableaux (public + privé)
- [ ] Cocher urgences + recherche simultanément → les deux filtres s'appliquent
- [ ] Lancer une collecte → le résumé enrichi s'affiche
