from models import ScoreWeight


def test_tokenize_removes_stop_words():
    from score_adaptive import _tokenize

    result = _tokenize("Installation des systèmes de détection incendie")
    assert "installation" in result
    assert "détection" in result or "detection" in result
    assert "des" not in result
    assert "de" not in result


def test_tokenize_filters_short_tokens():
    from score_adaptive import _tokenize

    result = _tokenize("SSI en ERP de type J")
    # tokens < 3 chars exclus
    assert all(len(t) >= 3 for t in result)


def test_recompute_returns_zero_when_insufficient_decisions(db):
    """Moins de 10 décisions → recompute retourne 0 sans modifier les scores."""
    from score_adaptive import recompute_adaptive_scores

    result = recompute_adaptive_scores(db)
    assert result == 0


def test_recompute_requires_ten_decisions(db, make_tender):
    """Exactement 9 décisions → toujours 0."""
    from score_adaptive import recompute_adaptive_scores

    for i in range(9):
        make_tender(
            status="Gagné",
            title=f"SSI installation ERP {i}",
            description="détection incendie SSI CMSI",
        )
    result = recompute_adaptive_scores(db)
    assert result == 0


def test_recompute_scores_undecided_tenders(db, make_tender):
    """10 décisions → les tenders non décidés reçoivent un adaptive_score."""
    from score_adaptive import recompute_adaptive_scores

    for i in range(8):
        make_tender(
            status="Gagné",
            title=f"SSI ERP installation {i}",
            description="détection incendie SSI CMSI",
        )
    for i in range(2):
        make_tender(
            status="Perdu",
            title=f"nettoyage jardinage {i}",
            description="espaces verts entretien",
        )
    # Tender non décidé
    undecided = make_tender(
        status="À qualifier",
        title="Installation SSI ERP",
        description="détection incendie",
    )
    nb = recompute_adaptive_scores(db)
    assert nb >= 1
    db.refresh(undecided)
    assert undecided.adaptive_score is not None
    assert 0 <= undecided.adaptive_score <= 100


def test_recompute_persists_score_weights(db, make_tender):
    """Les poids sont enregistrés dans score_weights."""
    from score_adaptive import recompute_adaptive_scores

    for i in range(10):
        make_tender(
            status="Gagné", title=f"SSI ERP {i}", description="détection incendie CMSI"
        )
    recompute_adaptive_scores(db)
    weights = db.query(ScoreWeight).all()
    assert len(weights) > 0


def test_recompute_go_tender_scores_higher_than_irrelevant(db, make_tender):
    """Un tender GO-like doit scorer plus haut qu'un irrelevant."""
    from score_adaptive import recompute_adaptive_scores

    for i in range(8):
        make_tender(
            status="Gagné",
            title=f"SSI ERP installation {i}",
            description="détection incendie SSI CMSI désenfumage",
        )
    for i in range(2):
        make_tender(
            status="Perdu",
            title=f"nettoyage jardinage {i}",
            description="tonte pelouse espaces verts",
        )
    t_go = make_tender(
        status="À qualifier",
        title="Installation SSI ERP Type J",
        description="détection incendie CMSI",
    )
    t_bad = make_tender(
        status="À qualifier",
        title="Tonte pelouse jardinage",
        description="entretien espaces verts",
    )
    recompute_adaptive_scores(db)
    db.refresh(t_go)
    db.refresh(t_bad)
    assert t_go.adaptive_score is not None
    assert t_bad.adaptive_score is not None
    assert t_go.adaptive_score >= t_bad.adaptive_score


# ── Sprint 2 : decay temporel ─────────────────────────────────────────────────


def test_age_weight_recent_returns_one():
    """Un tender collecté il y a 30 jours → poids 1.0."""
    from score_adaptive import _age_weight
    from datetime import datetime, timedelta

    class FakeTender:
        date_extraction = datetime.utcnow() - timedelta(days=30)

    assert _age_weight(FakeTender()) == 1.0


def test_age_weight_old_returns_half():
    """Un tender collecté il y a 200 jours → poids 0.5."""
    from score_adaptive import _age_weight
    from datetime import datetime, timedelta

    class FakeTender:
        date_extraction = datetime.utcnow() - timedelta(days=200)

    assert _age_weight(FakeTender()) == 0.5


def test_age_weight_boundary_180_days():
    """Exactement 180 jours → récent (poids 1.0) ; 181 jours → vieux (0.5)."""
    from score_adaptive import _age_weight
    from datetime import datetime, timedelta

    class FakeTender:
        pass

    t180 = FakeTender()
    t180.date_extraction = datetime.utcnow() - timedelta(days=180)
    assert _age_weight(t180) == 1.0

    t181 = FakeTender()
    t181.date_extraction = datetime.utcnow() - timedelta(days=181)
    assert _age_weight(t181) == 0.5


def test_age_weight_none_date_returns_one():
    """date_extraction absente → poids neutre 1.0."""
    from score_adaptive import _age_weight

    class FakeTender:
        date_extraction = None

    assert _age_weight(FakeTender()) == 1.0


def test_decay_old_decisions_still_produce_valid_score(db, make_tender):
    """Avec uniquement des décisions > 180 jours, recompute fonctionne toujours."""
    from score_adaptive import recompute_adaptive_scores
    from datetime import datetime, timedelta

    old_date = datetime.utcnow() - timedelta(days=200)
    for i in range(8):
        t = make_tender(
            status="Gagné",
            title=f"SSI ERP installation {i}",
            description="détection incendie SSI CMSI",
        )
        t.date_extraction = old_date
    for i in range(2):
        t = make_tender(
            status="Perdu",
            title=f"nettoyage jardinage {i}",
            description="espaces verts entretien",
        )
        t.date_extraction = old_date
    db.flush()

    undecided = make_tender(
        status="À qualifier",
        title="Installation SSI ERP",
        description="détection incendie",
    )
    nb = recompute_adaptive_scores(db)
    assert nb >= 1
    db.refresh(undecided)
    assert undecided.adaptive_score is not None
    assert 0 <= undecided.adaptive_score <= 100
