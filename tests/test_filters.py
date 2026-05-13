import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from filters import KEYWORDS_CONSTRUCTION, is_construction_relevant, is_prive_relevant


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
