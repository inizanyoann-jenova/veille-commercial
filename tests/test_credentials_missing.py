import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from unittest.mock import patch, MagicMock
import pytest


def _make_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    return db


def _run_id():
    return "run-test-1"


def test_marchessecurises_missing_credentials():
    import scraper_marchessecurises
    db = _make_db()
    with patch('scraper_marchessecurises.CredentialManager') as mock_cm, \
         patch('scraper_marchessecurises.init_db'), \
         patch('scraper_marchessecurises.SessionLocal', return_value=db), \
         patch('scraper_marchessecurises.start_scraper_run', return_value=_run_id()), \
         patch('scraper_marchessecurises.finish_scraper_run') as mock_finish:
        mock_cm.get.return_value = None
        result = scraper_marchessecurises.fetch_marchessecurises_tenders()
    assert result == 0
    mock_finish.assert_called_once()
    call_kwargs = mock_finish.call_args
    assert call_kwargs.kwargs.get('error') == 'CREDENTIALS_MISSING' or \
           (len(call_kwargs.args) > 4 and call_kwargs.args[4] == 'CREDENTIALS_MISSING') or \
           'CREDENTIALS_MISSING' in str(call_kwargs)


def test_instao_missing_credentials():
    import scraper_instao
    db = _make_db()
    with patch('scraper_instao.CredentialManager') as mock_cm, \
         patch('scraper_instao.init_db'), \
         patch('scraper_instao.SessionLocal', return_value=db), \
         patch('scraper_instao.start_scraper_run', return_value=_run_id()), \
         patch('scraper_instao.finish_scraper_run') as mock_finish:
        mock_cm.get.return_value = None
        result = scraper_instao.fetch_instao_tenders()
    assert result == 0
    mock_finish.assert_called_once()
    call_kwargs = mock_finish.call_args
    assert call_kwargs.kwargs.get('error') == 'CREDENTIALS_MISSING' or \
           (len(call_kwargs.args) > 4 and call_kwargs.args[4] == 'CREDENTIALS_MISSING') or \
           'CREDENTIALS_MISSING' in str(call_kwargs)


def test_tendersgo_missing_credentials():
    import scraper_tendersgo
    db = _make_db()
    with patch('scraper_tendersgo.CredentialManager') as mock_cm, \
         patch('scraper_tendersgo.init_db'), \
         patch('scraper_tendersgo.SessionLocal', return_value=db), \
         patch('scraper_tendersgo.start_scraper_run', return_value=_run_id()), \
         patch('scraper_tendersgo.finish_scraper_run') as mock_finish:
        mock_cm.get.return_value = None
        result = scraper_tendersgo.fetch_tendersgo_tenders()
    assert result == 0
    mock_finish.assert_called_once()
    call_kwargs = mock_finish.call_args
    assert call_kwargs.kwargs.get('error') == 'CREDENTIALS_MISSING' or \
           (len(call_kwargs.args) > 4 and call_kwargs.args[4] == 'CREDENTIALS_MISSING') or \
           'CREDENTIALS_MISSING' in str(call_kwargs)
