import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, PropertyMock, patch
import json
import pytest


def _make_page(initial_url, final_url):
    page = MagicMock()
    urls = [initial_url, final_url]
    url_iter = iter(urls)
    type(page).url = PropertyMock(side_effect=lambda: next(url_iter))
    page.evaluate.return_value = True
    return page


def _run_worker(page, url, selectors, email="u@u.com", password="pass"):
    import _test_login_worker as w
    with patch("playwright.sync_api.sync_playwright") as pw_mock:
        browser = pw_mock.return_value.__enter__.return_value.chromium.launch.return_value
        browser.new_page.return_value = page
        return w.test_login(url, selectors, email, password)


def test_worker_uses_wait_for_selector_not_query_selector():
    """Le worker doit attendre les champs (modale async) via wait_for_selector."""
    import _test_login_worker as w
    import inspect
    src = inspect.getsource(w.test_login)
    assert "wait_for_selector" in src, (
        "test_login doit utiliser wait_for_selector pour gérer les modales asynchrones"
    )
    assert "query_selector" not in src.split("wait_for_selector")[0].split("def test_login")[1], (
        "query_selector ne doit plus être utilisé pour trouver email/password"
    )


def test_worker_succeeds_when_field_appears_after_delay():
    """Le worker doit réussir même si le champ apparaît après le chargement de la page."""
    import _test_login_worker as w
    from unittest.mock import MagicMock, PropertyMock, patch

    el_email = MagicMock()
    el_pwd = MagicMock()

    with patch("playwright.sync_api.sync_playwright") as pw_mock:
        ctx = pw_mock.return_value.__enter__.return_value
        browser = ctx.chromium.launch.return_value
        page = browser.new_page.return_value

        page.wait_for_selector.side_effect = lambda sel, **kw: el_email if "email" in sel else el_pwd

        url_calls = []
        def _url_getter():
            call_n = len(url_calls)
            url_calls.append(1)
            return "https://x.com/login" if call_n == 0 else "https://x.com/dashboard"

        type(page).url = PropertyMock(side_effect=_url_getter)
        page.evaluate.return_value = True

        result = w.test_login(
            "https://x.com/login",
            {"email": "input[type='email']", "password": "input[type='password']", "submit": "button"},
            "u@u.com", "pass",
        )

    assert result.get("ok") is True, f"Attendu ok=True, obtenu : {result}"
