# Lot 1 — Digest Email + Page Direction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Envoyer automatiquement chaque matin un email récapitulatif des nouveaux marchés GO, et fournir une page Direction avec KPIs exécutifs + export PDF.

**Architecture:** `email_digest.py` contient toute la logique de construction et d'envoi (testable sans Streamlit). `send_digest.py` est un script autonome 20 lignes pour le Planificateur Windows. `pages/direction.py` sépare les fonctions de données pures (testables) de l'UI Streamlit.

**Tech Stack:** Python stdlib `smtplib` / `email`, `reportlab`, `kaleido`, `plotly`, SQLAlchemy, APScheduler (déjà présent)

---

## Fichiers concernés

| Action | Fichier | Rôle |
|---|---|---|
| Créer | `email_digest.py` | build_digest() + send_digest() |
| Créer | `send_digest.py` | Script autonome CLI |
| Créer | `pages/direction.py` | Page Direction + PDF |
| Créer | `tests/test_email_digest.py` | Tests digest |
| Créer | `tests/test_direction.py` | Tests fonctions données Direction |
| Modifier | `requirements.txt` | Ajouter kaleido, reportlab |
| Modifier | `.env.example` | Ajouter variables DIGEST_* |
| Modifier | `app.py` | Ajouter job APScheduler digest dans `_start_background_services` |
| Modifier | `pages/parametres.py` | Ajouter section "📧 Digest email" |

---

### Task 1 : Dépendances + configuration

**Files:**
- Modify: `requirements.txt`
- Modify: `.env.example`

- [ ] **Step 1 : Ajouter les dépendances dans requirements.txt**

Ajouter après la dernière ligne existante :
```
kaleido==0.2.1
reportlab==4.2.5
```

- [ ] **Step 2 : Documenter les variables digest dans .env.example**

Ajouter à la fin du fichier `.env.example` :
```
# Digest email quotidien (optionnel)
DIGEST_SMTP_HOST=smtp.gmail.com
DIGEST_SMTP_PORT=587
DIGEST_SMTP_USER=
DIGEST_SMTP_PASSWORD=
DIGEST_TO=
DIGEST_HOUR=7
```

- [ ] **Step 3 : Installer les nouvelles dépendances**

```bash
pip install kaleido==0.2.1 reportlab==4.2.5
```

Résultat attendu : `Successfully installed kaleido reportlab` (ou "already satisfied" si déjà présent)

- [ ] **Step 4 : Commit**

```bash
git add requirements.txt .env.example
git commit -m "chore: add kaleido + reportlab deps, document DIGEST_* env vars"
```

---

### Task 2 : email_digest.py — build_digest() (TDD)

**Files:**
- Create: `tests/test_email_digest.py`
- Create: `email_digest.py`

- [ ] **Step 1 : Écrire les tests failing**

Créer `tests/test_email_digest.py` :

```python
from datetime import datetime, timedelta
import pytest
from models import Tender
from fiche_logic import SCORE_GO, SCORE_ETUDE


def test_build_digest_returns_none_when_no_new_tenders(db):
    """Aucun marché publié dans les 24h → None."""
    from email_digest import build_digest
    result = build_digest(since_hours=24, db=db)
    assert result is None


def test_build_digest_returns_none_when_only_irrelevant(db, make_tender):
    """Marchés publiés mais score < SCORE_ETUDE → None."""
    from email_digest import build_digest
    make_tender(
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_ETUDE - 1,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is None


def test_build_digest_subject_contains_count(db, make_tender):
    """GO + À étudier → sujet contient le total."""
    from email_digest import build_digest
    make_tender(publication_date=datetime.utcnow() - timedelta(hours=1), relevance_score=SCORE_GO)
    make_tender(publication_date=datetime.utcnow() - timedelta(hours=2), relevance_score=SCORE_ETUDE)
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "2" in result["subject"]
    assert "DEF OI" in result["subject"]


def test_build_digest_html_has_go_section(db, make_tender):
    """Marché GO → section ✅ GO dans le HTML."""
    from email_digest import build_digest
    make_tender(
        title="Installation SSI ERP",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "✅ GO" in result["html"]
    assert "Installation SSI ERP" in result["html"]


def test_build_digest_html_has_etude_section(db, make_tender):
    """Marché À étudier → section 🔍 dans le HTML."""
    from email_digest import build_digest
    make_tender(
        title="Maintenance alarme",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_ETUDE,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "🔍" in result["html"]
    assert "Maintenance alarme" in result["html"]


def test_build_digest_html_has_urgence_section(db, make_tender):
    """Marché GO avec deadline dans 3 jours → section ⚠️ dans le HTML."""
    from email_digest import build_digest
    make_tender(
        title="Urgence SSI",
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
        status="À qualifier",
        deadline=datetime.utcnow() + timedelta(days=3),
    )
    result = build_digest(since_hours=24, db=db)
    assert result is not None
    assert "⚠️" in result["html"]


def test_build_digest_excludes_blacklisted(db, make_tender):
    """Marchés blacklistés exclus même si GO."""
    from email_digest import build_digest
    make_tender(
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
        is_blacklisted=True,
    )
    result = build_digest(since_hours=24, db=db)
    assert result is None
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_email_digest.py -v
```

Résultat attendu : `ModuleNotFoundError: No module named 'email_digest'`

- [ ] **Step 3 : Implémenter email_digest.py**

Créer `email_digest.py` :

```python
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

    with smtplib.SMTP(smtp_config["host"], smtp_config["port"]) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_config["user"], smtp_config["password"])
        server.send_message(msg)

    return True
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_email_digest.py -v
```

Résultat attendu : 7 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add email_digest.py tests/test_email_digest.py
git commit -m "feat: email_digest — build_digest + send_digest avec tests"
```

---

### Task 3 : email_digest.py — tests send_digest()

**Files:**
- Modify: `tests/test_email_digest.py`

- [ ] **Step 1 : Ajouter les tests send_digest**

Ajouter à la fin de `tests/test_email_digest.py` :

```python
from unittest.mock import patch, MagicMock


_SMTP_CONFIG = {
    "host": "smtp.gmail.com",
    "port": 587,
    "user": "test@gmail.com",
    "password": "secret",
    "to": "dest@gmail.com",
}


def test_send_digest_returns_false_when_nothing_to_send(db):
    """Aucun marché → send_digest retourne False sans appeler SMTP."""
    from email_digest import send_digest
    with patch("smtplib.SMTP") as mock_smtp:
        result = send_digest(_SMTP_CONFIG, db=db)
    assert result is False
    mock_smtp.assert_not_called()


def test_send_digest_returns_true_and_calls_smtp(db, make_tender):
    """Marché GO présent → send_digest retourne True et appelle SMTP."""
    from email_digest import send_digest
    make_tender(
        publication_date=datetime.utcnow() - timedelta(hours=1),
        relevance_score=SCORE_GO,
    )
    mock_server = MagicMock()
    with patch("smtplib.SMTP") as mock_smtp:
        mock_smtp.return_value.__enter__ = lambda s: mock_server
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
        result = send_digest(_SMTP_CONFIG, db=db)
    assert result is True
    mock_server.send_message.assert_called_once()
```

- [ ] **Step 2 : Vérifier que les tests passent**

```bash
pytest tests/test_email_digest.py -v
```

Résultat attendu : 9 tests PASSED

- [ ] **Step 3 : Commit**

```bash
git add tests/test_email_digest.py
git commit -m "test: couverture send_digest avec mock SMTP"
```

---

### Task 4 : send_digest.py — script autonome

**Files:**
- Create: `send_digest.py`

- [ ] **Step 1 : Créer send_digest.py**

```python
"""Script autonome — planifiable via Planificateur de tâches Windows.
Usage : python send_digest.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

smtp_config = {
    "host": os.getenv("DIGEST_SMTP_HOST", "smtp.gmail.com"),
    "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
    "user": os.getenv("DIGEST_SMTP_USER", ""),
    "password": os.getenv("DIGEST_SMTP_PASSWORD", ""),
    "to": os.getenv("DIGEST_TO", ""),
}

if not smtp_config["user"] or not smtp_config["to"]:
    print("❌ DIGEST_SMTP_USER et DIGEST_TO doivent être configurés dans .env")
    sys.exit(1)

from email_digest import send_digest

sent = send_digest(smtp_config)
print(f"✅ Digest envoyé" if sent else "ℹ️  Aucun nouveau marché à envoyer")
```

- [ ] **Step 2 : Vérifier que le script s'importe sans erreur**

```bash
python -c "import send_digest" 2>&1
```

Résultat attendu : aucune erreur (la variable smtp_config ne sera pas évaluée, juste importée)

- [ ] **Step 3 : Commit**

```bash
git add send_digest.py
git commit -m "feat: send_digest.py — script autonome CLI pour Planificateur Windows"
```

---

### Task 5 : pages/parametres.py — section Digest email

**Files:**
- Modify: `pages/parametres.py`

- [ ] **Step 1 : Lire la fin du fichier pour identifier le point d'insertion**

```bash
tail -30 pages/parametres.py
```

- [ ] **Step 2 : Ajouter la section digest à la fin du fichier**

Ajouter après la dernière section existante dans `pages/parametres.py` :

```python
# ── Digest email ──────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("📧 Digest email quotidien")

_smtp_host = os.getenv("DIGEST_SMTP_HOST", "")
_smtp_to = os.getenv("DIGEST_TO", "")

if not _smtp_host or not _smtp_to:
    st.warning(
        "Variables DIGEST_SMTP_HOST et DIGEST_TO non configurées dans `.env`. "
        "Consultez le Guide utilisateur pour la procédure de configuration."
    )
else:
    st.success(f"Configuré → envoi à **{_smtp_to}** via {_smtp_host}")
    if st.button("📧 Envoyer le digest maintenant"):
        from email_digest import send_digest as _send
        _cfg = {
            "host": os.getenv("DIGEST_SMTP_HOST"),
            "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
            "user": os.getenv("DIGEST_SMTP_USER"),
            "password": os.getenv("DIGEST_SMTP_PASSWORD"),
            "to": os.getenv("DIGEST_TO"),
        }
        with st.spinner("Envoi en cours…"):
            sent = _send(_cfg)
        if sent:
            st.success("✅ Digest envoyé avec succès")
        else:
            st.info("ℹ️ Aucun nouveau marché à envoyer (0 GO + 0 À étudier dans les 24h)")

    st.markdown("""
    **Heure d'envoi automatique :** `DIGEST_HOUR` dans `.env` (défaut : 7h00)

    **Script autonome :** planifier `python send_digest.py` via le Planificateur de tâches Windows
    pour recevoir l'email même si l'application est fermée.
    """)
```

Vérifier que `os` et `dotenv` sont déjà importés en tête de `pages/parametres.py`.
Si `os` n'est pas importé, ajouter `import os` et `from dotenv import load_dotenv; load_dotenv()` en tête.

- [ ] **Step 3 : Vérifier que la page se charge sans erreur**

```bash
python -c "import ast; ast.parse(open('pages/parametres.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 4 : Commit**

```bash
git add pages/parametres.py
git commit -m "feat: parametres — section digest email avec bouton test"
```

---

### Task 6 : app.py — job APScheduler digest quotidien

**Files:**
- Modify: `app.py`

- [ ] **Step 1 : Localiser la fonction `_start_background_services` dans app.py**

```bash
grep -n "_start_background_services\|add_job\|weekly_ping" app.py | head -20
```

- [ ] **Step 2 : Ajouter le job digest dans `_start_background_services`**

Dans `app.py`, dans la fonction `_start_background_services`, après la ligne `_scheduler.add_job(_rwp, "interval", weeks=1, id="weekly_ping")`, ajouter :

```python
    # Job digest email quotidien (uniquement si SMTP configuré)
    _digest_hour = int(os.getenv("DIGEST_HOUR", "7"))
    if os.getenv("DIGEST_SMTP_HOST") and os.getenv("DIGEST_TO"):
        def _send_daily_digest():
            from email_digest import send_digest as _sd
            _cfg = {
                "host": os.getenv("DIGEST_SMTP_HOST"),
                "port": int(os.getenv("DIGEST_SMTP_PORT", "587")),
                "user": os.getenv("DIGEST_SMTP_USER"),
                "password": os.getenv("DIGEST_SMTP_PASSWORD"),
                "to": os.getenv("DIGEST_TO"),
            }
            _sd(_cfg)

        _scheduler.add_job(
            _send_daily_digest,
            "cron",
            hour=_digest_hour,
            minute=0,
            id="daily_digest",
        )
```

Vérifier que `os` est bien importé en tête de `app.py` (il l'est déjà via `from dotenv import load_dotenv`).

- [ ] **Step 3 : Vérifier que app.py parse sans erreur**

```bash
python -c "import ast; ast.parse(open('app.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 4 : Commit**

```bash
git add app.py
git commit -m "feat: app.py — job APScheduler digest quotidien si SMTP configuré"
```

---

### Task 7 : pages/direction.py — fonctions de données (TDD)

**Files:**
- Create: `tests/test_direction.py`
- Create: `pages/direction.py` (fonctions de données uniquement)

- [ ] **Step 1 : Écrire les tests failing**

Créer `tests/test_direction.py` :

```python
from datetime import datetime, timedelta
import pytest
from models import Tender


def test_load_direction_kpis_empty_db(db):
    """DB vide → structure complète avec valeurs nulles."""
    from pages.direction import _load_direction_kpis_data
    kpis = _load_direction_kpis_data(db)
    assert "nb_actifs" in kpis
    assert "ca_previsionnel" in kpis
    assert "ca_gagne" in kpis
    assert "taux_conversion" in kpis
    assert kpis["nb_actifs"] == 0
    assert kpis["ca_gagne"] == 0


def test_load_direction_kpis_counts_actifs(db, make_tender):
    """GO + Soumis comptent comme actifs, Gagné/Perdu non."""
    from pages.direction import _load_direction_kpis_data
    from fiche_logic import SCORE_GO
    make_tender(relevance_score=SCORE_GO, status="À qualifier")   # GO actif
    make_tender(relevance_score=SCORE_GO, status="Soumis")        # Soumis actif
    make_tender(relevance_score=SCORE_GO, status="Gagné", amount=50000)
    make_tender(relevance_score=SCORE_GO, status="Perdu")
    kpis = _load_direction_kpis_data(db)
    assert kpis["nb_actifs"] == 2
    assert kpis["ca_gagne"] == 50000


def test_load_direction_kpis_taux_conversion(db, make_tender):
    """Taux = Gagné / Soumis * 100."""
    from pages.direction import _load_direction_kpis_data
    make_tender(status="Soumis")
    make_tender(status="Soumis")
    make_tender(status="Gagné")
    kpis = _load_direction_kpis_data(db)
    assert kpis["taux_conversion"] == 50


def test_load_activity_90d_empty(db):
    """DB vide → liste vide."""
    from pages.direction import _load_activity_90d_data
    result = _load_activity_90d_data(db)
    assert isinstance(result, list)


def test_load_activity_90d_groups_by_week(db, make_tender):
    """Marchés récents groupés par semaine ISO."""
    from pages.direction import _load_activity_90d_data
    make_tender(publication_date=datetime.utcnow() - timedelta(days=3), status="GO")
    make_tender(publication_date=datetime.utcnow() - timedelta(days=5), status="Soumis")
    result = _load_activity_90d_data(db)
    assert len(result) >= 1
    assert "semaine" in result[0]
    assert "count" in result[0]


def test_load_pipeline_direction_excludes_gagné_perdu(db, make_tender):
    """Tableau pipeline = GO + Soumis seulement."""
    from pages.direction import _load_pipeline_direction_data
    from fiche_logic import SCORE_GO
    make_tender(relevance_score=SCORE_GO, status="À qualifier")
    make_tender(relevance_score=SCORE_GO, status="Soumis")
    make_tender(relevance_score=SCORE_GO, status="Gagné")
    make_tender(relevance_score=SCORE_GO, status="Perdu")
    rows = _load_pipeline_direction_data(db)
    assert len(rows) == 2
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_direction.py -v
```

Résultat attendu : `ModuleNotFoundError` ou `ImportError` car `pages/direction.py` n'existe pas encore

- [ ] **Step 3 : Créer pages/direction.py avec les fonctions de données**

```python
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
from sqlalchemy import func
import streamlit as st

from database import SessionLocal, init_db
from fiche_logic import SCORE_GO
from models import Tender


# ── Fonctions de données pures (testables sans Streamlit) ────────────��────────

def _load_direction_kpis_data(db) -> dict:
    nb_actifs = db.query(Tender).filter(
        Tender.is_blacklisted == False,
        Tender.relevance_score >= SCORE_GO,
        Tender.status.notin_(["Gagné", "Perdu"]),
    ).count()

    ca_prev = db.query(func.sum(Tender.amount)).filter(
        Tender.is_blacklisted == False,
        Tender.status.in_(["Soumis", "En cours"]),
        Tender.amount != None,
    ).scalar() or 0

    ca_gagne = db.query(func.sum(Tender.amount)).filter(
        Tender.is_blacklisted == False,
        Tender.status == "Gagné",
        Tender.amount != None,
    ).scalar() or 0

    nb_soumis = db.query(Tender).filter(
        Tender.is_blacklisted == False, Tender.status == "Soumis"
    ).count()
    nb_gagne = db.query(Tender).filter(
        Tender.is_blacklisted == False, Tender.status == "Gagné"
    ).count()
    taux = round(nb_gagne / nb_soumis * 100) if nb_soumis > 0 else None

    return {
        "nb_actifs": nb_actifs,
        "ca_previsionnel": ca_prev,
        "ca_gagne": ca_gagne,
        "taux_conversion": taux,
    }


def _load_activity_90d_data(db) -> list[dict]:
    cutoff = datetime.utcnow() - timedelta(days=90)
    rows = db.query(Tender.publication_date, Tender.status).filter(
        Tender.is_blacklisted == False,
        Tender.publication_date >= cutoff,
        Tender.publication_date != None,
    ).all()

    buckets: dict[str, int] = {}
    for pub, status in rows:
        week = pub.strftime("%Y-W%W")
        buckets[week] = buckets.get(week, 0) + 1

    return [{"semaine": w, "count": c} for w, c in sorted(buckets.items())]


def _load_pipeline_direction_data(db) -> list:
    return (
        db.query(Tender)
        .filter(
            Tender.is_blacklisted == False,
            Tender.relevance_score >= SCORE_GO,
            Tender.status.notin_(["Gagné", "Perdu"]),
        )
        .order_by(Tender.deadline.asc().nullslast())
        .all()
    )
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_direction.py -v
```

Résultat attendu : 6 tests PASSED

- [ ] **Step 5 : Commit**

```bash
git add pages/direction.py tests/test_direction.py
git commit -m "feat: direction — fonctions données avec tests (kpis, activité 90j, pipeline)"
```

---

### Task 8 : pages/direction.py — UI Streamlit complète

**Files:**
- Modify: `pages/direction.py`

- [ ] **Step 1 : Ajouter le layout Streamlit après les fonctions de données**

Ajouter à la fin de `pages/direction.py` (après les fonctions de données) :

```python
# ── Page Streamlit ────────────────────────────────────────────────────────────

st.set_page_config(page_title="Direction — DEF OI", page_icon="📊", layout="wide")

@st.cache_resource
def _ensure_db_init():
    init_db()

_ensure_db_init()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }
#MainMenu, footer, header { visibility: hidden; }
.main .block-container { padding-top: 1.2rem; padding-left: 2.5rem; padding-right: 2.5rem; max-width: 100%; }
[data-testid="stMetric"] {
    background: #fff; border: 1px solid #f0f2f5; border-radius: 10px;
    padding: 12px 16px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
[data-testid="stMetricLabel"] { color: #9ca3af !important; font-size: 0.69rem !important; text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600 !important; }
[data-testid="stMetricValue"] { color: #111827 !important; font-size: 1.55rem !important; font-weight: 800 !important; letter-spacing: -0.02em; }
</style>
""", unsafe_allow_html=True)

st.markdown("# 📊 Direction — DEF OI")
st.caption("Vue exécutive — Pipeline commercial")
st.markdown("---")


@st.cache_data(ttl=120)
def _load_direction_kpis():
    db = SessionLocal()
    try:
        return _load_direction_kpis_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_activity_90d():
    db = SessionLocal()
    try:
        return _load_activity_90d_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@st.cache_data(ttl=120)
def _load_pipeline_direction():
    db = SessionLocal()
    try:
        return _load_pipeline_direction_data(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Bloc 1 : KPIs ─────────────────────────────────────────────────────────────

_kpis = _load_direction_kpis()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Opportunités actives", _kpis["nb_actifs"])
k2.metric("CA prévisionnel", f"{_kpis['ca_previsionnel']:,.0f} €".replace(",", " ") if _kpis["ca_previsionnel"] else "—")
k3.metric("CA Gagné 🏆", f"{_kpis['ca_gagne']:,.0f} €".replace(",", " ") if _kpis["ca_gagne"] else "—")
k4.metric("Taux conversion", f"{_kpis['taux_conversion']} %" if _kpis["taux_conversion"] is not None else "—")

st.markdown("---")

# ── Bloc 2 : Activité 90 jours ────────────────────────────────────────────────

import plotly.express as px
import pandas as pd

st.markdown("### 📅 Activité — 90 derniers jours")
_activity = _load_activity_90d()
if _activity:
    _df_act = pd.DataFrame(_activity)
    _fig = px.bar(
        _df_act, x="semaine", y="count",
        labels={"semaine": "Semaine", "count": "Marchés collectés"},
        color_discrete_sequence=["#cc2222"],
    )
    _fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=0, r=0), height=250)
    st.plotly_chart(_fig, use_container_width=True)
else:
    st.caption("Aucune donnée d'activité sur 90 jours.")

st.markdown("---")

# ── Bloc 3 : Tableau pipeline ─────────────────────────────────────────────────

st.markdown("### 📋 Pipeline en cours")
_pipeline = _load_pipeline_direction()
if _pipeline:
    import pandas as pd
    _df_pipe = pd.DataFrame([{
        "Titre": (t.title or "")[:60],
        "Statut": t.status,
        "Deadline": t.deadline.strftime("%d/%m/%Y") if t.deadline else "—",
        "Montant estimé": f"{t.amount:,} €".replace(",", " ") if t.amount else "—",
        "Source": t.source or "—",
    } for t in _pipeline])
    st.dataframe(_df_pipe, use_container_width=True, hide_index=True)
else:
    st.caption("Aucun marché GO ou Soumis en cours.")

st.markdown("---")

# ── Bloc 4 : Export PDF ───────────────────────────────────────────────────────

if st.button("📄 Télécharger le rapport PDF"):
    with st.spinner("Génération du PDF…"):
        _pdf = generate_direction_pdf(_kpis, _activity, _pipeline)
    _date = datetime.now().strftime("%Y%m%d")
    st.download_button(
        label="⬇️ Télécharger",
        data=_pdf,
        file_name=f"Rapport_Direction_DEF_{_date}.pdf",
        mime="application/pdf",
    )

st.page_link("app.py", label="← Retour à la veille marchés")
```

- [ ] **Step 2 : Vérifier la syntaxe**

```bash
python -c "import ast; ast.parse(open('pages/direction.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 3 : Vérifier que les tests existants passent toujours**

```bash
pytest tests/test_direction.py -v
```

Résultat attendu : 6 tests PASSED

- [ ] **Step 4 : Commit**

```bash
git add pages/direction.py
git commit -m "feat: direction — UI Streamlit (KPIs, graphique 90j, tableau pipeline, bouton PDF)"
```

---

### Task 9 : pages/direction.py — génération PDF (TDD)

**Files:**
- Modify: `tests/test_direction.py`
- Modify: `pages/direction.py`

- [ ] **Step 1 : Ajouter le test generate_direction_pdf**

Ajouter dans `tests/test_direction.py` :

```python
def test_generate_direction_pdf_returns_nonempty_bytes():
    """generate_direction_pdf retourne des bytes non vides (PDF valide)."""
    from pages.direction import generate_direction_pdf
    kpis = {"nb_actifs": 3, "ca_previsionnel": 80000, "ca_gagne": 30000, "taux_conversion": 40}
    pdf_bytes = generate_direction_pdf(kpis, [], [])
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500  # un PDF même vide fait > 500 octets


def test_generate_direction_pdf_with_activity(make_tender, db):
    """PDF généré avec données d'activité sans erreur."""
    from pages.direction import generate_direction_pdf, _load_activity_90d_data, _load_pipeline_direction_data
    from fiche_logic import SCORE_GO
    make_tender(publication_date=datetime.utcnow() - timedelta(days=2), relevance_score=SCORE_GO, status="Soumis")
    kpis = {"nb_actifs": 1, "ca_previsionnel": 0, "ca_gagne": 0, "taux_conversion": None}
    activity = _load_activity_90d_data(db)
    pipeline = _load_pipeline_direction_data(db)
    pdf_bytes = generate_direction_pdf(kpis, activity, pipeline)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
```

- [ ] **Step 2 : Vérifier que les tests échouent**

```bash
pytest tests/test_direction.py::test_generate_direction_pdf_returns_nonempty_bytes -v
```

Résultat attendu : `ImportError: cannot import name 'generate_direction_pdf'`

- [ ] **Step 3 : Ajouter generate_direction_pdf dans pages/direction.py**

Ajouter **avant** la section `# ── Page Streamlit` dans `pages/direction.py` :

```python
# ── Génération PDF ────────────────────────────────────────────────────────────

def generate_direction_pdf(kpis: dict, activity_data: list, pipeline: list) -> bytes:
    """Génère le rapport Direction en PDF. Retourne les bytes du fichier."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=2 * cm, rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # En-tête
    story.append(Paragraph("DEF Océan Indien", styles["Title"]))
    story.append(Paragraph("Rapport Direction — Pipeline Commercial", styles["Heading2"]))
    story.append(Paragraph(datetime.now().strftime("Généré le %d/%m/%Y"), styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    # KPIs
    kpi_table_data = [
        ["Opportunités actives", "CA prévisionnel", "CA gagné", "Taux conversion"],
        [
            str(kpis.get("nb_actifs", "—")),
            f"{kpis.get('ca_previsionnel', 0):,.0f} €".replace(",", " ") if kpis.get("ca_previsionnel") else "—",
            f"{kpis.get('ca_gagne', 0):,.0f} €".replace(",", " ") if kpis.get("ca_gagne") else "—",
            f"{kpis.get('taux_conversion')} %" if kpis.get("taux_conversion") is not None else "—",
        ],
    ]
    kpi_t = Table(kpi_table_data, colWidths=[4.2 * cm] * 4)
    kpi_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#cc2222")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
    ]))
    story.append(kpi_t)
    story.append(Spacer(1, 0.5 * cm))

    # Graphique activité (si kaleido disponible)
    if activity_data:
        try:
            import plotly.express as px
            import plotly.io as pio
            from io import BytesIO as _BytesIO
            from reportlab.platypus import Image as _RLImage
            import pandas as pd

            _df = pd.DataFrame(activity_data)
            _fig = px.bar(_df, x="semaine", y="count", color_discrete_sequence=["#cc2222"])
            _fig.update_layout(showlegend=False, margin=dict(t=10, b=10, l=0, r=0))
            _img_bytes = pio.to_image(_fig, format="png", width=700, height=220)
            story.append(_RLImage(_BytesIO(_img_bytes), width=16 * cm, height=5 * cm))
            story.append(Spacer(1, 0.3 * cm))
        except Exception:
            pass  # kaleido absent ou erreur → on saute le graphique

    # Tableau pipeline
    if pipeline:
        story.append(Paragraph("Pipeline en cours", styles["Heading3"]))
        pipe_data = [["Titre", "Statut", "Deadline", "Montant"]]
        for t in pipeline[:20]:
            pipe_data.append([
                (t.title or "")[:55],
                t.status,
                t.deadline.strftime("%d/%m/%Y") if t.deadline else "—",
                f"{t.amount:,} €".replace(",", " ") if t.amount else "—",
            ])
        pipe_t = Table(pipe_data, colWidths=[9 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        pipe_t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]))
        story.append(pipe_t)

    doc.build(story)
    return buffer.getvalue()
```

- [ ] **Step 4 : Vérifier que les tests passent**

```bash
pytest tests/test_direction.py -v
```

Résultat attendu : 8 tests PASSED

- [ ] **Step 5 : Vérifier la syntaxe complète**

```bash
python -c "import ast; ast.parse(open('pages/direction.py').read()); print('OK')"
```

Résultat attendu : `OK`

- [ ] **Step 6 : Commit final Lot 1**

```bash
git add pages/direction.py tests/test_direction.py
git commit -m "feat: direction — generate_direction_pdf avec reportlab + tests"
```

---

### Task 10 : Vérification finale Lot 1

- [ ] **Step 1 : Lancer la suite de tests complète**

```bash
pytest tests/ -v --tb=short 2>&1 | tail -30
```

Résultat attendu : tous les tests passent (0 failures)

- [ ] **Step 2 : Vérifier la syntaxe de tous les fichiers modifiés**

```bash
python -c "
import ast, pathlib
for f in ['email_digest.py','send_digest.py','pages/direction.py','pages/parametres.py','app.py']:
    ast.parse(pathlib.Path(f).read_text(encoding='utf-8'))
    print(f'OK: {f}')
"
```

Résultat attendu : `OK` pour chaque fichier

- [ ] **Step 3 : Commit de clôture**

```bash
git add -u
git commit -m "feat: Lot 1 complet — digest email quotidien + page Direction exécutive + PDF"
```
