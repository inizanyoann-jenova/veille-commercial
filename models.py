from sqlalchemy import Column, String, DateTime, Integer, Boolean, JSON
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(String, primary_key=True)
    title = Column(String)
    description = Column(String)
    source = Column(String)
    publication_date = Column(DateTime)
    deadline = Column(DateTime)
    status = Column(String, default="À qualifier")
    relevance_score = Column(Integer, default=0)
    is_maintenance = Column(Boolean, default=False)
    llm_analysis = Column(JSON)
    secteur = Column(String, default=None)
    type_opportunite = Column(String, default="Marché Public")
    amount = Column(Integer, default=None)
    is_blacklisted = Column(Boolean, default=False)
    is_saved = Column(Boolean, default=False)


class Credential(Base):
    __tablename__ = "credentials"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    site     = Column(String, unique=True, nullable=False)
    email    = Column(String, nullable=False)
    password = Column(String, nullable=False)  # chiffré Fernet
