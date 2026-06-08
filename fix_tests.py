import re
import os

filepath = r"c:\Users\Utilisateur\Desktop\toutes les app pour def\commercial et opportunité def OI\backend\test_main.py"
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# test_collect_returns_500_when_no_sources
content = re.sub(
    r'def test_collect_returns_500_when_no_sources.*?assert resp.status_code == 500\s+body = resp.json\(\)\s+assert "Aucune source" in body\.get\("detail", ""\)',
    r'''def test_collect_returns_202_when_no_sources():
    """Aucune source active -> job créé, background task renseigne error dans le job."""
    import main as m
    from fastapi.testclient import TestClient

    with patch("main.list_sources", return_value=[]):
        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    st = m._COLLECT_JOBS[job_id]
    assert "Aucune source" in st.get("error", "")''',
    content,
    flags=re.DOTALL
)

# test_collect_returns_200_partial_on_mixed_results
content = re.sub(
    r'def test_collect_returns_200_partial_on_mixed_results.*?assert resp.status_code == 200\s+body = resp.json\(\)\s+assert body\["status"\] == "partial"\s+assert body\["nb_ok"\] == 1\s+assert body\["nb_error"\] == 1\s+assert len\(body\["results"\]\) == 2',
    r'''def test_collect_returns_202_partial_on_mixed_results():
    """Une source OK + une source KO -> job partial."""
    import main as m
    from fastapi.testclient import TestClient

    ok_source = MagicMock()
    ok_source.is_manual = False
    ok_source.scraper_module = "mod_ok"
    ok_source.scraper_func = "run"
    ok_source.enabled = True
    ok_source.is_validated = True
    ok_source.name = "SourceOK"

    fail_source = MagicMock()
    fail_source.is_manual = False
    fail_source.scraper_module = "mod_fail"
    fail_source.scraper_func = "run"
    fail_source.enabled = True
    fail_source.is_validated = True
    fail_source.name = "SourceFAIL"

    def mock_import(name):
        mod = MagicMock()
        if name == "mod_fail":
            mod.run.side_effect = RuntimeError("timeout")
        return mod

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.count.return_value = 2

    with (
        patch("main.list_sources", return_value=[ok_source, fail_source]),
        patch("main.SessionLocal", return_value=mock_db),
        patch("main.start_scraper_run", return_value=1),
        patch("main.finish_scraper_run"),
        patch("main.auto_analyze_pending"),
        patch("main.auto_analyze_mistral"),
        patch("importlib.import_module", side_effect=mock_import),
    ):
        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    body = m._COLLECT_JOBS[job_id]
    assert body["status"] == "partial"
    assert body["nb_ok"] == 1
    assert body["nb_error"] == 1
    assert len(body["results"]) == 2''',
    content,
    flags=re.DOTALL
)

# test_collect_returns_200_ok_when_all_succeed
content = re.sub(
    r'def test_collect_returns_200_ok_when_all_succeed.*?assert resp.status_code == 200\s+body = resp.json\(\)\s+assert body\["status"\] == "ok"\s+assert body\["nb_ok"\] == 1\s+assert body\["nb_error"\] == 0',
    r'''def test_collect_returns_202_ok_when_all_succeed():
    """Toutes les sources OK -> job ok."""
    import main as m
    from fastapi.testclient import TestClient

    ok_source = MagicMock()
    ok_source.is_manual = False
    ok_source.scraper_module = "mod_ok"
    ok_source.scraper_func = "run"
    ok_source.enabled = True
    ok_source.is_validated = True
    ok_source.name = "SourceOK"

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.count.return_value = 3

    with (
        patch("main.list_sources", return_value=[ok_source]),
        patch("main.SessionLocal", return_value=mock_db),
        patch("main.start_scraper_run", return_value=1),
        patch("main.finish_scraper_run"),
        patch("main.auto_analyze_pending"),
        patch("main.auto_analyze_mistral"),
        patch("importlib.import_module", return_value=MagicMock()),
    ):
        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    body = m._COLLECT_JOBS[job_id]
    assert body["status"] == "ok"
    assert body["nb_ok"] == 1
    assert body["nb_error"] == 0''',
    content,
    flags=re.DOTALL
)

# test_collect_returns_500_when_all_sources_fail
content = re.sub(
    r'def test_collect_returns_500_when_all_sources_fail.*?assert resp.status_code == 500\s+body = resp.json\(\)\s+detail = body\.get\("detail", \{\}\)\s+assert "Toutes les sources ont échoué" in detail\.get\("message", ""\)\s+assert len\(detail\.get\("results", \[\]\)\) == 1\s+assert detail\["results"\]\[0\]\["status"\] == "error"',
    r'''def test_collect_returns_202_when_all_sources_fail():
    """Toutes les sources échouent -> job error."""
    import main as m
    from fastapi.testclient import TestClient

    fail_source = MagicMock()
    fail_source.is_manual = False
    fail_source.scraper_module = "mod_fail"
    fail_source.scraper_func = "run"
    fail_source.enabled = True
    fail_source.is_validated = True
    fail_source.name = "SourceFAIL"

    mock_db = MagicMock()
    mock_db.query.return_value.all.return_value = []

    with (
        patch("main.list_sources", return_value=[fail_source]),
        patch("main.SessionLocal", return_value=mock_db),
        patch("main.start_scraper_run", return_value=1),
        patch("main.finish_scraper_run"),
        patch("main.auto_analyze_pending"),
        patch("main.auto_analyze_mistral"),
        patch("importlib.import_module", side_effect=RuntimeError("crash")),
    ):
        client = TestClient(m.app, raise_server_exceptions=False)
        resp = client.post("/api/collect", json={})

    assert resp.status_code == 202
    job_id = resp.json()["job_id"]
    body = m._COLLECT_JOBS[job_id]
    assert body["status"] == "error"
    assert "Toutes les sources ont échoué" in body.get("error", "")
    assert len(body.get("results", [])) == 1
    assert body["results"][0]["status"] == "error"''',
    content,
    flags=re.DOTALL
)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
