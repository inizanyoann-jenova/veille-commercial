import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_compute_combined_score_with_gemini():
    from llm_analyzer import compute_combined_score
    result = compute_combined_score(gemini_score=80, local_score=50, gemini_available=True)
    assert result == round(80 * 0.70 + 50 * 0.30)  # 71


def test_compute_combined_score_without_gemini():
    from llm_analyzer import compute_combined_score
    result = compute_combined_score(gemini_score=80, local_score=50, gemini_available=False)
    assert result == 50  # local uniquement


def test_local_analyze_returns_new_fields():
    from llm_analyzer import _local_analyze
    result = _local_analyze("Maintenance SSI système de sécurité incendie La Réunion 974")
    assert "tag_pertinence" in result
    assert result["tag_pertinence"] in ("Très pertinent", "À évaluer", "Hors périmètre")
    assert "domaines_concernes" in result
    assert isinstance(result["domaines_concernes"], list)
    assert "justification_score" in result
    assert isinstance(result["justification_score"], str)
    assert "territoire_ia" in result


def test_local_analyze_ssi_reunion_high_score():
    from llm_analyzer import _local_analyze
    result = _local_analyze(
        "Marché de maintenance SSI CMSI alarme incendie - Saint-Denis La Réunion 974"
    )
    assert result["score_pertinence"] >= 65
    assert result["tag_pertinence"] == "Très pertinent"
    assert "SSI" in result["domaines_concernes"]


def test_local_analyze_gardiennage_low_score():
    from llm_analyzer import _local_analyze
    result = _local_analyze("Prestations de gardiennage et agents de sécurité")
    assert result["score_pertinence"] < 35
    assert result["tag_pertinence"] in ("À évaluer", "Hors périmètre")


def test_analyze_tender_returns_combined_score(monkeypatch):
    """Vérifie que analyze_tender combine scores quand Gemini répond."""
    from llm_analyzer import _local_analyze
    import llm_analyzer

    fake_gemini = {
        "score_pertinence": 80,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "Marché SSI direct.",
        "_source": "gemini",
    }
    monkeypatch.setattr(llm_analyzer, "_gemini_analyze", lambda text: fake_gemini)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")
    local = _local_analyze("Maintenance SSI La Réunion 974")
    expected_score = round(80 * 0.70 + local["score_pertinence"] * 0.30)
    assert result["score_pertinence"] == expected_score
    assert result["_source"] == "gemini"
