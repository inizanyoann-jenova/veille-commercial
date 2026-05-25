import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_utils import parse_date
from datetime import datetime


def test_parse_date_iso():
    result = parse_date("2026-04-15")
    assert result == datetime(2026, 4, 15)


def test_parse_date_iso_with_time():
    result = parse_date("2026-04-15T10:30:00")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_numeric():
    result = parse_date("15/04/2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_numeric_dashes():
    result = parse_date("15-04-2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_textual():
    result = parse_date("15 avril 2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_french_abbreviated():
    result = parse_date("15 avr. 2026")
    assert result == datetime(2026, 4, 15)


def test_parse_date_null_string():
    assert parse_date("null") is None


def test_parse_date_empty():
    assert parse_date("") is None


def test_parse_date_none():
    assert parse_date(None) is None


def test_parse_date_garbage():
    assert parse_date("pas une date") is None
