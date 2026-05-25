import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock


def _make_pw_mock(page_url: str = "https://example.com/results"):
    """Return (mock_pw, mock_page) — minimal sync_playwright context manager mock."""
    mock_page = MagicMock()
    mock_page.url = page_url
    mock_page.query_selector_all.return_value = []
    mock_page.query_selector.return_value = None
    mock_page.content.return_value = "<html></html>"

    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page

    mock_pw = MagicMock()
    mock_pw.__enter__ = MagicMock(return_value=mock_pw)
    mock_pw.__exit__ = MagicMock(return_value=False)
    mock_pw.chromium.launch.return_value = mock_browser

    return mock_pw, mock_page


# ── VAAO ─────────────────────────────────────────────────────────────────────


def test_fetch_vaao_empty_page():
    import scraper_vaao

    mock_pw, _ = _make_pw_mock()
    with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
        result = scraper_vaao.fetch()
    assert result == []


def test_fetch_vaao_inserts_relevant():
    import scraper_vaao

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_vaao._extract_card",
            return_value={
                "name": "Installation SSI alarme incendie Réunion",
                "description": "",
                "url": "https://www.vaao.fr/ao/1",
                "raw_date": "2026-04-15",
                "raw_deadline": "",
            },
        ):
            result = scraper_vaao.fetch()

    assert len(result) >= 1
    assert "SSI" in result[0]["name"] or "incendie" in result[0]["name"].lower()


def test_fetch_vaao_extracts_deadline():
    import scraper_vaao

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_vaao._extract_card",
            return_value={
                "name": "Installation SSI Réunion",
                "description": "",
                "url": "https://www.vaao.fr/ao/1",
                "raw_date": "2026-04-15",
                "raw_deadline": "2026-05-30",
            },
        ):
            result = scraper_vaao.fetch()

    assert len(result) >= 1
    assert result[0]["deadline"] == "2026-05-30"


def test_fetch_vaao_empty_deadline_stays_empty():
    import scraper_vaao

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_vaao.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_vaao._extract_card",
            return_value={
                "name": "Installation SSI Réunion",
                "description": "",
                "url": "https://www.vaao.fr/ao/1",
                "raw_date": "2026-04-15",
                "raw_deadline": "",
            },
        ):
            result = scraper_vaao.fetch()

    assert len(result) >= 1
    assert result[0]["deadline"] == ""


# ── Marché Online ─────────────────────────────────────────────────────────────


def test_fetch_marcheonline_empty():
    import scraper_marcheonline

    mock_pw, _ = _make_pw_mock()
    with patch("scraper_marcheonline.sync_playwright", return_value=mock_pw):
        result = scraper_marcheonline.fetch()
    assert result == []


# ── Nukema ────────────────────────────────────────────────────────────────────


def test_fetch_nukema_inserts_relevant():
    import scraper_nukema

    mock_pw, mock_page = _make_pw_mock(
        page_url="https://marches-publics.nukema.com/consultation"
    )
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch.dict(os.environ, {"NUKEMA_EMAIL": "test@test.com", "NUKEMA_PASSWORD": "pass"}):
        with patch("scraper_nukema.sync_playwright", return_value=mock_pw):
            with patch(
                "scraper_nukema._extract_card",
                return_value={
                    "name": "Maintenance CCTV vidéosurveillance campus universitaire",
                    "description": "Mayotte 976",
                    "url": "https://marches-publics.nukema.com/consultation/12345",
                    "raw_date": "2026-05-10",
                    "raw_deadline": "",
                },
            ):
                result = scraper_nukema.fetch()

    assert len(result) >= 1


def test_fetch_nukema_extracts_deadline():
    import scraper_nukema

    mock_pw, mock_page = _make_pw_mock(
        page_url="https://marches-publics.nukema.com/consultation"
    )
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_nukema.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_nukema._extract_card",
            return_value={
                "name": "Maintenance CCTV campus 976",
                "description": "",
                "url": "https://marches-publics.nukema.com/consultation/42",
                "raw_date": "2026-05-10",
                "raw_deadline": "2026-06-15",
            },
        ):
            result = scraper_nukema.fetch()

    assert len(result) >= 1
    assert result[0]["deadline"] == "2026-06-15"


# ── Marchés Sécurisés ─────────────────────────────────────────────────────────


def test_fetch_marchessecurises_skips_without_creds():
    import scraper_marchessecurises

    with patch.dict(os.environ, {"MARCHESSECURISES_LOGIN": "", "MARCHESSECURISES_PASSWORD": ""}):
        result = scraper_marchessecurises.fetch()
    assert result == []


def test_fetch_marchessecurises_with_creds_inserts():
    import scraper_marchessecurises

    mock_pw, mock_page = _make_pw_mock(
        page_url="https://www.marches-securises.fr/entreprise/?page=recherche"
    )
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch.dict(
        os.environ,
        {"MARCHESSECURISES_LOGIN": "u@u.com", "MARCHESSECURISES_PASSWORD": "pass"},
    ):
        with patch("scraper_marchessecurises.sync_playwright", return_value=mock_pw):
            with patch(
                "scraper_marchessecurises._extract_card",
                return_value={
                    "name": "Maintenance SSI incendie établissement public",
                    "description": "La Réunion 974",
                    "url": "https://www.marches-securises.fr/ao/99",
                    "raw_date": "2026-05-01",
                },
            ):
                result = scraper_marchessecurises.fetch()

    assert len(result) >= 1


# ── Instao ────────────────────────────────────────────────────────────────────


def test_fetch_instao_skips_without_creds():
    import scraper_instao

    with patch.dict(os.environ, {"INSTAO_EMAIL": "", "INSTAO_PASSWORD": ""}):
        result = scraper_instao.fetch()
    assert result == []


# ── Tenders Go ────────────────────────────────────────────────────────────────


def test_fetch_tendersgo_skips_without_creds():
    import scraper_tendersgo

    with patch.dict(os.environ, {"TENDERSGO_EMAIL": "", "TENDERSGO_PASSWORD": ""}):
        result = scraper_tendersgo.fetch()
    assert result == []


# ── IsDB ──────────────────────────────────────────────────────────────────────


def test_fetch_isdb_empty_page():
    import scraper_isdb

    mock_pw, _ = _make_pw_mock()
    with patch("scraper_isdb.sync_playwright", return_value=mock_pw):
        result = scraper_isdb.fetch()
    assert result == []


def test_fetch_isdb_inserts_relevant():
    import scraper_isdb

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_isdb.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_isdb._extract_card",
            return_value={
                "name": "Construction hôpital SSI alarme incendie Comores",
                "description": "Projet infrastructure sanitaire Comores",
                "url": "https://www.isdb.org/project-procurement/12345",
                "raw_date": "2026-05-15",
            },
        ):
            result = scraper_isdb.fetch()

    assert len(result) >= 1
    assert "SSI" in result[0]["name"] or "incendie" in result[0]["name"].lower()


def test_fetch_isdb_skips_irrelevant():
    import scraper_isdb

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_isdb.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_isdb._extract_card",
            return_value={
                "name": "Fournitures de bureau papeterie",
                "description": "Achat fournitures",
                "url": "https://www.isdb.org/project-procurement/99999",
                "raw_date": "",
            },
        ):
            result = scraper_isdb.fetch()

    assert result == []


# ── Centre Hospitalier Mayotte ────────────────────────────────────────────────


def test_fetch_chm_empty_page():
    import scraper_chm

    mock_pw, _ = _make_pw_mock()
    with patch("scraper_chm.sync_playwright", return_value=mock_pw):
        result = scraper_chm.fetch()
    assert result == []


def test_fetch_chm_inserts_relevant():
    import scraper_chm

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_chm.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_chm._extract_card",
            return_value={
                "name": "Maintenance SSI détection incendie CHM Mayotte",
                "description": "Entretien système sécurité incendie bâtiments hospitaliers",
                "url": "https://www.chm-mayotte.fr/appels-d-offres/77",
                "raw_date": "2026-05-18",
            },
        ):
            result = scraper_chm.fetch()

    assert len(result) >= 1
    assert "SSI" in result[0]["name"] or "incendie" in result[0]["name"].lower()


def test_fetch_chm_includes_all_items():
    """CHM n'applique aucun filtre par secteur — tous les marchés sont retournés."""
    import scraper_chm

    mock_pw, mock_page = _make_pw_mock()
    mock_page.query_selector_all.return_value = [MagicMock()]

    with patch("scraper_chm.sync_playwright", return_value=mock_pw):
        with patch(
            "scraper_chm._extract_card",
            return_value={
                "name": "Achat médicaments pharmacie",
                "description": "Fourniture produits pharmaceutiques",
                "url": "https://www.chm-mayotte.fr/appels-d-offres/55",
                "raw_date": "",
            },
        ):
            result = scraper_chm.fetch()

    assert len(result) >= 1
