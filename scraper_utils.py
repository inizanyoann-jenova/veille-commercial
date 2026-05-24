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
            resp = requests.get(url, params=params, timeout=timeout)
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

_INSERT_MAX_AGE_DAYS = 30


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
        return False

    pub = tender.publication_date
    if isinstance(pub, str):
        try:
            pub = _dt.fromisoformat(pub[:10])
        except (ValueError, TypeError):
            return False

    cutoff = _dt.now() - _td(days=_INSERT_MAX_AGE_DAYS)
    if pub < cutoff:
        return False

    if tender.id in existing_ids:
        return False

    db.add(tender)
    db.flush()
    existing_ids.add(tender.id)
    return True
