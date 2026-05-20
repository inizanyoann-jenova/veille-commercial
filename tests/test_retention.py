from datetime import datetime, timedelta
import pytest
from database import clean_obsolete_data
from models import Tender


def _make_tender(db, tid, pub_date, status="À qualifier", blacklisted=False):
    t = Tender(
        id=tid, title=f"Tender {tid}", source="http://x.com",
        publication_date=pub_date, status=status,
        relevance_score=0, is_maintenance=False,
        is_blacklisted=blacklisted,
    )
    db.add(t)
    db.commit()
    return t


def test_tender_older_than_30_days_is_archived(db):
    old_date = datetime.now() - timedelta(days=35)
    _make_tender(db, "OLD-001", old_date, "À qualifier")

    count = clean_obsolete_data(db, days=30)

    assert count == 1
    t = db.query(Tender).filter(Tender.id == "OLD-001").first()
    assert t.status == "Archivé"


def test_tender_within_30_days_is_preserved(db):
    recent_date = datetime.now() - timedelta(days=10)
    _make_tender(db, "RECENT-001", recent_date, "À qualifier")

    count = clean_obsolete_data(db, days=30)

    assert count == 0
    t = db.query(Tender).filter(Tender.id == "RECENT-001").first()
    assert t.status == "À qualifier"


def test_tender_with_decision_is_never_archived(db):
    old_date = datetime.now() - timedelta(days=60)
    _make_tender(db, "SOUMIS-001", old_date, "Soumis")
    _make_tender(db, "GAGNE-001", old_date, "Gagné")
    _make_tender(db, "PERDU-001", old_date, "Perdu")

    count = clean_obsolete_data(db, days=30)

    assert count == 0
    for tid in ("SOUMIS-001", "GAGNE-001", "PERDU-001"):
        t = db.query(Tender).filter(Tender.id == tid).first()
        assert t.status != "Archivé"


def test_tender_without_publication_date_is_preserved(db):
    _make_tender(db, "NODATE-001", None, "À qualifier")

    count = clean_obsolete_data(db, days=30)

    assert count == 0
    t = db.query(Tender).filter(Tender.id == "NODATE-001").first()
    assert t.status == "À qualifier"


def test_blacklisted_tender_is_preserved(db):
    old_date = datetime.now() - timedelta(days=45)
    _make_tender(db, "BLACK-001", old_date, "À qualifier", blacklisted=True)

    count = clean_obsolete_data(db, days=30)

    assert count == 0
    t = db.query(Tender).filter(Tender.id == "BLACK-001").first()
    assert t.status == "À qualifier"
