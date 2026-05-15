import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def db():
    from source_registry import Source  # noqa
    from models import ScraperRun       # noqa
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    from source_registry import Source
    s = Source(
        name="Test Source", url="https://example.com",
        category="Public", is_validated=True,
        ping_failures_count=0, last_ping_at=None,
    )
    session.add(s)
    session.commit()
    yield session
    session.close()


def test_ping_success_resets_failures(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 2

    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("source_registry.requests.get", return_value=mock_resp):
        result = _ping_source(db, source)

    assert result is True
    assert source.ping_failures_count == 0
    assert source.last_ping_at is not None


def test_ping_failure_increments_counter(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 1

    with patch("source_registry.requests.get", side_effect=Exception("timeout")):
        result = _ping_source(db, source)

    assert result is False
    assert source.ping_failures_count == 2
    assert source.is_validated is True  # not 3 failures yet


def test_ping_3_failures_invalidates_source(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 2

    with patch("source_registry.requests.get", side_effect=Exception("timeout")):
        result = _ping_source(db, source)

    assert result is False
    assert source.ping_failures_count == 3
    assert source.is_validated is False


def test_ping_http_4xx_increments_failures(db):
    from source_registry import _ping_source, Source
    source = db.query(Source).filter(Source.name == "Test Source").first()
    source.ping_failures_count = 0

    mock_resp = MagicMock()
    mock_resp.status_code = 403

    with patch("source_registry.requests.get", return_value=mock_resp):
        result = _ping_source(db, source)

    assert result is False
    assert source.ping_failures_count == 1
