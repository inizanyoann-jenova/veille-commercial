"""
Scraper Permis de Construire — Sit@del2 (SDES / data.gouv.fr).
Récupère les permis déposés sur les départements 974 (La Réunion) et 976 (Mayotte).
Filtre sur les types de bâtiments nécessitant du SSI : ERP, habitations collectives, industrie.
"""
import hashlib
from datetime import datetime, timedelta

import requests

from database import SessionLocal, init_db
from models import Tender

SITADEL_API = (
    "https://data.statistiques.developpement-durable.gouv.fr"
    "/api/explore/v2.1/catalog/datasets/sitadel/records"
)

TYPES_CIBLES = [
    "erp", "établissement recevant du public",
    "habitation collective", "logement collectif", "immeuble",
    "industriel", "entrepôt", "bureau", "commerce",
    "hôpital", "clinique", "hôtel", "école", "université",
    "équipement", "salle", "centre",
]


def _type_batiment_ok(record: dict) -> bool:
    text = " ".join([
        str(record.get("lib_type_batiment") or ""),
        str(record.get("lib_nature_proj") or ""),
        str(record.get("lib_usage_principal") or ""),
    ]).lower()
    return any(t in text for t in TYPES_CIBLES) or text.strip() == ""


def _parse_date(value) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value)[:10], fmt[:8])
        except ValueError:
            continue
    return None


def fetch_permis_construire(years_back: int = 1) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")

    try:
        for dept in ["974", "976"]:
            offset = 0
            limit = 100

            while True:
                params = {
                    "where": (
                        f"code_dep='{dept}'"
                        f" AND date_depot_doc >= '{date_min}'"
                    ),
                    "limit": limit,
                    "offset": offset,
                    "order_by": "date_depot_doc DESC",
                }

                try:
                    r = requests.get(SITADEL_API, params=params, timeout=30)
                    r.raise_for_status()
                except requests.HTTPError as exc:
                    # 404 = dataset unavailable; treat as empty result set
                    if exc.response is not None and exc.response.status_code in (404, 410):
                        break
                    raise RuntimeError(f"Sit@del2 API ({dept}) : {exc}") from exc
                except requests.RequestException as exc:
                    raise RuntimeError(f"Sit@del2 API ({dept}) : {exc}") from exc

                records = r.json().get("results", [])
                if not records:
                    break

                for rec in records:
                    if not _type_batiment_ok(rec):
                        continue

                    commune = rec.get("lib_nom_commune") or rec.get("lib_commune") or dept
                    nature = (
                        rec.get("lib_type_batiment")
                        or rec.get("lib_nature_proj")
                        or "Bâtiment"
                    )
                    surface = rec.get("surf_tot") or rec.get("surface_totale") or ""
                    surface_txt = f" — {surface} m²" if surface else ""

                    raw_id = (
                        rec.get("num_permis")
                        or rec.get("id_permis")
                        or hashlib.md5(str(rec).encode()).hexdigest()[:12]
                    )
                    tender_id = f"PC-{dept}-{raw_id}"

                    if db.query(Tender).filter(Tender.id == tender_id).first():
                        continue

                    title = f"[PC] {nature}{surface_txt} — {commune} ({dept})"
                    description = (
                        f"Permis de construire — Département {dept} — {commune}\n"
                        f"Nature : {nature}{surface_txt}\n"
                        f"Adresse : {rec.get('adresse') or rec.get('lib_adresse') or 'Non renseignée'}"
                    )

                    db.add(Tender(
                        id=tender_id,
                        title=title,
                        description=description,
                        source=(
                            rec.get("url") or
                            f"https://data.statistiques.developpement-durable.gouv.fr/explore/dataset/sitadel/table/?q={raw_id}"
                        ),
                        publication_date=_parse_date(rec.get("date_depot_doc") or rec.get("dat_depdoc")),
                        deadline=None,
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                        secteur="Privé",
                        type_opportunite="Permis Construire",
                    ))
                    inserted += 1

                db.commit()
                if len(records) < limit:
                    break
                offset += limit

    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    print("Collecte Permis de Construire (974 & 976)…")
    count = fetch_permis_construire()
    print(f"Terminé — {count} permis inséré(s).")
