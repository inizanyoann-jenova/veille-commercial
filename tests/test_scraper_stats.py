import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from datetime import datetime, timedelta
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


def test_scraper_stats_empty_db(db):
    from database import get_scraper_stats

    stats = get_scraper_stats(db)
    assert stats == []


def test_scraper_stats_one_ok_run(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id = start_scraper_run(db, "boamp")
    finish_scraper_run(db, run_id, nb_found=10, nb_new=5)

    stats = get_scraper_stats(db)
    assert len(stats) == 1
    s = stats[0]
    assert s["source_name"] == "boamp"
    assert s["runs_30j"] == 1
    assert s["runs_ok"] == 1
    assert s["runs_empty"] == 0


def test_scraper_stats_empty_run(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id = start_scraper_run(db, "decp")
    finish_scraper_run(db, run_id, nb_found=3, nb_new=0)

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["runs_empty"] == 1
    assert s["runs_ok"] == 1


def test_scraper_stats_error_run(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id = start_scraper_run(db, "vaao")
    finish_scraper_run(db, run_id, nb_found=0, nb_new=0, error="Timeout")

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["runs_ok"] == 0
    assert s["runs_30j"] == 1


def test_scraper_stats_avg_duration(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats
    from models import ScraperRun

    run_id = start_scraper_run(db, "ted")
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    run.finished_at = run.started_at + timedelta(seconds=42)
    db.commit()

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["avg_duration_s"] == pytest.approx(42.0, abs=1.0)


def test_scraper_stats_excludes_old_runs(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats
    from models import ScraperRun

    run_id = start_scraper_run(db, "boamp")
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    run.started_at = datetime.utcnow() - timedelta(days=35)
    run.finished_at = run.started_at + timedelta(seconds=10)
    run.status = "ok"
    db.commit()

    stats = get_scraper_stats(db)
    assert stats == []


def test_scraper_stats_last_run_at(db):
    from database import start_scraper_run, finish_scraper_run, get_scraper_stats

    run_id1 = start_scraper_run(db, "boamp")
    finish_scraper_run(db, run_id1, nb_found=5, nb_new=2)
    run_id2 = start_scraper_run(db, "boamp")
    finish_scraper_run(db, run_id2, nb_found=3, nb_new=1)

    stats = get_scraper_stats(db)
    s = stats[0]
    assert s["last_run_at"] is not None
    assert s["runs_30j"] == 2
