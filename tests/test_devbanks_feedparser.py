import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch


def _make_bozo_feed():
    """feedparser retourne un feed bozo (erreur réseau) avec entries vide."""
    feed = MagicMock()
    feed.entries = []
    feed.bozo = True
    feed.bozo_exception = ConnectionError("Unreachable")
    return feed


def test_devbanks_skips_bozo_feed_silently(monkeypatch):
    """Quand feedparser retourne un feed bozo (erreur réseau), le scraper skip sans lever."""
    import scraper_devbanks

    monkeypatch.setattr(
        "scraper_devbanks.feedparser.parse", lambda url: _make_bozo_feed()
    )
    result = scraper_devbanks.fetch()
    assert result == []


def test_devbanks_skips_empty_feed(monkeypatch):
    """Un feed vide sans erreur est également ignoré silencieusement."""
    import scraper_devbanks

    empty_feed = MagicMock()
    empty_feed.entries = []
    empty_feed.bozo = False
    monkeypatch.setattr(
        "scraper_devbanks.feedparser.parse", lambda url: empty_feed
    )
    result = scraper_devbanks.fetch()
    assert result == []
