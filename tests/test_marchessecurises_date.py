import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_marchessecurises import _normalise


def test_normalise_maps_raw_deadline_to_deadline():
    """_normalise doit renseigner deadline depuis raw_deadline, pas le laisser vide."""
    raw = {
        "name": "Marché SSI Réunion",
        "url": "https://marches-securises.fr/ao/123",
        "raw_date": "2026-01-15",
        "raw_deadline": "2026-02-28",
        "description": "Acheteur public 974",
    }
    result = _normalise(raw)
    assert result["publication_date"] == "2026-01-15"
    assert result["deadline"] == "2026-02-28"


def test_normalise_deadline_empty_when_no_raw_deadline():
    """Sans raw_deadline, deadline doit rester vide string."""
    raw = {
        "name": "Marché CCTV Mayotte",
        "url": "https://marches-securises.fr/ao/456",
        "raw_date": "2026-03-01",
        "description": "CHU Mayotte",
    }
    result = _normalise(raw)
    assert result["publication_date"] == "2026-03-01"
    assert result["deadline"] == ""


def test_normalise_deadline_french_date_format():
    """raw_deadline au format DD/MM/YYYY doit être parsé correctement via parse_date."""
    raw = {
        "name": "Marché incendie 974",
        "url": "https://marches-securises.fr/ao/789",
        "raw_date": "2026-04-01",
        "raw_deadline": "15/05/2026",
        "description": "",
    }
    result = _normalise(raw)
    assert result["deadline"] == "2026-05-15"
