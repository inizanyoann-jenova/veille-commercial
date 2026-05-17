from datetime import datetime, timedelta
import pytest
from models import Tender
from fiche_logic import SCORE_GO, SCORE_ETUDE


def test_build_digest_returns_none_when_no_new_tenders(db):
    """Aucun marché publié dans les 24h → None."""
    from email_digest import build_digest
    result = build_digest(since_hours=24, db=db)
    assert result is None


def test_build_digest_returns_none_when_only_irrelevant(db, make_tender):
    """Marchés publiés mais score < SCORE_ETUDE → None."""
    from email_digest import build_digest
    make_tender(
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_ETUDE - 1,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is None


def test_build_digest_subject_contains_count(db, make_tender):
    """GO + À étudier → sujet contient le total."""
    from email_digest import build_digest
    make_tender(publication_date=datetime.utcnow() - timedelta(hours=1), relevance_score=SCORE_GO)
    make_tender(publication_date=datetime.utcnow() - timedelta(hours=2), relevance_score=SCORE_ETUDE)
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "2" in result["subject"]
    assert "DEF OI" in result["subject"]


def test_build_digest_html_has_go_section(db, make_tender):
    """Marché GO → section ✅ GO dans le HTML."""
    from email_digest import build_digest
    make_tender(
        title="Installation SSI ERP",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "✅ GO" in result["html"]
    assert "Installation SSI ERP" in result["html"]


def test_build_digest_html_has_etude_section(db, make_tender):
    """Marché À étudier → section 🔍 dans le HTML."""
    from email_digest import build_digest
    make_tender(
        title="Maintenance alarme",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_ETUDE,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "🔍" in result["html"]
    assert "Maintenance alarme" in result["html"]


def test_build_digest_html_has_urgence_section(db, make_tender):
    """Marché GO avec deadline dans 3 jours → section ⚠️ dans le HTML."""
    from email_digest import build_digest
    make_tender(
        title="Urgence SSI",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
        status="À qualifier",
        deadline=datetime.utcnow() + timedelta(days=3),
    )
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "⚠️" in result["html"]


def test_build_digest_excludes_blacklisted(db, make_tender):
    """Marchés blacklistés exclus même si GO."""
    from email_digest import build_digest
    make_tender(
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
        is_blacklisted=True,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is None
