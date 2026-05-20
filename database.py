import logging as _logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from models import Base, Credential  # noqa: Credential enregistre la table credentials

_log = _logging.getLogger(__name__)

DATABASE_URL = "sqlite:///def_oi_veille.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Whitelist de migrations autorisées — (table, col_name, col_def)
_MIGRATIONS: list[tuple[str, str, str]] = [
    ("tenders", "date_extraction",        "DATETIME DEFAULT NULL"),
    ("tenders", "secteur",               "VARCHAR"),
    ("tenders", "type_opportunite",      "VARCHAR DEFAULT 'Marché Public'"),
    ("tenders", "amount",                "INTEGER"),
    ("tenders", "is_blacklisted",        "BOOLEAN DEFAULT 0"),
    ("tenders", "is_saved",              "BOOLEAN DEFAULT 0"),
    ("tenders", "notes",                 "TEXT"),
    ("tenders", "tags",                  "JSON DEFAULT '[]'"),
    ("sources", "is_validated",          "BOOLEAN DEFAULT 0"),
    ("sources", "ping_failures_count",   "INTEGER DEFAULT 0"),
    ("sources", "last_ping_at",          "DATETIME DEFAULT NULL"),
]

_VALID_TABLES = {"tenders", "sources"}
_VALID_COLS   = {col for _, col, _ in _MIGRATIONS}


def _run_migrations(engine) -> None:
    """Exécute les migrations de colonnes avec validation stricte des noms."""
    with engine.connect() as conn:
        for table, col_name, col_def in _MIGRATIONS:
            if table not in _VALID_TABLES:
                raise ValueError(f"Migration refusée — table inconnue : {table}")
            if col_name not in _VALID_COLS:
                raise ValueError(f"Migration refusée — colonne inconnue : {col_name}")
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}"))
                conn.commit()
            except OperationalError as e:
                err = str(e).lower()
                if "already exists" not in err and "duplicate column" not in err:
                    raise


def init_db():
    from source_registry import Source, init_sources  # noqa
    from models import ScraperRun, DuplicateCandidate  # noqa

    Base.metadata.create_all(bind=engine)
    _run_migrations(engine)

    db = SessionLocal()
    try:
        init_sources(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # Lot 2 — migrations idempotentes
    with engine.connect() as conn:
        for sql in [
            "ALTER TABLE tenders ADD COLUMN llm_structured JSON DEFAULT NULL",
            "ALTER TABLE tenders ADD COLUMN adaptive_score INTEGER DEFAULT NULL",
            # Toutes les sources automatiques sont désormais validées par défaut
            "UPDATE sources SET is_validated = 1 WHERE is_manual = 0 AND is_validated = 0",
            """CREATE TABLE IF NOT EXISTS score_weights (
                keyword TEXT PRIMARY KEY,
                weight_go REAL DEFAULT 0.0,
                weight_nogo REAL DEFAULT 0.0,
                updated_at DATETIME
            )""",
        ]:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from datetime import datetime as _dt, timezone as _tz, timedelta as _td
from difflib import SequenceMatcher as _SM
from sqlalchemy import and_ as _and, or_ as _or


def start_scraper_run(db, source_name: str) -> int:
    from models import ScraperRun
    run = ScraperRun(source_name=source_name, started_at=_dt.now(_tz.utc).replace(tzinfo=None), status="running")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run.id


def finish_scraper_run(db, run_id: int, nb_found: int, nb_new: int, error: str | None = None) -> None:
    from models import ScraperRun
    run = db.query(ScraperRun).filter(ScraperRun.id == run_id).first()
    if not run:
        _log.warning("finish_scraper_run: ScraperRun id=%s introuvable", run_id)
        return
    run.finished_at = _dt.now(_tz.utc).replace(tzinfo=None)
    run.nb_found = nb_found
    run.nb_new = nb_new
    run.error = error
    run.status = "error" if error else "ok"
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise


_DEDUP_MAX_TENDERS = 2000  # au-delà, O(N²) devient trop lent
_DEDUP_MAX_SECONDS = 30   # timeout pour éviter de bloquer l'UI


def detect_duplicates(db) -> int:
    """Détecte les paires de marchés avec titre similaire (>=0.80) et deadline à ±3j.
    Retourne le nombre de nouvelles paires insérées.
    S'arrête après _DEDUP_MAX_SECONDS secondes pour ne pas bloquer l'interface."""
    import time as _time
    from models import Tender, DuplicateCandidate
    from datetime import datetime as _ddt

    tenders = db.query(Tender).filter(Tender.is_blacklisted == False).all()
    if len(tenders) > _DEDUP_MAX_TENDERS:
        tenders = sorted(tenders, key=lambda t: (t.publication_date.replace(tzinfo=None) if t.publication_date else _ddt.min), reverse=True)[:_DEDUP_MAX_TENDERS]
    new_pairs = 0

    existing_raw = db.query(DuplicateCandidate.tender_id_a, DuplicateCandidate.tender_id_b).all()
    existing_pairs: set[tuple] = {
        (min(a, b), max(a, b)) for a, b in existing_raw
    }

    _deadline = _time.monotonic() + _DEDUP_MAX_SECONDS
    for i, a in enumerate(tenders):
        if _time.monotonic() > _deadline:
            _log.warning("detect_duplicates: timeout atteint après %d secondes — %d paires traitées", _DEDUP_MAX_SECONDS, new_pairs)
            break
        for b in tenders[i + 1:]:
            if a.source == b.source:
                continue
            if not a.title or not b.title:
                continue
            ratio = _SM(None, a.title.lower(), b.title.lower()).ratio()
            if ratio < 0.80:
                continue
            if a.deadline and b.deadline:
                dl_a = a.deadline.replace(tzinfo=None)
                dl_b = b.deadline.replace(tzinfo=None)
                if abs((dl_a - dl_b).days) > 3:
                    continue
            elif a.deadline or b.deadline:
                continue
            pair_key = (min(a.id, b.id), max(a.id, b.id))
            if pair_key not in existing_pairs:
                db.add(DuplicateCandidate(
                    tender_id_a=a.id,
                    tender_id_b=b.id,
                    similarity_score=round(ratio, 3),
                    detected_at=_ddt.now(_tz.utc).replace(tzinfo=None),
                ))
                existing_pairs.add(pair_key)
                new_pairs += 1

    db.commit()
    return new_pairs


def load_urgences(db, score_go: int = 65, days_ahead: int = 30) -> list[dict]:
    from models import Tender
    from datetime import datetime as _ddt, timedelta as _td, timezone as _tz

    today = _ddt.now(_tz.utc).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    cutoff = today + _td(days=days_ahead)
    rows = (
        db.query(Tender)
        .filter(
            Tender.relevance_score >= score_go,
            Tender.is_blacklisted == False,
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
            "jours": (t.deadline.replace(tzinfo=None) - today).days,
        }
        for t in rows
    ]


def count_decisions(db) -> int:
    """Nombre de tenders avec une décision enregistrée (Soumis/Gagné/Perdu)."""
    from models import Tender
    return db.query(Tender).filter(
        Tender.status.in_(["Soumis", "Gagné", "Perdu"]),
        Tender.is_blacklisted == False,
    ).count()


def load_pipeline_data(db, score_go: int = 65) -> dict:
    from models import Tender
    from datetime import datetime as _ddt

    tenders = db.query(Tender).filter(Tender.is_blacklisted == False).all()
    go, soumis, resultats = [], [], []
    for t in tenders:
        if t.status in ("Gagné", "Perdu"):
            resultats.append(t)
        elif t.status == "Soumis":
            soumis.append(t)
        elif t.relevance_score >= score_go:
            go.append(t)

    def _dl(t): return (t.deadline.replace(tzinfo=None) if t.deadline else _ddt.max)
    def _pub(t): return (t.publication_date.replace(tzinfo=None) if t.publication_date else _ddt.min)
    go.sort(key=_dl)
    soumis.sort(key=_dl)
    resultats.sort(key=_pub, reverse=True)
    return {"go": go, "soumis": soumis, "resultats": resultats}


def clean_obsolete_data(db, days: int = 30) -> int:
    """Archive les tenders 'À qualifier' dont la publication_date dépasse `days` jours.

    Règles strictes :
    - Ne touche JAMAIS les tenders avec statut Soumis/Gagné/Perdu/Archivé
    - Ne touche JAMAIS les tenders blacklistés
    - Ne touche JAMAIS les tenders sans publication_date
    - Retourne le nombre de tenders archivés
    """
    from models import Tender

    cutoff = _dt.now(_tz.utc).replace(tzinfo=None) - _td(days=days)

    tenders = (
        db.query(Tender)
        .filter(
            Tender.status == "À qualifier",
            Tender.is_blacklisted == False,
            Tender.publication_date != None,
            Tender.publication_date < cutoff,
        )
        .all()
    )

    for t in tenders:
        t.status = "Archivé"

    count = len(tenders)
    if count:
        db.commit()
        _log.info("clean_obsolete_data : %d tenders archivés (> %d jours)", count, days)
    return count
