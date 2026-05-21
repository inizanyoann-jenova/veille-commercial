"""Tests de performance pour valider les optimisations."""

import pytest
import time
from database import detect_duplicates, SessionLocal
from models import Base, Tender, DuplicateCandidate

@pytest.fixture
def perf_db():
    """Base de données avec des données de test pour les tests de performance."""
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=engine)
    db = Session()

    # Ajouter des données de test réalistes
    for i in range(100):
        db.add(Tender(
            id=f"TEST-{i:03d}",
            title=f"Maintenance SSI pour bâtiment {i % 10}",
            source=f"source-{i % 5}",
            status="À qualifier",
            relevance_score=70 + (i % 20),
            is_blacklisted=False,
            publication_date=None,
            deadline=None
        ))

    db.commit()
    yield db
    db.close()

def test_detect_duplicates_performance(perf_db):
    """Test que detect_duplicates s'exécute en moins de 5 secondes pour 100 tenders."""
    import time

    # Mesurer le temps d'exécution
    start_time = time.time()
    result = detect_duplicates(perf_db)
    elapsed = time.time() - start_time

    # Vérifier que la fonction termine en temps raisonnable
    assert elapsed < 5.0, f"Trop lent: {elapsed:.2f}s pour 100 tenders"

    # Vérifier que des doublons ont été détectés
    duplicates_count = perf_db.query(DuplicateCandidate).count()
    assert duplicates_count > 0, "Aucun doublon détecté"
    assert result >= 0, "Nombre de paires invalide"

def test_detect_duplicates_scalability(perf_db):
    """Test que la fonction scale raisonnablement avec plus de données."""
    from models import Tender

    # Ajouter plus de données
    for i in range(100, 200):
        perf_db.add(Tender(
            id=f"TEST-{i:03d}",
            title=f"Maintenance CMSI pour école {i % 15}",
            source=f"source-{i % 7}",
            status="À qualifier",
            relevance_score=65 + (i % 25),
            is_blacklisted=False
        ))
    perf_db.commit()

    start_time = time.time()
    result = detect_duplicates(perf_db)
    elapsed = time.time() - start_time

    # Avec 200 tenders, devrait terminer en moins de 15 secondes
    assert elapsed < 15.0, f"Trop lent: {elapsed:.2f}s pour 200 tenders"
    assert result >= 0, "Nombre de paires invalide"