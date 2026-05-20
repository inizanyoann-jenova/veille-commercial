"""
Scraper Banques de Développement Régionales — Océan Indien.
Sources : BAD (Afrique), BEI (Europe), COI (Océan Indien), JICA (Japon), KfW (Allemagne).
"""
import hashlib
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import INCLUSION_KEYWORDS
from models import Tender
from scraper_utils import load_existing_ids, insert_if_new, now_utc

_log = logging.getLogger(__name__)

FLUX_DEVBANKS = [
    ("Zone IO", "BAD - Actualités",   "https://www.afdb.org/en/rss/news-and-events.xml"),
    ("Zone IO", "BAD - Projets",      "https://www.afdb.org/en/rss/projects.xml"),
    ("Zone IO", "BEI - Actualités",   "https://www.eib.org/en/rss/all-news.htm"),
    ("Zone IO", "BEI - Projets",      "https://www.eib.org/en/rss/projects.htm"),
    ("Zone IO", "COI - Actualités",   "https://www.commissionoceanindien.org/feed/"),
    ("Madagascar", "JICA Madagascar", "https://www.jica.go.jp/madagascar/en/activities/rss.xml"),
    ("Maurice",    "JICA Maurice",    "https://www.jica.go.jp/mauritius/en/activities/rss.xml"),
    ("Zone IO", "KfW Dev Bank",       "https://www.kfw-entwicklungsbank.de/rss/news.xml"),
    ("Zone IO", "UNDP Procurement",   "https://procurement-notices.undp.org/rss_notices.cfm"),
    ("Zone IO", "ADB — Projets",      "https://www.adb.org/rss/projects.xml"),
]

PAYS_IO = [
    "madagascar", "mauritius", "île maurice", "ile maurice", "comores", "comoros",
    "réunion", "reunion", "mayotte", "indian ocean", "océan indien",
    "east africa", "afrique de l'est", "seychelles", "maldives",
]

SECTEURS_BANQUES = [
    "santé", "sante", "health", "hospital", "clinic",
    "education", "school", "university",
    "urban", "housing", "logement", "infrastructure",
    "transport", "energy", "énergie", "water", "eau",
    "tourism", "tourisme", "public administration",
    "construction", "bâtiment", "building",
]


def _is_relevant_devbank(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    geo_ok = any(p in text for p in PAYS_IO)
    secteur_ok = any(s in text for s in SECTEURS_BANQUES) or any(k in text for k in INCLUSION_KEYWORDS)
    return geo_ok and secteur_ok


def _parse_date(entry) -> datetime | None:
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).replace(tzinfo=None)
            except Exception:
                try:
                    parsed = entry.get(f"{attr}_parsed")
                    if parsed:
                        return datetime(*parsed[:6])
                except Exception:
                    pass
    return None


def _dedup_id(url: str) -> str:
    return "DB-" + hashlib.md5(url.encode()).hexdigest()[:12]


def fetch_devbanks() -> int:
    init_db()
    db = SessionLocal()
    total = 0
    _run_id = start_scraper_run(db, "Banques Dev. (BAD/BEI/COI)")

    try:
        existing_ids = load_existing_ids(db)

        for territoire, nom, url in FLUX_DEVBANKS:
            try:
                feed = feedparser.parse(url)
            except Exception as exc:
                _log.warning("Feed RSS '%s' inaccessible : %s", nom, type(exc).__name__)
                continue

            if not feed.entries:
                _log.debug("Feed '%s' : aucune entrée", nom)
                continue

            for entry in feed.entries:
                title = entry.get("title") or ""
                summary = entry.get("summary") or entry.get("description") or ""

                if not _is_relevant_devbank(title, summary):
                    continue

                link = entry.get("link") or url
                tender_id = _dedup_id(link)

                t = Tender(
                    id=tender_id,
                    title=f"[{nom}] {title[:200]}",
                    description=f"{territoire} — {nom}\n{summary[:500]}",
                    source=link,
                    publication_date=_parse_date(entry),
                    date_extraction=now_utc(),
                    deadline=None,
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Privé",
                    type_opportunite="Banque Dev.",
                )
                if insert_if_new(db, t, existing_ids):
                    total += 1

        if total:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=total, nb_new=total)
        _log.info("Banques Dev. : %d inséré(s)", total)
    except Exception as exc:
        _log.exception("Banques Dev. : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_devbanks()
    _log.info("Banques Dev. terminé — %d inséré(s)", count)
