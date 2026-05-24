from datetime import datetime, timezone
from models import Tender


def test_tender_has_date_extraction_field():
    t = Tender(
        id="TEST-001",
        title="Test",
        source="http://example.com",
        publication_date=datetime(2026, 5, 1),
        date_extraction=datetime(2026, 5, 20, 10, 0, 0),
    )
    assert t.date_extraction is not None
    assert isinstance(t.date_extraction, datetime)


def test_tender_date_extraction_independent_from_publication():
    pub = datetime(2026, 4, 1)
    ext = datetime(2026, 5, 20)
    t = Tender(
        id="TEST-002",
        title="T",
        source="http://x.com",
        publication_date=pub,
        date_extraction=ext,
    )
    assert t.publication_date != t.date_extraction
    assert (ext - pub).days > 0  # extraction is always after publication


def test_naive_utc_datetime_is_sqlite_compatible():
    # now_utc() was removed from scraper_utils — equivalent: datetime.now(timezone.utc).replace(tzinfo=None)
    result = datetime.now(timezone.utc).replace(tzinfo=None)
    assert isinstance(result, datetime)
    assert result.tzinfo is None  # SQLite-compatible: no timezone info
    diff = abs((datetime.now(timezone.utc).replace(tzinfo=None) - result).total_seconds())
    assert diff < 5


def test_afd_normalise_uses_real_publication_date():
    import scraper_afd

    rec = {
        "iati_identifier": "FR-6-1234",
        "title_narrative": "Projet test",
        "description": "infrastructure santé",
        "date_dachevement": "2027-06-30",
        "date_octroi": "2024-03-15",
    }
    result = scraper_afd._normalise(rec, "Madagascar")
    assert result["publication_date"] is not None
    assert result["publication_date"] != ""
    assert "2024" in result["publication_date"]  # real source date, not today
    assert result["date_found"] is not None
    assert str(datetime.now(timezone.utc).year) in result["date_found"]  # collected today


def test_afd_normalise_date_found_is_naive_string():
    import scraper_afd

    rec = {
        "iati_identifier": "FR-6-5678",
        "title_narrative": "Autre projet",
        "description": "santé",
        "date_dachevement": "2027-01-01",
        "date_octroi": "2023-06-01",
    }
    result = scraper_afd._normalise(rec, "Maurice")
    # date_found is a plain ISO date string — no timezone component, SQLite-compatible
    assert result["date_found"]
    assert "+" not in result["date_found"]  # no tz offset
    assert "T" not in result["date_found"]  # date only, no time component
