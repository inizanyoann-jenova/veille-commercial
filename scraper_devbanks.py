"""
Scraper Banques de Développement Régionales — Océan Indien.
Sources : BAD (Afrique), BEI (Europe), COI (Océan Indien), JICA (Japon), KfW (Allemagne).
Complément aux scrapers AFD et Banque Mondiale déjà existants.
"""
import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import INCLUSION_KEYWORDS
from models import Tender

FLUX_DEVBANKS = [
    ("Zone IO", "BAD - Actualités",   "https://www.afdb.org/en/rss/news-and-events.xml"),
    ("Zone IO", "BAD - Projets",      "https://www.afdb.org/en/rss/projects.xml"),
    ("Zone IO", "BEI - Actualités",   "https://www.eib.org/en/rss/all-news.htm"),
    ("Zone IO", "BEI - Projets",      "https://www.eib.org/en/rss/projects.htm"),
    ("Zone IO", "COI - Actualités",   "https://www.commissionoceanindien.org/feed/"),
    ("Madagascar", "JICA Madagascar", "https://www.jica.go.jp/madagascar/en/activities/rss.xml"),
    ("Maurice",    "JICA Maurice",    "https://www.jica.go.jp/mauritius/en/activities/rss.xml"),
    ("Zone IO", "KfW Dev Bank",       "https://www.kfw-entwicklungsbank.de/rss/news.xml"),
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
        for territoire, nom, url in FLUX_DEVBANKS:
            try:
                feed = feedparser.parse(url)
            except Exception:
                continue

            for entry in feed.entries:
                title = entry.get("title") or ""
                summary = entry.get("summary") or entry.get("description") or ""

                if not _is_relevant_devbank(title, summary):
                    continue

                link = entry.get("link") or url
                tender_id = _dedup_id(link)

                if db.query(Tender).filter(Tender.id == tender_id).first():
                    continue

                db.add(Tender(
                    id=tender_id,
                    title=f"[{nom}] {title[:200]}",
                    description=f"{territoire} — {nom}\n{summary[:500]}",
                    source=link,
                    publication_date=_parse_date(entry),
                    deadline=None,
                    status="À qualifier",
                    relevance_score=0,
                    is_maintenance=False,
                    llm_analysis=None,
                    secteur="Privé",
                    type_opportunite="Banque Dev.",
                ))
                total += 1

            db.commit()

        finish_scraper_run(db, _run_id, nb_found=total, nb_new=total)
    except Exception as _e:
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(_e))
        raise
    finally:
        db.close()

    return total


if __name__ == "__main__":
    print("Collecte Banques de Développement (BAD, BEI, COI, JICA, KfW)…")
    count = fetch_devbanks()
    print(f"Terminé — {count} projet(s)/article(s) inséré(s).")
