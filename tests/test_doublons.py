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
