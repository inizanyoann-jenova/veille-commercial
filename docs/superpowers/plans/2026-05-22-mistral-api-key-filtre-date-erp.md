# Mistral API Key, Filtre Date, OUI/NON, ERP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ajouter la saisie de la clé API Mistral dans la sidebar, rendre le rejet des offres sans date strict à la collecte, et enrichir le prompt Mistral avec un champ OUI/NON et une alerte ERP.

**Architecture:** Modifications ciblées sur 3 fichiers (`scraper_utils.py`, `llm_analyzer.py`, `app.py`). Aucune nouvelle dépendance. Aucune modification de schéma BDD.

**Tech Stack:** Python 3.11, Streamlit, Mistral AI SDK, SQLAlchemy, pytest

---

## File Map

| Fichier | Rôle dans ce plan |
|---------|-------------------|
| `scraper_utils.py` | Ajouter rejet offre sans date dans `insert_if_new()` |
| `llm_analyzer.py` | Ajouter `reset_mistral_client()` + mettre à jour `SYSTEM_PROMPT` |
| `app.py` | Ajouter bloc clé API sidebar + `_save_api_key_to_env()` + nettoyage nommage |
| `tests/test_database_helpers.py` | Mettre à jour test existant + ajouter test "date absente = rejet" |
| `tests/test_llm_analyzer.py` | Ajouter tests `reset_mistral_client` + champs `decision`/`alerte_erp` |

---

## Task 1 : Rejet strict des offres sans date dans `insert_if_new()`

**Files:**
- Modify: `scraper_utils.py:127-144`
- Modify: `tests/test_database_helpers.py:99-120`

### Contexte
`insert_if_new()` (ligne 127 de `scraper_utils.py`) rejette déjà les offres trop anciennes (> 31 jours) mais laisse passer les offres sans date (`publication_date = None`). On ajoute le rejet pour date absente. **Attention :** le test existant `test_insert_if_new_adds_tender` crée un Tender sans date — il faudra le mettre à jour.

- [ ] **Step 1 : Écrire le test qui va échouer (date absente = rejet)**

Dans `tests/test_database_helpers.py`, ajouter après la ligne 120 :

```python
def test_insert_if_new_rejects_tender_without_date(db):
    from scraper_utils import insert_if_new
    from models import Tender
    t = Tender(id="X-NODATE", title="Sans date", source="https://example.com",
               publication_date=None, status="À qualifier",
               relevance_score=0, is_blacklisted=False)
    existing = set()
    inserted = insert_if_new(db, t, existing)
    assert inserted is False
    assert "X-NODATE" not in existing
```

- [ ] **Step 2 : Lancer le test pour vérifier qu'il échoue**

```
pytest tests/test_database_helpers.py::test_insert_if_new_rejects_tender_without_date -v
```

Résultat attendu : **FAILED** — `assert False is False` (le tender est actuellement inséré)

- [ ] **Step 3 : Appliquer le changement dans `scraper_utils.py`**

Remplacer la fonction `insert_if_new` (lignes 127-144) par :

```python
def insert_if_new(db, tender_obj, seen_ids: set[str]) -> bool:
    """
    Insère tender_obj dans db si son ID n'est pas dans seen_ids.
    Rejette les articles sans date de publication ou publiés il y a plus de 1 mois.
    Met à jour seen_ids. Retourne True si inséré.
    Ne fait PAS de commit (à faire par l'appelant en batch).
    """
    if tender_obj.id in seen_ids:
        return False
    if not tender_obj.publication_date:
        _log.debug("insert_if_new: article ignoré (date absente) — %s", tender_obj.id)
        return False
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=_MAX_ARTICLE_AGE_DAYS)
    if tender_obj.publication_date.replace(tzinfo=None) < cutoff:
        _log.debug("insert_if_new: article ignoré (trop ancien) — %s", tender_obj.id)
        return False
    seen_ids.add(tender_obj.id)
    db.add(tender_obj)
    return True
```

- [ ] **Step 4 : Mettre à jour le test existant `test_insert_if_new_adds_tender`**

Le test existant (ligne 99) crée un Tender sans date — il faut lui en donner une récente :

```python
def test_insert_if_new_adds_tender(db):
    from scraper_utils import load_existing_ids, insert_if_new
    from models import Tender
    from datetime import datetime, timedelta
    t = Tender(id="X-001", title="Test", source="https://example.com",
               publication_date=datetime.now() - timedelta(days=5),
               status="À qualifier", relevance_score=0, is_blacklisted=False)
    existing = load_existing_ids(db)
    inserted = insert_if_new(db, t, existing)
    assert inserted is True
    assert "X-001" in existing
```

- [ ] **Step 5 : Lancer tous les tests du fichier**

```
pytest tests/test_database_helpers.py -v
```

Résultat attendu : tous **PASSED**

- [ ] **Step 6 : Commit**

```
git add scraper_utils.py tests/test_database_helpers.py
git commit -m "feat(scraper): rejeter les offres sans date de publication dans insert_if_new"
```

---

## Task 2 : `llm_analyzer.py` — `reset_mistral_client()` + SYSTEM_PROMPT enrichi

**Files:**
- Modify: `llm_analyzer.py:627-641` (client Mistral)
- Modify: `llm_analyzer.py:546-608` (SYSTEM_PROMPT)
- Modify: `tests/test_llm_analyzer.py`

### Contexte
`_mistral_client` est un singleton global (ligne 627). On ajoute `reset_mistral_client()` pour l'invalider depuis `app.py` quand la clé change. Le `SYSTEM_PROMPT` reçoit deux nouveaux champs JSON (`decision`, `alerte_erp`) et une instruction renforcée sur `date_publication`.

- [ ] **Step 1 : Écrire les tests qui vont échouer**

Dans `tests/test_llm_analyzer.py`, ajouter à la fin du fichier :

```python
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
```

- [ ] **Step 2 : Lancer les tests pour vérifier qu'ils échouent**

```
pytest tests/test_llm_analyzer.py::test_reset_mistral_client_sets_none tests/test_llm_analyzer.py::test_system_prompt_contains_decision_field tests/test_llm_analyzer.py::test_system_prompt_contains_alerte_erp_field tests/test_llm_analyzer.py::test_system_prompt_enforces_date_extraction -v
```

Résultat attendu : **FAILED** — `reset_mistral_client` n'existe pas, champs absents du prompt

- [ ] **Step 3 : Ajouter `reset_mistral_client()` dans `llm_analyzer.py`**

Après la ligne 641 (fin de `_get_mistral_client`), insérer :

```python
def reset_mistral_client() -> None:
    """Invalide le singleton Mistral — à appeler après changement de clé API."""
    global _mistral_client
    _mistral_client = None
```

- [ ] **Step 4 : Mettre à jour `SYSTEM_PROMPT` dans `llm_analyzer.py`**

Remplacer le bloc JSON de la réponse demandée (dans `SYSTEM_PROMPT`, autour de la ligne 587) — remplacer la section `Réponds UNIQUEMENT en JSON valide` jusqu'à la fin du JSON par :

```python
SYSTEM_PROMPT = """\
Tu es un analyste commercial expert pour DEF Océan Indien, société spécialisée \
en systèmes de sécurité incendie (SSI/CMSI), vidéosurveillance, courants faibles \
et QHSE. Ton rôle : évaluer précisément si un appel d'offres représente une \
opportunité commerciale réelle pour DEF OI.

ZONE PRIORITAIRE : La Réunion (974) et Mayotte (976) — présence locale, \
certifications, réseau établi.
ZONE SECONDAIRE : Madagascar, Maurice, Comores — axe de développement stratégique.
HORS ZONE : France métropole et international = score plafonné à 50 sauf \
composante technique SSI/CMSI très forte.

CŒUR DE MÉTIER DEF OI (domaines où DEF OI peut répondre) :
1. SSI complet : centrales incendie (Notifier, Hochiki, Apollo…), détecteurs \
adressables/conventionnels, déclencheurs manuels (DMC), SMSI, tableaux de \
signalisation (TSI), équipements d'alarme type 1-4, boucles incendie
2. CMSI / Désenfumage : volets coupe-feu, exutoires, extracteurs de fumée, \
amenées d'air, commandes manuelles centralisées, désenfumage naturel ou mécanique
3. Vidéosurveillance / CCTV : caméras IP/PTZ/dôme/thermiques, NVR/DVR, VMS, \
analytics, LPR (lecture de plaques)
4. Courants faibles : contrôle d'accès (badges, biométrie), interphonie, \
visiophone, GTC/GTB, anti-intrusion, télégestion
5. Maintenance réglementaire : vérifications annuelles SSI/CMSI (NF S 61-933), \
MCO, GMAO, astreinte, dépannage, contrats de service
6. QHSE / ERP : audits de sécurité incendie, formations SSIAP/évacuation, \
accompagnement commissions de sécurité, mise en conformité ERP

SIGNAL ERP — PRIORITÉ MAXIMALE : \
hôpital/CHU/EHPAD, école/lycée/université, mairie/préfecture, \
hôtel/résidence, centre commercial, gymnase/piscine/stade, musée/bibliothèque, \
IGH (immeuble grande hauteur). \
Si un ERP est mentionné + contexte sécurité = obligation légale SSI → \
renseigner alerte_erp ET basculer decision à OUI sauf exclusion formelle.

EXCLURE IMPÉRATIVEMENT — score ≤ 15 si aucun signal SSI/Vidéo/CF :
- Gardiennage, agents de sécurité, SSIAP pur, rondes, surveillance humaine
- Génie civil pur, VRD, terrassement, maçonnerie, charpente, gros œuvre
- Électricité HT/BT seule, éclairage public, postes de transformation
- Plomberie, chauffage/CVC pur (sauf CMSI), menuiserie, serrurerie
- Extincteurs seuls (sans SSI), fourniture de matériel de lutte incendie
- Sécurité civile, pompiers, secours

RÈGLE OUI/NON — le commercial ne doit louper aucune affaire :
- "OUI" si score_pertinence >= 45 ET territoire Réunion/Mayotte/Océan Indien
- "OUI" si ERP détecté + contexte sécurité, même si score < 45
- En cas de doute sur le périmètre technique : préférer "OUI"
- "NON" uniquement si exclusion formelle claire (gardiennage, génie civil, hors zone confirmé)

EXTRACTION DE DATE — OBLIGATOIRE :
Cherche IMPÉRATIVEMENT une date dans le texte (date de parution, date de \
publication, date d'avis, date de mise en ligne, date d'affichage…). \
Extrais-la au format YYYY-MM-DD. Si aucune date n'est trouvée dans le texte : \
retourner null.

Réponds UNIQUEMENT en JSON valide, sans commentaire :
{
  "score_pertinence": <entier 0-100>,
  "tag_pertinence": "Très pertinent" | "À évaluer" | "Hors périmètre",
  "decision": "OUI" | "NON",
  "alerte_erp": "<⚠️ ERP DÉTECTÉ — [type bâtiment] : SSI catégorie [X] obligatoire réglementairement>" | null,
  "type_marche": "Travaux" | "Maintenance" | "Fourniture" | "Mixte" | "Inconnu",
  "domaines_concernes": ["SSI", "CMSI", "Vidéosurveillance", "Courants faibles", \
"QHSE", "ERP", "Maintenance"],
  "territoire": "La Réunion" | "Mayotte" | "Océan Indien" | "France métropole" | \
"International" | "Non précisé",
  "marques_concurrentes_citees": ["marque1", "marque2"],
  "risques_penalites": "texte court décrivant pénalités/retenues ou null",
  "date_publication": "date de publication au format YYYY-MM-DD extraite du texte, sinon null",
  "justification_score": "3 phrases : (1) quels domaines métier DEF OI sont présents et avec quelle intensité dans le texte (SSI/CMSI/Vidéo/CF — citer les indices concrets), (2) pourquoi ce territoire est ou non stratégique pour DEF OI (avantage local 974/976, développement OI, ou hors zone), (3) type de prestation et impact commercial direct (maintenance = récurrent + marge, travaux = déclenche futur MCO, ERP = obligation réglementaire). Si hors périmètre, nommer précisément ce qui exclut (ex: gardiennage, génie civil, électricité HT)."
}

BARÈME DE SCORING :
85-100 : SSI/CMSI/Vidéo direct + La Réunion ou Mayotte (974/976)
65-84  : domaine DEF OI présent + territoire prioritaire, OU SSI fort + zone OI
45-64  : signal ERP avec contexte sécurité + territoire OI, OU courants faibles 974/976
25-44  : signal faible ou territoire secondaire seulement, mérite vérification DCE
5-24   : hors périmètre DEF OI ou signaux exclusion dominants\
"""
```

- [ ] **Step 5 : Lancer les tests**

```
pytest tests/test_llm_analyzer.py -v
```

Résultat attendu : tous **PASSED**

- [ ] **Step 6 : Commit**

```
git add llm_analyzer.py tests/test_llm_analyzer.py
git commit -m "feat(llm): ajouter reset_mistral_client + enrichir SYSTEM_PROMPT (decision, alerte_erp, date obligatoire)"
```

---

## Task 3 : `app.py` — Clé API Mistral dans la sidebar + nettoyage nommage

**Files:**
- Modify: `app.py:1505-1573` (bloc `with st.sidebar`)
- Modify: `app.py:1236` (variable `claude_ok` → `llm_ok`)
- Modify: `app.py:1255-1265` (fonction `_display_results`)
- Modify: `app.py:1309` (appel `auto_analyze_claude`)

### Contexte
La sidebar (`with st.sidebar:` ligne 1505) contient les filtres et le bouton collecte. On ajoute un bloc API key juste avant "⚡ Collecte". Les variables `claude_ok` et les messages "🤖 X analysé(s) par IA" sont renommés/mis à jour.

- [ ] **Step 1 : Ajouter `_save_api_key_to_env()` dans `app.py`**

Dans `app.py`, juste avant la ligne `with st.sidebar:` (ligne 1505), ajouter :

```python
def _save_api_key_to_env(api_key: str) -> None:
    """Écrit MISTRAL_API_KEY dans le fichier .env (crée le fichier si absent)."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    key_written = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MISTRAL_API_KEY="):
                    lines.append(f"MISTRAL_API_KEY={api_key}\n")
                    key_written = True
                else:
                    lines.append(line)
    if not key_written:
        lines.append(f"MISTRAL_API_KEY={api_key}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
```

- [ ] **Step 2 : Ajouter le bloc API key dans la sidebar**

Dans `with st.sidebar:`, juste avant `st.markdown("### ⚡ Collecte")` (ligne 1568), insérer :

```python
    st.markdown("---")
    st.markdown("### 🔑 Mistral API")
    _api_key_stored = os.getenv("MISTRAL_API_KEY", "")
    _api_key_input = st.text_input(
        "Clé API Mistral",
        value=_api_key_stored,
        type="password",
        key="mistral_api_key_input",
        label_visibility="collapsed",
        placeholder="sk-...",
    )
    if _api_key_stored:
        st.caption("✅ Clé active")
    else:
        st.caption("⚠️ Clé manquante — analyses LLM désactivées")
    if st.button("💾 Sauvegarder la clé", key="save_api_key", use_container_width=True):
        if _api_key_input.strip():
            _save_api_key_to_env(_api_key_input.strip())
            os.environ["MISTRAL_API_KEY"] = _api_key_input.strip()
            from llm_analyzer import reset_mistral_client
            reset_mistral_client()
            st.success("✓ Clé sauvegardée et active")
        else:
            st.error("La clé ne peut pas être vide.")
```

- [ ] **Step 3 : Renommer `claude_ok` → `llm_ok` dans `_analyze_results()`**

Ligne 1236, remplacer :

```python
claude_ok = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("_source") in ("claude", "gemini"))
```

Par :

```python
llm_ok = sum(1 for t in _new_tenders if (t.llm_analysis or {}).get("_source") in ("mistral", "claude", "gemini"))
```

Et à la ligne 1238, remplacer :

```python
return go_count, etude_count, pass_count, claude_ok
```

Par :

```python
return go_count, etude_count, pass_count, llm_ok
```

- [ ] **Step 4 : Mettre à jour `_display_results()` et la variable réceptrice**

Ligne 1255, la signature `_display_results(total, go_count, etude_count, pass_count, claude_ok, errors, new_ids)` → remplacer `claude_ok` par `llm_ok` dans la signature et dans le corps :

```python
def _display_results(total, go_count, etude_count, pass_count, llm_ok, errors, new_ids):
    if total and new_ids:
        message = (
            f"✅ {total} nouveau(x) marché(s) importé(s) — "
            f"🟢 {go_count} GO · 🟡 {etude_count} À étudier · 🔴 {pass_count} Passer"
        )
        if llm_ok:
            message += f" · 🤖 {llm_ok} analysé(s) par Mistral"
        st.success(message)
    elif total:
        st.success(f"✅ {total} nouveau(x) marché(s) importé(s) — analyse automatique effectuée.")
    elif not errors:
        st.info("Aucune nouvelle offre trouvée.")
```

- [ ] **Step 5 : Mettre à jour l'appel à `_display_results` ligne 1298**

```python
_display_results(total, go_count, etude_count, pass_count, claude_ok, errors, all_new_ids)
```

Remplacer par :

```python
_display_results(total, go_count, etude_count, pass_count, llm_ok, errors, all_new_ids)
```

Et ligne 1293, l'unpacking :

```python
go_count, etude_count, pass_count, claude_ok = _analyze_results(all_new_ids)
```

Remplacer par :

```python
go_count, etude_count, pass_count, llm_ok = _analyze_results(all_new_ids)
```

- [ ] **Step 6 : Lancer les tests pour vérifier qu'aucune régression n'est introduite**

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py -x
```

Résultat attendu : tous **PASSED**

- [ ] **Step 7 : Commit**

```
git add app.py
git commit -m "feat(app): ajouter saisie clé API Mistral dans sidebar + nettoyage nommage llm_ok"
```

---

## Vérification finale

- [ ] **Lancer la suite de tests complète**

```
pytest tests/ -v --ignore=tests/test_scrapers_playwright.py --ignore=tests/test_playwright_base.py
```

Résultat attendu : tous **PASSED**

- [ ] **Vérification manuelle de l'interface**

Lancer l'app :
```
streamlit run app.py
```

Vérifier dans la sidebar :
1. Le bloc "🔑 Mistral API" est visible avec un champ password
2. Le message "⚠️ Clé manquante" s'affiche si `.env` ne contient pas la clé
3. Saisir une clé factice (`sk-test`) → clic "💾 Sauvegarder" → message "✓ Clé sauvegardée"
4. Vérifier que le `.env` a été mis à jour (`MISTRAL_API_KEY=sk-test`)
5. Lancer une collecte → le message de résultat dit "analysé(s) par Mistral" et non "par IA"
