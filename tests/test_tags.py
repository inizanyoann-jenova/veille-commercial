import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Tender


@pytest.fixture
def db():
    from source_registry import Source  # noqa
    from models import ScraperRun       # noqa
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    t = Tender(id="test-1", title="Test SSI", tags=[])
    session.add(t)
    session.commit()
    yield session
    session.close()


def test_tender_tags_default_empty(db):
    t = db.query(Tender).filter(Tender.id == "test-1").first()
    assert t.tags == [] or t.tags is None


def test_tender_tags_field_exists(db):
    from models import Tender as T
    assert hasattr(T, "tags")
