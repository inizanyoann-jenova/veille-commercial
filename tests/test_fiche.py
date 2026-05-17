import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fiche_logic import _compute_fiche_data


# ── label_action & steps ─────────────────────────────────────────────────────

def test_go_deadline_passe():
    d = _compute_fiche_data(70, -3, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "⚠️ Date limite dépassée"
    assert len(d["steps"]) == 2

def test_go_delai_critique():
    d = _compute_fiche_data(70, 5, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🚨 Action immédiate — délai critique"
    assert len(d["steps"]) == 4

def test_go_priorite():
    d = _compute_fiche_data(70, 20, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🟢 Traiter en priorité"

def test_go_planifier():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🟢 Planifier la réponse"

def test_etude():
    d = _compute_fiche_data(50, 30, "Autre", "Non précisé", False, "", {})
    assert d["label_action"] == "🟡 À évaluer — décision requise"

def test_passer():
    d = _compute_fiche_data(10, None, "Autre", "Non précisé", False, "", {})
    assert d["label_action"] == "🔴 Hors périmètre DEF OI"


# ── sous-scores sm / sg / sk / smaint ────────────────────────────────────────

def test_sm_ssi():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "Non précisé", False, "", {})
    assert d["sm"] == 45

def test_sm_cmsi():
    d = _compute_fiche_data(70, None, "💨 CMSI / Désenfumage", "Non précisé", False, "", {})
    assert d["sm"] == 40

def test_sm_video():
    d = _compute_fiche_data(70, None, "📷 Vidéosurveillance / CCTV", "Non précisé", False, "", {})
    assert d["sm"] == 40

def test_sm_courants():
    d = _compute_fiche_data(70, None, "⚡ Courants faibles", "Non précisé", False, "", {})
    assert d["sm"] == 30

def test_sm_autre():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "", {})
    assert d["sm"] == 5

def test_sg_reunion():
    d = _compute_fiche_data(70, None, "Autre", "🏝️ La Réunion", False, "", {})
    assert d["sg"] == 30

def test_sg_mayotte():
    d = _compute_fiche_data(70, None, "Autre", "🏝️ Mayotte", False, "", {})
    assert d["sg"] == 30

def test_sg_madagascar():
    d = _compute_fiche_data(70, None, "Autre", "🌍 Madagascar", False, "", {})
    assert d["sg"] == 22

def test_sg_france():
    d = _compute_fiche_data(70, None, "Autre", "🇫🇷 France métropole", False, "", {})
    assert d["sg"] == 10

def test_sg_inconnu():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "", {})
    assert d["sg"] == 0

def test_sk_one_keyword_gives_6():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Installation SSI bâtiment", {})
    assert d["sk"] == 6


def test_sk_two_keywords_gives_10():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Marché CMSI désenfumage", {})
    assert d["sk"] == 10


def test_sk_three_keywords_gives_15():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "SSI CMSI détection incendie", {})
    assert d["sk"] == 15

def test_sk_absent():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Nettoyage parkings", {})
    assert d["sk"] == 0

def test_smaint_true():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", True, "", {})
    assert d["smaint"] == 10

def test_smaint_false():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "", {})
    assert d["smaint"] == 0


# ── bornes exactes ────────────────────────────────────────────────────────────

def test_score_exactement_go():
    d = _compute_fiche_data(65, None, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🟢 Planifier la réponse"

def test_score_exactement_etude():
    d = _compute_fiche_data(35, None, "Autre", "Non précisé", False, "", {})
    assert d["label_action"] == "🟡 À évaluer — décision requise"

def test_jours_restants_zero_label():
    d = _compute_fiche_data(70, 0, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🚨 Action immédiate — délai critique"

def test_jours_restants_zero_risque():
    d = _compute_fiche_data(70, 0, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert any("Délai très court" in r for r in d["risques"])


# ── atouts ────────────────────────────────────────────────────────────────────

def test_atout_coeur_metier_ssi():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "Non précisé", False, "", {})
    assert any("Cœur de métier" in a for a in d["atouts"])

def test_atout_coeur_metier_video():
    d = _compute_fiche_data(70, None, "📷 Vidéosurveillance / CCTV", "Non précisé", False, "", {})
    assert any("Cœur de métier" in a for a in d["atouts"])

def test_atout_perimetre_courants():
    d = _compute_fiche_data(70, None, "⚡ Courants faibles", "Non précisé", False, "", {})
    assert any("Périmètre DEF OI" in a for a in d["atouts"])

def test_atout_presence_locale_974():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert any("974/976" in a for a in d["atouts"])

def test_atout_ocean_indien():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "🌍 Madagascar", False, "", {})
    assert any("Océan Indien" in a for a in d["atouts"])

def test_atout_maintenance():
    d = _compute_fiche_data(70, None, "🔥 SSI / Détection incendie", "Non précisé", True, "", {})
    assert any("Maintenance" in a for a in d["atouts"])

def test_atout_signal_direct():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "SSI CMSI détection incendie", {})
    assert any("Signal direct" in a for a in d["atouts"])

def test_atout_pertinence_limitee_si_aucun():
    d = _compute_fiche_data(70, None, "Autre", "Non précisé", False, "Nettoyage", {})
    assert any("Pertinence limitée" in a for a in d["atouts"])
    assert len(d["atouts"]) == 1


# ── risques ───────────────────────────────────────────────────────────────────

def test_risque_concurrent():
    a = {"marques_concurrentes_citees": ["Siemens", "Bosch"]}
    d = _compute_fiche_data(70, 30, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", a)
    assert any("Siemens" in r for r in d["risques"])

def test_risque_delai_court():
    d = _compute_fiche_data(70, 7, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert any("Délai très court" in r for r in d["risques"])

def test_risque_penalites():
    a = {"risques_penalites": "Pénalités de retard élevées"}
    d = _compute_fiche_data(70, 30, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", a)
    assert any("Pénalités" in r for r in d["risques"])

def test_risque_vide_si_tout_ok():
    d = _compute_fiche_data(70, 60, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["risques"] == []


# ── validation défensive (entrées invalides) ───────────────────────────────────

def test_none_score_defaults_to_zero():
    d = _compute_fiche_data(None, None, "Autre", "Non précisé", False, "", {})
    assert d["label_action"] == "🔴 Hors périmètre DEF OI"


def test_score_above_100_clamped():
    d = _compute_fiche_data(150, None, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", {})
    assert d["label_action"] == "🟢 Planifier la réponse"


def test_none_a_dict_defaults_gracefully():
    d = _compute_fiche_data(70, 30, "🔥 SSI / Détection incendie", "🏝️ La Réunion", False, "", None)
    assert isinstance(d["risques"], list)


def test_none_domaine_and_territoire():
    d = _compute_fiche_data(10, None, None, None, False, None, {})
    assert d["label_action"] == "🔴 Hors périmètre DEF OI"
    assert d["sm"] == 5
    assert d["sg"] == 0


def test_get_acheteur_history_returns_empty_when_no_match(db, make_tender):
    from fiche_logic import get_acheteur_history
    t = make_tender(title='Installation videosurveillance port')
    result = get_acheteur_history(db, t)
    assert result['nb_total'] == 0


def test_get_acheteur_history_returns_empty_for_short_title(db, make_tender):
    from fiche_logic import get_acheteur_history
    t = make_tender(title='SSI')
    result = get_acheteur_history(db, t)
    assert result['nb_total'] == 0


def test_get_acheteur_history_finds_similar_tenders(db, make_tender):
    from fiche_logic import get_acheteur_history
    target = make_tender(title='Installation detection incendie college')
    make_tender(title='Installation detection incendie lycee', status='Gagne', amount=80000)
    make_tender(title='Installation detection incendie mairie', status='Perdu')
    result = get_acheteur_history(db, target)
    assert result['nb_total'] >= 2


def test_get_acheteur_history_excludes_blacklisted(db, make_tender):
    from fiche_logic import get_acheteur_history
    target = make_tender(title='Installation detection incendie college')
    make_tender(title='Installation detection incendie mairie', is_blacklisted=True)
    make_tender(title='Installation detection incendie lycee', is_blacklisted=True)
    result = get_acheteur_history(db, target)
    assert result['nb_total'] == 0


def test_get_acheteur_history_excludes_self(db, make_tender):
    from fiche_logic import get_acheteur_history
    t = make_tender(title='Installation detection incendie college')
    make_tender(title='Installation detection incendie lycee', status='Gagne', amount=50000)
    result = get_acheteur_history(db, t)
    for other in result.get('derniers', []):
        assert other.id != t.id
