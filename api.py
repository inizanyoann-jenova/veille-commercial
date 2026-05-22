import logging
import tempfile

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from database import SessionLocal, init_db
from health_check import run_all_health_checks
from llm_analyzer import analyze_tender, auto_analyze_claude, auto_analyze_pending
from models import Tender
from source_registry import list_sources, add_source, remove_source, toggle_enabled
from export_excel import generate_executive_report

_log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app = FastAPI(title="DEF OI Veille Commerciale", version="2.0.0", lifespan=lifespan)


@app.get("/health")
def health():
    results = run_all_health_checks()
    return {
        "status": "ok",
        "sources": {
            name: {"ok": r.ok, "http_status": r.http_status, "error": r.error}
            for name, r in results.items()
        },
    }


@app.get("/tenders")
def list_tenders(
    score_min: int = Query(0),
    status: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    db = SessionLocal()
    try:
        query = db.query(Tender).filter(
            Tender.is_blacklisted == False,
            Tender.relevance_score >= score_min,
        )
        if status:
            query = query.filter(Tender.status == status)
        if q:
            from sqlalchemy import or_
            query = query.filter(
                or_(Tender.title.ilike(f"%{q}%"), Tender.description.ilike(f"%{q}%"))
            )
        total = query.count()
        tenders = (
            query.order_by(Tender.relevance_score.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return {
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "title": t.title,
                    "score": t.relevance_score,
                    "status": t.status,
                    "amount": t.amount,
                    "publication_date": str(t.publication_date) if t.publication_date else None,
                    "source_url": t.source_url,
                    "llm_analysis": t.llm_analysis,
                }
                for t in tenders
            ],
        }
    finally:
        db.close()


@app.post("/tenders/{tender_id}/analyze")
def analyze_one(tender_id: str):
    db = SessionLocal()
    try:
        t = db.query(Tender).filter(Tender.id == tender_id).first()
        if not t:
            raise HTTPException(status_code=404, detail="Marché introuvable")
        text = f"{t.title or ''} {t.description or ''}"
        try:
            result = analyze_tender(text, source_url=t.source)
            t.llm_analysis = result
            t.relevance_score = result.get("score_pertinence", t.relevance_score)
            db.commit()
            return result
        except HTTPException:
            raise
        except Exception:
            db.rollback()
            raise
    finally:
        db.close()


class AutoAnalyzeRequest(BaseModel):
    max_per_run: int = 10


@app.post("/auto-analyze")
def auto_analyze(req: AutoAnalyzeRequest):
    db = SessionLocal()
    try:
        nb_done, retry_after = auto_analyze_claude(db, max_per_run=req.max_per_run)
        return {"nb_done": nb_done, "retry_after": retry_after}
    finally:
        db.close()


@app.post("/auto-analyze/local")
def auto_analyze_local():
    db = SessionLocal()
    try:
        try:
            nb_done = auto_analyze_pending(db)
            return {"nb_done": nb_done}
        except Exception:
            db.rollback()
            raise
    finally:
        db.close()


class ScrapeRequest(BaseModel):
    sources: list[str] = []
    max_tenders: int = 50


@app.post("/scrape")
def scrape(req: ScrapeRequest):
    from importlib import import_module
    db = SessionLocal()
    try:
        all_sources = list_sources(db)
        enabled = [
            s for s in all_sources
            if s.enabled and (not req.sources or s.name in req.sources)
            and s.scraper_module is not None
        ]
    finally:
        db.close()

    results = {}
    for src in enabled:
        try:
            mod = import_module(src.scraper_module)
            if hasattr(mod, "run"):
                count = mod.run(max_results=req.max_tenders)
            else:
                count = 0
            results[src.name] = {"ok": True, "count": count}
        except Exception as exc:
            results[src.name] = {"ok": False, "error": str(exc)[:200]}
    return results


@app.get("/sources")
def get_sources(category: Optional[str] = Query(None)):
    db = SessionLocal()
    try:
        sources = list_sources(db, category=category)
        return [
            {
                "id": s.id,
                "name": s.name,
                "url": s.url,
                "category": s.category,
                "enabled": s.enabled,
                "is_manual": s.is_manual,
                "notes": s.notes,
            }
            for s in sources
        ]
    finally:
        db.close()


class SourceCreate(BaseModel):
    name: str
    url: str
    category: str
    notes: Optional[str] = None


@app.post("/sources", status_code=201)
def create_source(src: SourceCreate):
    db = SessionLocal()
    try:
        s = add_source(db, name=src.name, url=src.url, category=src.category, notes=src.notes)
        return {"id": s.id, "name": s.name}
    finally:
        db.close()


@app.delete("/sources/{source_id}")
def delete_source(source_id: int):
    db = SessionLocal()
    try:
        ok = remove_source(db, source_id)
        if not ok:
            raise HTTPException(status_code=400, detail="Source introuvable ou non supprimable (scraper dédié)")
        return {"ok": True}
    finally:
        db.close()


@app.patch("/sources/{source_id}/toggle")
def toggle_source(source_id: int):
    db = SessionLocal()
    try:
        new_state = toggle_enabled(db, source_id)
        if new_state is None:
            raise HTTPException(status_code=404, detail="Source introuvable")
        return {"enabled": new_state}
    finally:
        db.close()


@app.get("/export/excel")
def export_excel():
    db = SessionLocal()
    try:
        data = generate_executive_report(db)
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=rapport_def_oi.xlsx"},
        )
    finally:
        db.close()
