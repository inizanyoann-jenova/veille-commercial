import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime


def test_simhash_returns_int():
    from database import _simhash
    h = _simhash("hello world")
    assert isinstance(h, int)


def test_simhash_64_bits():
    from database import _simhash
    h = _simhash("test text")
    assert 0 <= h < (1 << 64)


def test_simhash_deterministic():
    from database import _simhash
    text = "Installation système SSI détection incendie bâtiment A"
    assert _simhash(text) == _simhash(text)


def test_simhash_empty_string():
    from database import _simhash
    h = _simhash("")
    assert isinstance(h, int)


def test_hamming_distance_identical():
    from database import _hamming_distance
    assert _hamming_distance(0xABCDEF, 0xABCDEF) == 0


def test_hamming_distance_one_bit():
    from database import _hamming_distance
    assert _hamming_distance(0b1000, 0b1001) == 1


def test_hamming_distance_max():
    from database import _hamming_distance
    assert _hamming_distance(0, (1 << 64) - 1) == 64


def test_simhash_similar_texts_close_hamming():
    from database import _simhash, _hamming_distance
    h1 = _simhash("Installation SSI bâtiment A Réunion 2026")
    h2 = _simhash("Installation SSI bâtiment A Réunion 2026 marché public")
    assert _hamming_distance(h1, h2) < 20


def test_simhash_different_texts_far_hamming():
    from database import _simhash, _hamming_distance
    h1 = _simhash("Installation système SSI détection incendie")
    h2 = _simhash("Permis construire lotissement résidentiel voirie")
    assert _hamming_distance(h1, h2) > 8


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make(db, id, title, source, deadline=None):
    from models import Tender
    t = Tender(
        id=id,
        title=title,
        description="",
        source=source,
        publication_date=datetime(2026, 1, 15),
        deadline=deadline,
        status="À qualifier",
        relevance_score=50,
        is_blacklisted=False,
        tags=[],
        secteur="Public",
    )
    db.add(t)
    db.flush()
    return t


def test_detect_duplicates_identical_titles_different_sources(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Installation système SSI détection incendie bâtiment A", "boamp", dl)
    _make(db, "B1", "Installation système SSI détection incendie bâtiment A", "decp", dl)

    n = detect_duplicates(db)
    assert n >= 1


def test_detect_duplicates_same_source_not_flagged(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Installation système SSI détection incendie", "boamp", dl)
    _make(db, "A2", "Installation système SSI détection incendie", "boamp", dl)

    n = detect_duplicates(db)
    assert n == 0


def test_detect_duplicates_different_deadlines_not_flagged(db):
    from database import detect_duplicates

    _make(db, "A1", "Installation système SSI incendie bâtiment A", "boamp", datetime(2026, 8, 1))
    _make(db, "B1", "Installation système SSI incendie bâtiment A", "decp", datetime(2026, 9, 15))

    n = detect_duplicates(db)
    assert n == 0


def test_detect_duplicates_completely_different_titles(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Permis construire lotissement résidentiel voirie", "boamp", dl)
    _make(db, "B1", "Installation vidéosurveillance CCTV parking souterrain", "decp", dl)

    n = detect_duplicates(db)
    assert n == 0


def test_detect_duplicates_max_tenders_param(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    for i in range(10):
        _make(db, f"T{i}", f"Marché SSI bâtiment {i}", f"source_{i}", dl)

    n = detect_duplicates(db, max_tenders=5)
    assert isinstance(n, int)


def test_detect_duplicates_no_duplicate_twice(db):
    from database import detect_duplicates

    dl = datetime(2026, 8, 15)
    _make(db, "A1", "Installation système SSI incendie bâtiment complet", "boamp", dl)
    _make(db, "B1", "Installation système SSI incendie bâtiment complet", "decp", dl)

    n1 = detect_duplicates(db)
    n2 = detect_duplicates(db)
    assert n1 >= 1
    assert n2 == 0
