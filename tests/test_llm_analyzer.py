import sys
import os

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

    result = _local_analyze(
        "Maintenance SSI système de sécurité incendie La Réunion 974"
    )
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
    """Vérifie que analyze_tender combine scores quand Mistral répond."""
    from llm_analyzer import _local_analyze
    import llm_analyzer

    fake_mistral = {
        "score_pertinence": 80,
        "tag_pertinence": "Très pertinent",
        "type_marche": "Maintenance",
        "domaines_concernes": ["SSI"],
        "territoire": "La Réunion",
        "marques_concurrentes_citees": [],
        "risques_penalites": None,
        "justification_score": "Marché SSI direct.",
        "_source": "mistral",
    }
    monkeypatch.setattr(llm_analyzer, "_mistral_analyze", lambda text: fake_mistral)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")
    local = _local_analyze("Maintenance SSI La Réunion 974")
    expected_score = round(80 * 0.70 + local["score_pertinence"] * 0.30)
    assert result["score_pertinence"] == expected_score
    assert result["_source"] == "mistral"


def test_local_analyze_empty_string():
    from llm_analyzer import _local_analyze

    result = _local_analyze("")
    assert "score_pertinence" in result
    assert result["score_pertinence"] == 0


def test_analyze_tender_structured_returns_none_for_short_description():
    """Description < 50 chars -> None sans appeler l API."""
    from llm_analyzer import analyze_tender_structured

    result = analyze_tender_structured("Titre", "Court")
    assert result is None


def test_analyze_tender_structured_returns_none_without_api_key(monkeypatch):
    """Pas de MISTRAL_API_KEY -> None."""
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    import llm_analyzer

    llm_analyzer._mistral_client = None
    from llm_analyzer import analyze_tender_structured

    result = analyze_tender_structured(
        "Installation SSI ERP type J",
        "Installation d un systeme de securite incendie dans un ERP de type J, categorie 2.",
    )
    assert result is None


def test_analyze_tender_structured_parses_valid_json(monkeypatch):
    """Réponse Mistral JSON valide -> dict avec les bons champs."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234")
    import llm_analyzer
    from unittest.mock import MagicMock

    fake_json = '{"budget_estime": "150 000 euro", "type_travaux": "Installation neuve", "lots": ["Lot 1 - Detection"], "keywords_techniques": ["SSI categorie A"], "acheteur_type": "Etablissement scolaire", "niveau_concurrence": "Eleve", "recommandation": "GO", "score_confiance": 82, "justification": "ERP type J, coeur de metier."}'
    mock_choice = MagicMock()
    mock_choice.message.content = fake_json
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = mock_response
    llm_analyzer._mistral_client = None
    monkeypatch.setattr(llm_analyzer, "_get_mistral_client", lambda: mock_client)

    from llm_analyzer import analyze_tender_structured

    result = analyze_tender_structured(
        "Installation SSI ERP type J",
        "Installation d un systeme de securite incendie dans un ERP de type J categorie 2, desenfumage CMSI inclus.",
        amount=150000,
    )

    assert result is not None
    assert result["recommandation"] == "GO"
    assert result["score_confiance"] == 82
    assert "budget_estime" in result
    assert isinstance(result["lots"], list)


def test_analyze_tender_structured_handles_invalid_json(monkeypatch):
    """Mistral retourne du texte invalide -> None sans exception."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234")
    import llm_analyzer
    from unittest.mock import MagicMock

    mock_choice = MagicMock()
    mock_choice.message.content = "Desole, je ne peux pas repondre."
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.complete.return_value = mock_response
    llm_analyzer._mistral_client = None
    monkeypatch.setattr(llm_analyzer, "_get_mistral_client", lambda: mock_client)

    from llm_analyzer import analyze_tender_structured

    result = analyze_tender_structured(
        "Installation SSI",
        "Installation d un systeme de securite incendie complet avec CMSI et desenfumage.",
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


def test_mistral_analyze_raises_auth_error_on_401(monkeypatch):
    """HTTP 401 -> _LLMAuthError (fast-fail, pas de None silencieux)."""
    monkeypatch.setenv("MISTRAL_API_KEY", "fake-mistral-key-1234567890abcdef")
    import llm_analyzer
    import pytest
    from unittest.mock import MagicMock, patch

    exc_401 = Exception("Unauthorized")
    exc_401.status_code = 401

    with patch("llm_analyzer._get_mistral_client") as mock_get:
        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = exc_401
        mock_get.return_value = mock_client
        llm_analyzer._mistral_client = None

        with pytest.raises(llm_analyzer._LLMAuthError):
            llm_analyzer._mistral_analyze("test")


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


def test_analyze_tender_routes_to_mistral(monkeypatch):
    """analyze_tender utilise toujours _mistral_analyze."""
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
    calls = {"mistral": 0}

    def fake_mistral(text):
        calls["mistral"] += 1
        return fake_mistral_result

    monkeypatch.setattr(llm_analyzer, "_mistral_analyze", fake_mistral)

    result = llm_analyzer.analyze_tender("Maintenance SSI La Réunion 974")

    assert calls["mistral"] == 1
    assert result["_source"] == "mistral"


def test_reset_mistral_client_sets_none():
    import llm_analyzer

    llm_analyzer._mistral_client = object()  # simuler un client existant
    llm_analyzer.reset_mistral_client()
    assert llm_analyzer._mistral_client is None


def test_system_prompt_contains_decision_field():
    from llm_analyzer import SYSTEM_PROMPT

    assert '"decision"' in SYSTEM_PROMPT
    assert '"OUI"' in SYSTEM_PROMPT
    assert '"NON"' in SYSTEM_PROMPT


def test_system_prompt_contains_alerte_erp_field():
    from llm_analyzer import SYSTEM_PROMPT

    assert '"alerte_erp"' in SYSTEM_PROMPT


def test_system_prompt_enforces_date_extraction():
    from llm_analyzer import SYSTEM_PROMPT

    assert "IMPÉRATIVEMENT" in SYSTEM_PROMPT or "obligatoire" in SYSTEM_PROMPT.lower()


# ---------------------------------------------------------------------------
# Critique #2 — Thread-safety du singleton Mistral
# ---------------------------------------------------------------------------


def test_mistral_singleton_has_thread_lock():
    """Un threading.Lock protège le singleton _mistral_client (attribut requis)."""
    import threading
    import llm_analyzer

    assert hasattr(llm_analyzer, "_mistral_client_lock"), (
        "_mistral_client_lock absent de llm_analyzer — le singleton n'est pas thread-safe"
    )
    assert isinstance(llm_analyzer._mistral_client_lock, type(threading.Lock())), (
        "_mistral_client_lock doit être un threading.Lock"
    )


def test_get_mistral_client_thread_safe_no_duplicate_creation(monkeypatch):
    """Appels concurrents à _get_mistral_client() ne créent qu'un seul client."""
    import threading
    import llm_analyzer

    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key-concurrent-test")
    llm_analyzer._mistral_client = None

    creation_count = [0]
    original_init = None

    # Patch le constructeur Mistral pour compter les instanciations
    from mistralai.client import Mistral as _RealMistral

    class CountingMistral(_RealMistral):
        def __init__(self, **kwargs):
            creation_count[0] += 1
            super().__init__(**kwargs)

    monkeypatch.setattr("llm_analyzer.Mistral", CountingMistral, raising=False)

    # Injecter le patch dans le module
    import mistralai.client as _mc
    original_cls = _mc.Mistral
    _mc.Mistral = CountingMistral

    try:
        results = []

        def get():
            results.append(llm_analyzer._get_mistral_client())

        threads = [threading.Thread(target=get) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert creation_count[0] <= 2, (
            f"Le constructeur Mistral a été appelé {creation_count[0]} fois "
            f"pour 10 threads concurrents — le singleton n'est pas protégé"
        )
        # Tous les threads ont obtenu un client non-None
        assert all(r is not None for r in results)
    finally:
        _mc.Mistral = original_cls
        llm_analyzer._mistral_client = None


def test_reset_mistral_client_thread_safe(monkeypatch):
    """reset_mistral_client() et _get_mistral_client() sont safe en parallèle."""
    import threading
    import llm_analyzer

    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key-reset-safe")
    llm_analyzer._mistral_client = None
    errors = []

    def do_get():
        try:
            llm_analyzer._get_mistral_client()
        except Exception as e:
            errors.append(f"get: {e}")

    def do_reset():
        try:
            llm_analyzer.reset_mistral_client()
        except Exception as e:
            errors.append(f"reset: {e}")

    threads = [
        threading.Thread(target=(do_get if i % 2 == 0 else do_reset))
        for i in range(20)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Exceptions sous accès concurrent : {errors}"


# ---------------------------------------------------------------------------
# Finding #3 — Clé de cache incohérente avec la troncature à 6000 chars
# ---------------------------------------------------------------------------


def test_local_cache_key_uses_truncated_text():
    """Deux textes identiques sur [:6000] partagent le cache — _local_analyze_impl appelé une seule fois."""
    import llm_analyzer
    from unittest.mock import patch

    base = "SSI incendie alarme détecteur La Réunion 974 " * 134  # ~6000 chars
    text_a = base[:6000] + " SUFFIXE_UNIQUEMENT_A_texte_tres_long"
    text_b = base[:6000] + " SUFFIXE_COMPLETEMENT_DIFFERENT_B_encore_plus_long"

    assert text_a[:6000] == text_b[:6000], "Précondition : les 6000 premiers chars doivent être identiques"
    assert text_a != text_b, "Précondition : les textes complets doivent différer"

    with llm_analyzer._local_cache_lock:
        llm_analyzer._local_cache.clear()

    call_count = [0]
    original_impl = llm_analyzer._local_analyze_impl

    def counting_impl(text):
        call_count[0] += 1
        return original_impl(text)

    with patch.object(llm_analyzer, "_local_analyze_impl", counting_impl):
        llm_analyzer._local_analyze(text_a)
        llm_analyzer._local_analyze(text_b)

    assert call_count[0] == 1, (
        f"_local_analyze_impl appelé {call_count[0]} fois pour 2 textes "
        f"identiques sur les 6000 premiers chars — clé de cache sur texte complet au lieu de [:6000]"
    )


# ---------------------------------------------------------------------------
# Finding #4 — auto_analyze_pending() sans LIMIT mémoire
# ---------------------------------------------------------------------------


def test_auto_analyze_pending_accepts_limit_parameter():
    """auto_analyze_pending() expose un paramètre limit pour limiter la charge mémoire."""
    import inspect
    from llm_analyzer import auto_analyze_pending

    sig = inspect.signature(auto_analyze_pending)
    assert "limit" in sig.parameters, (
        "auto_analyze_pending() n'a pas de paramètre 'limit' — "
        "charge tous les tenders en RAM sans filet de sécurité"
    )


# ---------------------------------------------------------------------------
# Finding #5 — analyze_tender_structured() : échecs silencieux sans log
# ---------------------------------------------------------------------------


def test_analyze_tender_structured_logs_warning_on_exception(monkeypatch, caplog):
    """analyze_tender_structured() log un warning quand Mistral lève une exception."""
    import logging
    import llm_analyzer
    from unittest.mock import MagicMock

    monkeypatch.setenv("MISTRAL_API_KEY", "fake-key-log-test")

    mock_client = MagicMock()
    mock_client.chat.complete.side_effect = Exception("Simulated network error")
    monkeypatch.setattr(llm_analyzer, "_get_mistral_client", lambda: mock_client)

    with caplog.at_level(logging.WARNING, logger="llm_analyzer"):
        result = llm_analyzer.analyze_tender_structured(
            "Installation SSI ERP",
            "Installation d'un système de sécurité incendie complet dans un ERP de type J.",
        )

    assert result is None
    assert caplog.records, (
        "Aucun log émis lors d'une exception dans analyze_tender_structured — "
        "les échecs sont invisibles en production"
    )
    assert any("analyze_tender_structured" in r.message for r in caplog.records), (
        "Le log doit mentionner 'analyze_tender_structured' pour être identifiable"
    )
