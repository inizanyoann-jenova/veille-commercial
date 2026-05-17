# Lot 2 — LLM Structuré + Score Adaptatif + Croisement DECP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enrichir chaque fiche marché avec une analyse LLM structurée (budget, lots, recommandation motivée), calculer un score adaptatif appris des décisions passées, et afficher l'historique de l'acheteur dans la base DECP.

**Architecture:** `score_adaptive.py` est totalement indépendant de Streamlit (testable en isolation). `llm_analyzer.py` reçoit une nouvelle fonction `analyze_tender_structured` parallèle à l'existante. `fiche_logic.py` reçoit `get_acheteur_history`. `app.py` orchestre l'affichage de ces nouvelles données dans les fiches. Aucun scraper modifié.

**Tech Stack:** SQLAlchemy, Claude API (anthropic, déjà présent), Python stdlib `re` / `collections`, APScheduler (déjà présent)

---

## Fichiers concernés

| Action | Fichier | Rôle |
|---|---|---|
| Modifier | `models.py` | Ajouter `llm_structured`, `adaptive_score` à Tender ; ajouter `ScoreWeight` |
| Modifier | `database.py` | Migrations idempotentes + helper `count_decisions` |
| Créer | `score_adaptive.py` | `_tokenize()` + `recompute_adaptive_scores()` |
| Créer | `tests/test_score_adaptive.py` | Tests score adaptatif |
| Modifier | `llm_analyzer.py` | Ajouter `analyze_tender_structured()` |
| Modifier | `tests/test_llm_analyzer.py` | Tests analyse structurée |
| Modifier | `fiche_logic.py` | Ajouter `get_acheteur_history()` |
| Modifier | `tests/test_fiche.py` | Tests historique acheteur |
| Modifier | `app.py` | Affichage llm_structured + adaptive_score dans fiche + colonne tableau + tri |
| Modifier | `pages/parametres.py` | Section score adaptatif |

---

### Task 1 : models.py + database.py — nouvelles colonnes et table

**Files:**
- Modify: `models.py`
- Modify: `database.py`

- [ ] **Step 1 : Ajouter llm_structured et adaptive_score à Tender dans models.py**

Dans `models.py`, dans la classe `Tender`, ajouter après la ligne `tags = Column(JSON, default=list)` :

```python
    llm_structured  = Column(JSON, default=None)
    adaptive_score  = Column(Integer, default=None)
```

- [ ] **Step 2 : Ajouter la classe ScoreWeight dans models.py**

Ajouter après la classe `DuplicateCandidate` dans `models.py` :

```python
class ScoreWeight(Base):
    __tablename__ = "score_weights"

    keyword     = Column(String, primary_key=True)
    weight_go   = Column(Float, default=0.0)
    weight_nogo = Column(Float, default=0.0)
    updated_at  = Column(DateTime)
```

Vérifier que `Float` est importé — si non, l'ajouter à la ligne d'import SQLAlchemy (il l'est déjà dans `DuplicateCandidate`).

- [ ] **Step 3 : Ajouter les migrations idempotentes dans database.py**

Dans `database.py`, dans la fonction `init_db()`, après les migrations existantes, ajouter :

```python
    # Lot 2 — migrations idempotentes
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE tenders ADD COLUMN llm_structured JSON DEFAULT NULL",
            "ALTER TABLE tenders ADD COLUMN adaptive_score INTEGER DEFAULT NULL",
            """CREATE TABLE IF NOT EXISTS score_weights (
                keyword TEXT PRIMARY KEY,
                weight_go REAL DEFAULT 0.0,
                weight_nogo REAL DEFAULT 0.0,
                updated_at DATETIME
            )""",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()
```

Vérifier que `text` est importé depuis `sqlalchemy` (chercher `from sqlalchemy import` en tête de `database.py`).

- [ ] **Step 4 : Ajouter count_decisions() dans database.py**

Dans `database.py`, ajouter la fonction suivante :

```python
def count_decisions(db) -> int:
    """Nombre de tenders avec une décision enregistrée (Soumis/Gagné/Perdu)."""
    from models import Tender
    return db.query(Tender).filter(
        Tender.status.in_(["Soumis", "Gagné", "Perdu"]),
        Tender.is_blacklisted == False,
    ).count()
```

- [ ] **Step 5 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('models.py').read()); print('models OK')"
python -c "import ast; ast.parse(open('database.py').read()); print('database OK')"
```

Résultat attendu : `models OK` puis `database OK`

- [ ] **Step 6 : Vérifier que les tests existants passent toujours**

```bash
pytest tests/ -v --tb=short -q 2>&1 | tail -10
```

Résultat attendu : tous les tests existants PASSED

- [ ] **Step 7 : Commit**

```bash
git add models.py database.py
git commit -m "feat: models — llm_structured, adaptive_score, ScoreWeight + migrations + count_decisions"
```

---

### Task 2 : score_adaptive.py — tokenize + recompute (TDD)

**Files:**
- Create: `tests/test_score_adaptive.py`
- Create: `score_adaptive.py`

- [ ] **Step 1 : Écrire les tests failing**

Créer `tests/test_score_adaptive.py` :

```python
import pytest
from models import Tender, ScoreWeight
from database import count_decisions


def test_tokenize_removes_stop_words():
    from score_adaptive import _tokenize
    result = _tokenize("Installation des systèmes de détection incendie")
    assert "installation" in result
    assert "détection" in result or "detection" in result
    assert "des" not in result
    assert "de" not in result


def test_tokenize_filters_short_tokens():
    from score_adaptive import _tokenize
    result = _tokenize("SSI en ERP de type J")
    # tokens < 3 chars exclus
    assert all(len(t) >= 3 for t in result)


def test_recompute_returns_zero_when_insufficient_decisions(db):
    """Moins de 10 décisions → recompute retourne 0 sans modifier les scores."""
    from score_adaptive import recompute_adaptive_scores
    result = recompute_adaptive_scores(db)
    assert result == 0


def test_recompute_requires_ten_decisions(db, make_tender):
    """Exactement 9 décisions → toujours 0."""
    from score_adaptive import recompute_adaptive_scores
    for i in range(9):
        make_tender(status="Gagné", title=f"SSI installation ERP {i}", description="détection incendie SSI CMSI")
    result = recompute_adaptive_scores(db)
    assert result == 0


def test_recompute_scores_undecided_tenders(db, make_tender):
    """10 décisions → les tenders non décidés reçoivent un adaptive_score."""
    from score_adaptive import recompute_adaptive_scores
    for i in range(8):
        make_tender(status="Gagné", title=f"SSI ERP installation {i}", description="détection incendie SSI CMSI")
    for i in range(2):
        make_tender(status="Perdu", title=f"nettoyage jardinage {i}", description="espaces verts entretien")
    # Tender non décidé
    undecided = make_tender(status="À qualifier", title="Installation SSI ERP", description="détection incendie")
    nb = recompute_adaptive_scores(db)
    assert nb >= 1
    db.refresh(undecided)
    assert undecided.adaptive_score is not None
    assert 0 <= undecided.adaptive_score <= 100


def test_recompute_persists_score_weights(db, make_tender):
    """Les poids sont enregistrés dans score_weights."""
    from score_adaptive import recompute_adaptive_scores
    for i in range(10):
        make_tender(status="Gagné", title=f"SSI ERP {i}", description="détection incendie CMSI")
    recompute_adaptive_scores(db)
    weights = db.query(ScoreWeight).all()
    assert len(weights) > 0


def test_recompute_go_tender_scores_higher_than_irrelevant(db, make_tender):
    """Un tender GO-like doit scorer plus haut qu'un irrelevant."""
    from score_adaptive import recompute_adaptive_scores
    for i in range(8):
        make_tender(status="Gagné", title=f"SSI ERP installation {i}", description="détection incendie SSI CMSI désenfumage")
    for i in range(2):
        make_tender(status="Perdu", title=f"nettoyage jardinage {i}", description="tonte pelouse espaces verts")
    t_go = make_tender(status="À qualifier", title="Installation SSI ERP Type J", description="détection incendie CMSI")
    t_bad = make_tender(status="À qualifier", title="Tonte pelouse jardinage", description="entretien espaces verts")
    recompute_adaptive_scores(db)
    db.refresh(t_go)
    db.refresh(t_bad)
    assert t_go.adaptive_score is not None
    assert t_bad.adaptive_score is not None
    assert t_go.adaptive_score >= t_bad.adaptive_score
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_score_adaptive.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'score_adaptive'`

- [ ] **Step 3 : Créer score_adaptive.py**

```python
import re
from collections import Counter
from datetime import datetime

from database import SessionLocal
from models import ScoreWeight, Tender

_STOP_WORDS = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "au", "aux",
    "sur", "pour", "par", "dans", "avec", "qui", "que", "ne", "pas", "plus",
    "marché", "travaux", "fourniture", "service", "services", "accord", "cadre",
    "lot", "prestation", "mise", "place", "aux", "son", "ses", "leur", "leurs",
}

_POSITIVE_STATUSES = {"Soumis", "Gagné"}
_NEGATIVE_STATUSES = {"Perdu"}
_MIN_DECISIONS = 10


def _tokenize(text: str) -> list[str]:
    """Extrait les tokens significatifs d'un texte (longueur ≥ 3, hors stop words)."""
    tokens = re.findall(r"\b[a-zàâäéèêëîïôùûüç]{3,}\b", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


def recompute_adaptive_scores(db=None) -> int:
    """
    Recalcule adaptive_score pour tous les tenders non décidés.
    Nécessite au moins _MIN_DECISIONS décisions enregistrées.
    Retourne le nombre de tenders mis à jour (0 si données insuffisantes).
    """
    _close = db is None
    if db is None:
        db = SessionLocal()
    try:
        pos_tenders = db.query(Tender).filter(
            Tender.status.in_(_POSITIVE_STATUSES),
            Tender.is_blacklisted == False,
            Tender.title != None,
        ).all()
        neg_tenders = db.query(Tender).filter(
            Tender.status.in_(_NEGATIVE_STATUSES),
            Tender.is_blacklisted == False,
            Tender.title != None,
        ).all()

        if len(pos_tenders) + len(neg_tenders) < _MIN_DECISIONS:
            return 0

        pos_counter: Counter = Counter()
        for t in pos_tenders:
            pos_counter.update(_tokenize((t.title or "") + " " + (t.description or "")))

        neg_counter: Counter = Counter()
        for t in neg_tenders:
            neg_counter.update(_tokenize((t.title or "") + " " + (t.description or "")))

        total_pos = max(sum(pos_counter.values()), 1)
        total_neg = max(sum(neg_counter.values()), 1)

        weights: dict[str, tuple[float, float]] = {}
        for token in set(pos_counter) | set(neg_counter):
            freq_go = pos_counter.get(token, 0) / total_pos
            freq_nogo = neg_counter.get(token, 0) / total_neg
            if freq_go + freq_nogo > 0.0005:
                weights[token] = (freq_go, freq_nogo)

        # Persister les poids
        now = datetime.utcnow()
        for token, (wgo, wnogo) in weights.items():
            sw = db.query(ScoreWeight).filter(ScoreWeight.keyword == token).first()
            if sw:
                sw.weight_go = wgo
                sw.weight_nogo = wnogo
                sw.updated_at = now
            else:
                db.add(ScoreWeight(keyword=token, weight_go=wgo, weight_nogo=wnogo, updated_at=now))
        db.commit()

        # Scorer les tenders non décidés
        undecided = db.query(Tender).filter(
            Tender.status.notin_(list(_POSITIVE_STATUSES | _NEGATIVE_STATUSES)),
            Tender.is_blacklisted == False,
        ).all()

        updated = 0
        for t in undecided:
            tokens = _tokenize((t.title or "") + " " + (t.description or ""))
            if not tokens:
                continue
            raw = sum(weights[tok][0] - weights[tok][1] for tok in tokens if tok in weights)
            # Normalisation sigmoïde-like vers 0–100
            normalized = int(50 + 50 * max(-1.0, min(1.0, raw / max(len(tokens) * 0.05, 1))))
            t.adaptive_score = normalized
            updated += 1

        db.commit()
        return updated
    finally:
        if _close:
            db.close()
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_score_adaptive.py -v
```

Résultat attendu : 7 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add score_adaptive.py tests/test_score_adaptive.py
git commit -m "feat: score_adaptive — tokenize + recompute avec TDD (min 10 décisions)"
```

---

### Task 3 : app.py — colonne adaptive_score + option de tri

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Localiser le tableau principal dans app.py**

```bash
grep -n "adaptive_score\|relevance_score\|st.dataframe\|df\[.Score" app.py | head -20
```

- [ ] **Step 2 : Ajouter la colonne adaptive_score dans le DataFrame du tableau**

Dans `app.py`, dans la fonction ou le bloc qui construit le DataFrame pour `st.data_editor` ou `st.dataframe`, ajouter la colonne `adaptive_score` (avec `"—"` si `None`) :

Trouver le bloc de construction du DataFrame (chercher `"Score"` ou `relevance_score`) et ajouter :
```python
"🧠 Score adaptatif": t.adaptive_score if t.adaptive_score is not None else "—",
```
à côté de la colonne de score existante.

- [ ] **Step 3 : Ajouter l'option de tri dans la sidebar**

Dans `app.py`, dans la sidebar (chercher `st.sidebar`), dans la section de filtres ou de tri, ajouter :

```python
_sort_options = ["Score pertinence ↓", "Score adaptatif ↓", "Deadline ↑", "Date publication ↓"]
_sort = st.sidebar.selectbox("Trier par", _sort_options, key="sort_order")
```

Puis dans la requête principale, appliquer le tri selon `_sort` :
```python
if _sort == "Score adaptatif ↓":
    query = query.order_by(Tender.adaptive_score.desc().nullslast())
elif _sort == "Deadline ↑":
    query = query.order_by(Tender.deadline.asc().nullslast())
elif _sort == "Date publication ↓":
    query = query.order_by(Tender.publication_date.desc().nullslast())
else:
    query = query.order_by(Tender.relevance_score.desc())
```

- [ ] **Step 4 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 5 : Commit**

```bash
git add app.py
git commit -m "feat: app — colonne adaptive_score dans tableau + tri par score adaptatif"
```

---

### Task 4 : pages/parametres.py — section score adaptatif

**Files:**
- Modify: `pages/parametres.py`

- [ ] **Step 1 : Ajouter la section score adaptatif dans parametres.py**

Ajouter après la section digest email dans `pages/parametres.py` :

```python
# ── Score adaptatif ─────────────────────────────────────────────────────��─────

st.markdown("---")
st.subheader("🧠 Score adaptatif")

from database import count_decisions as _count_dec, SessionLocal as _SL_adp

_db_adp = _SL_adp()
try:
    _nb_dec = _count_dec(_db_adp)
finally:
    _db_adp.close()

_MIN_DEC = 10
if _nb_dec < _MIN_DEC:
    st.info(f"Pas encore assez de données : **{_nb_dec}/{_MIN_DEC}** décisions enregistrées (Soumis/Gagné/Perdu). "
            f"Le score adaptatif s'activera automatiquement une fois {_MIN_DEC} décisions atteintes.")
else:
    st.success(f"{_nb_dec} décisions disponibles — score adaptatif actif")
    if st.button("🔄 Recalculer le score adaptatif maintenant"):
        from score_adaptive import recompute_adaptive_scores as _recompute
        with st.spinner("Recalcul en cours…"):
            _nb = _recompute()
        st.success(f"✅ {_nb} marchés mis à jour")
        st.cache_data.clear()
```

- [ ] **Step 2 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('pages/parametres.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 3 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat: parametres — section score adaptatif avec compteur décisions + bouton recalcul"
```

---

### Task 5 : app.py — APScheduler job hebdomadaire score adaptatif

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Ajouter le job weekly dans `_start_background_services`**

Dans `app.py`, dans `_start_background_services`, après le job `daily_digest`, ajouter :

```python
    def _weekly_adaptive_scores():
        from score_adaptive import recompute_adaptive_scores as _r
        _r()

    _scheduler.add_job(
        _weekly_adaptive_scores,
        "interval",
        weeks=1,
        id="weekly_adaptive_scores",
    )
```

- [ ] **Step 2 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 3 : Commit**

```bash
git add app.py
git commit -m "feat: app — job APScheduler hebdomadaire recompute_adaptive_scores"
```

---

### Task 6 : llm_analyzer.py — analyze_tender_structured() (TDD)

**Files:**
- Modify: `tests/test_llm_analyzer.py`
- Modify: `llm_analyzer.py`

- [ ] **Step 1 : Ajouter les tests analyze_tender_structured**

Dans `tests/test_llm_analyzer.py`, ajouter :

```python
from unittest.mock import patch, MagicMock


def test_analyze_tender_structured_returns_none_for_short_description():
    """Description < 50 chars → None sans appeler l'API."""
    from llm_analyzer import analyze_tender_structured
    result = analyze_tender_structured("Titre", "Court")
    assert result is None


def test_analyze_tender_structured_returns_none_without_api_key(monkeypatch):
    """Pas de clé API → None."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from llm_analyzer import analyze_tender_structured
    result = analyze_tender_structured(
        "Installation SSI ERP type J",
        "Installation d'un système de sécurité incendie dans un ERP de type J, catégorie 2.",
    )
    assert result is None


def test_analyze_tender_structured_parses_valid_json(monkeypatch):
    """Réponse Claude JSON valide → dict avec les bons champs."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    mock_response_json = """{
        "budget_estime": "150 000 €",
        "type_travaux": "Installation neuve",
        "lots": ["Lot 1 — Détection"],
        "keywords_techniques": ["SSI catégorie A"],
        "acheteur_type": "Établissement scolaire",
        "niveau_concurrence": "Élevé",
        "recommandation": "GO",
        "score_confiance": 82,
        "justification": "ERP type J, cœur de métier."
    }"""

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=mock_response_json)]

    from llm_analyzer import analyze_tender_structured
    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_msg

        result = analyze_tender_structured(
            "Installation SSI ERP type J",
            "Installation d'un système de sécurité incendie dans un ERP de type J catégorie 2, désenfumage CMSI inclus.",
            amount=150000,
        )

    assert result is not None
    assert result["recommandation"] == "GO"
    assert result["score_confiance"] == 82
    assert "budget_estime" in result
    assert isinstance(result["lots"], list)


def test_analyze_tender_structured_handles_invalid_json(monkeypatch):
    """Claude retourne du texte invalide → None sans exception."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text="Désolé, je ne peux pas répondre.")]

    from llm_analyzer import analyze_tender_structured
    with patch("anthropic.Anthropic") as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_msg

        result = analyze_tender_structured(
            "Installation SSI",
            "Installation d'un système de sécurité incendie complet avec CMSI et désenfumage.",
        )

    assert result is None
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_llm_analyzer.py -k "structured" -v
```

Résultat attendu : `ImportError` ou `AttributeError` car `analyze_tender_structured` n'existe pas encore

- [ ] **Step 3 : Ajouter analyze_tender_structured dans llm_analyzer.py**

Dans `llm_analyzer.py`, ajouter après la fonction `analyze_tender` existante :

```python
_STRUCTURED_SYSTEM = (
    "Tu es un expert en marchés publics SSI, CMSI, désenfumage, vidéosurveillance "
    "et courants faibles pour les DOM (La Réunion 974, Mayotte 976). "
    "Tu retournes UNIQUEMENT un objet JSON valide, sans texte avant ni après."
)

_STRUCTURED_USER_TPL = """Analyse ce marché et retourne ce JSON strict :

{{
  "budget_estime": "<montant en € ou null>",
  "type_travaux": "Installation neuve" | "Rénovation" | "Maintenance" | "Étude" | "Mixte" | "Inconnu",
  "lots": ["Lot 1 — ...", "..."],
  "keywords_techniques": ["ERP type J", "SSI catégorie A", "..."],
  "acheteur_type": "Commune" | "Établissement scolaire" | "Hôpital" | "Administration" | "Privé" | "Autre",
  "niveau_concurrence": "Faible" | "Moyen" | "Élevé",
  "recommandation": "GO" | "NON",
  "score_confiance": <entier 0-100>,
  "justification": "<1-2 phrases>"
}}

--- MARCHÉ ---
Titre : {title}
Description : {description}
Montant estimé : {amount}
"""


def analyze_tender_structured(
    title: str,
    description: str,
    amount: int | None = None,
) -> dict | None:
    """
    Analyse structurée LLM d'un marché. Retourne un dict JSON ou None si :
    - description trop courte (< 50 chars)
    - clé API absente
    - réponse non-JSON
    - quota / erreur réseau
    """
    if not description or len(description.strip()) < 50:
        return None

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    amount_str = f"{amount:,} €".replace(",", " ") if amount else "Non renseigné"
    prompt = _STRUCTURED_USER_TPL.format(
        title=title or "",
        description=description[:3000],
        amount=amount_str,
    )

    try:
        import anthropic as _anthropic
        client = _anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=_STRUCTURED_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # Extraire le JSON même si Claude ajoute du texte autour
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return None
        return json.loads(raw[start:end])
    except Exception:
        return None
```

Vérifier que `json` et `os` sont importés en tête de `llm_analyzer.py` (ils le sont déjà).

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_llm_analyzer.py -k "structured" -v
```

Résultat attendu : 4 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat: llm_analyzer — analyze_tender_structured avec JSON strict + tests"
```

---

### Task 7 : app.py — déclenchement auto + affichage llm_structured dans la fiche

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Localiser le déclenchement de l'analyse LLM dans app.py**

```bash
grep -n "auto_analyze\|llm_analysis\|analyze_tender\|llm_structured" app.py | head -20
```

- [ ] **Step 2 : Ajouter l'appel analyze_tender_structured après chaque collecte**

Dans `app.py`, dans la fonction ou le bloc qui appelle `auto_analyze_pending` ou `auto_analyze_claude` après la collecte, ajouter le déclenchement de l'analyse structurée :

```python
def _trigger_structured_analysis():
    """Analyse structurée des marchés sans llm_structured et score >= SCORE_ETUDE."""
    from llm_analyzer import analyze_tender_structured as _ats
    from database import SessionLocal as _SL
    _db = _SL()
    try:
        targets = (
            _db.query(Tender)
            .filter(
                Tender.llm_structured == None,
                Tender.relevance_score >= SCORE_ETUDE,
                Tender.is_blacklisted == False,
            )
            .limit(20)
            .all()
        )
        for t in targets:
            result = _ats(t.title or "", t.description or "", t.amount)
            if result:
                t.llm_structured = result
        _db.commit()
    except Exception:
        _db.rollback()
    finally:
        _db.close()
```

Appeler `_trigger_structured_analysis()` dans un thread daemon après chaque collecte (même pattern que les autres analyses en background).

- [ ] **Step 3 : Afficher llm_structured dans la fiche marché**

Dans `app.py`, dans la section d'affichage de la fiche marché (chercher `llm_analysis` ou `fiche`), ajouter après la section de résumé narratif existante :

```python
# ── Analyse structurée IA ────────────────────────────────────────────────��───
if tender.llm_structured:
    _s = tender.llm_structured
    st.markdown("#### 🤖 Analyse structurée")
    _c1, _c2 = st.columns(2)
    with _c1:
        st.markdown(f"**Budget estimé** {_s.get('budget_estime') or '—'}")
        st.markdown(f"**Type de travaux** {_s.get('type_travaux') or '—'}")
        st.markdown(f"**Acheteur** {_s.get('acheteur_type') or '—'}")
    with _c2:
        st.markdown(f"**Concurrence** {_s.get('niveau_concurrence') or '—'}")
        _conf = _s.get('score_confiance')
        st.markdown(f"**Confiance IA** {_conf} %" if _conf is not None else "**Confiance IA** —")
        _reco = _s.get('recommandation', '')
        _badge = "✅ GO" if _reco == "GO" else ("🔴 NON" if _reco == "NON" else "—")
        st.markdown(f"**Recommandation** {_badge}")
    _lots = _s.get('lots', [])
    if _lots:
        st.markdown(f"**Lots** {' · '.join(_lots)}")
    _justif = _s.get('justification', '')
    if _justif:
        st.caption(_justif)
    # Bouton réanalyse
    if st.button("🔄 Ré-analyser (LLM structuré)", key=f"rellm_{tender.id}"):
        from llm_analyzer import analyze_tender_structured as _ats
        with st.spinner("Analyse en cours…"):
            _new = _ats(tender.title or "", tender.description or "", tender.amount)
        if _new:
            _db_fiche = SessionLocal()
            try:
                _t = _db_fiche.query(Tender).filter(Tender.id == tender.id).first()
                if _t:
                    _t.llm_structured = _new
                    _db_fiche.commit()
            finally:
                _db_fiche.close()
            st.cache_data.clear()
            st.rerun()
        else:
            st.warning("Analyse impossible (description trop courte ou clé API manquante)")
```

- [ ] **Step 4 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 5 : Commit**

```bash
git add app.py
git commit -m "feat: app — déclenchement auto llm_structured + affichage dans fiche"
```

---

### Task 8 : fiche_logic.py — get_acheteur_history() (TDD)

**Files:**
- Modify: `tests/test_fiche.py`
- Modify: `fiche_logic.py`

- [ ] **Step 1 : Ajouter les tests get_acheteur_history**

Dans `tests/test_fiche.py`, ajouter :

```python
def test_get_acheteur_history_returns_empty_when_no_match(db, make_tender):
    """Aucun marché similaire → nb_total = 0."""
    from fiche_logic import get_acheteur_history
    t = make_tender(title="Installation vidéosurveillance port")
    result = get_acheteur_history(db, t)
    assert result["nb_total"] == 0


def test_get_acheteur_history_returns_empty_for_short_title(db, make_tender):
    """Titre < 2 mots significatifs → nb_total = 0."""
    from fiche_logic import get_acheteur_history
    t = make_tender(title="SSI")
    result = get_acheteur_history(db, t)
    assert result["nb_total"] == 0


def test_get_acheteur_history_finds_similar_tenders(db, make_tender):
    """2+ marchés avec mots-clés communs → résultats retournés."""
    from fiche_logic import get_acheteur_history
    target = make_tender(title="Installation détection incendie collège")
    make_tender(title="Installation détection incendie lycée", status="Gagné", amount=80000)
    make_tender(title="Installation détection incendie mairie", status="Perdu")
    result = get_acheteur_history(db, target)
    assert result["nb_total"] >= 2
    assert result["nb_gagnes"] == 1
    assert result["montant_total_gagne"] == 80000


def test_get_acheteur_history_excludes_blacklisted(db, make_tender):
    """Marchés blacklistés exclus des résultats."""
    from fiche_logic import get_acheteur_history
    target = make_tender(title="Installation détection incendie collège")
    make_tender(title="Installation détection incendie mairie", is_blacklisted=True)
    make_tender(title="Installation détection incendie lycée", is_blacklisted=True)
    result = get_acheteur_history(db, target)
    assert result["nb_total"] == 0


def test_get_acheteur_history_excludes_self(db, make_tender):
    """Le tender lui-même n'apparaît pas dans l'historique."""
    from fiche_logic import get_acheteur_history
    t = make_tender(title="Installation détection incendie collège")
    make_tender(title="Installation détection incendie lycée", status="Gagné", amount=50000)
    result = get_acheteur_history(db, t)
    for other in result.get("derniers", []):
        assert other.id != t.id
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_fiche.py -k "acheteur" -v
```

Résultat attendu : `ImportError` car `get_acheteur_history` n'existe pas

- [ ] **Step 3 : Ajouter get_acheteur_history dans fiche_logic.py**

Dans `fiche_logic.py`, ajouter en fin de fichier (après les fonctions existantes) :

```python
import re as _re

_HISTORY_STOP = {
    "le", "la", "les", "de", "du", "des", "un", "une", "et", "en", "au", "aux",
    "sur", "pour", "par", "dans", "avec", "marché", "travaux", "fourniture",
    "prestation", "services", "accord", "cadre", "lot", "mise", "place",
}


def get_acheteur_history(db, tender) -> dict:
    """
    Cherche dans la base les marchés partageant les mots-clés du titre du tender.
    Retourne un dict avec nb_total, nb_go, nb_gagnes, montant_total_gagne, derniers.
    Retourne {"nb_total": 0} si moins de 2 correspondances ou titre trop court.
    """
    from sqlalchemy import func as _func
    from models import Tender as _Tender

    title = (tender.title or "").lower()
    tokens = [
        t for t in _re.findall(r"\b[a-zàâäéèêëîïôùûüç]{4,}\b", title)
        if t not in _HISTORY_STOP
    ][:3]

    if len(tokens) < 2:
        return {"nb_total": 0}

    query = db.query(_Tender).filter(
        _Tender.id != tender.id,
        _Tender.is_blacklisted == False,
    )
    for token in tokens:
        query = query.filter(_func.lower(_Tender.title).contains(token))

    matches = query.order_by(_Tender.publication_date.desc()).limit(10).all()

    if len(matches) < 2:
        return {"nb_total": 0}

    nb_go = sum(1 for t in matches if t.relevance_score >= SCORE_GO)
    nb_gagnes = sum(1 for t in matches if t.status == "Gagné")
    montant_gagne = sum(t.amount for t in matches if t.status == "Gagné" and t.amount)

    return {
        "nb_total": len(matches),
        "nb_go": nb_go,
        "nb_gagnes": nb_gagnes,
        "montant_total_gagne": montant_gagne,
        "derniers": matches[:3],
    }
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_fiche.py -k "acheteur" -v
```

Résultat attendu : 5 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add fiche_logic.py tests/test_fiche.py
git commit -m "feat: fiche_logic — get_acheteur_history avec TDD (3 tokens, min 2 matches)"
```

---

### Task 9 : app.py — affichage historique acheteur dans la fiche

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Localiser la section fiche dans app.py**

```bash
grep -n "get_acheteur\|Historique acheteur\|fiche_logic\|_compute_fiche" app.py | head -10
```

- [ ] **Step 2 : Ajouter le badge adaptive_score dans la fiche marché**

Dans `app.py`, dans la section de la fiche marché, dans le bloc des métriques ou badges principaux du marché, ajouter :

```python
# Badge score adaptatif (visible seulement si calculé)
if tender.adaptive_score is not None:
    st.markdown(f"🧠 **Score adaptatif : {tender.adaptive_score}**")
```

- [ ] **Step 3 : Ajouter l'affichage de l'historique acheteur dans la fiche**

Dans `app.py`, dans la section de la fiche marché (après la section analyse structurée ajoutée en Task 7), ajouter :

```python
# ── Historique acheteur ──────────────────────────────────────────────────────
_db_hist = SessionLocal()
try:
    _hist = get_acheteur_history(_db_hist, tender)
finally:
    _db_hist.close()

if _hist.get("nb_total", 0) >= 2:
    st.markdown("#### 🏛️ Historique acheteur")
    _h1, _h2, _h3 = st.columns(3)
    _h1.metric("Marchés similaires", _hist["nb_total"])
    _h2.metric("GO / Soumis", _hist["nb_go"])
    _h3.metric("Gagnés 🏆", _hist["nb_gagnes"])
    if _hist["montant_total_gagne"]:
        st.caption(f"💰 {_hist['montant_total_gagne']:,} € gagnés sur cet acheteur".replace(",", " "))
    for _prev in _hist.get("derniers", []):
        _dl = _prev.deadline.strftime("%b %Y") if _prev.deadline else "—"
        if st.button(
            f"→ {(_prev.title or '')[:55]} | {_prev.status} | {_dl}",
            key=f"hist_{tender.id}_{_prev.id}",
        ):
            st.session_state["selected_tender_id"] = _prev.id
            st.rerun()
```

Vérifier que `get_acheteur_history` est importé en tête de `app.py` :
```python
from fiche_logic import SCORE_GO, SCORE_ETUDE, _compute_fiche_data, get_acheteur_history
```

- [ ] **Step 3 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 4 : Vérifier que tous les tests passent**

```bash
pytest tests/ -v --tb=short -q 2>&1 | tail -15
```

Résultat attendu : 0 failures

- [ ] **Step 5 : Commit final Lot 2**

```bash
git add app.py
git commit -m "feat: app — affichage historique acheteur dans fiche marché"
```

---

### Task 10 : Vérification finale Lot 2

- [ ] **Step 1 : Suite de tests complète**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Résultat attendu : 0 failures, tous les tests des nouveaux fichiers PASSED

- [ ] **Step 2 : Vérifier la syntaxe de tous les fichiers modifiés**

```bash
python -c "
import ast, pathlib
for f in ['models.py','database.py','score_adaptive.py','llm_analyzer.py','fiche_logic.py','app.py','pages/parametres.py']:
    ast.parse(pathlib.Path(f).read_text(encoding='utf-8'))
    print(f'OK: {f}')
"
```

Résultat attendu : `OK` pour chaque fichier

- [ ] **Step 3 : Commit de clôture Lot 2**

```bash
git add -u
git commit -m "feat: Lot 2 complet — LLM structuré + score adaptatif + historique acheteur DECP"
```
