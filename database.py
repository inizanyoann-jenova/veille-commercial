from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from models import Base, Credential  # noqa: Credential enregistre la table credentials

DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    # Import lazy pour éviter la dépendance circulaire au niveau module
    from source_registry import Source, init_sources  # noqa: enregistre Source avec Base
    from models import ScraperRun, DuplicateCandidate  # noqa: registers both with Base

    Base.metadata.create_all(bind=engine)

    # Migrations de colonnes existantes (conservées)
    with engine.connect() as conn:
        for col_name, col_def in [
            ("secteur", "VARCHAR"),
            ("type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
            ("amount", "INTEGER"),
            ("is_blacklisted", "BOOLEAN DEFAULT 0"),
            ("is_saved", "BOOLEAN DEFAULT 0"),
            ("notes", "TEXT"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE tenders ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except OperationalError as e:
                if "already exists" not in str(e) and "duplicate column" not in str(e):
                    raise

    # Migration table sources
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE sources ADD COLUMN is_validated BOOLEAN DEFAULT 0"))
            conn.commit()
        except OperationalError as e:
            if "already exists" not in str(e) and "duplicate column" not in str(e):
                raise

    # Migration colonnes Source : ping
    with engine.connect() as conn:
        for col_name, col_def in [
            ("ping_failures_count", "INTEGER DEFAULT 0"),
            ("last_ping_at", "DATETIME DEFAULT NULL"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE sources ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except OperationalError as e:
                if "already exists" not in str(e) and "duplicate column" not in str(e):
                    raise

    # Migration colonne Tender : tags
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE tenders ADD COLUMN tags JSON DEFAULT '[]'"))
            conn.commit()
        except OperationalError as e:
            if "already exists" not in str(e) and "duplicate column" not in str(e):
                raise

    # Seeding des sources par défaut si la table est vide
    db = SessionLocal()
    try:
        init_sources(db)
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from datetime import datetime as _dt, timezone as _tz
from difflib import SequenceMatcher as _SM
from sqlalchemy import and_ as _and, or_ as _or


def start_scraper_run(db, source_name: str) -> int:
    from models import ScraperRun
    run = ScraperRun(source_name=source_name, started_at=_dt.now(_tz.utc), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run.id


def finish_scraper_run(db, run_id: int, nb_found: int, nb_new: int, error: str | None = None) -> None:
    from models import ScraperRun
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    if not run:
        return
    run.finished_at = _dt.now(_tz.utc)
    run.nb_found = nb_found
    run.nb_new = nb_new
    run.error = error
    run.status = "error" if error else "ok"
    db.commit()


def detect_duplicates(db) -> int:
    """Détecte les paires de marchés avec titre similaire (>=0.80) et deadline à ±3j.
    Retourne le nombre de nouvelles paires insérées."""
    from models import Tender, DuplicateCandidate
    from datetime import datetime as _ddt, UTC as _UTC

    tenders = db.query(Tender).filter(Tender.is_blacklisted != True).all()
    new_pairs = 0

    for i, a in enumerate(tenders):
        for b in tenders[i + 1:]:
            if a.source == b.source:
                continue
            if not a.title or not b.title:
                continue
            ratio = _SM(None, a.title.lower(), b.title.lower()).ratio()
            if ratio < 0.80:
                continue
            if a.deadline and b.deadline:
                if abs((a.deadline - b.deadline).days) > 3:
                    continue
            elif a.deadline or b.deadline:
                continue
            existing = db.query(DuplicateCandidate).filter(
                _or(
                    _and(DuplicateCandidate.tender_id_a == a.id, DuplicateCandidate.tender_id_b == b.id),
                    _and(DuplicateCandidate.tender_id_a == b.id, DuplicateCandidate.tender_id_b == a.id),
                )
            ).first()
            if not existing:
                db.add(DuplicateCandidate(
                    tender_id_a=a.id,
                    tender_id_b=b.id,
                    similarity_score=round(ratio, 3),
                    detected_at=_ddt.now(_UTC),
                ))
                new_pairs += 1

    db.commit()
    return new_pairs


def load_urgences(db, score_go: int = 65, days_ahead: int = 30) -> list[dict]:
    from models import Tender
    from datetime import datetime as _ddt, timedelta as _td

    today = _ddt.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff = today + _td(days=days_ahead)
    rows = (
        db.query(Tender)
        .filter(
            Tender.relevance_score >= score_go,
            Tender.is_blacklisted != True,
            Tender.deadline != None,
            Tender.deadline >= today,
            Tender.deadline <= cutoff,
            ~Tender.status.in_(["Gagné", "Perdu"]),
        )
        .order_by(Tender.deadline.asc())
        .all()
    )
    return [
        {
            "id": t.id,
            "title": t.title,
            "score": t.relevance_score,
            "jours": (t.deadline - today).days,
        }
        for t in rows
    ]
