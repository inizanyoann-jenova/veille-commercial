from datetime import datetime, timedelta
import pytest
from models import Tender


def test_load_direction_kpis_empty_db(db):
    """DB vide → structure complète avec valeurs nulles."""
    from pages.direction import _load_direction_kpis_data
    kpis = _load_direction_kpis_data(db)
    assert "nb_actifs" in kpis
    assert "ca_previsionnel" in kpis
    assert "ca_gagne" in kpis
    assert "taux_conversion" in kpis
    assert kpis["nb_actifs"] == 0
    assert kpis["ca_gagne"] == 0


def test_load_direction_kpis_counts_actifs(db, make_tender):
    """GO + Soumis comptent comme actifs, Gagné/Perdu non."""
    from pages.direction import _load_direction_kpis_data
    from fiche_logic import SCORE_GO
    make_tender(relevance_score=SCORE_GO, status="À qualifier")   # GO actif
    make_tender(relevance_score=SCORE_GO, status="Soumis")        # Soumis actif
    make_tender(relevance_score=SCORE_GO, status="Gagné", amount=50000)
    make_tender(relevance_score=SCORE_GO, status="Perdu")
    kpis = _load_direction_kpis_data(db)
    assert kpis["nb_actifs"] == 2
    assert kpis["ca_gagne"] == 50000


def test_load_direction_kpis_taux_conversion(db, make_tender):
    """Taux = Gagné / Soumis * 100."""
    from pages.direction import _load_direction_kpis_data
    make_tender(status="Soumis")
    make_tender(status="Soumis")
    make_tender(status="Gagné")
    kpis = _load_direction_kpis_data(db)
    assert kpis["taux_conversion"] == 50


def test_load_activity_90d_empty(db):
    """DB vide → liste vide."""
    from pages.direction import _load_activity_90d_data
    result = _load_activity_90d_data(db)
    assert isinstance(result, list)


def test_load_activity_90d_groups_by_week(db, make_tender):
    """Marchés récents groupés par semaine ISO."""
    from pages.direction import _load_activity_90d_data
    make_tender(publication_date=datetime.utcnow() - timedelta(days=3), status="GO")
    make_tender(publication_date=datetime.utcnow() - timedelta(days=5), status="Soumis")
    result = _load_activity_90d_data(db)
    assert len(result) >= 1
    assert "semaine" in result[0]
    assert "count" in result[0]


def test_load_pipeline_direction_excludes_gagné_perdu(db, make_tender):
    """Tableau pipeline = GO + Soumis seulement."""
    from pages.direction import _load_pipeline_direction_data
    from fiche_logic import SCORE_GO
    make_tender(relevance_score=SCORE_GO, status="À qualifier")
    make_tender(relevance_score=SCORE_GO, status="Soumis")
    make_tender(relevance_score=SCORE_GO, status="Gagné")
    make_tender(relevance_score=SCORE_GO, status="Perdu")
    rows = _load_pipeline_direction_data(db)
    assert len(rows) == 2
