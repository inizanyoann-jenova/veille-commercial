import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def test_marchessecurises_missing_credentials():
    import scraper_marchessecurises

    os.environ.pop("MARCHESSECURISES_LOGIN", None)
    os.environ.pop("MARCHESSECURISES_PASSWORD", None)
    result = scraper_marchessecurises.fetch()
    assert result == []


def test_instao_missing_credentials():
    import scraper_instao

    os.environ.pop("INSTAO_EMAIL", None)
    os.environ.pop("INSTAO_PASSWORD", None)
    result = scraper_instao.fetch()
    assert result == []


def test_tendersgo_missing_credentials():
    import scraper_tendersgo

    os.environ.pop("TENDERSGO_EMAIL", None)
    os.environ.pop("TENDERSGO_PASSWORD", None)
    result = scraper_tendersgo.fetch()
    assert result == []
