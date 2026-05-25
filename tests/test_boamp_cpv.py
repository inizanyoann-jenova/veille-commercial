import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_boamp import _normalise


def test_normalise_cpv_joined_from_descripteur_libelle():
    """descripteur_libelle liste → cpv = valeurs jointes par ', '."""
    raw = {
        "idweb": "AO-2026-001",
        "objet": "Maintenance SSI",
        "dateparution": "2026-01-15",
        "datelimitereponse": "2026-02-15",
        "descripteur_libelle": ["45312100", "Systèmes d'alarme incendie"],
        "url_avis": "",
    }
    result = _normalise(raw, "974")
    assert "cpv" in result
    assert result["cpv"] == "45312100, Systèmes d'alarme incendie"


def test_normalise_cpv_empty_when_no_descripteurs():
    """descripteur_libelle absent → cpv = ''."""
    raw = {
        "idweb": "AO-2026-002",
        "objet": "Construction bâtiment",
        "dateparution": "2026-01-15",
    }
    result = _normalise(raw, "974")
    assert "cpv" in result
    assert result["cpv"] == ""


def test_normalise_cpv_string_input_passthrough():
    """descripteur_libelle string (incohérence API) → cpv = la string telle quelle."""
    raw = {
        "idweb": "AO-2026-003",
        "objet": "Test",
        "dateparution": "2026-01-15",
        "descripteur_libelle": "45312100",
    }
    result = _normalise(raw, "974")
    assert result["cpv"] == "45312100"
