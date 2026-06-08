# tests/test_filters_atexia.py
import pytest
from filters import classify_relevance, is_relevant_def


# ── Nouveaux secteurs ATEXIA ──────────────────────────────────────────────────

def test_courants_forts_est_pertinent():
    result, _ = classify_relevance("Travaux de courants forts bâtiment tertiaire")
    assert result is True


def test_tgbt_est_pertinent():
    result, _ = classify_relevance("Fourniture et pose TGBT armoire électrique")
    assert result is True


def test_irve_est_pertinent():
    result, _ = classify_relevance("Installation IRVE borne de recharge véhicule électrique")
    assert result is True


def test_photovoltaique_est_pertinent():
    result, _ = classify_relevance("Centrale photovoltaïque autoconsommation 50 kWc")
    assert result is True


def test_decret_tertiaire_est_pertinent():
    result, _ = classify_relevance("Audit énergétique décret tertiaire OPERAT")
    assert result is True


def test_groupe_electrogene_est_pertinent():
    result, _ = classify_relevance("Location groupe électrogène continuité d'énergie")
    assert result is True


def test_nf_c_15_100_est_pertinent():
    result, _ = classify_relevance("Mise aux normes électriques NF C 15-100")
    assert result is True


def test_fibre_optique_est_pertinent():
    result, _ = classify_relevance("Déploiement fibre optique réseau informatique")
    assert result is True


def test_acteur_local_shlmr_est_pertinent():
    """SHLMR dans le texte + mot construction → potentiel SSI implicite."""
    result, tags = classify_relevance("Construction logements sociaux SHLMR Saint-Denis Réunion")
    assert result is True


def test_relamping_est_pertinent():
    result, _ = classify_relevance("Relamping éclairage LED intérieur bâtiment")
    assert result is True


# ── Suppression Mayotte du filtre géographique ───────────────────────────────

def test_mayotte_seul_ne_declenche_plus():
    """Un texte mentionnant uniquement Mayotte + construction ne doit plus matcher."""
    result, _ = classify_relevance("Construction logements Mamoudzou Mayotte département 976")
    assert result is False


def test_reunion_seule_declenche_toujours():
    """Un texte mentionnant La Réunion + construction doit toujours matcher."""
    result, _ = classify_relevance("Construction école Saint-Denis La Réunion")
    assert result is True


def test_974_declenche_toujours():
    result, _ = classify_relevance("Travaux extension hôpital 974")
    assert result is True


# ── Secteurs historiques DEF OI toujours actifs ───────────────────────────────

def test_ssi_toujours_pertinent():
    result, _ = classify_relevance("Système de sécurité incendie SSI catégorie A")
    assert result is True


def test_videosurveillance_toujours_pertinent():
    result, _ = classify_relevance("Installation vidéosurveillance CCTV parking")
    assert result is True
