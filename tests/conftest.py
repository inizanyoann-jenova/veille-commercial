import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Tender


@pytest.fixture(scope="session")
def engine():
    import source_registry  # noqa: registers Source model
    from models import ScraperRun  # noqa: registers ScraperRun model
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    """Session with per-test rollback — no data leaks between tests."""
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def make_tender(db):
    """Factory: make_tender(id="T1", title="...", **kwargs) → Tender added to db."""
    _counter = [0]

    def _factory(**kwargs):
        _counter[0] += 1
        defaults = {
            "id": f"TEST-{_counter[0]:04d}",
            "title": "Marché test",
            "description": "Description test",
            "source": "https://example.com",
            "publication_date": None,
            "deadline": None,
            "status": "À qualifier",
            "relevance_score": 0,
            "is_maintenance": False,
            "llm_analysis": None,
            "secteur": "Public",
            "type_opportunite": "Marché Public",
            "is_blacklisted": False,
            "amount": None,
            "tags": None,
        }
        defaults.update(kwargs)
        t = Tender(**defaults)
        db.add(t)
        db.flush()
        return t

    return _factory
