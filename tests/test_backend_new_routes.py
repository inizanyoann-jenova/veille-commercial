import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend"))

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base


@pytest.fixture(scope="module")
def _engine():
    from models import ScraperRun, DuplicateCandidate  # noqa

    e = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(e)
    return e


@pytest.fixture
def db(_engine):
    Session = sessionmaker(bind=_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


# ── GET /api/health ────────────────────────────────────────────────────────────


def test_health_returns_ok_structure():
    import main as bm

    mock_r = MagicMock(ok=True, http_status=200, error=None)
    with patch("main.run_all_health_checks", return_value={"BOAMP": mock_r}):
        result = bm.health()
    assert result["status"] == "ok"
    assert "BOAMP" in result["sources"]
    assert result["sources"]["BOAMP"]["ok"] is True
    assert result["sources"]["BOAMP"]["http_status"] == 200


# ── POST /api/sources ──────────────────────────────────────────────────────────


def test_create_source_returns_id_and_name(db):
    import main as bm

    body = bm.SourceCreate(
        name="Test Source", url="https://example.com", category="Public"
    )
    result = bm.create_source(src=body, db=db)
    assert result["name"] == "Test Source"
    assert "id" in result


# ── DELETE /api/sources/{id} ──────────────────────────────────────────────────


def test_delete_manual_source_returns_ok(db):
    import main as bm
    from source_registry import add_source

    s = add_source(db, name="À supprimer", url="https://del.com", category="Privé")
    result = bm.delete_source(source_id=s.id, db=db)
    assert result == {"ok": True}


def test_delete_source_with_scraper_raises_400(db):
    import main as bm
    from fastapi import HTTPException
    from models import Source

    s = Source(
        name="Scraper Source",
        url="https://scraper.com",
        category="Public",
        scraper_module="scraper_boamp",
        scraper_func="fetch_boamp_tenders",
    )
    db.add(s)
    db.flush()
    with pytest.raises(HTTPException) as exc_info:
        bm.delete_source(source_id=s.id, db=db)
    assert exc_info.value.status_code == 400


# ── PATCH /api/sources/{id}/toggle ────────────────────────────────────────────


def test_toggle_source_flips_enabled_state(db):
    import main as bm
    from source_registry import add_source

    s = add_source(db, name="Toggle Test", url="https://toggle.com", category="Privé")
    initial = s.enabled
    result = bm.toggle_source(source_id=s.id, db=db)
    assert result["enabled"] == (not initial)


def test_toggle_nonexistent_source_raises_404(db):
    import main as bm
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        bm.toggle_source(source_id=99999, db=db)
    assert exc_info.value.status_code == 404


# ── GET /api/export/excel ──────────────────────────────────────────────────────


def test_export_excel_returns_xlsx_response(db):
    import main as bm

    fake_xlsx = b"PK\x03\x04fake_xlsx_content"
    with patch("main.generate_executive_report", return_value=fake_xlsx):
        response = bm.export_excel(db=db)
    assert response.body == fake_xlsx
    assert "spreadsheetml" in response.media_type
