import logging
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from main import _tender_to_dict


def _make_mock_tender():
    t = MagicMock()
    t.id = 'test-1'
    t.title = 'Marché SSI La Réunion'
    t.description = 'ssi détection incendie la réunion'
    t.source = 'DECP'
    t.publication_date = None
    t.date_extraction = None
    t.deadline = None
    t.status = 'À qualifier'
    t.relevance_score = 75
    t.adaptive_score = None
    t.is_maintenance = False
    t.secteur = 'Public'
    t.type_opportunite = 'Marché Public'
    t.amount = None
    t.is_blacklisted = False
    t.is_saved = False
    t.notes = None
    t.tags = []
    t.llm_analysis = {}
    t.llm_structured = None
    return t


def test_tender_to_dict_includes_fiche_data_and_jours_restants():
    result = _tender_to_dict(_make_mock_tender())
    assert 'fiche_data' in result
    assert 'jours_restants' in result


def test_fiche_data_has_required_keys():
    result = _tender_to_dict(_make_mock_tender())
    fd = result['fiche_data']
    for key in ('sm', 'sg', 'sk', 'smaint', 'label_action', 'steps', 'atouts', 'risques'):
        assert key in fd, f"Clé manquante : {key}"
    assert isinstance(fd['steps'], list)
    assert isinstance(fd['atouts'], list)
    assert isinstance(fd['risques'], list)


def test_jours_restants_is_none_when_no_deadline():
    result = _tender_to_dict(_make_mock_tender())
    assert result['jours_restants'] is None


def test_fiche_data_sm_score_for_ssi_tender():
    t = _make_mock_tender()
    result = _tender_to_dict(t)
    assert result['fiche_data']['sm'] == 45, (
        f"Expected sm=45 for SSI/La Réunion tender, got {result['fiche_data']['sm']}"
    )


def test_lifespan_starts_and_stops_scheduler():
    """Le scheduler doit démarrer au startup et s'arrêter proprement."""
    with patch("main.BackgroundScheduler") as mock_cls:
        mock_scheduler = MagicMock()
        mock_scheduler.get_jobs.return_value = [MagicMock(), MagicMock()]
        mock_cls.return_value = mock_scheduler

        from fastapi.testclient import TestClient
        import main as m
        with TestClient(m.app) as client:
            resp = client.get("/api/tenders")
            assert resp.status_code == 200

        mock_scheduler.start.assert_called_once()
        mock_scheduler.shutdown.assert_called_once_with(wait=False)


def test_collect_critical_log_on_scraper_failure(caplog):
    """Un scraper qui lève une exception doit générer un log CRITICAL."""
    import main as m

    failing_source = MagicMock()
    failing_source.is_manual = False
    failing_source.scraper_module = "fake_module"
    failing_source.scraper_func = "fake_func"
    failing_source.enabled = True
    failing_source.is_validated = True
    failing_source.name = "FakeSource"

    with patch("main.list_sources", return_value=[failing_source]), \
         patch("main.SessionLocal") as mock_sl, \
         patch("main.start_scraper_run", return_value=99), \
         patch("main.finish_scraper_run"), \
         patch("importlib.import_module", side_effect=RuntimeError("playwright crash")), \
         caplog.at_level(logging.CRITICAL, logger="main"):

        from fastapi.testclient import TestClient
        client = TestClient(m.app)
        resp = client.post("/api/collect", json={})

    assert any(
        r.levelno >= logging.CRITICAL and "FakeSource" in r.getMessage()
        for r in caplog.records
    ), "Aucun log CRITICAL trouvé pour le scraper en échec"
