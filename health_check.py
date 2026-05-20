"""
Module de health check — DEF OI Veille Commerciale.

Vérifie pour chaque source :
  1. Code HTTP 200
  2. Présence d'un marqueur structurel (clé JSON ou texte HTML)

Usage : run_all_health_checks() -> dict[str, HealthResult]
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

_log = logging.getLogger(__name__)

TIMEOUT = 10  # secondes


@dataclass
class HealthResult:
    name: str
    ok: bool
    http_status: Optional[int] = None
    error: Optional[str] = None
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )


# Registre des sources avec leur marqueur structurel attendu.
# marker_type: "json_key" | "html_text" | "none"
_SOURCE_MARKERS: list[dict] = [
    {
        "name": "BOAMP — Journal Officiel",
        "url": "https://boamp-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/boamp/records?limit=1",
        "marker_type": "json_key",
        "marker_value": "results",
    },
    {
        "name": "TED Europe",
        "url": "https://api.ted.europa.eu/v3/notices/search",
        "marker_type": "json_key",
        "marker_value": "notices",
        "method": "post",
        "body": {"query": "FT~SSI", "limit": 1},
    },
    {
        "name": "AFD — Agence Française de Développement",
        "url": "https://opendata.afd.fr/api/explore/v2.1/catalog/datasets/les-projets-de-l-afd/records?limit=1",
        "marker_type": "json_key",
        "marker_value": "results",
    },
    {
        "name": "Banque Mondiale",
        "url": "https://search.worldbank.org/api/v2/projects?format=json&countrycode=MG&rows=1",
        "marker_type": "json_key",
        "marker_value": "projects",
    },
    {
        "name": "Permis de construire",
        "url": "https://data.statistiques.developpement-durable.gouv.fr/api/explore/v2.1/catalog/datasets/sitadel/records?limit=1",
        "marker_type": "json_key",
        "marker_value": "results",
    },
    {
        "name": "Marché Online",
        "url": "https://www.marchesonline.com/appels-offres/lieu/d-o-m-t-o-m-R95/reunion-D101",
        "marker_type": "html_text",
        "marker_value": "blockNotice",
    },
    {
        "name": "Instao",
        "url": "https://www.instao.fr/bids",
        "marker_type": "html_text",
        "marker_value": "bid",
    },
    {
        "name": "Marchés Sécurisés",
        "url": "https://www.marches-securises.fr/entreprise/?page=connexion",
        "marker_type": "html_text",
        "marker_value": "connexion",
    },
    {
        "name": "Tenders Go",
        "url": "https://app.tendersgo.com",
        "marker_type": "html_text",
        "marker_value": "tender",
    },
]

_HEADERS = {"User-Agent": "DEF-OI-HealthCheck/1.0"}


def check_source(
    name: str,
    url: str,
    marker_type: str = "none",
    marker_value: str = "",
    method: str = "get",
    body: dict | None = None,
) -> HealthResult:
    """Vérifie une source : HTTP 200 + marqueur structurel."""
    try:
        if method == "post":
            resp = requests.post(url, json=body or {}, timeout=TIMEOUT, headers=_HEADERS, allow_redirects=True)
        else:
            resp = requests.get(url, timeout=TIMEOUT, headers=_HEADERS, allow_redirects=True)

        http_status = resp.status_code

        if resp.status_code >= 400:
            return HealthResult(
                name=name, ok=False, http_status=http_status,
                error=f"HTTP {resp.status_code}",
            )

        if marker_type == "json_key":
            try:
                data = resp.json()
                if marker_value not in data:
                    return HealthResult(
                        name=name, ok=False, http_status=http_status,
                        error=f"Marqueur JSON '{marker_value}' absent — structure du site changée ?",
                    )
            except Exception:
                return HealthResult(
                    name=name, ok=False, http_status=http_status,
                    error="Réponse non JSON — structure du site changée ?",
                )

        elif marker_type == "html_text":
            if marker_value not in resp.text:
                return HealthResult(
                    name=name, ok=False, http_status=http_status,
                    error=f"Marqueur HTML '{marker_value}' absent — structure du site changée ?",
                )

        return HealthResult(name=name, ok=True, http_status=http_status)

    except Exception as exc:
        _log.warning("HealthCheck [%s] : %s", name, exc)
        return HealthResult(name=name, ok=False, error=str(exc))


def run_all_health_checks() -> dict[str, HealthResult]:
    """Lance le health check sur toutes les sources enregistrées."""
    results: dict[str, HealthResult] = {}
    for source in _SOURCE_MARKERS:
        name = source["name"]
        _log.info("HealthCheck : vérification de '%s'", name)
        results[name] = check_source(
            name=name,
            url=source["url"],
            marker_type=source.get("marker_type", "none"),
            marker_value=source.get("marker_value", ""),
            method=source.get("method", "get"),
            body=source.get("body"),
        )
    return results


def persist_health_results(db, results: dict[str, HealthResult]) -> None:
    """Persiste les résultats dans la table sources (champs ping existants)."""
    from source_registry import Source
    for name, result in results.items():
        source = db.query(Source).filter(Source.name == name).first()
        if not source:
            continue
        source.last_ping_at = result.checked_at
        if result.ok:
            source.ping_failures_count = 0
        else:
            source.ping_failures_count = (source.ping_failures_count or 0) + 1
            if source.ping_failures_count >= 3:
                source.is_validated = False
    db.commit()
