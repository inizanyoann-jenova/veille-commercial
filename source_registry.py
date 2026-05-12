from sqlalchemy import Column, Integer, String, Boolean
from models import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    url = Column(String, nullable=False)
    category = Column(String, nullable=False)   # 'Public' | 'Privé' | 'International'
    scraper_module = Column(String, default=None)
    scraper_func = Column(String, default=None)
    is_manual = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    notes = Column(String, default=None)
    display_order = Column(Integer, default=99)


_DEFAULT_SOURCES = [
    # ── Automatiques existants ────────────────────────────────────────────────
    {"name": "BOAMP — Journal Officiel",
     "url": "https://boamp-datadila.opendatasoft.com",
     "category": "Public", "scraper_module": "scraper_boamp",
     "scraper_func": "fetch_boamp_tenders", "is_manual": False, "display_order": 1},
    {"name": "DECP / PLACE",
     "url": "https://data.economie.gouv.fr",
     "category": "Public", "scraper_module": "scraper_decp",
     "scraper_func": "fetch_decp_tenders", "is_manual": False, "display_order": 2},
    {"name": "TED Europe",
     "url": "https://ted.europa.eu",
     "category": "Public", "scraper_module": "scraper_ted",
     "scraper_func": "fetch_ted_tenders", "is_manual": False, "display_order": 3},
    {"name": "Permis de construire",
     "url": "https://www.geoportail-urbanisme.gouv.fr",
     "category": "Privé", "scraper_module": "scraper_permis",
     "scraper_func": "fetch_permis_construire", "is_manual": False, "display_order": 10},
    {"name": "Presse & Institutions IO",
     "url": "https://www.zinfos974.com",
     "category": "Privé", "scraper_module": "scraper_presse",
     "scraper_func": "fetch_presse_io", "is_manual": False, "display_order": 11},
    {"name": "Banques Dev. (BAD/BEI/COI)",
     "url": "https://www.afdb.org",
     "category": "International", "scraper_module": "scraper_devbanks",
     "scraper_func": "fetch_devbanks", "is_manual": False, "display_order": 20},
    {"name": "AFD — Agence Française de Développement",
     "url": "https://opendata.afd.fr",
     "category": "International", "scraper_module": "scraper_afd",
     "scraper_func": "fetch_afd_projects", "is_manual": False, "display_order": 21},
    {"name": "Banque Mondiale",
     "url": "https://api.worldbank.org",
     "category": "International", "scraper_module": "scraper_worldbank",
     "scraper_func": "fetch_worldbank_projects", "is_manual": False, "display_order": 22},
    {"name": "UNGM",
     "url": "https://www.ungm.org/Public/Notice/SearchNotices",
     "category": "International", "scraper_module": "scraper_ungm",
     "scraper_func": "fetch_ungm_tenders", "is_manual": False, "display_order": 23},
    # ── Manuels (accès guidé) ─────────────────────────────────────────────────
    {"name": "Marché Online", "url": "https://www.marcheonline.com",
     "category": "Public", "is_manual": True, "display_order": 30},
    {"name": "Marchés Publics Info", "url": "https://www.marches-publics.info",
     "category": "Public", "is_manual": True, "display_order": 31},
    {"name": "e-marchés publics", "url": "https://www.e-marches-publics.fr",
     "category": "Public", "is_manual": True, "display_order": 32},
    {"name": "France Marchés", "url": "https://www.france-marches.fr",
     "category": "Privé", "is_manual": True, "display_order": 40},
    {"name": "Marchés Sécurisés", "url": "https://www.marches-securises.fr",
     "category": "Privé", "is_manual": True, "display_order": 41},
    {"name": "Achatpublic.com", "url": "https://www.achatpublic.com",
     "category": "Privé", "is_manual": True, "display_order": 42},
    {"name": "Dematis", "url": "https://www.dematis.com",
     "category": "Privé", "is_manual": True, "display_order": 43},
    {"name": "Instao", "url": "https://www.instao.fr",
     "category": "Privé", "is_manual": True, "display_order": 44},
    {"name": "Vaao", "url": "https://www.vaao.fr",
     "category": "Privé", "is_manual": True, "display_order": 45},
    {"name": "Nukema", "url": "https://www.nukema.fr",
     "category": "Privé", "is_manual": True, "display_order": 46},
    {"name": "Deepbloo", "url": "https://www.deepbloo.com",
     "category": "International", "is_manual": True, "display_order": 50},
    {"name": "Tenders Go", "url": "https://www.tendersgo.com",
     "category": "International", "is_manual": True, "display_order": 51},
    {"name": "Marchés internationaux", "url": "https://www.marches-internationaux.com",
     "category": "International", "is_manual": True, "display_order": 52},
]


def init_sources(db) -> None:
    """Insère les sources par défaut si la table est vide. Idempotent."""
    if db.query(Source).count() == 0:
        for data in _DEFAULT_SOURCES:
            db.add(Source(**data))
        db.commit()


def list_sources(db, category: str | None = None) -> list:
    """Retourne toutes les sources, optionnellement filtrées par catégorie."""
    q = db.query(Source)
    if category:
        q = q.filter(Source.category == category)
    return q.order_by(Source.display_order, Source.name).all()


def add_source(db, name: str, url: str, category: str, notes: str = None):
    """Ajoute une source manuelle. Retourne l'objet Source créé."""
    s = Source(name=name, url=url, category=category,
               is_manual=True, enabled=True, notes=notes)
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
