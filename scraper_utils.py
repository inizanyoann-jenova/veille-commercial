"""
Utilitaires partagés par tous les scrapers DEF OI.

Fournit :
  - parse_date()        — parsing de date multi-format
  - retry_get()         — GET avec retry exponentiel et rate limiting
  - retry_post()        — POST avec retry exponentiel
  - load_existing_ids() — charge les IDs tender existants (évite N+1)
  - insert_if_new()     — insère un tender si non présent dans seen_ids
"""
import logging
import time
from datetime import datetime

import requests

_log = logging.getLogger(__name__)

_DEFAULT_RATE_DELAY = 1.0   # secondes
_MAX_RETRIES        = 3
_BASE_BACKOFF       = 2.0   # secondes (doublé à chaque retry)


def parse_date(value) -> datetime | None:
    """Parse une date depuis divers formats (str, list, None). Retourne None si non parseable."""
    if not value:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if not value:
        return None
    s = str(value).strip()
    for fmt, trunc in [
        ("%Y-%m-%dT%H:%M:%S", 19),
        ("%Y-%m-%d",           10),
        ("%d/%m/%Y",           10),
        ("%d-%m-%Y",           10),
        ("%Y%m%d",              8),
    ]:
        try:
            return datetime.strptime(s[:trunc], fmt)
        except ValueError:
            continue
    _log.debug("parse_date: format non reconnu pour '%s'", s[:30])
    return None


def retry_get(
    url: str,
    *,
    params: dict | None = None,
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
            _log.info("retry_get: tentative %d/%d — attente %.1fs (url=%s)", attempt + 1, retries, delay, url)
            time.sleep(delay)
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", _BASE_BACKOFF * 2))
                _log.warning("retry_get: 429 Too Many Requests — attente %ds", retry_after)
                time.sleep(retry_after)
                last_exc = requests.exceptions.HTTPError(response=resp)
                continue
            resp.raise_for_status()
            time.sleep(rate_delay)
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            _log.warning("retry_get: erreur tentative %d/%d : %s", attempt + 1, retries, type(exc).__name__)
    raise last_exc  # type: ignore[misc]


def retry_post(
    url: str,
    *,
    json: dict | None = None,
    timeout: int = 30,
    rate_delay: float = _DEFAULT_RATE_DELAY,
    retries: int = _MAX_RETRIES,
) -> requests.Response:
    """POST avec retry exponentiel — même logique que retry_get."""
    last_exc: Exception | None = None
    for attempt in range(retries):
        if attempt > 0:
            delay = _BASE_BACKOFF * (2 ** (attempt - 1))
            _log.info("retry_post: tentative %d/%d — attente %.1fs", attempt + 1, retries, delay)
            time.sleep(delay)
        try:
            resp = requests.post(url, json=json, timeout=timeout)
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("retry-after", _BASE_BACKOFF * 2))
                _log.warning("retry_post: 429 — attente %ds", retry_after)
                time.sleep(retry_after)
                last_exc = requests.exceptions.HTTPError(response=resp)
                continue
            resp.raise_for_status()
            time.sleep(rate_delay)
            return resp
        except requests.exceptions.RequestException as exc:
            last_exc = exc
            _log.warning("retry_post: erreur tentative %d/%d : %s", attempt + 1, retries, type(exc).__name__)
    raise last_exc  # type: ignore[misc]


def load_existing_ids(db) -> set[str]:
    """
    Charge tous les IDs de tenders existants en une seule requête.
    À appeler AVANT la boucle d'insertion pour éviter les N+1 queries.
    """
    from models import Tender
    return {row[0] for row in db.query(Tender.id).all()}


def insert_if_new(db, tender_obj, seen_ids: set[str]) -> bool:
    """
    Insère tender_obj dans db si son ID n'est pas dans seen_ids.
    Met à jour seen_ids. Retourne True si inséré.
    Ne fait PAS de commit (à faire par l'appelant en batch).
    """
    if tender_obj.id in seen_ids:
        return False
    seen_ids.add(tender_obj.id)
    db.add(tender_obj)
    return True
