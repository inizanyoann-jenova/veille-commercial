import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock
from scraper_utils import parse_rss_date


def _entry(published=None, updated=None, published_parsed=None, updated_parsed=None):
    """Construit un faux entry feedparser."""
    e = MagicMock()
    e.published = published
    e.updated = updated
    e.published_parsed = published_parsed
    e.updated_parsed = updated_parsed
    # feedparser entries exposent get() comme un dict
    e.get.side_effect = lambda k, d=None: {
        "published_parsed": published_parsed,
        "updated_parsed": updated_parsed,
    }.get(k, d)
    return e


def test_parse_rss_date_from_published_rfc2822():
    """Format RFC 2822 standard (email.utils.parsedate_to_datetime)."""
    e = _entry(published="Mon, 20 Jan 2026 08:00:00 +0000")
    result = parse_rss_date(e)
    assert result == "2026-01-20"


def test_parse_rss_date_falls_back_to_updated():
    """Sans published, utilise updated."""
    e = _entry(published=None, updated="Fri, 15 May 2026 12:00:00 +0200")
    result = parse_rss_date(e)
    assert result == "2026-05-15"


def test_parse_rss_date_falls_back_to_parsed_tuple():
    """Si la string RFC échoue, utilise published_parsed (time.struct_time)."""
    e = _entry(published="invalid", published_parsed=(2026, 3, 10, 0, 0, 0, 0, 0, 0))
    result = parse_rss_date(e)
    assert result == "2026-03-10"


def test_parse_rss_date_returns_empty_when_no_date():
    """Sans aucune date exploitable, retourne chaîne vide."""
    e = _entry()
    result = parse_rss_date(e)
    assert result == ""


def test_devbanks_uses_parse_rss_date():
    """scraper_devbanks doit importer parse_rss_date de scraper_utils."""
    import scraper_devbanks
    assert hasattr(scraper_devbanks, "parse_rss_date"), (
        "scraper_devbanks n'importe pas parse_rss_date depuis scraper_utils"
    )


def test_presse_uses_parse_rss_date():
    """scraper_presse doit importer parse_rss_date de scraper_utils."""
    import scraper_presse
    assert hasattr(scraper_presse, "parse_rss_date"), (
        "scraper_presse n'importe pas parse_rss_date depuis scraper_utils"
    )
