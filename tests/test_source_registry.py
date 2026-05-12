import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    # Import Source après Base pour enregistrer le modèle
    from source_registry import Source
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_init_sources_populates_table(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    sources = list_sources(db)
    assert len(sources) >= 9  # au moins les sources existantes + nouvelles


def test_init_sources_is_idempotent(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    init_sources(db)  # deuxième appel ne doit pas dupliquer
    sources = list_sources(db)
    names = [s.name for s in sources]
    assert len(names) == len(set(names))


def test_list_sources_by_category(db):
    from source_registry import init_sources, list_sources
    init_sources(db)
    public = list_sources(db, category="Public")
    assert all(s.category == "Public" for s in public)
    assert len(public) >= 3


def test_add_source(db):
    from source_registry import init_sources, add_source, list_sources
    init_sources(db)
    before = len(list_sources(db))
    add_source(db, name="Test Source", url="https://example.com", category="Public")
    after = len(list_sources(db))
    assert after == before + 1


def test_remove_manual_source(db):
    from source_registry import init_sources, add_source, remove_source, list_sources
    init_sources(db)
    s = add_source(db, name="À supprimer", url="https://example.com", category="Privé")
    result = remove_source(db, s.id)
    assert result is True
    assert all(src.name != "À supprimer" for src in list_sources(db))


def test_remove_auto_source_is_blocked(db):
    from source_registry import init_sources, list_sources, remove_source
    init_sources(db)
    auto_sources = [s for s in list_sources(db) if s.scraper_module is not None]
    assert len(auto_sources) > 0
    result = remove_source(db, auto_sources[0].id)
    assert result is False  # protection


def test_toggle_enabled(db):
    from source_registry import init_sources, list_sources, toggle_enabled
    init_sources(db)
    source = list_sources(db)[0]
    original = source.enabled
    toggle_enabled(db, source.id)
    db.refresh(source)
    assert source.enabled != original
