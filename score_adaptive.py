from datetime import timezone
import re
from collections import Counter
from datetime import datetime, timedelta

from database import SessionLocal
from models import ScoreWeight, Tender

_STOP_WORDS = {
    "le",
    "la",
    "les",
    "de",
    "du",
    "des",
    "un",
    "une",
    "et",
    "en",
    "au",
    "aux",
    "sur",
    "pour",
    "par",
    "dans",
    "avec",
    "qui",
    "que",
    "ne",
    "pas",
    "plus",
    "marché",
    "travaux",
    "fourniture",
    "service",
    "services",
    "accord",
    "cadre",
    "lot",
    "prestation",
    "mise",
    "place",
    "aux",
    "son",
    "ses",
    "leur",
    "leurs",
}

_POSITIVE_STATUSES = {"Soumis", "Gagné"}
_NEGATIVE_STATUSES = {"Perdu"}
_MIN_DECISIONS = 10


def _age_weight(tender) -> float:
    """Retourne 0.5 pour les tenders collectés > 180 jours, 1.0 sinon."""
    dt = getattr(tender, "date_extraction", None)
    if dt is None:
        return 1.0
    days_old = (datetime.now(timezone.utc).replace(tzinfo=None) - dt).days
    return 0.5 if days_old > 180 else 1.0


def _tokenize(text: str) -> list[str]:
    """Extrait les tokens significatifs d'un texte (longueur ≥ 3, hors stop words)."""
    tokens = re.findall(r"\b[a-zàâäéèêëîïôùûüç]{3,}\b", text.lower())
    return [t for t in tokens if t not in _STOP_WORDS]


def recompute_adaptive_scores(db=None) -> int:
    """
    Recalcule adaptive_score pour tous les tenders non décidés.
    Nécessite au moins _MIN_DECISIONS décisions enregistrées.
    Retourne le nombre de tenders mis à jour (0 si données insuffisantes).
    """
    _close = db is None
    if db is None:
        db = SessionLocal()
    try:
        pos_tenders = (
            db.query(Tender)
            .filter(
                Tender.status.in_(_POSITIVE_STATUSES),
                Tender.is_blacklisted.is_(False),
                Tender.title.is_not(None),
            )
            .all()
        )
        neg_tenders = (
            db.query(Tender)
            .filter(
                Tender.status.in_(_NEGATIVE_STATUSES),
                Tender.is_blacklisted.is_(False),
                Tender.title.is_not(None),
            )
            .all()
        )

        if len(pos_tenders) + len(neg_tenders) < _MIN_DECISIONS:
            return 0

        pos_counter: Counter = Counter()
        for t in pos_tenders:
            w = _age_weight(t)
            for token in _tokenize((t.title or "") + " " + (t.description or "")):
                pos_counter[token] += w

        neg_counter: Counter = Counter()
        for t in neg_tenders:
            w = _age_weight(t)
            for token in _tokenize((t.title or "") + " " + (t.description or "")):
                neg_counter[token] += w

        total_pos = max(sum(pos_counter.values()), 1)
        total_neg = max(sum(neg_counter.values()), 1)

        weights: dict[str, tuple[float, float]] = {}
        for token in set(pos_counter) | set(neg_counter):
            freq_go = pos_counter.get(token, 0) / total_pos
            freq_nogo = neg_counter.get(token, 0) / total_neg
            if freq_go + freq_nogo > 0.0005:
                weights[token] = (freq_go, freq_nogo)

        # Persister les poids
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        for token, (wgo, wnogo) in weights.items():
            sw = db.query(ScoreWeight).filter(ScoreWeight.keyword == token).first()
            if sw:
                sw.weight_go = wgo
                sw.weight_nogo = wnogo
                sw.updated_at = now
            else:
                db.add(
                    ScoreWeight(
                        keyword=token, weight_go=wgo, weight_nogo=wnogo, updated_at=now
                    )
                )
        db.commit()

        # Scorer les tenders non décidés
        undecided = (
            db.query(Tender)
            .filter(
                Tender.status.notin_(list(_POSITIVE_STATUSES | _NEGATIVE_STATUSES)),
                Tender.is_blacklisted.is_(False),
            )
            .all()
        )

        updated = 0
        for t in undecided:
            tokens = _tokenize((t.title or "") + " " + (t.description or ""))
            if not tokens:
                continue
            raw = sum(
                weights[tok][0] - weights[tok][1] for tok in tokens if tok in weights
            )
            # Normalisation sigmoïde-like vers 0–100
            normalized = int(
                50 + 50 * max(-1.0, min(1.0, raw / max(len(tokens) * 0.05, 1)))
            )
            t.adaptive_score = normalized
            updated += 1

        db.commit()
        return updated
    finally:
        if _close:
            db.close()
