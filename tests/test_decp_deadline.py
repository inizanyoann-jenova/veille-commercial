import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_decp import _normalise


def test_normalise_calculates_deadline_from_dureemois():
    raw = {
        "id": "2026-DECP-001",
        "objet": "SSI alarme incendie lycée",
        "datenotification": "2026-01-15",
        "dureemois": 6,
        "lieuexecution_code": "97400",
        "codecpv": "45312100",
        "montant": 50000,
        "acheteur_id": "CHU-974",
    }
    result = _normalise(raw)
    assert result["deadline"] == "2026-07-15"


def test_normalise_deadline_crosses_year():
    raw = {
        "id": "2026-DECP-002",
        "objet": "Maintenance CCTV",
        "datenotification": "2026-10-01",
        "dureemois": 6,
        "lieuexecution_code": "97600",
        "codecpv": "35111300",
        "montant": None,
        "acheteur_id": "",
    }
    result = _normalise(raw)
    assert result["deadline"] == "2027-04-01"


def test_normalise_no_dureemois_leaves_deadline_empty():
    raw = {
        "id": "2026-DECP-003",
        "objet": "Travaux construction",
        "datenotification": "2026-04-01",
        "dureemois": None,
        "lieuexecution_code": "97400",
        "codecpv": "",
        "montant": None,
        "acheteur_id": "",
    }
    result = _normalise(raw)
    assert result["deadline"] == ""


def test_normalise_dureemois_12_months():
    raw = {
        "id": "2026-DECP-004",
        "objet": "Maintenance SSI annuelle",
        "datenotification": "2026-03-31",
        "dureemois": 12,
        "lieuexecution_code": "97400",
        "codecpv": "45312100",
        "montant": 20000,
        "acheteur_id": "",
    }
    result = _normalise(raw)
    assert result["deadline"] == "2027-03-31"
