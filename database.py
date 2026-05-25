import logging as _logging

from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from models import Base  # noqa: Credential enregistre la table credentials

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
    ("tenders", "date_extraction", "DATETIME DEFAULT NULL"),
    ("tenders", "secteur", "VARCHAR"),
    ("tenders", "type_opportunite", "VARCHAR DEFAULT 'Marché Public'"),
    ("tenders", "amount", "INTEGER"),
    ("tenders", "is_blacklisted", "BOOLEAN DEFAULT 0"),
    ("tenders", "is_saved", "BOOLEAN DEFAULT 0"),
    ("tenders", "notes", "TEXT"),
    ("tenders", "tags", "JSON DEFAULT '[]'"),
    ("sources", "is_validated", "BOOLEAN DEFAULT 0"),
    ("sources", "ping_failures_count", "INTEGER DEFAULT 0"),
    ("sources", "last_ping_at", "DATETIME DEFAULT NULL"),
    ("tenders", "url", "VARCHAR DEFAULT NULL"),
]

_VALID_TABLES = {"tenders", "sources"}


def _run_migrations(engine) -> None:
    """Exécute les migrations de colonnes avec validation stricte des noms.

    Sécurité :
    - Les noms de tables sont validés contre _VALID_TABLES
    - Seules les migrations définies dans _MIGRATIONS (liste statique) sont exécutées
    - Approche sécurisée pour une application locale avec validation stricte en amont
    """
    with engine.connect() as conn:
        for table, col_name, col_def in _MIGRATIONS:
            if table not in _VALID_TABLES:
                raise ValueError(f"Migration refusée — table inconnue : {table}")
            try:
                # Pour une application locale, cette approche est sécurisée grâce à la validation whitelist
                # Les requêtes DDL avec noms de tables/colonnes paramétrés ne sont pas supportées par SQLAlchemy
                conn.execute(
                    text(f"ALTER TABLE {table} ADD COLUMN {col_name} {col_def}")
                )
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


from datetime import datetime as _dt, timezone as _tz, timedelta as _td  # noqa: E402
import hashlib as _hashlib  # noqa: E402
from collections import defaultdict as _defaultdict  # noqa: E402


def start_scraper_run(db, source_name: str) -> int:
    from models import ScraperRun

    run = ScraperRun(
        source_name=source_name,
        started_at=_dt.now(_tz.utc).replace(tzinfo=None),
        status="running",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run.id


def finish_scraper_run(
    db, run_id: int, nb_found: int, nb_new: int, error: str | None = None
) -> None:
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


def _simhash(text: str) -> int:
    """Fingerprint SimHash 64 bits d'un texte."""
    words = text.lower().split()
    v = [0] * 64
    for word in words:
        h = int(_hashlib.md5(word.encode("utf-8", errors="replace")).hexdigest(), 16)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    return sum(1 << i for i in range(64) if v[i] > 0)


def _hamming_distance(a: int, b: int) -> int:
    """Distance de Hamming entre deux entiers 64 bits."""
    return bin(a ^ b).count("1")


_DEDUP_MAX_TENDERS = 2000


def detect_duplicates(db, max_tenders: int = _DEDUP_MAX_TENDERS) -> int:
    """Détecte les paires de marchés dupliqués via SimHash 64 bits + bucketing LSH.
    Retourne le nombre de nouvelles paires insérées."""
    from models import Tender, DuplicateCandidate

    existing_raw = db.query(
        DuplicateCandidate.tender_id_a, DuplicateCandidate.tender_id_b
    ).all()
    existing_pairs: set[tuple] = {(min(a, b), max(a, b)) for a, b in existing_raw}

    tenders = (
        db.query(Tender)
        .filter(Tender.is_blacklisted.is_(False), Tender.title.is_not(None), Tender.title != "")
        .all()
    )
    if len(tenders) > max_tenders:
        tenders = sorted(
            tenders,
            key=lambda t: (
                t.publication_date.replace(tzinfo=None) if t.publication_date else _dt.min
            ),
            reverse=True,
        )[:max_tenders]

    fingerprints: dict[str, int] = {t.id: _simhash(t.title) for t in tenders}
    tender_map: dict[str, Tender] = {t.id: t for t in tenders}

    BANDS = 4
    BAND_BITS = 16
    buckets: list[dict] = [_defaultdict(list) for _ in range(BANDS)]
    for tid, sh in fingerprints.items():
        for band_idx in range(BANDS):
            key = (sh >> (band_idx * BAND_BITS)) & 0xFFFF
            buckets[band_idx][key].append(tid)

    candidate_pairs: set[tuple] = set()
    for band in buckets:
        for bucket_items in band.values():
            if len(bucket_items) < 2:
                continue
            for i in range(len(bucket_items)):
                for j in range(i + 1, len(bucket_items)):
                    pair_key = (min(bucket_items[i], bucket_items[j]), max(bucket_items[i], bucket_items[j]))
                    if pair_key not in existing_pairs:
                        candidate_pairs.add(pair_key)

    new_pairs = 0
    for aid, bid in candidate_pairs:
        a = tender_map.get(aid)
        b = tender_map.get(bid)
        if a is None or b is None:
            continue
        if a.source == b.source:
            continue
        if _hamming_distance(fingerprints[aid], fingerprints[bid]) > 8:
            continue
        if a.deadline and b.deadline:
            dl_a = a.deadline.replace(tzinfo=None)
            dl_b = b.deadline.replace(tzinfo=None)
            if abs((dl_a - dl_b).days) > 3:
                continue
        elif a.deadline or b.deadline:
            continue

        sim_score = round(1.0 - _hamming_distance(fingerprints[aid], fingerprints[bid]) / 64.0, 3)
        db.add(
            DuplicateCandidate(
                tender_id_a=aid,
                tender_id_b=bid,
                similarity_score=sim_score,
                detected_at=_dt.now(_tz.utc).replace(tzinfo=None),
            )
        )
        existing_pairs.add((aid, bid))
        new_pairs += 1

    if new_pairs > 0:
        db.commit()

    _log.info("detect_duplicates (SimHash): %d nouvelles paires", new_pairs)
    return new_pairs


def load_urgences(db, score_go: int = 65, days_ahead: int = 30) -> list[dict]:
    from models import Tender
    from datetime import datetime as _ddt, timedelta as _td, timezone as _tz

    today = _ddt.now(_tz.utc).replace(
        tzinfo=None, hour=0, minute=0, second=0, microsecond=0
    )
    cutoff = today + _td(days=days_ahead)
    rows = (
        db.query(Tender)
        .filter(
            Tender.relevance_score >= score_go,
            Tender.is_blacklisted.is_(False),
            Tender.deadline.is_not(None),
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
            "relevance_score": t.relevance_score,
            "jours_restants": (t.deadline.replace(tzinfo=None) - today).days,
            "source": t.source,
            "url": t.url,
            "description": t.description[:300] if t.description else None,
            "secteur": t.secteur,
            "amount": t.amount,
            "llm_resume": (t.llm_analysis or {}).get("resume") if t.llm_analysis else None,
        }
        for t in rows
    ]


def count_decisions(db) -> int:
    """Nombre de tenders avec une décision enregistrée (Soumis/Gagné/Perdu)."""
    from models import Tender

    return (
        db.query(Tender)
        .filter(
            Tender.status.in_(["Soumis", "Gagné", "Perdu"]),
            Tender.is_blacklisted.is_(False),
        )
        .count()
    )


def load_pipeline_data(db, score_go: int = 65) -> dict:
    from models import Tender
    from datetime import datetime as _ddt

    tenders = db.query(Tender).filter(Tender.is_blacklisted.is_(False)).all()
    go, soumis, resultats = [], [], []
    for t in tenders:
        if t.status in ("Gagné", "Perdu"):
            resultats.append(t)
        elif t.status == "Soumis":
            soumis.append(t)
        elif t.relevance_score >= score_go:
            go.append(t)

    def _dl(t):
        return t.deadline.replace(tzinfo=None) if t.deadline else _ddt.max

    def _pub(t):
        return (
            t.publication_date.replace(tzinfo=None) if t.publication_date else _ddt.min
        )

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
            Tender.is_blacklisted.is_(False),
            Tender.publication_date.is_not(None),
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


def delete_old_tenders(db, months: int = 3) -> int:
    """Supprime définitivement les tenders publiés il y a plus de `months` mois.

    Règles strictes :
    - Ne supprime JAMAIS les tenders avec statut Soumis/Gagné/Perdu
    - Ne supprime JAMAIS les tenders sans publication_date
    - Retourne le nombre de tenders supprimés
    """
    from models import Tender

    cutoff = _dt.now(_tz.utc).replace(tzinfo=None) - _td(days=months * 30)

    tenders = (
        db.query(Tender)
        .filter(
            Tender.publication_date.is_not(None),
            Tender.publication_date < cutoff,
            ~Tender.status.in_(["Soumis", "Gagné", "Perdu"]),
        )
        .all()
    )

    count = len(tenders)
    for t in tenders:
        db.delete(t)
    if count:
        db.commit()
        _log.info(
            "delete_old_tenders : %d tenders supprimés (> %d mois)", count, months
        )
    return count


def reset_tenders_db(db) -> int:
    """Vide tenders, scraper_runs et duplicate_candidates. Retourne le nb de tenders supprimés.

    Préserve : sources, credentials, score_weights.
    """
    from models import Tender, ScraperRun, DuplicateCandidate

    nb_tenders = db.query(Tender).count()
    db.query(DuplicateCandidate).delete(synchronize_session=False)
    db.query(ScraperRun).delete(synchronize_session=False)
    db.query(Tender).delete(synchronize_session=False)
    db.commit()
    _log.info("reset_tenders_db : %d tenders supprimés", nb_tenders)
    return nb_tenders


def get_scraper_stats(db, days: int = 30) -> list[dict]:
    """Statistiques d'exécution des scrapers pour les N derniers jours.
    Retourne une liste triée par source_name."""
    from models import ScraperRun

    cutoff = _dt.now(_tz.utc).replace(tzinfo=None) - _td(days=days)
    runs = (
        db.query(ScraperRun)
        .filter(ScraperRun.started_at >= cutoff, ScraperRun.status != "running")
        .all()
    )

    aggregated: dict[str, dict] = {}
    for r in runs:
        name = r.source_name
        if name not in aggregated:
            aggregated[name] = {
                "runs_30j": 0,
                "runs_ok": 0,
                "runs_empty": 0,
                "total_duration_s": 0.0,
                "runs_with_duration": 0,
                "last_run_at": None,
            }
        agg = aggregated[name]
        agg["runs_30j"] += 1
        if r.status == "ok":
            agg["runs_ok"] += 1
            if (r.nb_new or 0) == 0:
                agg["runs_empty"] += 1
        if r.finished_at and r.started_at:
            duration = (r.finished_at - r.started_at).total_seconds()
            agg["total_duration_s"] += duration
            agg["runs_with_duration"] += 1
        if r.finished_at:
            if agg["last_run_at"] is None or r.finished_at > agg["last_run_at"]:
                agg["last_run_at"] = r.finished_at

    result = []
    for name in sorted(aggregated):
        agg = aggregated[name]
        n_dur = agg["runs_with_duration"]
        avg_dur = round(agg["total_duration_s"] / n_dur, 1) if n_dur > 0 else None
        last_at = agg["last_run_at"]
        result.append({
            "source_name": name,
            "runs_30j": agg["runs_30j"],
            "runs_ok": agg["runs_ok"],
            "runs_empty": agg["runs_empty"],
            "avg_duration_s": avg_dur,
            "last_run_at": last_at.isoformat() if last_at else None,
        })
    return result
