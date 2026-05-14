import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture
def engine():
    from source_registry import Source  # noqa: registers Source
    from models import ScraperRun       # noqa: registers ScraperRun
    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(engine):
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def test_scraper_run_table_exists(engine):
    inspector = inspect(engine)
    assert "scraper_runs" in inspector.get_table_names()


def test_scraper_run_columns(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("scraper_runs")}
    assert {"id", "source_name", "started_at", "finished_at",
            "nb_found", "nb_new", "error", "status"} <= cols


def test_tender_has_tags_column(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("tenders")}
    assert "tags" in cols


def test_source_has_ping_columns(engine):
    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("sources")}
    assert "ping_failures_count" in cols
    assert "last_ping_at" in cols
