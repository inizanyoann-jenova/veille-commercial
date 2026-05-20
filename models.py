from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON, Float, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tender(Base):
    __tablename__ = "tenders"

    id               = Column(String, primary_key=True)
    title            = Column(String)
    description      = Column(String)
    source           = Column(String)
    publication_date = Column(DateTime)
    date_extraction  = Column(DateTime)   # timestamp when our script collected this
    deadline         = Column(DateTime)
    status           = Column(String, default="À qualifier")
    relevance_score  = Column(Integer, default=0)
    is_maintenance   = Column(Boolean, default=False)
    llm_analysis     = Column(JSON)
    secteur          = Column(String, default=None)
    type_opportunite = Column(String, default="Marché Public")
    amount           = Column(Integer, default=None)
    is_blacklisted   = Column(Boolean, default=False)
    is_saved         = Column(Boolean, default=False)
    notes            = Column(String, default=None)
    tags             = Column(JSON, default=list)
    llm_structured   = Column(JSON, default=None)
    adaptive_score   = Column(Integer, default=None)

    __table_args__ = (
        Index("idx_tender_blacklisted",     "is_blacklisted"),
        Index("idx_tender_status",          "status"),
        Index("idx_tender_score",           "relevance_score"),
        Index("idx_tender_deadline",        "deadline"),
        Index("idx_tender_publication",     "publication_date"),
        Index("idx_tender_score_blacklist", "relevance_score", "is_blacklisted"),
        Index("idx_tender_extraction",      "date_extraction"),
    )


class Credential(Base):
    __tablename__ = "credentials"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    site     = Column(String, unique=True, nullable=False)
    email    = Column(String, nullable=False)
    password = Column(String, nullable=False)  # chiffré Fernet


class ScraperRun(Base):
    __tablename__ = "scraper_runs"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    source_name = Column(String, nullable=False)
    started_at  = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    nb_found    = Column(Integer, default=0)
    nb_new      = Column(Integer, default=0)
    error       = Column(String, nullable=True)
    status      = Column(String, default="running")


class DuplicateCandidate(Base):
    __tablename__ = "duplicate_candidates"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    tender_id_a      = Column(String, nullable=False)
    tender_id_b      = Column(String, nullable=False)
    similarity_score = Column(Float, nullable=False)
    detected_at      = Column(DateTime, nullable=False)
    resolved         = Column(Boolean, default=False)


class ScoreWeight(Base):
    __tablename__ = "score_weights"

    keyword     = Column(String, primary_key=True)
    weight_go   = Column(Float, default=0.0)
    weight_nogo = Column(Float, default=0.0)
    updated_at  = Column(DateTime)
