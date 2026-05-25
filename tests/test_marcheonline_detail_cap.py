import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch


def _make_pw_mock():
    mock_page = MagicMock()
    mock_page.url = "https://www.marchesonline.com/results"
    mock_page.content.return_value = "<html></html>"

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw, mock_page


def _many_candidates(n: int) -> list[dict]:
    return [
        {
            "title": f"Marché SSI n°{i}",
            "url": f"https://www.marchesonline.com/ao/{i}",
            "description": "",
            "date": "2026-01-01",
            "deadline": "",
        }
        for i in range(n)
    ]


def test_marcheonline_has_max_details_constant():
    """_MAX_DETAILS doit être défini comme constante dans le module."""
    import scraper_marcheonline

    assert hasattr(scraper_marcheonline, "_MAX_DETAILS"), (
        "scraper_marcheonline doit exposer _MAX_DETAILS pour limiter les visites détail"
    )
    assert scraper_marcheonline._MAX_DETAILS > 0


def test_marcheonline_caps_detail_fetches(monkeypatch):
    """Avec plus de _MAX_DETAILS candidats, _extract_detail ne doit pas être appelé plus de _MAX_DETAILS fois."""
    import scraper_marcheonline

    cap = scraper_marcheonline._MAX_DETAILS
    n_candidates = cap + 20  # volontairement au-delà du cap

    mock_pw, mock_page = _make_pw_mock()
    detail_calls = []

    def fake_extract_detail(page, url):
        detail_calls.append(url)
        return ""

    monkeypatch.setattr(
        scraper_marcheonline, "_extract_from_comments", lambda html: _many_candidates(n_candidates)
    )
    monkeypatch.setattr(
        scraper_marcheonline, "_get_next_url", lambda html: None
    )
    monkeypatch.setattr(
        scraper_marcheonline, "_extract_detail", fake_extract_detail
    )

    with patch("scraper_marcheonline.sync_playwright", return_value=mock_pw):
        scraper_marcheonline.fetch()

    assert len(detail_calls) <= cap, (
        f"_extract_detail appelé {len(detail_calls)} fois — "
        f"doit être plafonné à _MAX_DETAILS={cap}"
    )


def test_marcheonline_detail_all_fetched_below_cap(monkeypatch):
    """En dessous du cap, tous les candidats sont enrichis."""
    import scraper_marcheonline

    cap = scraper_marcheonline._MAX_DETAILS
    n_urls = len(scraper_marcheonline._URLS)
    # 3 candidats par URL → total bien en dessous du cap
    n_per_url = 3
    n_total = n_per_url * n_urls

    mock_pw, mock_page = _make_pw_mock()
    detail_calls = []

    monkeypatch.setattr(
        scraper_marcheonline, "_extract_from_comments", lambda html: _many_candidates(n_per_url)
    )
    monkeypatch.setattr(
        scraper_marcheonline, "_get_next_url", lambda html: None
    )
    monkeypatch.setattr(
        scraper_marcheonline, "_extract_detail",
        lambda page, url: detail_calls.append(url) or ""
    )

    with patch("scraper_marcheonline.sync_playwright", return_value=mock_pw):
        scraper_marcheonline.fetch()

    assert len(detail_calls) == n_total, (
        f"En dessous du cap ({n_total} < {cap}), tous les candidats doivent être enrichis, "
        f"mais _extract_detail n'a été appelé que {len(detail_calls)} fois"
    )
