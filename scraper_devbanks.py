"""
Banques de Développement Régionales — Océan Indien.
Sources RSS : BAD (Afrique), BEI (Europe), COI (Océan Indien), JICA, KfW, UNDP, ADB.
Method: RSS feed parsing via feedparser.
"""

import feedparser
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FLUX_DEVBANKS = [
    ("Zone IO", "BAD - Actualités", "https://www.afdb.org/en/rss/news-and-events.xml"),
    ("Zone IO", "BAD - Projets", "https://www.afdb.org/en/rss/projects.xml"),
    ("Zone IO", "BEI - Actualités", "https://www.eib.org/en/rss/all-news.htm"),
    ("Zone IO", "BEI - Projets", "https://www.eib.org/en/rss/projects.htm"),
    ("Zone IO", "COI - Actualités", "https://www.commissionoceanindien.org/feed/"),
    (
        "Madagascar",
        "JICA Madagascar",
        "https://www.jica.go.jp/madagascar/en/activities/rss.xml",
    ),
    (
        "Maurice",
        "JICA Maurice",
        "https://www.jica.go.jp/mauritius/en/activities/rss.xml",
    ),
    ("Zone IO", "KfW Dev Bank", "https://www.kfw-entwicklungsbank.de/rss/news.xml"),
    (
        "Zone IO",
        "UNDP Procurement",
        "https://procurement-notices.undp.org/rss_notices.cfm",
    ),
    ("Zone IO", "ADB — Projets", "https://www.adb.org/rss/projects.xml"),
]

PAYS_IO = [
    "madagascar",
    "mauritius",
    "île maurice",
    "ile maurice",
    "comores",
    "comoros",
    "réunion",
    "reunion",
    "mayotte",
    "indian ocean",
    "océan indien",
    "east africa",
    "afrique de l'est",
    "seychelles",
    "maldives",
]

SECTEURS_BANQUES = [
    "santé",
    "sante",
    "health",
    "hospital",
    "clinic",
    "education",
    "school",
    "university",
    "urban",
    "housing",
    "logement",
    "infrastructure",
    "transport",
    "energy",
    "énergie",
    "water",
    "eau",
    "tourism",
    "tourisme",
    "public administration",
    "construction",
    "bâtiment",
    "building",
    "ssi",
    "incendie",
    "sécurité",
    "securite",
    "fire",
    "surveillance",
    "cctv",
    "electrical",
    "électrique",
]


def _is_relevant(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    geo_ok = any(p in text for p in PAYS_IO)
    secteur_ok = any(s in text for s in SECTEURS_BANQUES)
    return geo_ok and secteur_ok


def _parse_date(entry) -> str:
    """Extract and return publication date as ISO string."""
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return parsedate_to_datetime(val).date().isoformat()
            except Exception:
                try:
                    parsed = entry.get(f"{attr}_parsed")
                    if parsed:
                        return datetime(*parsed[:6]).date().isoformat()
                except Exception:
                    pass
    return ""


def fetch() -> list[dict]:
    """
    Returns relevant items from development bank RSS feeds for Indian Ocean region.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []

    for territoire, nom, feed_url in FLUX_DEVBANKS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception:
            continue

        if not feed.entries:
            continue

        for entry in feed.entries:
            title = entry.get("title") or ""
            summary = entry.get("summary") or entry.get("description") or ""

            if not _is_relevant(title, summary):
                continue

            results.append(_normalise(entry, territoire, nom, feed_url))

    return results


def _normalise(entry, territoire: str, nom: str, feed_url: str) -> dict:
    """Convert raw RSS entry to standard schema."""
    title = entry.get("title") or ""
    summary = entry.get("summary") or entry.get("description") or ""
    link = entry.get("link") or feed_url

    return {
        "name": f"[{nom}] {title[:200]}",
        "url": link,
        "source": nom,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": _parse_date(entry),
        "deadline": "",
        "territoire": territoire,
        "description": summary[:500],
        "type_opportunite": "Banque Dev.",
    }
