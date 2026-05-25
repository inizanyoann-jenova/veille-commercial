"""
Utilitaires réseau partagés par les scrapers DEF OI.
Fournit retry_get() et retry_post() avec backoff exponentiel et gestion 429.
"""

import logging
import time

import requests

_log = logging.getLogger(__name__)

_DEFAULT_RATE_DELAY = 1.0
_MAX_RETRIES = 3
_BASE_BACKOFF = 2.0


def retry_get(
    url: str,
    *,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
    rate_delay: float = _DEFAULT_RATE_DELAY,
    retries: int = _MAX_RETRIES,
) -> requests.Response:
    """
    GET avec retry exponentiel sur erreurs réseau et 5xx/429.
    Lève requests.RequestException après épuisement des tentatives.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        if attempt > 0:
            delay = _BASE_BACKOFF * (2 ** (attempt - 1))
            time.sleep(delay)
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", _BASE_BACKOFF * 2))
                time.sleep(retry_after)
                last_exc = requests.exceptions.HTTPError(response=resp)
                continue
            resp.raise_for_status()
            time.sleep(rate_delay)
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def retry_post(
    url: str,
    *,
    json: dict | None = None,
    headers: dict | None = None,
    timeout: int = 30,
    rate_delay: float = _DEFAULT_RATE_DELAY,
    retries: int = _MAX_RETRIES,
) -> requests.Response:
    """
    POST avec retry exponentiel — même logique que retry_get.
    """
    last_exc: Exception | None = None
    for attempt in range(retries):
        if attempt > 0:
            delay = _BASE_BACKOFF * (2 ** (attempt - 1))
            time.sleep(delay)
        try:
            resp = requests.post(url, json=json, headers=headers, timeout=timeout)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", _BASE_BACKOFF * 2))
                time.sleep(retry_after)
                last_exc = requests.exceptions.HTTPError(response=resp)
                continue
            resp.raise_for_status()
            time.sleep(rate_delay)
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
    raise last_exc  # type: ignore[misc]


# ── Helpers DB partagés par les scrapers ──────────────────────────────────────

import os as _os
_INSERT_MAX_AGE_DAYS = int(_os.getenv("SCRAPER_WINDOW_DAYS", "30"))


def load_existing_ids(db) -> set:
    """Retourne l'ensemble des IDs de tenders existants en base."""
    from models import Tender as _Tender
    return {row.id for row in db.query(_Tender.id).all()}


def insert_if_new(db, tender, existing_ids: set) -> bool:
    """Insère le tender si son ID est absent et sa date de publication valide et récente.

    Règles :
    - Rejeté si publication_date est None
    - Rejeté si publication_date > _INSERT_MAX_AGE_DAYS jours
    - Rejeté si id déjà dans existing_ids (doublon)
    Mutate existing_ids : ajoute l'id inséré.
    """
    from datetime import datetime as _dt, timedelta as _td

    if tender.publication_date is None:
        _log.warning(
            "insert_if_new: rejeté (date manquante) — id=%s titre=%s",
            tender.id,
            (tender.title or "")[:60],
        )
        return False

    pub = tender.publication_date
    if isinstance(pub, str):
        try:
            pub = _dt.fromisoformat(pub[:10])
        except (ValueError, TypeError):
            return False

    if hasattr(pub, "tzinfo") and pub.tzinfo is not None:
        pub = pub.replace(tzinfo=None)
    cutoff = _dt.now() - _td(days=_INSERT_MAX_AGE_DAYS)
    if pub < cutoff:
        return False

    if tender.id in existing_ids:
        return False

    db.add(tender)
    db.flush()
    existing_ids.add(tender.id)
    return True


# ── Utilitaire parsing dates ──────────────────────────────────────────────────

import re as _re
from datetime import datetime as _datetime
from email.utils import parsedate_to_datetime as _parsedate_to_datetime

_FR_MONTHS = {
    "janvier": 1, "jan": 1,
    "février": 2, "fevrier": 2, "fév": 2, "fev": 2,
    "mars": 3, "mar": 3,
    "avril": 4, "avr": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7, "juil": 7,
    "août": 8, "aout": 8, "aou": 8,
    "septembre": 9, "sep": 9, "sept": 9,
    "octobre": 10, "oct": 10,
    "novembre": 11, "nov": 11,
    "décembre": 12, "decembre": 12, "déc": 12, "dec": 12,
}


def parse_date(s: "str | None") -> "_datetime | None":
    """Parse une chaîne date vers datetime. Supporte ISO, numérique français et textuel français."""
    if not s or s in ("null", "None", "N/A", ""):
        return None
    s = s.strip()
    # ISO: 2026-04-15 ou 2026-04-15T10:30:00
    try:
        return _datetime.fromisoformat(s[:10])
    except (ValueError, TypeError):
        pass
    # Numérique français: 15/04/2026 ou 15-04-2026
    m = _re.match(r"^(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})$", s)
    if m:
        try:
            return _datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            pass
    # Textuel français: "15 avril 2026" ou "15 avr. 2026"
    m = _re.match(r"^(\d{1,2})\s+([a-zéûôàèê\.]+)\s+(\d{4})$", s.lower())
    if m:
        month_key = m.group(2).rstrip(".")
        month = _FR_MONTHS.get(month_key)
        if month:
            try:
                return _datetime(int(m.group(3)), month, int(m.group(1)))
            except ValueError:
                pass
    return None


def parse_rss_date(entry) -> str:
    """Extrait la date de publication d'un entry feedparser en chaîne ISO YYYY-MM-DD.

    Essaie successivement : published (RFC 2822) → updated (RFC 2822) →
    published_parsed (struct_time) → updated_parsed (struct_time).
    Retourne "" si aucune date exploitable.
    """
    for attr in ("published", "updated"):
        val = getattr(entry, attr, None)
        if val:
            try:
                return _parsedate_to_datetime(val).date().isoformat()
            except Exception:
                try:
                    parsed = entry.get(f"{attr}_parsed")
                    if parsed:
                        return _datetime(*parsed[:6]).date().isoformat()
                except Exception:
                    pass
    return ""
