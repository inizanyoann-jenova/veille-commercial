from datetime import datetime
from models import Tender
from scraper_utils import now_utc


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
    t = Tender(id="TEST-002", title="T", source="http://x.com",
               publication_date=pub, date_extraction=ext)
    assert t.publication_date != t.date_extraction
    assert (ext - pub).days > 0   # extraction is always after publication


def test_now_utc_returns_naive_utc_datetime():
    result = now_utc()
    assert isinstance(result, datetime)
    assert result.tzinfo is None   # SQLite-compatible: no timezone info
    # Must be close to current time (within 5 seconds)
    from datetime import datetime as _dt, timezone as _tz
    diff = abs((_dt.now(_tz.utc).replace(tzinfo=None) - result).total_seconds())
    assert diff < 5


def test_afd_build_tender_uses_real_publication_date():
    import scraper_afd
    rec = {
        "iati_identifier": "FR-6-1234",
        "title_narrative": "Projet test",
        "description": "infrastructure santé",
        "date_dachevement": "2027-06-30",
        "date_octroi": "2024-03-15",
    }
    t = scraper_afd._build_tender(rec, "Madagascar")
    assert t.publication_date is not None
    assert t.publication_date.year == 2024   # real source date, not today
    assert t.date_extraction is not None
    assert t.date_extraction.year == 2026    # collected today


def test_afd_build_tender_date_extraction_is_naive():
    import scraper_afd
    rec = {
        "iati_identifier": "FR-6-5678",
        "title_narrative": "Autre projet",
        "description": "santé",
        "date_dachevement": "2027-01-01",
        "date_octroi": "2023-06-01",
    }
    t = scraper_afd._build_tender(rec, "Maurice")
    assert t.date_extraction.tzinfo is None  # SQLite-compatible
