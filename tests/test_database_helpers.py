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


def test_start_scraper_run_creates_record(db):
    from database import start_scraper_run
    from models import ScraperRun
    run_id = start_scraper_run(db, "BOAMP — Journal Officiel")
    assert isinstance(run_id, int)
    record = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    assert record is not None
    assert record.source_name == "BOAMP — Journal Officiel"
    assert record.status == "running"
    assert record.started_at is not None


def test_finish_scraper_run_ok(db):
    from database import start_scraper_run, finish_scraper_run
    from models import ScraperRun
    run_id = start_scraper_run(db, "TED Europe")
    finish_scraper_run(db, run_id, nb_found=10, nb_new=3)
    record = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    assert record.status == "ok"
    assert record.nb_found == 10
    assert record.nb_new == 3
    assert record.finished_at is not None
    assert record.error is None


def test_finish_scraper_run_error(db):
    from database import start_scraper_run, finish_scraper_run
    from models import ScraperRun
    run_id = start_scraper_run(db, "VAAO")
    finish_scraper_run(db, run_id, nb_found=0, nb_new=0, error="Connection timeout")
    record = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    assert record.status == "error"
    assert record.error == "Connection timeout"


def test_finish_scraper_run_invalid_id_does_not_raise(db):
    from database import finish_scraper_run
    finish_scraper_run(db, run_id=99999, nb_found=0, nb_new=0)


def test_load_existing_ids_empty_db(db):
    from scraper_utils import load_existing_ids
    ids = load_existing_ids(db)
    assert isinstance(ids, set)
    assert len(ids) == 0


def test_insert_if_new_adds_tender(db):
    from scraper_utils import load_existing_ids, insert_if_new
    from models import Tender
    t = Tender(id="X-001", title="Test", source="https://example.com",
               status="À qualifier", relevance_score=0, is_blacklisted=False)
    existing = load_existing_ids(db)
    inserted = insert_if_new(db, t, existing)
    assert inserted is True
    assert "X-001" in existing


def test_insert_if_new_skips_duplicate(db):
    from scraper_utils import load_existing_ids, insert_if_new
    from models import Tender
    t1 = Tender(id="X-002", title="Test", source="https://example.com",
                status="À qualifier", relevance_score=0, is_blacklisted=False)
    t2 = Tender(id="X-002", title="Test bis", source="https://example.com",
                status="À qualifier", relevance_score=0, is_blacklisted=False)
    existing = load_existing_ids(db)
    insert_if_new(db, t1, existing)
    inserted_second = insert_if_new(db, t2, existing)
    assert inserted_second is False


def test_reset_tenders_db_vide_les_trois_tables(db, make_tender):
    from models import ScraperRun, DuplicateCandidate
    from datetime import datetime
    from database import reset_tenders_db

    # Populate
    make_tender(id="T-RESET-1")
    make_tender(id="T-RESET-2")
    db.add(ScraperRun(source_name="test", started_at=datetime.utcnow(), status="done"))
    db.add(DuplicateCandidate(
        tender_id_a="T-RESET-1", tender_id_b="T-RESET-2",
        similarity_score=0.9, detected_at=datetime.utcnow(),
    ))
    db.flush()

    nb = reset_tenders_db(db)

    from models import Tender
    assert db.query(Tender).count() == 0
    assert db.query(ScraperRun).count() == 0
    assert db.query(DuplicateCandidate).count() == 0
    assert nb == 2  # nombre de tenders supprimés


def test_reset_tenders_db_preserve_sources(db):
    from database import reset_tenders_db
    from source_registry import Source

    nb_sources_avant = db.query(Source).count()
    reset_tenders_db(db)
    assert db.query(Source).count() == nb_sources_avant
