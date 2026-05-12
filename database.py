from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    # Import lazy pour éviter la dépendance circulaire au niveau module
    from source_registry import Source, init_sources  # noqa: enregistre Source avec Base

    Base.metadata.create_all(bind=engine)

    # Migrations de colonnes existantes (conservées)
    with engine.connect() as conn:
        for col_name, col_def in [
            ("secteur", "VARCHAR"),
            ("type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE tenders ADD COLUMN {col_name} {col_def}"))
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
