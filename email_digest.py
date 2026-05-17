import os
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from database import SessionLocal
from fiche_logic import SCORE_GO, SCORE_ETUDE
from models import Tender


def build_digest(since_hours: int = 24, db=None) -> dict | None:
    """Retourne {"subject": ..., "html": ...} ou None si rien à envoyer."""
    _close = db is None
    if db is None:
        db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=since_hours)
        urgence_limit = datetime.utcnow() + timedelta(days=7)
        now = datetime.utcnow()

        new_tenders = (
            db.query(Tender)
            .filter(
                Tender.is_blacklisted == False,
                Tender.publication_date >= cutoff,
            )
            .order_by(Tender.relevance_score.desc())
            .all()
        )

        go = [t for t in new_tenders if t.relevance_score >= SCORE_GO]
        etude = [t for t in new_tenders if SCORE_ETUDE <= t.relevance_score < SCORE_GO]

        if not go and not etude:
            return None

        urgences = (
            db.query(Tender)
            .filter(
                Tender.is_blacklisted == False,
                Tender.relevance_score >= SCORE_GO,
                Tender.status.notin_(["Gagné", "Perdu"]),
                Tender.deadline != None,
                Tender.deadline >= now,
                Tender.deadline <= urgence_limit,
            )
            .order_by(Tender.deadline.asc())
            .all()
        )

        total = len(go) + len(etude)
        date_str = datetime.now().strftime("%d %B %Y")
        subject = f"[DEF OI] {total} nouvelle(s) opportunité(s) — {date_str}"
        html = _build_html(go, etude, urgences, date_str, now)
        return {"subject": subject, "html": html}
    finally:
        if _close:
            db.close()


def _build_html(go, etude, urgences, date_str, now) -> str:
    def _go_row(t):
        deadline = t.deadline.strftime("%d/%m/%Y") if t.deadline else "—"
        return (
            f"<tr>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #f0f2f5'>{t.title or '—'}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #f0f2f5;white-space:nowrap'>{t.relevance_score}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #f0f2f5;white-space:nowrap'>{deadline}</td>"
            f"<td style='padding:6px 8px;border-bottom:1px solid #f0f2f5'>{t.source or '—'}</td>"
            f"</tr>"
        )

    def _etude_item(t):
        deadline = t.deadline.strftime("%d/%m/%Y") if t.deadline else "—"
        return (
            f"<li style='margin-bottom:4px'><strong>{t.title or '—'}</strong>"
            f" · Score {t.relevance_score} · Deadline {deadline}</li>"
        )

    def _urgence_item(t):
        jours = (t.deadline.date() - now.date()).days if t.deadline else 0
        return (
            f"<li style='margin-bottom:4px;color:#dc2626'>"
            f"<strong>{t.title or '—'}</strong> · ⚠️ {jours}j restants</li>"
        )

    go_section = ""
    if go:
        rows = "".join(_go_row(t) for t in go)
        go_section = f"""
        <h2 style='color:#166534;margin-top:24px'>✅ GO — {len(go)} marché(s) qualifié(s)</h2>
        <p style='color:#6b7280;font-size:0.9em'>Ces marchés sont qualifiés et prêts à traiter</p>
        <table style='width:100%;border-collapse:collapse;font-size:0.9em'>
          <thead><tr style='background:#f9fafb'>
            <th style='text-align:left;padding:6px 8px'>Titre</th>
            <th style='text-align:left;padding:6px 8px'>Score</th>
            <th style='text-align:left;padding:6px 8px'>Deadline</th>
            <th style='text-align:left;padding:6px 8px'>Source</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>"""

    etude_section = ""
    if etude:
        items = "".join(_etude_item(t) for t in etude)
        etude_section = f"""
        <h2 style='color:#92400e;margin-top:24px'>🔍 À étudier — {len(etude)} marché(s)</h2>
        <p style='color:#6b7280;font-size:0.9em'>Ces marchés méritent un regard — ouvre la fiche pour décider</p>
        <ul style='font-size:0.9em;padding-left:20px'>{items}</ul>"""

    urgence_section = ""
    if urgences:
        items = "".join(_urgence_item(t) for t in urgences)
        urgence_section = f"""
        <h2 style='color:#dc2626;margin-top:24px'>⚠️ Urgences — deadline &lt; 7 jours</h2>
        <ul style='font-size:0.9em;padding-left:20px'>{items}</ul>"""

    return f"""<html><body style='font-family:Inter,system-ui,sans-serif;max-width:700px;margin:0 auto;padding:24px;color:#111827'>
  <h1 style='color:#cc2222;margin-bottom:4px'>DEF Océan Indien — Veille Marchés</h1>
  <p style='color:#6b7280'>{date_str}</p>
  <hr style='border:none;border-top:1px solid #f0f2f5;margin:16px 0'>
  {go_section}{etude_section}{urgence_section}
  <hr style='border:none;border-top:1px solid #f0f2f5;margin:24px 0'>
  <p style='font-size:0.8em;color:#9ca3af'>
    <a href='http://localhost:8501' style='color:#cc2222'>Ouvrir l'application →</a>
  </p>
</body></html>"""


def send_digest(smtp_config: dict, db=None) -> bool:
    """Construit et envoie le digest. Retourne True si un email a été envoyé."""
    data = build_digest(db=db)
    if data is None:
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = data["subject"]
    msg["From"] = smtp_config["user"]
    msg["To"] = smtp_config["to"]
    msg.attach(MIMEText(data["html"], "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_config["user"], smtp_config["password"])
            server.send_message(msg)
        return True
    except Exception:
        return False
