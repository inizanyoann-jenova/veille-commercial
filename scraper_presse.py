"""
Scraper RSS — Presse locale et institutions de l'Océan Indien.
Filtre les articles mentionnant des projets de construction/bâtiment
susceptibles de nécessiter du SSI/CMSI/Vidéosurveillance.
"""
import hashlib
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from filters import is_prive_relevant
from models import Tender
from scraper_utils import load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

FLUX_PRESSE = [
    ("La Réunion", "Le JIR",             "https://www.lejir.com/feed/"),
    ("La Réunion", "Le Quotidien",        "https://www.lequotidiendelarunion.fr/feed/"),
    ("La Réunion", "Zinfos974",           "https://www.zinfos974.com/feed/"),
    ("La Réunion", "Imaz Press",          "https://www.imazpresss.re/feed/"),
    ("La Réunion", "Réunion la 1ère",     "https://la1ere.francetvinfo.fr/reunion/rss.xml"),
    ("La Réunion", "Clicanoo",            "https://www.clicanoo.re/rss"),
    ("La Réunion", "Batiactu DOM",        "https://www.batiactu.com/rss/rss_actualites.xml"),
    ("Mayotte",    "Mayotte Hebdo",       "https://www.mayottehebdo.com/feed/"),
    ("Mayotte",    "Journal de Mayotte",  "https://lejournaldemayotte.yt/feed/"),
    ("Mayotte",    "Kwezi",               "https://kwezi.fr/feed/"),
    ("Mayotte",    "Mayotte la 1ère",     "https://la1ere.francetvinfo.fr/mayotte/rss.xml"),
    ("Maurice",    "L'Express Maurice",   "https://lexpress.mu/rss"),
    ("Maurice",    "Le Défi",             "https://www.defimedia.info/feed/"),
    ("Maurice",    "Business Magazine",   "https://businessmag.mu/feed/"),
    ("Madagascar", "La Tribune Mada",     "https://www.latribune.mg/feed/"),
    ("Madagascar", "L'Express Mada",      "https://lexpress.mg/feed/"),
    ("Madagascar", "Midi Madagasikara",   "https://www.midi-madagasikara.mg/feed/"),
    ("Comores",    "Alwatwan",            "https://alwatwan.net/feed/"),
    ("Comores",    "HZK-Presse",          "https://www.hzk-presse.com/feed/"),
    ("Comores",    "La Gazette Comores",  "https://www.lagazettedescomores.com/feed/"),
]

FLUX_INSTITUTIONS = [
    ("La Réunion", "Région Réunion",      "https://regionreunion.com/feed/"),
    ("La Réunion", "CD 974",              "https://www.cg974.re/feed/"),
    ("La Réunion", "CCI Réunion",         "https://www.reunion.cci.fr/feed/"),
    ("La Réunion", "CINOR",               "https://www.cinor.re/feed/"),
    ("La Réunion", "CIVIS",               "https://www.civis.re/feed/"),
    ("La Réunion", "CIREST",              "https://www.cirest.fr/feed/"),
    ("La Réunion", "CASUD",               "https://www.casud.re/feed/"),
    ("La Réunion", "TCO",                 "https://www.tco.re/feed/"),
    ("La Réunion", "SPL Horizon",         "https://www.spl-horizon.re/feed/"),
    ("La Réunion", "SHLMR",               "https://www.shlmr.re/feed/"),
    ("La Réunion", "Erilia Réunion",      "https://www.erilia.fr/feed/"),
    ("La Réunion", "SODIAC",              "https://www.sodiac.re/feed/"),
    ("Mayotte",    "CD 976",              "https://www.cg976.re/feed/"),
    ("Mayotte",    "CCI Mayotte",         "https://www.mayotte.cci.fr/feed/"),
    ("Mayotte",    "SIM Mayotte",         "https://www.sim976.re/feed/"),
]


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
    return "RSS-" + hashlib.md5(url.encode()).hexdigest()[:14]


def _fetch_feed(territoire: str, nom: str, url: str, db, type_opp: str, filter_fn, existing_ids: set) -> int:
    inserted = 0
    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        _log.warning("Feed RSS '%s' inaccessible : %s", nom, type(exc).__name__)
        return 0

    if not feed.entries:
        _log.debug("Feed '%s' : aucune entrée", nom)
        return 0

    for entry in feed.entries:
        title = entry.get("title") or ""
        summary = entry.get("summary") or entry.get("description") or ""

        if not filter_fn(f"{title} {summary}"):
            continue

        link = entry.get("link") or url
        tender_id = _dedup_id(link)

        t = Tender(
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
            type_opportunite=type_opp,
        )
        if insert_if_new(db, t, existing_ids):
            inserted += 1

    return inserted


def fetch_presse_io() -> int:
    init_db()
    db = SessionLocal()
    total = 0
    _run_id = start_scraper_run(db, "Presse & Institutions IO")
    try:
        existing_ids = load_existing_ids(db)

        for territoire, nom, url in FLUX_PRESSE:
            total += _fetch_feed(territoire, nom, url, db, "Presse", is_prive_relevant, existing_ids)
        for territoire, nom, url in FLUX_INSTITUTIONS:
            total += _fetch_feed(territoire, nom, url, db, "Institution", is_prive_relevant, existing_ids)

        if total:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=total, nb_new=total)
        _log.info("Presse & Institutions IO : %d inséré(s)", total)
    except Exception as exc:
        _log.exception("Presse IO : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()
    return total


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_presse_io()
    _log.info("Presse IO terminé — %d inséré(s)", count)
