import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock


# ── Tests scraper_decp ─────────────────────────────────────────────────────


def test_fetch_decp_returns_empty_on_empty_response():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    import scraper_decp

    with patch("requests.get", return_value=mock_resp):
        result = scraper_decp.fetch()
    assert result == []


def test_fetch_decp_returns_relevant_record():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "id": "DECP-TEST-001",
                "objetmarche": "Maintenance SSI alarme incendie La Réunion",
                "nomacheteur": "CHU Réunion",
                "datenotification": "2025-03-01",
                "montant": 50000,
                "urlpublication": "https://data.economie.gouv.fr/test",
                "codedepartementexecution": "974",
            }
        ],
        "total_count": 1,
    }

    import scraper_decp

    with patch("requests.get", return_value=mock_resp):
        result = scraper_decp.fetch()

    assert len(result) == 1
    assert "SSI" in result[0]["name"] or "incendie" in result[0]["name"].lower()


def test_fetch_decp_includes_erp_via_construction_filter():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "id": "DECP-ERP-001",
                "objetmarche": "Construction d'un nouveau collège à La Réunion",
                "nomacheteur": "Département de La Réunion",
                "datenotification": "2026-05-01",
                "codedepartementexecution": "974",
            }
        ],
        "total_count": 1,
    }

    import scraper_decp

    with patch("requests.get", return_value=mock_resp) as req:
        result = scraper_decp.fetch()

    where_clause = req.call_args.kwargs["params"]["where"]
    assert "construction" in where_clause
    assert "collège" in where_clause
    assert len(result) == 1


# ── Tests scraper_ungm ─────────────────────────────────────────────────────


def test_fetch_ungm_returns_empty_on_no_results():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # json() returns a MagicMock — neither list nor dict → _search_ungm returns []
    mock_resp.json.return_value = []

    import scraper_ungm

    with patch("requests.post", return_value=mock_resp):
        result = scraper_ungm.fetch()
    assert result == []


# ── Tests scraper_ted ─────────────────────────────────────────────────────────


def test_ted_api_url_is_v3():
    import importlib
    import scraper_ted

    importlib.reload(scraper_ted)
    assert scraper_ted.TED_API_URL == "https://api.ted.europa.eu/v3/notices/search"


def test_ted_mayotte_query_includes_city_variants():
    import importlib
    import scraper_ted

    importlib.reload(scraper_ted)
    q = scraper_ted.QUERIES["Mayotte"]
    assert "Mamoudzou" in q
    assert "Dzaoudzi" in q
    assert "Mahorais" in q


def test_ted_public_search_includes_cpv():
    import importlib
    import scraper_ted

    importlib.reload(scraper_ted)
    assert "PC=45312100" in scraper_ted._PUBLIC_SEARCH
    assert "PC=50610000" in scraper_ted._PUBLIC_SEARCH


def test_ted_fetch_sends_date_filter():
    """Le payload envoyé à l'API doit contenir un filtre de date PD>=."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"notices": []}

    captured_payloads = []

    def fake_post(url, json=None, **kwargs):
        captured_payloads.append(json or {})
        return mock_resp

    import importlib
    import scraper_ted

    importlib.reload(scraper_ted)

    with patch("requests.post", side_effect=fake_post):
        scraper_ted.fetch()

    assert len(captured_payloads) > 0
    assert "PD>=" in captured_payloads[0].get("query", "")


# ── Tests DECP CPV + fenêtre temporelle ──────────────────────────────────────


def test_decp_cpv_filter_in_where_clause():
    """Le where DECP doit inclure les codes CPV SSI."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    import importlib
    import scraper_decp

    importlib.reload(scraper_decp)

    with patch("requests.get", return_value=mock_resp) as req:
        scraper_decp.fetch()

    where_clause = req.call_args.kwargs["params"]["where"]
    assert "45312100" in where_clause
    assert "50610000" in where_clause


def test_decp_window_defaults_to_30_days():
    """La fenêtre par défaut doit être 30 jours."""
    import os
    from datetime import datetime, timedelta
    import importlib
    import scraper_decp

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"results": [], "total_count": 0}

    os.environ.pop("DECP_WINDOW_DAYS", None)

    with patch("requests.get", return_value=mock_resp) as req:
        importlib.reload(scraper_decp)
        scraper_decp.fetch()

    where_clause = req.call_args.kwargs["params"]["where"]
    expected_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    assert expected_date in where_clause


# ── Tests BOAMP fenêtre temporelle ───────────────────────────────────────────


def test_boamp_window_defaults_to_30_days():
    """La fenêtre par défaut doit être 30 jours."""
    import os
    from datetime import datetime, timedelta
    import scraper_boamp

    captured = {}

    def fake_retry_get(url, *, params=None, headers=None, timeout=15, **kwargs):
        captured["params"] = params or {}
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"results": []}
        return resp

    os.environ.pop("SCRAPER_WINDOW_DAYS", None)

    with patch("scraper_boamp.retry_get", side_effect=fake_retry_get):
        scraper_boamp.fetch()

    where_clause = captured.get("params", {}).get("where", "")
    expected_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    assert expected_date in where_clause


# ── Tests scraper_devbanks — UNDP / ADB ───────────────────────────────────────


def test_fetch_devbanks_undp_included():
    """Un flux UNDP avec une entrée OI/construction doit être retourné."""
    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda k, default="": {
        "title": "UNDP Procurement — Construction hospital Madagascar",
        "summary": "Construction of new hospital infrastructure in madagascar health",
        "link": "https://procurement-notices.undp.org/view_notice.cfm?notice_id=99999",
    }.get(k, default)
    mock_entry.published = None
    mock_entry.updated = None

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    import scraper_devbanks

    with patch("feedparser.parse", return_value=mock_feed):
        result = scraper_devbanks.fetch()

    assert len(result) >= 1
    assert any("UNDP" in r["name"] or "madagascar" in r["name"].lower() for r in result)


def test_fetch_devbanks_irrelevant_skipped():
    """Une entrée sans lien OI/secteur ne doit pas être retournée."""
    mock_entry = MagicMock()
    mock_entry.get.side_effect = lambda k, default="": {
        "title": "Project in Germany — Software Development",
        "summary": "IT consulting project in Berlin",
        "link": "https://www.adb.org/projects/12345",
    }.get(k, default)
    mock_entry.published = None
    mock_entry.updated = None

    mock_feed = MagicMock()
    mock_feed.entries = [mock_entry]

    import scraper_devbanks

    with patch("feedparser.parse", return_value=mock_feed):
        result = scraper_devbanks.fetch()

    assert result == []
