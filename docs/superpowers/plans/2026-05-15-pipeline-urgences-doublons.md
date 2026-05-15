# Pipeline Kanban, Widget Urgences & Doublons — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Pipeline Kanban page, an urgences deadline widget on the main page, and a duplicate detection/merge feature in Paramètres.

**Architecture:** Testable data logic lives in `database.py` as plain functions taking a `db` session. Streamlit UI in page files calls these helpers. The new `DuplicateCandidate` model follows the same pattern as `ScraperRun` in `models.py`.

**Tech Stack:** Python, SQLAlchemy, Streamlit, difflib (stdlib), SQLite

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `models.py` | Add `DuplicateCandidate` SQLAlchemy model |
| Modify | `database.py` | Migration + `detect_duplicates()`, `load_urgences()`, `load_pipeline_data()` |
| Modify | `app.py` | Urgences widget before the search bar (~line 1609) |
| Create | `pages/pipeline.py` | Pipeline Kanban page UI |
| Modify | `pages/parametres.py` | Doublons detection section at end of file |
| Create | `tests/test_doublons.py` | Tests for `DuplicateCandidate` model and `detect_duplicates()` |
| Create | `tests/test_urgences_pipeline.py` | Tests for `load_urgences()` and `load_pipeline_data()` |

---

### Task 1: DuplicateCandidate model + migration

**Files:**
- Modify: `models.py`
- Modify: `database.py:14-15` (add import in `init_db`)
- Test: `tests/test_doublons.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_doublons.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def engine():
    from source_registry import Source          # noqa: registers Source
    from models import ScraperRun, DuplicateCandidate  # noqa: registers models
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_duplicate_candidates_table_exists(engine):
    inspector = inspect(engine)
    assert "duplicate_candidates" in inspector.get_table_names()


def test_duplicate_candidates_columns(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("duplicate_candidates")}
    assert {"id", "tender_id_a", "tender_id_b", "similarity_score", "detected_at", "resolved"} <= cols
```

- [ ] **Step 2: Run test to verify it fails**

```
cd "c:/Users/Utilisateur/Desktop/toutes les app pour def/commercial et opportunité def OI"
python -m pytest tests/test_doublons.py -v
```

Expected: `ImportError: cannot import name 'DuplicateCandidate' from 'models'`

- [ ] **Step 3: Add DuplicateCandidate to models.py**

In `models.py`, the first line imports `Column, String, DateTime, Integer, Boolean, JSON`. Add `Float` to that import. Then append the class after `ScraperRun`:

```python
# models.py — first line, update existing import:
from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, Float

# append after ScraperRun class:
class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    tender_id_a      = Column(String, nullable=False)
    tender_id_b      = Column(String, nullable=False)
    similarity_score = Column(Float, nullable=False)
    detected_at      = Column(DateTime, nullable=False)
    resolved         = Column(Boolean, default=False)
```

- [ ] **Step 4: Register DuplicateCandidate in init_db()**

In `database.py`, line 15, replace the existing ScraperRun import:

```python
    from models import ScraperRun, DuplicateCandidate  # noqa: registers both with Base
```

- [ ] **Step 5: Run tests to verify they pass**

```
python -m pytest tests/test_doublons.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add models.py database.py tests/test_doublons.py
git commit -m "feat: DuplicateCandidate model + migration"
```

---

### Task 2: detect_duplicates() function

**Files:**
- Modify: `database.py` (append function at end)
- Modify: `tests/test_doublons.py` (append tests)

- [ ] **Step 1: Append failing tests to tests/test_doublons.py**

```python
from datetime import datetime


def _make_tender(db, id, title, source, deadline=None, score=70):
    from models import Tender
    t = Tender(
        id=id, title=title, source=source,
        relevance_score=score, deadline=deadline,
        status="À qualifier", is_blacklisted=False,
    )
    db.add(t)
    db.commit()
    return t


def test_detect_finds_similar_titles_different_sources(db):
    from database import detect_duplicates
    from models import DuplicateCandidate
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a1", "Rénovation SSI CHU Mayotte", "BOAMP", deadline=dl)
    _make_tender(db, "b1", "Rénovation SSI CHU Mayotte", "TED", deadline=dl)

    count = detect_duplicates(db)

    assert count == 1
    pair = db.query(DuplicateCandidate).first()
    assert pair.similarity_score >= 0.80
    assert pair.resolved is False


def test_detect_skips_same_source(db):
    from database import detect_duplicates
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a2", "Maintenance CMSI Hôpital", "BOAMP", deadline=dl)
    _make_tender(db, "b2", "Maintenance CMSI Hôpital", "BOAMP", deadline=dl)

    count = detect_duplicates(db)

    assert count == 0


def test_detect_skips_different_deadline(db):
    from database import detect_duplicates
    _make_tender(db, "a3", "SSI Lycée Victor Hugo", "BOAMP", deadline=datetime(2026, 6, 1))
    _make_tender(db, "b3", "SSI Lycée Victor Hugo", "TED",   deadline=datetime(2026, 7, 15))

    count = detect_duplicates(db)

    assert count == 0


def test_detect_no_duplicate_when_titles_differ(db):
    from database import detect_duplicates
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a4", "SSI Lycée Bellepierre", "BOAMP", deadline=dl)
    _make_tender(db, "b4", "Vidéosurveillance Mairie", "TED", deadline=dl)

    count = detect_duplicates(db)

    assert count == 0


def test_detect_does_not_create_duplicate_pair_twice(db):
    from database import detect_duplicates
    dl = datetime(2026, 6, 1)
    _make_tender(db, "a5", "Courants faibles Hôtel Lux", "BOAMP", deadline=dl)
    _make_tender(db, "b5", "Courants faibles Hôtel Lux", "TED",   deadline=dl)

    detect_duplicates(db)
    count_second = detect_duplicates(db)

    assert count_second == 0
```

- [ ] **Step 2: Run tests to verify they fail**

```
python -m pytest tests/test_doublons.py -v
```

Expected: `AttributeError: module 'database' has no attribute 'detect_duplicates'`

- [ ] **Step 3: Implement detect_duplicates() in database.py**

Append to `database.py`:

```python
from difflib import SequenceMatcher as _SM
from sqlalchemy import and_ as _and, or_ as _or


def detect_duplicates(db) -> int:
    """Détecte les paires de marchés avec titre similaire (>=0.80) et deadline à ±3j.
    Retourne le nombre de nouvelles paires insérées."""
    from models import Tender, DuplicateCandidate
    from datetime import datetime as _ddt

    tenders = db.query(Tender).filter(Tender.is_blacklisted != True).all()
    new_pairs = 0

    for i, a in enumerate(tenders):
        for b in tenders[i + 1:]:
            if a.source == b.source:
                continue
            if not a.title or not b.title:
                continue
            ratio = _SM(None, a.title.lower(), b.title.lower()).ratio()
            if ratio < 0.80:
                continue
            if a.deadline and b.deadline:
                if abs((a.deadline - b.deadline).days) > 3:
                    continue
            elif a.deadline or b.deadline:
                continue
            existing = db.query(DuplicateCandidate).filter(
                _or(
                    _and(DuplicateCandidate.tender_id_a == a.id, DuplicateCandidate.tender_id_b == b.id),
                    _and(DuplicateCandidate.tender_id_a == b.id, DuplicateCandidate.tender_id_b == a.id),
                )
            ).first()
            if not existing:
                db.add(DuplicateCandidate(
                    tender_id_a=a.id,
                    tender_id_b=b.id,
                    similarity_score=round(ratio, 3),
                    detected_at=_ddt.utcnow(),
                ))
                new_pairs += 1

    db.commit()
    return new_pairs
```

- [ ] **Step 4: Run all tests to verify they pass**

```
python -m pytest tests/test_doublons.py -v
```

Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_doublons.py
git commit -m "feat: detect_duplicates() — similarité titre >= 0.80 + deadline ±3j"
```

---

### Task 3: load_urgences() helper + tests

**Files:**
- Modify: `database.py` (append function)
- Create: `tests/test_urgences_pipeline.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_urgences_pipeline.py`:

```python
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def engine():
    from source_registry import Source                      # noqa
    from models import ScraperRun, DuplicateCandidate       # noqa
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _today_midnight():
    return datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)


def _add_tender(db, id, title, score, deadline_offset_days, status="À qualifier", blacklisted=False):
    from models import Tender
    midnight = _today_midnight()
    deadline = (midnight + timedelta(days=deadline_offset_days)) if deadline_offset_days is not None else None
    t = Tender(
        id=id, title=title, source="TEST",
        relevance_score=score, deadline=deadline,
        status=status, is_blacklisted=blacklisted,
    )
    db.add(t)
    db.commit()
    return t


def test_urgences_returns_go_with_deadline_in_range(db):
    from database import load_urgences
    _add_tender(db, "u1", "SSI CHU Mayotte", score=80, deadline_offset_days=5)

    result = load_urgences(db)

    assert len(result) == 1
    assert result[0]["id"] == "u1"
    assert result[0]["jours"] == 5


def test_urgences_excludes_low_score(db):
    from database import load_urgences
    _add_tender(db, "u2", "Travaux divers", score=40, deadline_offset_days=5)

    assert load_urgences(db) == []


def test_urgences_excludes_past_deadline(db):
    from database import load_urgences
    _add_tender(db, "u3", "SSI Lycée", score=80, deadline_offset_days=-1)

    assert load_urgences(db) == []


def test_urgences_excludes_deadline_beyond_30j(db):
    from database import load_urgences
    _add_tender(db, "u4", "CMSI Hôpital", score=80, deadline_offset_days=35)

    assert load_urgences(db) == []


def test_urgences_excludes_gagne_perdu(db):
    from database import load_urgences
    _add_tender(db, "u5", "SSI Mairie", score=80, deadline_offset_days=5, status="Gagné")
    _add_tender(db, "u6", "CMSI Centre", score=80, deadline_offset_days=5, status="Perdu")

    assert load_urgences(db) == []


def test_urgences_excludes_blacklisted(db):
    from database import load_urgences
    _add_tender(db, "u7", "SSI Stade", score=80, deadline_offset_days=5, blacklisted=True)

    assert load_urgences(db) == []


def test_urgences_sorted_by_deadline_asc(db):
    from database import load_urgences
    _add_tender(db, "u8", "SSI A", score=80, deadline_offset_days=20)
    _add_tender(db, "u9", "SSI B", score=80, deadline_offset_days=5)

    result = load_urgences(db)

    assert result[0]["id"] == "u9"
    assert result[1]["id"] == "u8"
```

- [ ] **Step 2: Run tests to verify they fail**

```
python -m pytest tests/test_urgences_pipeline.py -v -k urgences
```

Expected: `AttributeError: module 'database' has no attribute 'load_urgences'`

- [ ] **Step 3: Implement load_urgences() in database.py**

Append to `database.py`:

```python
def load_urgences(db, score_go: int = 65, days_ahead: int = 30) -> list[dict]:
    from models import Tender
    from datetime import datetime as _ddt, timedelta as _td

    today = _ddt.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = today + _td(days=days_ahead)
    rows = (
        db.query(Tender)
        .filter(
            Tender.relevance_score >= score_go,
            Tender.is_blacklisted != True,
            Tender.deadline != None,
            Tender.deadline >= today,
            Tender.deadline <= cutoff,
            ~Tender.status.in_(["Gagné", "Perdu"]),
        )
        .order_by(Tender.deadline.asc())
        .all()
    )
    return [
        {
            "id": t.id,
            "title": t.title,
            "score": t.relevance_score,
            "jours": (t.deadline - today).days,
        }
        for t in rows
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

```
python -m pytest tests/test_urgences_pipeline.py -v -k urgences
```

Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_urgences_pipeline.py
git commit -m "feat: load_urgences() — marchés GO avec deadline dans 30j"
```

---

### Task 4: load_pipeline_data() helper + tests

**Files:**
- Modify: `database.py` (append function)
- Modify: `tests/test_urgences_pipeline.py` (append tests)

- [ ] **Step 1: Append failing tests to tests/test_urgences_pipeline.py**

```python
def test_pipeline_go_contains_high_score_tenders(db):
    from database import load_pipeline_data
    _add_tender(db, "p1", "SSI Prioritaire", score=75, deadline_offset_days=10, status="À qualifier")

    data = load_pipeline_data(db)

    assert "p1" in [t.id for t in data["go"]]
    assert "p1" not in [t.id for t in data["soumis"]]
    assert "p1" not in [t.id for t in data["resultats"]]


def test_pipeline_excludes_low_score_from_go(db):
    from database import load_pipeline_data
    _add_tender(db, "p2", "Divers travaux", score=40, deadline_offset_days=10, status="À qualifier")

    data = load_pipeline_data(db)

    assert "p2" not in [t.id for t in data["go"]]


def test_pipeline_soumis_column(db):
    from database import load_pipeline_data
    _add_tender(db, "p3", "CMSI Hôpital", score=80, deadline_offset_days=10, status="Soumis")

    data = load_pipeline_data(db)

    assert "p3" in [t.id for t in data["soumis"]]
    assert "p3" not in [t.id for t in data["go"]]


def test_pipeline_resultats_column(db):
    from database import load_pipeline_data
    _add_tender(db, "p4", "SSI Gagné", score=80, deadline_offset_days=10, status="Gagné")
    _add_tender(db, "p5", "SSI Perdu", score=80, deadline_offset_days=10, status="Perdu")

    data = load_pipeline_data(db)

    ids = [t.id for t in data["resultats"]]
    assert "p4" in ids
    assert "p5" in ids


def test_pipeline_go_sorted_by_deadline_asc(db):
    from database import load_pipeline_data
    _add_tender(db, "p6", "SSI A", score=80, deadline_offset_days=20)
    _add_tender(db, "p7", "SSI B", score=80, deadline_offset_days=5)

    data = load_pipeline_data(db)

    ids = [t.id for t in data["go"]]
    assert ids.index("p7") < ids.index("p6")
```

- [ ] **Step 2: Run tests to verify they fail**

```
python -m pytest tests/test_urgences_pipeline.py -v -k pipeline
```

Expected: `AttributeError: module 'database' has no attribute 'load_pipeline_data'`

- [ ] **Step 3: Implement load_pipeline_data() in database.py**

Append to `database.py`:

```python
def load_pipeline_data(db, score_go: int = 65) -> dict:
    from models import Tender
    from datetime import datetime as _ddt

    tenders = db.query(Tender).filter(Tender.is_blacklisted != True).all()
    go, soumis, resultats = [], [], []
    for t in tenders:
        if t.status in ("Gagné", "Perdu"):
            resultats.append(t)
        elif t.status == "Soumis":
            soumis.append(t)
        elif t.relevance_score >= score_go:
            go.append(t)

    go.sort(key=lambda t: t.deadline or _ddt.max)
    soumis.sort(key=lambda t: t.deadline or _ddt.max)
    resultats.sort(key=lambda t: t.publication_date or _ddt.min, reverse=True)
    return {"go": go, "soumis": soumis, "resultats": resultats}
```

- [ ] **Step 4: Run all tests to verify they pass**

```
python -m pytest tests/test_urgences_pipeline.py -v
```

Expected: PASS (12 tests)

- [ ] **Step 5: Commit**

```bash
git add database.py tests/test_urgences_pipeline.py
git commit -m "feat: load_pipeline_data() — colonnes GO/Soumis/Résultats"
```

---

### Task 5: Widget Urgences dans app.py

**Files:**
- Modify: `app.py` (insert before `# ── Recherche` section at ~line 1609)

- [ ] **Step 1: Insert the urgences widget in app.py**

Locate the block (around line 1606–1609):

```python
    st.markdown("---")


# ── Recherche ─────────────────────────────────────────────────────────────────
```

Replace it with:

```python
    st.markdown("---")


# ── Widget Urgences ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def _load_urgences_cached() -> list[dict]:
    from database import load_urgences
    db = SessionLocal()
    try:
        return load_urgences(db)
    finally:
        db.close()


def _render_urgences():
    urgences = _load_urgences_cached()
    if not urgences:
        return
    st.markdown("#### ⏰ Marchés GO — délais imminents")
    cols = st.columns(min(len(urgences), 4))
    for col, u in zip(cols, urgences[:4]):
        j = u["jours"]
        if j < 7:
            bg, border, badge = "#fef2f2", "#fecaca", f"🔴 {j}j restants"
        elif j < 15:
            bg, border, badge = "#fffbeb", "#fde68a", f"🟡 {j}j restants"
        else:
            bg, border, badge = "#f0fdf4", "#bbf7d0", f"🟢 {j}j restants"
        title_short = u["title"][:55] + ("…" if len(u["title"]) > 55 else "")
        col.markdown(
            f'<div style="background:{bg};border:1px solid {border};border-radius:8px;'
            f'padding:10px;font-size:0.82rem"><strong>{title_short}</strong><br>'
            f'{badge} · Score : {u["score"]}</div>',
            unsafe_allow_html=True,
        )
    if len(urgences) > 4:
        st.caption(f"… et {len(urgences) - 4} autre(s) marché(s) GO avec deadline dans les 30 jours.")
    st.markdown("---")


_render_urgences()


# ── Recherche ─────────────────────────────────────────────────────────────────
```

- [ ] **Step 2: Launch the app and verify**

```
streamlit run app.py
```

- Widget absent si aucun marché GO avec deadline ≤ 30j
- Si présent : cartes colorées (rouge/orange/vert) avec titre + jours + score
- Max 4 cartes, caption si plus de 4

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat(C): widget urgences délais en haut de la page principale"
```

---

### Task 6: Page Pipeline Kanban

**Files:**
- Create: `pages/pipeline.py`

- [ ] **Step 1: Create pages/pipeline.py**

```python
from datetime import date

import streamlit as st

from database import SessionLocal, init_db, load_pipeline_data
from models import Tender

st.set_page_config(page_title="Pipeline — DEF OI", page_icon="📋", layout="wide")
init_db()

st.markdown("# 📋 Pipeline commercial")
st.caption("Vue Kanban des marchés en cours — transitions de statut en un clic")
st.markdown("---")


def _jours_badge(deadline) -> tuple[str, str]:
    if deadline is None:
        return "⚫ pas de deadline", "#f3f4f6"
    today = date.today()
    dl_date = deadline.date() if hasattr(deadline, "date") else deadline
    days = (dl_date - today).days
    if days < 0:
        return f"⚠️ {abs(days)}j dépassé", "#fef2f2"
    if days < 7:
        return f"🔴 {days}j", "#fef2f2"
    if days <= 30:
        return f"🟡 {days}j", "#fffbeb"
    return f"🟢 {days}j", "#f0fdf4"


def _set_status(tender_id: str, new_status: str):
    db = SessionLocal()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if t:
            t.status = new_status
            db.commit()
    finally:
        db.close()
    st.cache_data.clear()
    st.rerun()


def _card(t: Tender):
    badge, bg = _jours_badge(t.deadline)
    title_short = t.title[:60] + ("…" if len(t.title) > 60 else "")
    st.markdown(
        f'<div style="background:{bg};border:1px solid #e5e7eb;border-radius:8px;'
        f'padding:10px;margin-bottom:6px;font-size:0.82rem">'
        f'<strong>{title_short}</strong><br>'
        f'{badge} · Score : {t.relevance_score}</div>',
        unsafe_allow_html=True,
    )


db = SessionLocal()
try:
    data = load_pipeline_data(db)
finally:
    db.close()

col_go, col_soumis, col_results = st.columns(3)

with col_go:
    st.markdown(f"### ✅ GO ({len(data['go'])})")
    if not data["go"]:
        st.caption("Aucun marché GO en cours.")
    for t in data["go"]:
        _card(t)
        if st.button("Marquer Soumis", key=f"soumis_{t.id}"):
            _set_status(t.id, "Soumis")

with col_soumis:
    st.markdown(f"### 📤 Soumis ({len(data['soumis'])})")
    if not data["soumis"]:
        st.caption("Aucune offre soumise en cours.")
    for t in data["soumis"]:
        _card(t)
        c1, c2 = st.columns(2)
        if c1.button("Gagné 🏆", key=f"gagne_{t.id}"):
            _set_status(t.id, "Gagné")
        if c2.button("Perdu", key=f"perdu_{t.id}"):
            _set_status(t.id, "Perdu")

with col_results:
    st.markdown("### 🏆 Résultats")
    gagnes = [t for t in data["resultats"] if t.status == "Gagné"]
    perdus = [t for t in data["resultats"] if t.status == "Perdu"]
    if not gagnes and not perdus:
        st.caption("Aucun résultat enregistré.")
    if gagnes:
        st.markdown("**Gagné**")
        for t in gagnes:
            _card(t)
    if perdus:
        st.markdown("**Perdu**")
        for t in perdus:
            _card(t)

st.markdown("---")
st.page_link("app.py", label="← Retour à la veille marchés")
```

- [ ] **Step 2: Launch the app and verify**

```
streamlit run app.py
```

- Page "Pipeline" accessible depuis la navigation Streamlit
- 3 colonnes GO / Soumis / Résultats s'affichent
- "Marquer Soumis" sur une carte GO → la carte disparaît de GO et apparaît dans Soumis (rerun immédiat)
- "Gagné 🏆" / "Perdu" sur une carte Soumis → la carte passe dans Résultats
- Colonnes Gagné / Perdu sous-groupées dans la colonne Résultats

- [ ] **Step 3: Commit**

```bash
git add pages/pipeline.py
git commit -m "feat(B): page Pipeline Kanban — GO/Soumis/Résultats avec transitions de statut"
```

---

### Task 7: Section Doublons dans Paramètres

**Files:**
- Modify: `pages/parametres.py` (append at end, after line 451)

- [ ] **Step 1: Append section to pages/parametres.py**

```python
# ── Détection de doublons ─────────────────────────────────────────────────────

st.header("🔍 Doublons détectés")
st.caption("Marchés collectés depuis plusieurs sources avec un titre similaire (≥ 80 %) et la même deadline (±3 jours).")

from database import detect_duplicates as _detect_dups, SessionLocal as _SL_dd
from models import Tender as _Tender_dd, DuplicateCandidate as _DC
from sqlalchemy import or_ as _or_dd, and_ as _and_dd


def _get_unresolved_pairs():
    _db = _SL_dd()
    try:
        pairs = _db.query(_DC).filter(_DC.resolved == False).all()
        result = []
        for p in pairs:
            a = _db.query(_Tender_dd).filter(_Tender_dd.id == p.tender_id_a).first()
            b = _db.query(_Tender_dd).filter(_Tender_dd.id == p.tender_id_b).first()
            if a and b:
                result.append((p, a, b))
        return result
    finally:
        _db.close()


def _merge_pair(keep_id: str, archive_id: str, pair_id: int):
    _db = _SL_dd()
    try:
        archive = _db.query(_Tender_dd).filter(_Tender_dd.id == archive_id).first()
        if archive:
            archive.is_blacklisted = True
        pair = _db.query(_DC).filter(_DC.id == pair_id).first()
        if pair:
            pair.resolved = True
        _db.commit()
    finally:
        _db.close()
    st.rerun()


def _ignore_pair(pair_id: int):
    _db = _SL_dd()
    try:
        pair = _db.query(_DC).filter(_DC.id == pair_id).first()
        if pair:
            pair.resolved = True
        _db.commit()
    finally:
        _db.close()
    st.rerun()


if st.button("🔍 Détecter les doublons", key="run_detect_duplicates"):
    with st.spinner("Analyse en cours…"):
        _db2 = _SL_dd()
        try:
            nb = _detect_dups(_db2)
        finally:
            _db2.close()
    if nb:
        st.success(f"{nb} nouvelle(s) paire(s) détectée(s).")
    else:
        st.info("Aucun nouveau doublon détecté.")

_pairs = _get_unresolved_pairs()

if not _pairs:
    st.caption("Aucun doublon à traiter.")
else:
    st.markdown(f"**{len(_pairs)} paire(s) à examiner**")
    for _pair, _a, _b in _pairs:
        with st.expander(f"Paire #{_pair.id} — similarité {_pair.similarity_score:.0%}", expanded=True):
            _recommended = _a if _a.relevance_score >= _b.relevance_score else _b
            _other = _b if _recommended.id == _a.id else _a

            _ca, _cb = st.columns(2)
            for _col, _tender, _label in [
                (_ca, _recommended, "✅ Recommandé à conserver"),
                (_cb, _other, ""),
            ]:
                with _col:
                    if _label:
                        st.success(_label)
                    st.markdown(f"**{_tender.title}**")
                    st.caption(f"Source : {_tender.source} · Score : {_tender.relevance_score}")
                    if _tender.deadline:
                        st.caption(f"Deadline : {_tender.deadline.strftime('%d/%m/%Y')}")

            _c1, _c2, _c3 = st.columns(3)
            if _c1.button(f"Garder {_a.source[:12]} — archiver {_b.source[:12]}", key=f"keep_a_{_pair.id}"):
                _merge_pair(keep_id=_a.id, archive_id=_b.id, pair_id=_pair.id)
            if _c2.button(f"Garder {_b.source[:12]} — archiver {_a.source[:12]}", key=f"keep_b_{_pair.id}"):
                _merge_pair(keep_id=_b.id, archive_id=_a.id, pair_id=_pair.id)
            if _c3.button("Ignorer", key=f"ignore_{_pair.id}"):
                _ignore_pair(_pair.id)
```

- [ ] **Step 2: Launch the app and verify**

```
streamlit run app.py
```

Naviguer vers Paramètres → section "🔍 Doublons détectés" :
- Bouton "Détecter les doublons" lance l'analyse et affiche le nombre de paires trouvées
- Chaque paire s'affiche avec les deux marchés côte-à-côte, le recommandé mis en évidence (vert)
- "Garder X — archiver Y" → Y disparaît de la liste principale, la paire disparaît de la liste
- "Ignorer" → la paire disparaît sans archivage

- [ ] **Step 3: Commit**

```bash
git add pages/parametres.py
git commit -m "feat(D): détection et fusion de doublons dans Paramètres"
```
