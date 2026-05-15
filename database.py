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
