import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from scraper_marcheonline import _parse_detail_html


def test_itemprop_description_simple():
    html = '<p itemprop="description">Installation SSI bâtiment hôpital Réunion</p>'
    result = _parse_detail_html(html)
    assert "SSI" in result
    assert "hôpital" in result


def test_ao_objet_class():
    html = '<div class="ao-objet">Installation désenfumage lycée Saint-Denis</div>'
    result = _parse_detail_html(html)
    assert "désenfumage" in result


def test_objet_marche_class():
    html = '<span class="objet-marche">Travaux réhabilitation EHPAD Mayotte</span>'
    result = _parse_detail_html(html)
    assert "réhabilitation" in result


def test_no_match_returns_empty_string():
    html = '<div class="unrelated">Contenu sans rapport</div>'
    assert _parse_detail_html(html) == ""


def test_short_match_ignored():
    # Texte trop court (< 10 chars) → ignoré pour éviter les faux positifs
    html = '<p itemprop="description">Lot 3</p>'
    assert _parse_detail_html(html) == ""


def test_strips_nested_html_tags():
    html = '<p itemprop="description"><strong>CMSI</strong> et désenfumage pour collège</p>'
    result = _parse_detail_html(html)
    assert "CMSI" in result
    assert "<" not in result


def test_description_lot_class():
    html = '<div class="description-lot">Vidéosurveillance campus universitaire 974</div>'
    result = _parse_detail_html(html)
    assert "Vidéosurveillance" in result


def test_multiple_elements_returns_first_only():
    html = (
        '<p itemprop="description">Premier AO installation SSI lycée</p>'
        '<p itemprop="description">Deuxième AO désenfumage hôpital Mayotte</p>'
    )
    result = _parse_detail_html(html)
    assert "Premier AO" in result
    assert "Deuxième AO" not in result
