# Support multi-provider LLM (Anthropic + Mistral) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettre à l'utilisateur de choisir entre Anthropic (Claude) et Mistral comme moteur LLM pour l'analyse des marchés depuis la page Paramètres, sans obligation de configurer les deux clés.

**Architecture:** `LLM_PROVIDER` dans `.env` contrôle le routage dans `llm_analyzer.py`. `analyze_tender()` et `auto_analyze_claude()` lisent cette variable pour appeler `_claude_analyze()` ou `_mistral_analyze()`. La page Paramètres expose un sélecteur radio provider + une section clé Mistral en parallèle de la section Anthropic existante. Fallback sur analyse locale si aucune clé configurée.

**Tech Stack:** Python 3.11+, Streamlit, `mistralai>=1.0.0` (SDK officiel Mistral), `python-dotenv`, pytest + monkeypatch

---

### Task 1: Dépendances et variables d'environnement

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1: Ajouter `mistralai` à `requirements.txt`**

Ouvrir `requirements.txt` et ajouter après la ligne `anthropic>=0.25.0` :

```
mistralai>=1.0.0
```

- [ ] **Step 2: Mettre à jour `.env.example`**

Ouvrir `.env.example`. Remplacer la ligne `ANTHROPIC_API_KEY=sk-ant-api03-...votre_cle_anthropic_ici...` par :

```
ANTHROPIC_API_KEY=sk-ant-api03-...votre_cle_anthropic_ici...
MISTRAL_API_KEY=
LLM_PROVIDER=anthropic
```

- [ ] **Step 3: Installer la dépendance**

```bash
pip install "mistralai>=1.0.0"
```

Résultat attendu : `Successfully installed mistralai-X.Y.Z` (pas d'erreur)

- [ ] **Step 4: Commiter**

```bash
git add requirements.txt .env.example
git commit -m "feat: add mistralai dependency and LLM_PROVIDER env var"
```

---

### Task 2: `_get_mistral_client()` et `_mistral_analyze()` dans `llm_analyzer.py`

**Files:**
- Modify: `llm_analyzer.py`
- Test: `tests/test_llm_analyzer.py`

- [ ] **Step 1: Écrire les tests qui vont échouer**

Ajouter à la fin de `tests/test_llm_analyzer.py` :

```python
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
pytest tests/test_llm_analyzer.py::test_mistral_analyze_returns_none_without_key -v
```

Résultat attendu : `FAILED` avec `AttributeError: module 'llm_analyzer' has no attribute '_mistral_analyze'`

- [ ] **Step 3: Ajouter le client et la fonction dans `llm_analyzer.py`**

Dans `llm_analyzer.py`, localiser la ligne `_anthropic_client = None` (environ ligne 535). Juste après le bloc `_get_anthropic_client()` (fin de la fonction, environ ligne 549), ajouter :

```python
_mistral_client = None


def _get_mistral_client():
    global _mistral_client
    api_key = os.getenv("MISTRAL_API_KEY", "").strip()
    if not api_key:
        return None
    if _mistral_client is None:
        try:
            from mistralai import Mistral
            _mistral_client = Mistral(api_key=api_key)
        except Exception:
            return None
    return _mistral_client


def _mistral_analyze(text: str) -> dict | None:
    """Analyse via l'API Mistral (mistral-large-latest).

    Retourne None si la clé API est absente ou en cas d'erreur inattendue.
    Lève _LLMQuotaError si le quota API est atteint (429).
    """
    client = _get_mistral_client()
    if client is None:
        return None
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Analyse ce marché :\n\n"
                        "<MARCHE_CONTENT>\n"
                        f"{text[:8000]}\n"
                        "</MARCHE_CONTENT>"
                    ),
                },
            ],
        )
        raw = response.choices[0].message.content
        if not raw:
            _log.warning("Mistral : réponse vide")
            return None
        raw_clean = raw.strip()
        raw_clean = re.sub(r"^```(?:json)?\s*", "", raw_clean)
        raw_clean = re.sub(r"\s*```$", "", raw_clean).strip()
        try:
            result = json.loads(raw_clean)
        except json.JSONDecodeError:
            _log.warning("Mistral : réponse non-JSON — fallback analyse locale")
            return None
        result["_source"] = "mistral"
        return result
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        if status == 429:
            retry_after = None
            try:
                retry_after = int(getattr(exc, "headers", {}).get("retry-after", 0)) or None
            except Exception:
                pass
            raise _LLMQuotaError(retry_after=retry_after)
        if status in (401, 403):
            _log.warning("Clé API Mistral invalide ou permissions insuffisantes")
            return None
        _log.warning("Mistral analyse échouée (erreur inattendue) : %s", str(exc)[:200])
        return None
```

- [ ] **Step 4: Lancer tous les nouveaux tests**

```bash
pytest tests/test_llm_analyzer.py::test_mistral_analyze_returns_none_without_key tests/test_llm_analyzer.py::test_mistral_analyze_returns_dict_on_valid_response tests/test_llm_analyzer.py::test_mistral_analyze_raises_quota_error_on_429 tests/test_llm_analyzer.py::test_mistral_analyze_returns_none_on_auth_error tests/test_llm_analyzer.py::test_mistral_analyze_returns_none_on_invalid_json -v
```

Résultat attendu : `5 passed`

- [ ] **Step 5: Vérifier la suite complète**

```bash
pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : tous les tests passent.

- [ ] **Step 6: Commiter**

```bash
git add llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat: add _mistral_analyze() and _get_mistral_client() to llm_analyzer"
```

---

### Task 3: Routage `LLM_PROVIDER` dans `analyze_tender()` et `auto_analyze_claude()`

**Files:**
- Modify: `llm_analyzer.py`
- Test: `tests/test_llm_analyzer.py`

- [ ] **Step 1: Écrire les tests de routage**

Ajouter à la fin de `tests/test_llm_analyzer.py` :

```python
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
```

- [ ] **Step 2: Vérifier que les tests échouent**

```bash
pytest tests/test_llm_analyzer.py::test_analyze_tender_routes_to_mistral_when_provider_is_mistral tests/test_llm_analyzer.py::test_analyze_tender_routes_to_claude_by_default -v
```

Résultat attendu : `FAILED` (le routage n'est pas encore implémenté).

- [ ] **Step 3: Modifier `analyze_tender()` dans `llm_analyzer.py`**

Remplacer la fonction `analyze_tender` existante par :

```python
def analyze_tender(text: str, source_url: str | None = None) -> dict:
    """
    Analyse un appel d'offre. Si source_url est fourni et accessible publiquement,
    enrichit le texte avec le contenu de la page DCE avant l'analyse.
    Route vers Claude ou Mistral selon LLM_PROVIDER (.env). Fallback analyse locale.
    """
    if source_url:
        dce_content = fetch_dce_content(source_url)
        if dce_content:
            text = text + "\n\n[Contenu page DCE]\n" + dce_content

    local_result = _local_analyze(text)

    provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
    try:
        if provider == "mistral":
            llm_result = _mistral_analyze(text)
        else:
            llm_result = _claude_analyze(text)
    except _LLMQuotaError:
        llm_result = None

    if llm_result is not None:
        combined_score = compute_combined_score(
            llm_score=llm_result.get("score_pertinence", 0),
            local_score=local_result.get("score_pertinence", 0),
            llm_available=True,
        )
        llm_result["score_pertinence"] = combined_score
        llm_result.setdefault("tag_pertinence", _score_to_tag(combined_score))
        llm_result.setdefault("domaines_concernes", local_result.get("domaines_concernes", []))
        llm_result.setdefault("justification_score", local_result.get("justification_score", ""))
        llm_result.setdefault("territoire_ia", local_result.get("territoire_ia", "Non précisé"))
        return llm_result

    return local_result
```

- [ ] **Step 4: Modifier `auto_analyze_claude()` dans `llm_analyzer.py`**

Dans la fonction `auto_analyze_claude()`, localiser ce bloc (environ lignes 751–760) :

```python
        try:
            llm_result = _claude_analyze(text)
        except _LLMQuotaError as qe:
            # Quota atteint : on sauvegarde ce qui est fait et on arrête immédiatement
            if nb_done > 0:
                db.commit()
            if progress_cb:
                progress_cb(len(pending), len(pending), "")
            retry = qe.retry_after if qe.retry_after is not None else 60
            return nb_done, retry
```

Le remplacer par :

```python
        provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
        try:
            if provider == "mistral":
                llm_result = _mistral_analyze(text)
            else:
                llm_result = _claude_analyze(text)
        except _LLMQuotaError as qe:
            # Quota atteint : on sauvegarde ce qui est fait et on arrête immédiatement
            if nb_done > 0:
                db.commit()
            if progress_cb:
                progress_cb(len(pending), len(pending), "")
            retry = qe.retry_after if qe.retry_after is not None else 60
            return nb_done, retry
```

- [ ] **Step 5: Lancer les tests de routage**

```bash
pytest tests/test_llm_analyzer.py::test_analyze_tender_routes_to_mistral_when_provider_is_mistral tests/test_llm_analyzer.py::test_analyze_tender_routes_to_claude_by_default -v
```

Résultat attendu : `2 passed`

- [ ] **Step 6: Vérifier toute la suite de tests**

```bash
pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : tous les tests passent.

- [ ] **Step 7: Commiter**

```bash
git add llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat: route analyze_tender() and auto_analyze_claude() via LLM_PROVIDER"
```

---

### Task 4: Refonte de la section IA dans `pages/parametres.py`

**Files:**
- Modify: `pages/parametres.py`

*Cette tâche modifie l'UI Streamlit — test manuel uniquement (pas de test unitaire pour les widgets Streamlit).*

- [ ] **Step 1: Remplacer la section IA dans `pages/parametres.py`**

Localiser le bloc commençant par (environ ligne 90) :

```python
# ── Section clé API Claude ────────────────────────────────────────────────────
st.header("🤖 Intelligence Artificielle — Clé API Claude")
```

…jusqu'à la fin de la section test Claude (environ ligne 181, fin du `except Exception as exc:`). Remplacer **tout ce bloc** par :

```python
# ── Section Intelligence Artificielle ────────────────────────────────────────
st.header("🤖 Intelligence Artificielle")
st.caption("Choisissez le fournisseur IA et configurez votre clé. Une seule clé suffit.")

_current_provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
_provider_options = ["Anthropic (Claude)", "Mistral"]
_provider_index = 1 if _current_provider == "mistral" else 0

_selected_provider = st.radio(
    "Fournisseur IA actif",
    _provider_options,
    index=_provider_index,
    horizontal=True,
    help="Le fournisseur sélectionné sera utilisé pour toutes les analyses de marchés.",
)

_new_provider_value = "mistral" if _selected_provider == "Mistral" else "anthropic"
if _new_provider_value != _current_provider:
    from dotenv import set_key as _set_key
    _set_key(".env", "LLM_PROVIDER", _new_provider_value)
    os.environ["LLM_PROVIDER"] = _new_provider_value
    st.success(f"Fournisseur basculé vers **{_selected_provider}** ✓")
    st.rerun()

st.markdown("---")

# ── Sous-section Anthropic ────────────────────────────────────────────────────
st.subheader("🔵 Anthropic (Claude)")
st.caption("Modèle utilisé : claude-opus-4-7. Clé commençant par `sk-ant-`.")

current_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
_key_ok = bool(current_key and not current_key.startswith("sk-ant-...") and len(current_key) > 20)

if _key_ok:
    st.success(f"✅ Clé configurée (`{current_key[:8]}…{'*' * 8}`)")
else:
    st.warning("⚠️ Clé non configurée — saisir ci-dessous pour activer Claude.")

with st.expander("🔑 Configurer la clé Anthropic", expanded=not _key_ok):
    st.markdown("""
**Obtenir une clé :** [console.anthropic.com](https://console.anthropic.com) → API Keys → Create Key

**Coût estimé :** moins de 1 €/mois pour 50–150 marchés analysés.
Un rechargement de 5 $ couvre généralement plusieurs mois d'utilisation.
""")
    new_key = st.text_input(
        "Clé API Anthropic",
        type="password",
        placeholder="sk-ant-api03-…",
        key="anthropic_api_key_input",
        help="La clé doit commencer par sk-ant-",
    )
    col_save, col_test, col_spacer = st.columns([2, 2, 4])
    with col_save:
        if st.button("💾 Enregistrer la clé", key="save_anthropic_key", type="primary"):
            key_to_save = new_key.strip()
            if key_to_save.startswith("sk-ant-") and len(key_to_save) > 20:
                from dotenv import set_key as _set_key
                _set_key(".env", "ANTHROPIC_API_KEY", key_to_save)
                os.environ["ANTHROPIC_API_KEY"] = key_to_save
                try:
                    import llm_analyzer
                    llm_analyzer._anthropic_client = None
                except Exception:
                    pass
                st.success("✅ Clé enregistrée — active immédiatement, sans redémarrage.")
                st.rerun()
            else:
                st.error("Format invalide — la clé doit commencer par `sk-ant-`")
    with col_test:
        if st.button("🧪 Tester la clé", key="test_anthropic_key"):
            key_to_test = new_key.strip() or current_key
            if not key_to_test or key_to_test == "sk-ant-...":
                st.error("Entrez d'abord une clé.")
            else:
                with st.spinner("Connexion à Claude en cours…"):
                    try:
                        import anthropic as _ant
                        _test_client = _ant.Anthropic(api_key=key_to_test)
                        _test_client.messages.create(
                            model="claude-haiku-4-5-20251001",
                            max_tokens=5,
                            messages=[{"role": "user", "content": "OK"}],
                        )
                        st.success("✅ Clé valide — connexion à Claude réussie.")
                    except _ant.AuthenticationError:
                        st.error("❌ Clé invalide — vérifiez la valeur copiée depuis console.anthropic.com")
                    except Exception as exc:
                        st.error(f"Erreur inattendue : {exc}")

st.markdown("")

# ── Sous-section Mistral ──────────────────────────────────────────────────────
st.subheader("🟠 Mistral AI")
st.caption("Modèle utilisé : mistral-large-latest. Plan gratuit : 1 milliard de tokens/mois.")

current_mistral_key = os.getenv("MISTRAL_API_KEY", "").strip()
_mistral_key_ok = bool(current_mistral_key and len(current_mistral_key) > 20)

if _mistral_key_ok:
    st.success(f"✅ Clé configurée (`{current_mistral_key[:8]}…{'*' * 8}`)")
else:
    st.warning("⚠️ Clé non configurée — saisir ci-dessous pour activer Mistral.")

with st.expander("🔑 Configurer la clé Mistral", expanded=not _mistral_key_ok):
    st.markdown("""
**Obtenir une clé gratuite :** [console.mistral.ai](https://console.mistral.ai) → API Keys → Create new key

**Plan gratuit :** 1 milliard de tokens/mois, accès à tous les modèles, aucune carte bancaire requise.
""")
    new_mistral_key = st.text_input(
        "Clé API Mistral",
        type="password",
        placeholder="Coller votre clé Mistral ici…",
        key="mistral_api_key_input",
    )
    col_save_mis, col_test_mis, _ = st.columns([2, 2, 4])
    with col_save_mis:
        if st.button("💾 Enregistrer la clé", key="save_mistral_key", type="primary"):
            key_to_save = new_mistral_key.strip()
            if len(key_to_save) > 20:
                from dotenv import set_key as _set_key
                _set_key(".env", "MISTRAL_API_KEY", key_to_save)
                os.environ["MISTRAL_API_KEY"] = key_to_save
                try:
                    import llm_analyzer
                    llm_analyzer._mistral_client = None
                except Exception:
                    pass
                st.success("✅ Clé enregistrée — active immédiatement, sans redémarrage.")
                st.rerun()
            else:
                st.error("Clé invalide — vérifiez que vous avez bien copié la clé complète.")
    with col_test_mis:
        if st.button("🧪 Tester la clé", key="test_mistral_key"):
            key_to_test = new_mistral_key.strip() or current_mistral_key
            if not key_to_test:
                st.error("Entrez d'abord une clé.")
            else:
                with st.spinner("Connexion à Mistral en cours…"):
                    try:
                        from mistralai import Mistral as _Mistral
                        _test_mistral = _Mistral(api_key=key_to_test)
                        _test_mistral.chat.complete(
                            model="mistral-small-latest",
                            messages=[{"role": "user", "content": "OK"}],
                        )
                        st.success("✅ Clé valide — connexion à Mistral réussie.")
                    except Exception as _exc:
                        _status = getattr(_exc, "status_code", None)
                        if _status in (401, 403):
                            st.error("❌ Clé invalide — vérifiez console.mistral.ai")
                        else:
                            st.error(f"Erreur inattendue : {_exc}")
```

- [ ] **Step 2: Lancer l'application et tester manuellement**

```bash
streamlit run app.py
```

Dans la page **Paramètres → 🤖 Intelligence Artificielle**, vérifier :

1. Le radio button affiche "Anthropic (Claude)" sélectionné par défaut
2. Changer vers "Mistral" → message de confirmation + rechargement automatique
3. Les deux sous-sections (🔵 Anthropic et 🟠 Mistral) sont visibles simultanément
4. Saisir une clé fictive dans Mistral (> 20 chars) → bouton Enregistrer → succès + rechargement
5. Bouton "🧪 Tester" Anthropic avec une vraie clé → ✅ ou ❌ selon validité
6. Retourner sur "Anthropic (Claude)" → radio rebascule + `.env` mis à jour

- [ ] **Step 3: Commiter**

```bash
git add pages/parametres.py
git commit -m "feat: refonte section IA Paramètres — sélecteur provider + clé Mistral"
```
