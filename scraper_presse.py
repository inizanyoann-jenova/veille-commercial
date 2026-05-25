"""
Presse locale et institutions de l'Océan Indien — flux RSS.
Filtre les articles mentionnant des projets de construction/bâtiment
susceptibles de nécessiter du SSI/CMSI/vidéosurveillance.
Method: RSS feed parsing via feedparser.
"""

import feedparser
from datetime import datetime, timezone

from scraper_utils import parse_rss_date

FLUX_PRESSE = [
    ("La Réunion", "Le JIR", "https://www.lejir.com/feed/"),
    ("La Réunion", "Le Quotidien", "https://www.lequotidiendelarunion.fr/feed/"),
    ("La Réunion", "Zinfos974", "https://www.zinfos974.com/feed/"),
    ("La Réunion", "Imaz Press", "https://www.imazpresss.re/feed/"),
    ("La Réunion", "Réunion la 1ère", "https://la1ere.francetvinfo.fr/reunion/rss.xml"),
    ("La Réunion", "Clicanoo", "https://www.clicanoo.re/rss"),
    ("La Réunion", "Batiactu DOM", "https://www.batiactu.com/rss/rss_actualites.xml"),
    ("Mayotte", "Mayotte Hebdo", "https://www.mayottehebdo.com/feed/"),
    ("Mayotte", "Journal de Mayotte", "https://lejournaldemayotte.yt/feed/"),
    ("Mayotte", "Kwezi", "https://kwezi.fr/feed/"),
    ("Mayotte", "Mayotte la 1ère", "https://la1ere.francetvinfo.fr/mayotte/rss.xml"),
    ("Maurice", "L'Express Maurice", "https://lexpress.mu/rss"),
    ("Maurice", "Le Défi", "https://www.defimedia.info/feed/"),
    ("Maurice", "Business Magazine", "https://businessmag.mu/feed/"),
    ("Madagascar", "La Tribune Mada", "https://www.latribune.mg/feed/"),
    ("Madagascar", "L'Express Mada", "https://lexpress.mg/feed/"),
    ("Madagascar", "Midi Madagasikara", "https://www.midi-madagasikara.mg/feed/"),
    ("Comores", "Alwatwan", "https://alwatwan.net/feed/"),
    ("Comores", "HZK-Presse", "https://www.hzk-presse.com/feed/"),
    ("Comores", "La Gazette Comores", "https://www.lagazettedescomores.com/feed/"),
    ("OI", "L'Éco Austral", "https://www.ecoaustral.com/feed/"),
]

FLUX_INSTITUTIONS = [
    ("La Réunion", "Région Réunion", "https://regionreunion.com/feed/"),
    ("La Réunion", "CD 974", "https://www.cg974.re/feed/"),
    ("La Réunion", "CCI Réunion", "https://www.reunion.cci.fr/feed/"),
    ("La Réunion", "CINOR", "https://www.cinor.re/feed/"),
    ("La Réunion", "CIVIS", "https://www.civis.re/feed/"),
    ("La Réunion", "CIREST", "https://www.cirest.fr/feed/"),
    ("La Réunion", "CASUD", "https://www.casud.re/feed/"),
    ("La Réunion", "TCO", "https://www.tco.re/feed/"),
    ("La Réunion", "SPL Horizon", "https://www.spl-horizon.re/feed/"),
    ("La Réunion", "SHLMR", "https://www.shlmr.re/feed/"),
    ("La Réunion", "Erilia Réunion", "https://www.erilia.fr/feed/"),
    ("La Réunion", "SODIAC", "https://www.sodiac.re/feed/"),
    ("Mayotte", "CD 976", "https://www.cg976.re/feed/"),
    ("Mayotte", "CCI Mayotte", "https://www.mayotte.cci.fr/feed/"),
    ("Mayotte", "SIM Mayotte", "https://www.sim976.re/feed/"),
]

# Articles mentionnant des projets de construction/bâtiment → opportunité SSI/CMSI/vidéo
MOTS_CLES_PERTINENTS = [
    "construction",
    "chantier",
    "travaux",
    "bâtiment",
    "batiment",
    "réhabilitation",
    "rehabilitation",
    "rénovation",
    "renovation",
    "extension",
    "aménagement",
    "amenagement",
    "infrastructure",
    "hôpital",
    "hopital",
    "clinique",
    "école",
    "ecole",
    "lycée",
    "lycee",
    "collège",
    "college",
    "université",
    "universite",
    "mairie",
    "centre commercial",
    "hôtel",
    "hotel",
    "résidence",
    "residence",
    "immeuble",
    "logement",
    "erp",
    "établissement",
    "ssi",
    "cmsi",
    "incendie",
    "désenfumage",
    "desenfumage",
    "vidéosurveillance",
    "videosurveillance",
    "sécurité",
    "securite",
    "appel d'offres",
    "appel offres",
    "marché public",
    "consultation",
]


def _is_relevant(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(mot in text for mot in MOTS_CLES_PERTINENTS)


def _collect_feed(territoire: str, nom: str, feed_url: str, type_opp: str) -> list[dict]:
    """Parse one RSS feed and return relevant items."""
    try:
        feed = feedparser.parse(feed_url)
    except Exception:
        return []

    results = []
    for entry in feed.entries:
        title = entry.get("title") or ""
        summary = entry.get("summary") or entry.get("description") or ""

        if not _is_relevant(title, summary):
            continue

        results.append(_normalise(entry, territoire, nom, feed_url, type_opp))

    return results


def fetch() -> list[dict]:
    """
    Returns relevant articles from Indian Ocean press and institution RSS feeds.
    Each item: name, url, source, date_found + domain-specific fields.
    """
    results = []

    for territoire, nom, url in FLUX_PRESSE:
        results.extend(_collect_feed(territoire, nom, url, "Presse"))
    for territoire, nom, url in FLUX_INSTITUTIONS:
        results.extend(_collect_feed(territoire, nom, url, "Institution"))

    return results


def _normalise(entry, territoire: str, nom: str, feed_url: str, type_opp: str) -> dict:
    """Convert raw RSS entry to standard schema."""
    title = entry.get("title") or ""
    summary = entry.get("summary") or entry.get("description") or ""
    link = entry.get("link") or feed_url

    return {
        "name": f"[{nom}] {title[:200]}",
        "url": link,
        "source": nom,
        "date_found": datetime.now(timezone.utc).date().isoformat(),
        "publication_date": parse_rss_date(entry),
        "deadline": "",
        "territoire": territoire,
        "description": summary[:500],
        "type_opportunite": type_opp,
    }
