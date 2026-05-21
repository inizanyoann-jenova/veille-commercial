import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock
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
