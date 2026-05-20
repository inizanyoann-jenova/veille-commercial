import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_compute_combined_score_with_gemini():
    from llm_analyzer import compute_combined_score
    result = compute_combined_score(llm_score=80, local_score=50, llm_available=True)
    assert result == round(80 * 0.70 + 50 * 0.30)  # 71


def test_compute_combined_score_without_gemini():
    from llm_analyzer import compute_combined_score
    result = compute_combined_score(llm_score=80, local_score=50, llm_available=False)
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
    """Vérifie que analyze_tender combine scores quand Claude répond."""
    from llm_analyzer import _local_analyze
    import llm_analyzer

    fake_claude = {
        "score_pertinence": 80,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "Marché SSI direct.",
        "_source": "claude",
    }
    monkeypatch.setattr(llm_analyzer, "_claude_analyze", lambda text: fake_claude)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")
    local = _local_analyze("Maintenance SSI La Réunion 974")
    expected_score = round(80 * 0.70 + local["score_pertinence"] * 0.30)
    assert result["score_pertinence"] == expected_score
    assert result["_source"] == "claude"


def test_local_analyze_empty_string():
    from llm_analyzer import _local_analyze
    result = _local_analyze("")
    assert "score_pertinence" in result
    assert result["score_pertinence"] == 0


def test_authentication_error_does_not_log_key(monkeypatch, caplog):
    """AuthenticationError must not expose the API key in logs."""
    import llm_analyzer
    import anthropic
    import logging

    fake_key = "sk-ant-api03-FAKE_SECRET_KEY_1234567890"

    def _raise_auth(*args, **kwargs):
        raise anthropic.AuthenticationError(
            message="401 Invalid API key",
            response=None,
            body={"error": {"type": "authentication_error"}},
        )

    monkeypatch.setattr(llm_analyzer, "_anthropic_client", None)
    monkeypatch.setenv("ANTHROPIC_API_KEY", fake_key)
    monkeypatch.setattr(anthropic.Anthropic, "messages", property(lambda self: type("M", (), {"create": _raise_auth})()))

    with caplog.at_level(logging.WARNING, logger="llm_analyzer"):
        result = llm_analyzer._claude_analyze("test")

    assert result is None
    for record in caplog.records:
        assert fake_key not in record.getMessage()


from unittest.mock import patch, MagicMock


def test_analyze_tender_structured_returns_none_for_short_description():
    """Description < 50 chars -> None sans appeler l API."""
    from llm_analyzer import analyze_tender_structured
    result = analyze_tender_structured('Titre', 'Court')
    assert result is None


def test_analyze_tender_structured_returns_none_without_api_key(monkeypatch):
    """Pas de cle API -> None."""
    monkeypatch.delenv('ANTHROPIC_API_KEY', raising=False)
    from llm_analyzer import analyze_tender_structured
    result = analyze_tender_structured(
        'Installation SSI ERP type J',
        'Installation d un systeme de securite incendie dans un ERP de type J, categorie 2.',
    )
    assert result is None


def test_analyze_tender_structured_parses_valid_json(monkeypatch):
    """Reponse Claude JSON valide -> dict avec les bons champs."""
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key')
    mock_response_json = '''{        "budget_estime": "150 000 euro",        "type_travaux": "Installation neuve",        "lots": ["Lot 1 - Detection"],        "keywords_techniques": ["SSI categorie A"],        "acheteur_type": "Etablissement scolaire",        "niveau_concurrence": "Eleve",        "recommandation": "GO",        "score_confiance": 82,        "justification": "ERP type J, coeur de metier."    }'''

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text=mock_response_json)]

    from llm_analyzer import analyze_tender_structured
    with patch('anthropic.Anthropic') as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_msg

        result = analyze_tender_structured(
            'Installation SSI ERP type J',
            'Installation d un systeme de securite incendie dans un ERP de type J categorie 2, desenfumage CMSI inclus.',
            amount=150000,
        )

    assert result is not None
    assert result['recommandation'] == 'GO'
    assert result['score_confiance'] == 82
    assert 'budget_estime' in result
    assert isinstance(result['lots'], list)


def test_analyze_tender_structured_handles_invalid_json(monkeypatch):
    """Claude retourne du texte invalide -> None sans exception."""
    monkeypatch.setenv('ANTHROPIC_API_KEY', 'sk-ant-test-key')

    mock_msg = MagicMock()
    mock_msg.content = [MagicMock(text='Desole, je ne peux pas repondre.')]

    from llm_analyzer import analyze_tender_structured
    with patch('anthropic.Anthropic') as MockAnthropic:
        mock_client = MagicMock()
        MockAnthropic.return_value = mock_client
        mock_client.messages.create.return_value = mock_msg

        result = analyze_tender_structured(
            'Installation SSI',
            'Installation d un systeme de securite incendie complet avec CMSI et desenfumage.',
        )

    assert result is None


def test_mistral_analyze_returns_none_without_key(monkeypatch):
    """Pas de MISTRAL_API_KEY -> None sans appel réseau."""
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    import llm_analyzer
    llm_analyzer._mistral_client = None
    result = llm_analyzer._mistral_analyze("test texte")
    assert result is None


def test_mistral_analyze_returns_dict_on_valid_response(monkeypatch):
    """Réponse JSON valide -> dict avec _source='mistral'."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234567890abcdef")
    import llm_analyzer
    from unittest.mock import MagicMock, patch

    fake_json = (
        '{"score_pertinence": 75, "tag_pertinence": "Très pertinent", '
        '"type_marche": "Maintenance", "domaines_concernes": ["SSI"], '
        '"territoire": "La Réunion", "marques_concurrentes_citees": [], '
        '"risques_penalites": null, "justification_score": "SSI La Réunion."}'
    )
    mock_choice = MagicMock()
    mock_choice.message.content = fake_json
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("llm_analyzer._get_mistral_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_get.return_value = mock_client
        llm_analyzer._mistral_client = None

        result = llm_analyzer._mistral_analyze("Maintenance SSI La Réunion 974")

    assert result is not None
    assert result["_source"] == "mistral"
    assert result["score_pertinence"] == 75


def test_mistral_analyze_raises_quota_error_on_429(monkeypatch):
    """HTTP 429 -> _LLMQuotaError levée."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234567890abcdef")
    import llm_analyzer
    from unittest.mock import MagicMock, patch
    import pytest

    exc_429 = Exception("Rate limit")
    exc_429.status_code = 429

    with patch("llm_analyzer._get_mistral_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = exc_429
        mock_get.return_value = mock_client
        llm_analyzer._mistral_client = None

        with pytest.raises(llm_analyzer._LLMQuotaError):
            llm_analyzer._mistral_analyze("test")


def test_mistral_analyze_returns_none_on_auth_error(monkeypatch):
    """HTTP 401 -> None (clé invalide), pas d'exception propagée."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234567890abcdef")
    import llm_analyzer
    from unittest.mock import MagicMock, patch

    exc_401 = Exception("Unauthorized")
    exc_401.status_code = 401

    with patch("llm_analyzer._get_mistral_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = exc_401
        mock_get.return_value = mock_client
        llm_analyzer._mistral_client = None

        result = llm_analyzer._mistral_analyze("test")

    assert result is None


def test_mistral_analyze_returns_none_on_invalid_json(monkeypatch):
    """Réponse non-JSON -> None (pas d'exception propagée)."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234567890abcdef")
    import llm_analyzer
    from unittest.mock import MagicMock, patch

    mock_choice = MagicMock()
    mock_choice.message.content = "Désolé je ne peux pas répondre."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    with patch("llm_analyzer._get_mistral_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_get.return_value = mock_client
        llm_analyzer._mistral_client = None

        result = llm_analyzer._mistral_analyze("test texte")

    assert result is None


def test_analyze_tender_routes_to_mistral_when_provider_is_mistral(monkeypatch):
    """LLM_PROVIDER=mistral -> _mistral_analyze appelé, pas _claude_analyze."""
    monkeypatch.setenv("LLM_PROVIDER", "mistral")
    import llm_analyzer

    fake_mistral_result = {
        "score_pertinence": 70,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "SSI Réunion.",
        "_source": "mistral",
    }
    calls = {"mistral": 0, "claude": 0}

    def fake_mistral(text):
        calls["mistral"] += 1
        return fake_mistral_result

    def fake_claude(text):
        calls["claude"] += 1
        return None

    monkeypatch.setattr(llm_analyzer, "_mistral_analyze", fake_mistral)
    monkeypatch.setattr(llm_analyzer, "_claude_analyze", fake_claude)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")

    assert calls["mistral"] == 1
    assert calls["claude"] == 0
    assert result["_source"] == "mistral"


def test_analyze_tender_routes_to_claude_by_default(monkeypatch):
    """LLM_PROVIDER absent -> _claude_analyze appelé (rétrocompat)."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    import llm_analyzer

    calls = {"mistral": 0, "claude": 0}

    def fake_claude(text):
        calls["claude"] += 1
        return None

    def fake_mistral(text):
        calls["mistral"] += 1
        return None

    monkeypatch.setattr(llm_analyzer, "_claude_analyze", fake_claude)
    monkeypatch.setattr(llm_analyzer, "_mistral_analyze", fake_mistral)

    llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")

    assert calls["claude"] == 1
    assert calls["mistral"] == 0
