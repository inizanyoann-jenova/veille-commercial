"""
Scraper Permis de Construire — Sit@del2 (SDES / data.gouv.fr).
Récupère les permis déposés sur les départements 974 (La Réunion) et 976 (Mayotte).
Filtre sur les types de bâtiments nécessitant du SSI : ERP, habitations collectives, industrie.
"""
import hashlib
import logging
from datetime import datetime, timedelta

from database import SessionLocal, init_db, start_scraper_run, finish_scraper_run
from models import Tender
from scraper_utils import parse_date, retry_get, load_existing_ids, insert_if_new

_log = logging.getLogger(__name__)

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


def fetch_permis_construire(years_back: int = 1) -> int:
    init_db()
    db = SessionLocal()
    inserted = 0
    date_min = (datetime.now() - timedelta(days=365 * years_back)).strftime("%Y-%m-%d")
    _run_id = start_scraper_run(db, "Permis de construire")

    try:
        existing_ids = load_existing_ids(db)

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
                    r = retry_get(SITADEL_API, params=params, rate_delay=1.0)
                except Exception as exc:
                    _log.warning("Sit@del2 API (%s) inaccessible : %s", dept, type(exc).__name__)
                    break

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

                    title = f"[PC] {nature}{surface_txt} — {commune} ({dept})"
                    description = (
                        f"Permis de construire — Département {dept} — {commune}\n"
                        f"Nature : {nature}{surface_txt}\n"
                        f"Adresse : {rec.get('adresse') or rec.get('lib_adresse') or 'Non renseignée'}"
                    )

                    t = Tender(
                        id=tender_id,
                        title=title,
                        description=description,
                        source=(
                            rec.get("url") or
                            f"https://data.statistiques.developpement-durable.gouv.fr/explore/dataset/sitadel/table/?q={raw_id}"
                        ),
                        publication_date=parse_date(rec.get("date_depot_doc") or rec.get("dat_depdoc")),
                        deadline=None,
                        status="À qualifier",
                        relevance_score=0,
                        is_maintenance=False,
                        llm_analysis=None,
                        secteur="Privé",
                        type_opportunite="Permis Construire",
                    )
                    if insert_if_new(db, t, existing_ids):
                        inserted += 1

                if len(records) < limit:
                    break
                offset += limit

        if inserted:
            db.commit()
        finish_scraper_run(db, _run_id, nb_found=inserted, nb_new=inserted)
        _log.info("Permis construire : %d inséré(s)", inserted)
    except Exception as exc:
        _log.exception("Permis construire : erreur collecte")
        finish_scraper_run(db, _run_id, nb_found=0, nb_new=0, error=str(exc))
        raise
    finally:
        db.close()

    return inserted


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = fetch_permis_construire()
    _log.info("Permis construire terminé — %d inséré(s)", count)
