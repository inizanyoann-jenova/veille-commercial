# tests/test_filters.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from filters import KEYWORDS_CONSTRUCTION, is_construction_relevant


def test_keywords_construction_not_empty():
    assert len(KEYWORDS_CONSTRUCTION) > 0


def test_is_construction_relevant_hotel():
    assert is_construction_relevant("Construction d'un hôtel 4 étoiles à Saint-Denis") is True


def test_is_construction_relevant_irrelevant():
    assert is_construction_relevant("Résultats du championnat de pétanque") is False


def test_is_construction_relevant_chantier():
    assert is_construction_relevant("Nouveau chantier immobilier dans le Nord") is True
