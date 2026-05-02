from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base

DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    Base.metadata.create_all(bind=engine)
    # Migration : ajoute les colonnes si elles n'existent pas (SQLite ne les crée pas via create_all)
    with engine.connect() as conn:
        for col_name, col_def in [
            ("secteur", "VARCHAR"),
            ("type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE tenders ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except Exception:
                pass  # Colonne déjà présente


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
