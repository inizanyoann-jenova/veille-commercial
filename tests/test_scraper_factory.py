import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
import pytest
from scraper_factory import _extract_code, _validate_syntax, generate, GenerationResult


def test_extract_code_from_backtick_block():
    text = "Voici le code :\n```python\ndef fetch() -> list:\n    return []\n```\nFin."
    result = _extract_code(text)
    assert "def fetch" in result


def test_extract_code_from_bare_backtick_block():
    text = "```\ndef fetch():\n    return []\n```"
    result = _extract_code(text)
    assert "def fetch" in result


def test_extract_code_without_backticks():
    text = "Explication.\ndef fetch() -> list[dict]:\n    return []\n"
    result = _extract_code(text)
    assert "def fetch" in result


def test_extract_code_empty_response():
    result = _extract_code("Pas de code ici.")
    assert result == ""


def test_validate_syntax_valid():
    code = "from datetime import datetime\ndef fetch():\n    return []\n"
    assert _validate_syntax(code) is True


def test_validate_syntax_invalid():
    code = "def fetch(\n    broken syntax here"
    assert _validate_syntax(code) is False


def test_generate_no_mistral_client():
    with patch("scraper_factory._get_mistral_client", return_value=None):
        result = generate("https://example.com", "Test Site", "Public", db=None)
    assert result.status == "failed"
    assert "Mistral" in result.reason


def test_generate_site_unreachable():
    with patch("scraper_factory._get_mistral_client", return_value=MagicMock()), \
         patch("scraper_factory._fetch_html", side_effect=ValueError("Impossible de télécharger")):
        result = generate("https://unreachable.example", "Test", "Public", db=None)
    assert result.status == "failed"
    assert "télécharger" in result.reason


def test_generate_zero_results(tmp_path):
    mock_client = MagicMock()
    mock_client.chat.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="def fetch():\n    return []\n"))]
    )
    with patch("scraper_factory._get_mistral_client", return_value=mock_client), \
         patch("scraper_factory._fetch_html", return_value="<html><body>test</body></html>"), \
         patch("scraper_factory._test_scraper_module", return_value=[]), \
         patch("scraper_factory.ROOT_DIR", str(tmp_path)):
        result = generate("https://example.com", "Test", "Public", db=None)
    assert result.status == "failed"
    assert "0 résultats" in result.reason
    assert list(tmp_path.glob("*.py")) == []


def test_generate_success(tmp_path):
    preview_item = {
        "name": "Marché test",
        "url": "https://example.com/ao/1",
        "source": "Test",
        "date_found": "2026-05-25",
        "publication_date": "",
        "deadline": "",
        "description": "",
    }
    mock_client = MagicMock()
    mock_client.chat.complete.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="def fetch():\n    return []\n"))]
    )
    with patch("scraper_factory._get_mistral_client", return_value=mock_client), \
         patch("scraper_factory._fetch_html", return_value="<html><body>test</body></html>"), \
         patch("scraper_factory._test_scraper_module", return_value=[preview_item]), \
         patch("scraper_factory.add_auto_source", return_value=MagicMock()), \
         patch("scraper_factory.ROOT_DIR", str(tmp_path)):
        result = generate("https://example.com", "Test Site", "Public", db=MagicMock())
    assert result.status == "ok"
    assert result.nb_results == 1
    assert result.preview[0]["name"] == "Marché test"
    saved = list(tmp_path.glob("scraper_custom_*.py"))
    assert len(saved) == 1
