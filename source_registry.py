from models import Source  # noqa: F401  # re-export — `from source_registry import Source` fonctionne toujours
import requests
from datetime import datetime as _dt_src, timezone as _tz_src


_DEFAULT_SOURCES = [
    # ── Automatiques existants ────────────────────────────────────────────────
    {
        "name": "BOAMP — Journal Officiel",
        "url": "https://boamp-datadila.opendatasoft.com",
        "category": "Public",
        "scraper_module": "scraper_boamp",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 1,
    },
    {
        "name": "DECP / PLACE",
        "url": "https://data.economie.gouv.fr",
        "category": "Public",
        "scraper_module": "scraper_decp",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 2,
    },
    {
        "name": "TED Europe",
        "url": "https://ted.europa.eu",
        "category": "Public",
        "scraper_module": "scraper_ted",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 3,
    },
    {
        "name": "Permis de construire",
        "url": "https://www.geoportail-urbanisme.gouv.fr",
        "category": "Privé",
        "scraper_module": "scraper_permis",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 10,
    },
    {
        "name": "Presse & Institutions IO",
        "url": "https://www.zinfos974.com",
        "category": "Privé",
        "scraper_module": "scraper_presse",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 11,
    },
    {
        "name": "Banques Dev. (BAD/BEI/COI)",
        "url": "https://www.afdb.org",
        "category": "International",
        "scraper_module": "scraper_devbanks",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 20,
    },
    {
        "name": "AFD — Agence Française de Développement",
        "url": "https://opendata.afd.fr",
        "category": "International",
        "scraper_module": "scraper_afd",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 21,
    },
    {
        "name": "Banque Mondiale",
        "url": "https://api.worldbank.org",
        "category": "International",
        "scraper_module": "scraper_worldbank",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 22,
    },
    {
        "name": "UNGM",
        "url": "https://www.ungm.org/Public/Notice/SearchNotices",
        "category": "International",
        "scraper_module": "scraper_ungm",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 23,
    },
    {
        "name": "VAAO",
        "url": "https://www.vaao.fr",
        "category": "Public",
        "scraper_module": "scraper_vaao",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 4,
    },
    {
        "name": "Marché Online",
        "url": "https://www.marchesonline.com",
        "category": "Public",
        "scraper_module": "scraper_marcheonline",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 5,
    },
    {
        "name": "Marchés Publics — Dép. 974",
        "url": "https://cg974.e-marchespublics.com",
        "category": "Public",
        "scraper_module": "scraper_dept974",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 6,
    },
    {
        "name": "Nukema",
        "url": "https://marches-publics.nukema.com",
        "category": "Public",
        "scraper_module": "scraper_nukema",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 7,
    },
    {
        "name": "Marchés Public Info",
        "url": "https://www.marches-publics.info",
        "category": "Public",
        "scraper_module": "scraper_marchespublicsinfo",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 8,
    },
    {
        "name": "Marchés Sécurisés",
        "url": "https://www.marches-securises.fr",
        "category": "Privé",
        "scraper_module": "scraper_marchessecurises",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 12,
    },
    {
        "name": "Instao",
        "url": "https://www.instao.fr",
        "category": "Privé",
        "scraper_module": "scraper_instao",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 13,
    },
    {
        "name": "Tenders Go",
        "url": "https://www.tendersgo.com",
        "category": "International",
        "scraper_module": "scraper_tendersgo",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 24,
    },
    {
        "name": "UNDP Procurement",
        "url": "https://procurement-notices.undp.org",
        "category": "International",
        "scraper_module": "scraper_devbanks",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 25,
    },
    {
        "name": "ADB — Banque Asiatique de Développement",
        "url": "https://www.adb.org",
        "category": "International",
        "scraper_module": "scraper_devbanks",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 26,
    },
    {
        "name": "Centre Hospitalier de Mayotte",
        "url": "https://www.chm-mayotte.fr/appels-d-offres",
        "category": "Public",
        "scraper_module": "scraper_chm",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 27,
    },
    # ── Manuels (accès guidé) ─────────────────────────────────────────────────
    {
        "name": "PLACE — Portail commandes publiques",
        "url": "https://www.marches-publics.gouv.fr",
        "category": "Public",
        "is_manual": True,
        "display_order": 30,
    },
    {
        "name": "France Marchés",
        "url": "https://www.france-marches.fr",
        "category": "Privé",
        "is_manual": True,
        "display_order": 40,
    },
    {
        "name": "Achatpublic.com",
        "url": "https://www.achatpublic.com",
        "category": "Privé",
        "is_manual": True,
        "display_order": 42,
    },
    {
        "name": "Dematis",
        "url": "https://www.dematis.com",
        "category": "Privé",
        "is_manual": True,
        "display_order": 43,
    },
    {
        "name": "Deepbloo",
        "url": "https://www.deepbloo.com",
        "category": "International",
        "is_manual": True,
        "display_order": 50,
    },
    {
        "name": "DG Market",
        "url": "https://www.dgmarket.com",
        "category": "International",
        "is_manual": True,
        "display_order": 51,
    },
    # ── Marchés publics locaux OI ─────────────────────────────────────────────
    {
        "name": "Région Réunion — Marchés publics",
        "url": "https://regionreunion.com/region/marches-publics",
        "category": "Public",
        "is_manual": True,
        "display_order": 31,
    },
    {
        "name": "CINOR — Marchés publics",
        "url": "https://www.cinor.re/marches-publics",
        "category": "Public",
        "is_manual": True,
        "display_order": 32,
    },
    {
        "name": "TCO — Marchés publics",
        "url": "https://www.tco.re/commande-publique",
        "category": "Public",
        "is_manual": True,
        "display_order": 33,
    },
    {
        "name": "CHU Réunion — Marchés publics",
        "url": "https://www.chu-reunion.fr/appels-offres",
        "category": "Public",
        "is_manual": True,
        "display_order": 34,
    },
    {
        "name": "Département de Mayotte — Marchés",
        "url": "https://www.departement976.fr/appels-d-offres",
        "category": "Public",
        "is_manual": True,
        "display_order": 35,
    },
    {
        "name": "CADEMA — Marchés publics",
        "url": "https://www.cadema.yt/appels-d-offres",
        "category": "Public",
        "is_manual": True,
        "display_order": 36,
    },
    {
        "name": "ARMP Madagascar",
        "url": "https://www.armp.mg/appels-offres",
        "category": "International",
        "is_manual": True,
        "display_order": 37,
    },
    {
        "name": "CPB Mauritius — Procurement",
        "url": "https://procurement.govmu.org",
        "category": "International",
        "is_manual": True,
        "display_order": 38,
    },
    # ── Banques de développement — OI ────────────────────────────────────────
    {
        "name": "IsDB — Banque Islamique de Développement",
        "url": "https://www.isdb.org/project-procurement",
        "category": "International",
        "scraper_module": "scraper_isdb",
        "scraper_func": "fetch",
        "is_manual": False,
        "display_order": 55,
    },
    {
        "name": "IFC — Projets Afrique / OI",
        "url": "https://projects.ifc.org",
        "category": "International",
        "is_manual": True,
        "display_order": 52,
    },
    {
        "name": "AIIB — Projets approuvés",
        "url": "https://www.aiib.org/en/projects/approved/index.html",
        "category": "International",
        "is_manual": True,
        "display_order": 53,
    },
    {
        "name": "COI — Commission Océan Indien",
        "url": "https://www.commissionoceanindien.org/appels-doffres/",
        "category": "International",
        "is_manual": True,
        "display_order": 54,
    },
]

# URLs défuntes à supprimer des bases existantes (domaines DNS morts ou non vérifiés)
_DEFUNCT_URLS = {
    "https://www.e-marches-publics.fr",
    "https://www.marches-internationaux.com",
    "https://www.semader.re/appels-d-offres",
}


def init_sources(db) -> None:
    """Insère les sources par défaut manquantes. Idempotent.
    Supprime aussi les URLs défuntes des bases existantes."""
    # Nettoyage des domaines morts (migration silencieuse)
    deleted = (
        db.query(Source)
        .filter(Source.url.in_(_DEFUNCT_URLS))
        .filter(Source.scraper_module.is_(None))  # noqa: E711
        .all()
    )
    for s in deleted:
        db.delete(s)
    if deleted:
        db.flush()

    # Migration : mettre à jour scraper_func vers "fetch" pour les sources existantes
    _old_func_names = {
        "fetch_boamp_tenders", "fetch_decp_tenders", "fetch_ted_tenders",
        "fetch_permis_construire", "fetch_presse_io", "fetch_devbanks",
        "fetch_afd_projects", "fetch_worldbank_projects", "fetch_ungm_tenders",
        "fetch_vaao_tenders", "fetch_marcheonline_tenders", "fetch_dept974_tenders",
        "fetch_semader_tenders", "fetch_nukema_tenders", "fetch_marchespublicsinfo_tenders",
        "fetch_marchessecurises_tenders", "fetch_instao_tenders", "fetch_tendersgo_tenders",
        "fetch_chm_tenders", "fetch_isdb_tenders",
    }
    (
        db.query(Source)
        .filter(Source.scraper_func.in_(_old_func_names))
        .update({"scraper_func": "fetch"}, synchronize_session=False)
    )

    existing_names = {s.name for s in db.query(Source.name).all()}
    for data in _DEFAULT_SOURCES:
        if data["name"] not in existing_names:
            src = Source(**data)
            if not src.is_manual:
                src.is_validated = True
            db.add(src)
    db.commit()


def list_sources(db, category: str | None = None) -> list:
    """Retourne toutes les sources, optionnellement filtrées par catégorie."""
    q = db.query(Source)
    if category:
        q = q.filter(Source.category == category)
    return q.order_by(Source.display_order, Source.name).all()


def add_source(db, name: str, url: str, category: str, notes: str = None):
    """Ajoute une source manuelle. Retourne l'objet Source créé."""
    s = Source(
        name=name, url=url, category=category, is_manual=True, enabled=True, notes=notes
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def remove_source(db, source_id: int) -> bool:
    """Supprime une source manuelle. Retourne False si la source a un scraper dédié."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s or s.scraper_module is not None:
        return False
    db.delete(s)
    db.commit()
    return True


def toggle_enabled(db, source_id: int) -> bool | None:
    """Bascule l'état enabled d'une source. Retourne le nouvel état, ou None si source introuvable."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if not s:
        return None
    s.enabled = not s.enabled
    db.commit()
    return s.enabled


def validate_source(db, source_id: int) -> None:
    """Marque une source comme validée (test de connexion réussi)."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if s:
        s.is_validated = True
        db.commit()


def invalidate_source(db, source_id: int) -> None:
    """Remet is_validated à False (credentials modifiés ou source inaccessible)."""
    s = db.query(Source).filter(Source.id == source_id).first()
    if s:
        s.is_validated = False
        db.commit()


def _ping_source(db, source) -> bool:
    try:
        resp = requests.get(
            source.url,
            timeout=8,
            allow_redirects=True,
            headers={"User-Agent": "DEF-OI-Monitor/1.0"},
        )
        ok = resp.status_code < 400
    except Exception:
        ok = False

    if ok:
        source.ping_failures_count = 0
    else:
        source.ping_failures_count = (source.ping_failures_count or 0) + 1
        if source.ping_failures_count >= 3:
            source.is_validated = False

    source.last_ping_at = _dt_src.now(_tz_src.utc).replace(tzinfo=None)
    db.commit()
    return ok


def _run_weekly_ping() -> None:
    from database import SessionLocal as _SL_ping

    db = _SL_ping()
    try:
        sources = db.query(Source).filter(Source.is_validated.is_(True)).all()
        for s in sources:
            _ping_source(db, s)
    finally:
        db.close()


def add_auto_source(db, name: str, url: str, category: str, module_name: str):
    """Enregistre une source auto-générée (scraper_custom_*). Retourne l'objet Source créé."""
    existing = db.query(Source).filter(Source.url == url).first()
    if existing:
        return existing
    s = Source(
        name=name,
        url=url,
        category=category,
        scraper_module=module_name,
        scraper_func="fetch",
        is_manual=False,
        enabled=True,
        is_validated=True,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s
