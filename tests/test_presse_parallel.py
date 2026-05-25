import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_presse_fetch_processes_all_feeds(monkeypatch):
    """fetch() doit appeler _collect_feed pour chaque flux PRESSE et INSTITUTION."""
    import scraper_presse

    call_log = []

    def fake_collect(territoire, nom, url, type_opp):
        call_log.append((territoire, nom, type_opp))
        return []

    monkeypatch.setattr(scraper_presse, "_collect_feed", fake_collect)
    result = scraper_presse.fetch()

    total = len(scraper_presse.FLUX_PRESSE) + len(scraper_presse.FLUX_INSTITUTIONS)
    assert len(call_log) == total, (
        f"fetch() a appelé _collect_feed {len(call_log)} fois au lieu de {total}"
    )
    assert result == []


def test_presse_fetch_combines_results_from_all_feeds(monkeypatch):
    """Les résultats de tous les flux sont combinés dans la liste retournée."""
    import scraper_presse

    def fake_collect(territoire, nom, url, type_opp):
        return [{"name": f"[{nom}] item", "url": url, "source": nom}]

    monkeypatch.setattr(scraper_presse, "_collect_feed", fake_collect)
    result = scraper_presse.fetch()

    total = len(scraper_presse.FLUX_PRESSE) + len(scraper_presse.FLUX_INSTITUTIONS)
    assert len(result) == total, (
        f"fetch() a retourné {len(result)} items au lieu de {total} "
        "(un item par flux attendu)"
    )


def test_presse_feed_types_correctly_assigned(monkeypatch):
    """FLUX_PRESSE doit recevoir type 'Presse', FLUX_INSTITUTIONS type 'Institution'."""
    import scraper_presse

    call_log = []

    def fake_collect(territoire, nom, url, type_opp):
        call_log.append((nom, type_opp))
        return []

    monkeypatch.setattr(scraper_presse, "_collect_feed", fake_collect)
    scraper_presse.fetch()

    presse_noms = {nom for _, nom, _ in scraper_presse.FLUX_PRESSE}
    institution_noms = {nom for _, nom, _ in scraper_presse.FLUX_INSTITUTIONS}

    for nom, type_opp in call_log:
        if nom in presse_noms:
            assert type_opp == "Presse", f"{nom} doit avoir type 'Presse', got '{type_opp}'"
        elif nom in institution_noms:
            assert type_opp == "Institution", f"{nom} doit avoir type 'Institution', got '{type_opp}'"
