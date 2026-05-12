import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch
import pytest


def test_extract_cards_empty_page():
    from playwright_base import extract_cards
    page = MagicMock()
    page.query_selector_all.return_value = []
    result = extract_cards(page, ".card", {"title": ".title"})
    assert result == []


def test_extract_cards_with_attribute():
    from playwright_base import extract_cards
    page = MagicMock()
    el = MagicMock()
    child = MagicMock()
    child.get_attribute.return_value = "https://example.com/ao/1"
    el.query_selector.return_value = child
    page.query_selector_all.return_value = [el]
    result = extract_cards(page, ".card", {"url": "a@href"})
    assert result[0]["url"] == "https://example.com/ao/1"


def test_paginate_no_next_button():
    from playwright_base import paginate
    page = MagicMock()
    page.query_selector.return_value = None
    result = paginate(page, ".next", max_pages=5)
    assert result is False


def test_paginate_clicks_next():
    from playwright_base import paginate
    page = MagicMock()
    btn = MagicMock()
    btn.is_enabled.return_value = True
    page.query_selector.side_effect = [btn, None]
    paginate(page, ".next", max_pages=3)
    btn.click.assert_called_once()


def test_login_returns_true_on_success():
    from playwright_base import login
    page = MagicMock()
    selectors = {"email": "#email", "password": "#pwd", "submit": "button[type=submit]"}
    result = login(page, "https://example.com/login", "u@u.com", "pass", selectors)
    assert result is True


def test_login_returns_false_on_exception():
    from playwright_base import login
    page = MagicMock()
    page.goto.side_effect = Exception("Timeout")
    selectors = {"email": "#email", "password": "#pwd", "submit": "button"}
    result = login(page, "https://example.com/login", "u@u.com", "pass", selectors)
    assert result is False
