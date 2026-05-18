import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from filters import KEYWORDS_CONSTRUCTION, is_construction_relevant, is_prive_relevant, classify_relevance


# ── is_construction_relevant ─────────────────────────────────────────────────

def test_keywords_construction_not_empty():
    assert len(KEYWORDS_CONSTRUCTION) > 0


def test_is_construction_relevant_hotel():
    assert is_construction_relevant("Construction d'un hôtel 4 étoiles à Saint-Denis") is True


def test_is_construction_relevant_irrelevant():
    assert is_construction_relevant("Résultats du championnat de pétanque") is False


def test_is_construction_relevant_chantier():
    assert is_construction_relevant("Nouveau chantier immobilier dans le Nord") is True


# ── is_prive_relevant : vrais positifs ───────────────────────────────────────

def test_prive_ssi_direct():
    """Mention directe SSI → toujours pertinent."""
    assert is_prive_relevant("Installation d'un SSI dans un bâtiment commercial") is True


def test_prive_construction_hopital():
    """Construction + ERP → pertinent."""
    assert is_prive_relevant("Lancement du chantier du nouvel hôpital de Saint-Pierre") is True


def test_prive_renovation_lycee():
    """Rénovation + ERP → pertinent."""
    assert is_prive_relevant("Réhabilitation du lycée de Saint-Paul : travaux prévus en 2025") is True


def test_prive_nouveau_hotel():
    """Nouveau bâtiment + ERP → pertinent."""
    assert is_prive_relevant("Construction d'un nouveau resort 5 étoiles à Grand Baie") is True


# ── is_prive_relevant : faux positifs corrigés ───────────────────────────────

def test_prive_livres_scolaires_rejete():
    """Article sur les livres scolaires → NON pertinent (école sans chantier)."""
    assert is_prive_relevant("La Région distribue des livres scolaires aux élèves de 6e") is False


def test_prive_ecole_seule_rejetee():
    """'École' seul sans contexte construction → NON pertinent."""
    assert is_prive_relevant("L'école de Saint-Denis accueille de nouveaux élèves cette année") is False


def test_prive_hotel_seul_rejete():
    """'Hôtel' seul sans contexte construction → NON pertinent."""
    assert is_prive_relevant("L'hôtel Le Récif affiche complet pour les fêtes") is False


def test_prive_hopital_actualite_rejetee():
    """Actualité hospitalière sans construction → NON pertinent."""
    assert is_prive_relevant("Le CHU de La Réunion recrute des infirmiers pour son service urgences") is False


def test_prive_exclusion_gardiennage():
    """Exclusion absolue gardiennage → NON pertinent même avec SSI."""
    assert is_prive_relevant("Marché de gardiennage et SSI pour la mairie") is False


def test_prive_rentre_scolaire_rejetee():
    """Rentrée scolaire → NON pertinent."""
    assert is_prive_relevant("Rentrée scolaire 2024 : tout ce qu'il faut savoir pour les lycéens") is False


# ── Tests recherche plein texte ───────────────────────────────────────────────

def _make_row(titre: str, source: str = "") -> dict:
    return {"Titre": titre, "Source": source, "Date Limite": "—", "Go/No-Go": "🟢 GO"}


def test_search_query_titre():
    rows = [_make_row("Maintenance SSI CHU"), _make_row("Vidéosurveillance port")]
    q = "ssi"
    result = [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 1
    assert result[0]["Titre"] == "Maintenance SSI CHU"


def test_search_query_source():
    rows = [_make_row("Marché 1", source="boamp.fr"), _make_row("Marché 2", source="ted.europa.eu")]
    q = "boamp"
    result = [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 1


def test_search_query_empty_returns_all():
    rows = [_make_row("A"), _make_row("B")]
    q = ""
    result = rows if not q else [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 2


def test_search_query_case_insensitive():
    rows = [_make_row("Alarme INCENDIE")]
    q = "incendie"
    result = [r for r in rows if q in r["Titre"].lower() or q in r["Source"].lower()]
    assert len(result) == 1


# ── Tests filtre urgences ─────────────────────────────────────────────────────

from datetime import datetime, timedelta


def _urgent_row(days_remaining: int) -> dict:
    d = (datetime.now() + timedelta(days=days_remaining)).strftime("%d/%m/%Y")
    return {"Titre": "Test", "Source": "", "Date Limite": d, "Go/No-Go": "🟢 GO"}


def _is_urgent(r: dict) -> bool:
    dl = r["Date Limite"]
    if dl == "—":
        return False
    try:
        d = datetime.strptime(dl, "%d/%m/%Y").date()
        return (d - datetime.now().date()).days <= 14
    except ValueError:
        return False


def test_urgent_within_14_days():
    row = _urgent_row(7)
    assert _is_urgent(row) is True


def test_urgent_exactly_14_days():
    row = _urgent_row(14)
    assert _is_urgent(row) is True


def test_urgent_15_days_not_urgent():
    row = _urgent_row(15)
    assert _is_urgent(row) is False


def test_urgent_overdue_is_urgent():
    row = _urgent_row(-3)
    assert _is_urgent(row) is True


def test_urgent_no_deadline_not_urgent():
    row = {"Titre": "Test", "Source": "", "Date Limite": "—", "Go/No-Go": "🟢 GO"}
    assert _is_urgent(row) is False


# ── classify_relevance ────────────────────────────────────────────────────────

def test_classify_ssi_direct_retourne_true_sans_tag():
    ok, tags = classify_relevance("Installation SSI — Lycée Paul Vergès")
    assert ok is True
    assert tags == []


def test_classify_cmsi_direct_retourne_true_sans_tag():
    ok, tags = classify_relevance("Maintenance CMSI centre commercial Saint-Denis")
    assert ok is True
    assert tags == []


def test_classify_rehabilitation_ecole_retourne_tag_implicite():
    ok, tags = classify_relevance("Réhabilitation de l'école primaire Sainte-Marie")
    assert ok is True
    assert "Potentiel SSI implicite" in tags


def test_classify_construction_hopital_retourne_tag_implicite():
    ok, tags = classify_relevance("Construction d'un hôpital neuf à Saint-Pierre")
    assert ok is True
    assert "Potentiel SSI implicite" in tags


def test_classify_erp_sans_chantier_retourne_false():
    """ERP seul sans mot construction → non pertinent."""
    ok, tags = classify_relevance("L'école de Saint-Denis accueille de nouveaux élèves")
    assert ok is False
    assert tags == []


def test_classify_exclusion_gardiennage_retourne_false():
    ok, tags = classify_relevance("Marché de gardiennage et SSI pour la mairie")
    assert ok is False
    assert tags == []


def test_classify_hors_sujet_retourne_false():
    ok, tags = classify_relevance("Achat de fournitures de bureau")
    assert ok is False
    assert tags == []


def test_classify_renovation_mairie_retourne_tag_implicite():
    ok, tags = classify_relevance("Rénovation de la mairie de Saint-Leu — Lot général")
    assert ok is True
    assert "Potentiel SSI implicite" in tags


def test_classify_ssi_substring_non_pertinent():
    """'ssi' comme sous-chaîne (ex: 'concession') ne doit pas déclencher de match."""
    ok, tags = classify_relevance("Concession autoroutière sans lien avec la sécurité incendie")
    assert ok is False
    assert tags == []
