import os
import streamlit as st
from dotenv import load_dotenv
from credential_manager import CredentialManager
from database import init_db
from database import SessionLocal as _SL_src
from source_registry import Source as _SrcModel, toggle_enabled as _toggle_enabled

load_dotenv()

@st.cache_resource
def _ensure_db_init():
    init_db()

_ensure_db_init()

st.set_page_config(page_title="Paramètres — DEF OI", page_icon="⚙️", layout="wide")
st.title("⚙️ Paramètres")

# ── Section sources à collecter ───────────────────────────────────────────────
st.header("⚡ Sources à collecter")
st.caption("Activez ou désactivez les sources prises en compte lors du lancement de la collecte.")

_db_src_p = _SL_src()
try:
    _all_sources_p = _db_src_p.query(_SrcModel).order_by(_SrcModel.display_order).all()
finally:
    _db_src_p.close()

_CAT_ICONS = {"Public": "📋 Public", "Privé": "🏗️ Privé", "International": "🌍 International"}
for _cat in ["Public", "Privé", "International"]:
    _cat_src = [s for s in _all_sources_p if s.category == _cat]
    if not _cat_src:
        continue
    st.subheader(_CAT_ICONS[_cat])
    for _s in _cat_src:
        _col_toggle, _col_label = st.columns([1, 9])
        with _col_toggle:
            _new_enabled = st.toggle(
                "Activée",
                value=bool(_s.enabled),
                key=f"src_enabled_{_s.id}",
                label_visibility="collapsed",
            )
        with _col_label:
            _status_icon = "✅" if _s.is_validated else ("📋" if _s.is_manual else "⚠️")
            st.markdown(f"{_status_icon} **{_s.name}**")
        if _new_enabled != bool(_s.enabled):
            _db_tog = _SL_src()
            try:
                _toggle_enabled(_db_tog, _s.id)
            finally:
                _db_tog.close()
            _action = "activée" if _new_enabled else "désactivée"
            st.toast(f"Source '{_s.name}' {_action} ✓")
            st.rerun()  # obligatoire — _s est stale après toggle

st.markdown("---")

# ── Section clé API Claude ────────────────────────────────────────────────────
st.header("🤖 Intelligence Artificielle — Clé API Claude")
st.caption("Claude analyse les appels d'offres et produit des scores de pertinence enrichis (70 % IA + 30 % règles métier).")

current_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
_key_ok = bool(current_key and not current_key.startswith("sk-ant-...") and len(current_key) > 20)

if _key_ok:
    st.success(f"✅ Clé API Claude configurée (`{current_key[:8]}…{'*' * 8}`)")
else:
    st.warning("⚠️ Clé API Claude non configurée — l'analyse IA tourne en mode local uniquement (règles métier).")

with st.expander(
    "🔑 Configurer / modifier la clé API Claude",
    expanded=not _key_ok,
):
    st.markdown("""
**Comment obtenir votre clé API ?**

1. Ouvrez [console.anthropic.com](https://console.anthropic.com) dans votre navigateur
2. Connectez-vous avec le compte DEF OI (ou créez un compte si besoin)
3. Dans le menu de gauche, cliquez **API Keys**
4. Cliquez **Create Key**, donnez-lui un nom (ex : "DEF OI Veille")
5. Copiez la clé affichée — elle commence par `sk-ant-api03-…`
   ⚠️ Cette clé n'est affichée **qu'une seule fois** — copiez-la immédiatement

Collez-la ci-dessous puis cliquez **Enregistrer**.
""")

    new_key = st.text_input(
        "Clé API Anthropic",
        type="password",
        placeholder="sk-ant-api03-…",
        key="anthropic_api_key_input",
        help="La clé doit commencer par sk-ant-",
    )

    col_save, col_test, col_spacer = st.columns([2, 2, 4])
    with col_save:
        if st.button("💾 Enregistrer la clé", key="save_anthropic_key", type="primary"):
            key_to_save = new_key.strip()
            if key_to_save.startswith("sk-ant-") and len(key_to_save) > 20:
                from dotenv import set_key as _set_key
                _set_key(".env", "ANTHROPIC_API_KEY", key_to_save)
                os.environ["ANTHROPIC_API_KEY"] = key_to_save
                # Réinitialiser le client pour prendre la nouvelle clé en compte immédiatement
                try:
                    import llm_analyzer
                    llm_analyzer._anthropic_client = None
                except Exception:
                    pass
                st.success("✅ Clé enregistrée — active immédiatement, sans redémarrage.")
                st.rerun()
            else:
                st.error("Format invalide — la clé doit commencer par `sk-ant-`")

    with col_test:
        if st.button("🧪 Tester la clé", key="test_anthropic_key"):
            key_to_test = new_key.strip() or current_key
            if not key_to_test or key_to_test == "sk-ant-...":
                st.error("Entrez d'abord une clé.")
            else:
                with st.spinner("Connexion à Claude en cours…"):
                    try:
                        import anthropic as _ant
                        _test_client = _ant.Anthropic(api_key=key_to_test)
                        _test_client.messages.create(
                            model="claude-opus-4-7",
                            max_tokens=5,
                            messages=[{"role": "user", "content": "OK"}],
                        )
                        st.success("✅ Clé valide — connexion à Claude réussie.")
                    except _ant.AuthenticationError:
                        st.error("❌ Clé invalide — vérifiez la valeur copiée depuis console.anthropic.com")
                    except Exception as exc:
                        st.error(f"Erreur inattendue : {exc}")

# ── Section identifiants ──────────────────────────────────────────────────────
_SITE_LABELS = {
    "vaao":               ("VAAO",                      "Public"),
    "marcheonline":       ("Marché Online",              "Public"),
    "dept974":            ("Marchés Publics — Dép. 974", "Public"),
    "nukema":             ("Nukema",                     "Public"),
    "marchespublicsinfo": ("Marchés Public Info",        "Public"),
    "marches_securises":  ("Marchés Sécurisés",          "Privé"),
    "instao":             ("Instao",                     "Privé"),
    "tendersgo":          ("Tenders Go",                 "International"),
}

st.markdown("---")
st.header("🔐 Identifiants des sources")
st.caption("Les mots de passe sont chiffrés en base de données. Les variables `.env` ont la priorité.")

configured = {c["site"]: c for c in CredentialManager.list_configured()}

from database import SessionLocal as _SL_cred
from source_registry import Source as _SrcCred, validate_source as _validate_src, invalidate_source as _invalidate_src
import requests as _req

_SITE_TO_SOURCE_NAME = {
    "vaao":               "VAAO",
    "marcheonline":       "Marché Online",
    "dept974":            "Marchés Publics — Dép. 974",
    "nukema":             "Nukema",
    "marchespublicsinfo": "Marchés Public Info",
    "marches_securises":  "Marchés Sécurisés",
    "instao":             "Instao",
    "tendersgo":          "Tenders Go",
}

_db_cred = _SL_cred()
try:
    _sources_by_name = {s.name: s for s in _db_cred.query(_SrcCred).all()}
finally:
    _db_cred.close()

for site_key, (site_label, category) in _SITE_LABELS.items():
    cred = configured.get(site_key)
    _src_obj = _sources_by_name.get(_SITE_TO_SOURCE_NAME.get(site_key, ""))
    _is_validated = _src_obj.is_validated if _src_obj else False
    if cred and _is_validated:
        icon = "✅"
    elif cred:
        icon = "🔌"
    else:
        icon = "⬜"
    with st.expander(f"{icon} {site_label} — {category}"):
        if cred and cred.get("has_env_override"):
            _em = cred["email"]
            _em_masked = _em[:3] + "…" + _em[_em.find("@"):] if "@" in _em and len(_em) > 6 else "***"
            st.success(f"Configuré via `.env` — email : `{_em_masked}`")
            st.info("Pour modifier, éditez le fichier `.env` et relancez l'application.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                new_email = st.text_input(
                    "Email / Identifiant",
                    value=cred["email"] if cred else "",
                    key=f"email_{site_key}",
                )
            with col2:
                new_pwd = st.text_input(
                    "Mot de passe",
                    type="password",
                    placeholder="••••••••" if cred else "",
                    key=f"pwd_{site_key}",
                )
            btn1, btn2, btn3 = st.columns([2, 2, 4])
            with btn1:
                if st.button("💾 Enregistrer", key=f"save_{site_key}"):
                    if new_email and new_pwd:
                        CredentialManager.save(site_key, new_email, new_pwd)
                        st.success("Identifiants enregistrés ✓")
                        st.rerun()
                    else:
                        st.error("Email et mot de passe requis")
            with btn2:
                if cred and st.button("🗑️ Supprimer", key=f"del_{site_key}"):
                    CredentialManager.delete(site_key)
                    if _src_obj:
                        _db_inv = _SL_cred()
                        try:
                            _invalidate_src(_db_inv, _src_obj.id)
                        finally:
                            _db_inv.close()
                    st.rerun()
            with btn3:
                if cred and st.button("🔌 Tester la connexion", key=f"test_{site_key}"):
                    with st.spinner("Test en cours…"):
                        _TEST_URLS = {
                            "marcheonline":      ("https://www.marchesonline.com/connexion",
                                                  {"email": "#email-input", "password": "input[type='password'].modal_connexion_input", "submit": "button.primary-dark-btn"}),
                            "nukema":            ("https://www.actu.nukema.com/connexion",
                                                  {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                            "marches_securises": ("https://www.marches-securises.fr/entreprise/?page=connexion",
                                                  {"email": "input[name='login']", "password": "input[name='pass']", "submit": "input[type='submit']"}),
                            "instao":            ("https://www.instao.fr/connexion",
                                                  {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                            "tendersgo":         ("https://app.tendersgo.com/login",
                                                  {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                        }
                        if site_key not in _TEST_URLS:
                            st.info("Test de connexion non disponible pour cette source (accès public).")
                        else:
                            import subprocess, json, sys as _sys, os as _os
                            url, selectors = _TEST_URLS[site_key]
                            email_to_test = new_email or cred["email"]
                            if new_pwd:
                                pwd_to_test = new_pwd
                            else:
                                stored = CredentialManager.get(site_key)
                                pwd_to_test = stored[1] if stored else ""
                            if not pwd_to_test:
                                st.error("Mot de passe introuvable — enregistrez-le d'abord.")
                            else:
                                worker = _os.path.join(
                                    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                    "_test_login_worker.py",
                                )
                                payload = json.dumps({
                                    "url": url,
                                    "selectors": selectors,
                                    "email": email_to_test,
                                    "password": pwd_to_test,
                                })
                                try:
                                    proc = subprocess.run(
                                        [_sys.executable, worker],
                                        input=payload,
                                        capture_output=True, text=True, timeout=15,
                                    )
                                    if proc.returncode != 0 and not proc.stdout.strip():
                                        st.error("❌ Erreur du worker Playwright — vérifiez les logs.")
                                    else:
                                        try:
                                            diag = json.loads(proc.stdout)
                                        except Exception:
                                            st.error("❌ Réponse inattendue du worker — vérifiez les logs.")
                                            raise
                                        if diag.get("ok"):
                                            st.success(f"✅ Connexion réussie — redirigé vers `{diag.get('url_finale', '—')}`")
                                            _src_name = _SITE_TO_SOURCE_NAME.get(site_key)
                                            if _src_name:
                                                _db_val = _SL_cred()
                                                try:
                                                    _src = _db_val.query(_SrcCred).filter(_SrcCred.name == _src_name).first()
                                                    if _src:
                                                        _validate_src(_db_val, _src.id)
                                                finally:
                                                    _db_val.close()
                                            st.rerun()
                                        elif "erreur_worker" in diag:
                                            st.error(f"❌ Erreur : {diag['erreur_worker']}")
                                            st.code(diag.get("traceback", ""), language="python")
                                        elif "champ_manquant" in diag:
                                            st.error(f"❌ Champ introuvable sur la page : {diag['champ_manquant']}")
                                            st.caption(f"URL : {diag.get('url_initiale', '—')}")
                                            if diag.get("champs_page"):
                                                st.info("Champs détectés sur la page :\n" + "\n".join(diag["champs_page"]))
                                        elif "erreur_page" in diag:
                                            st.error(f"❌ Identifiants incorrects — message du site : *{diag['erreur_page']}*")
                                        elif diag.get("no_redirect"):
                                            st.warning(f"⚠️ Pas de redirection après login (URL : `{diag.get('url_finale', '—')}`). Possible CAPTCHA ou identifiants incorrects.")
                                        else:
                                            st.error("❌ Connexion échouée — vérifiez vos identifiants.")
                                except subprocess.TimeoutExpired:
                                    st.error("❌ Timeout — la page de connexion n'a pas répondu en 15 secondes.")

# ── Section sources automatiques (HTTP ping) ──────────────────────────────────
st.markdown("---")
st.header("📡 Sources automatiques")
st.caption("Un test HTTP vérifie que chaque source est accessible. Valider une source la fait apparaître dans la sidebar de collecte.")

_db_auto = _SL_cred()
try:
    _auto_sources = (
        _db_auto.query(_SrcCred)
        .filter(_SrcCred.is_manual == False)
        .order_by(_SrcCred.display_order, _SrcCred.name)
        .all()
    )
finally:
    _db_auto.close()

_col_all, _ = st.columns([3, 5])
with _col_all:
    if st.button("🔌 Tout tester", key="ping_all", help="Teste toutes les sources automatiques en une fois"):
        _nb_ok, _nb_fail = 0, 0
        _db_batch = _SL_cred()
        try:
            with st.spinner("Test en cours…"):
                for _sa in _auto_sources:
                    try:
                        _r = _req.get(_sa.url, timeout=8, allow_redirects=True,
                                      headers={"User-Agent": "Mozilla/5.0 DEF-OI-Checker"})
                        if _r.status_code < 400 and len(_r.content) > 200:
                            _validate_src(_db_batch, _sa.id)
                            _nb_ok += 1
                        else:
                            _nb_fail += 1
                    except Exception:
                        _nb_fail += 1
        finally:
            _db_batch.close()
        st.success(f"✅ {_nb_ok} source(s) validée(s) — ❌ {_nb_fail} inaccessible(s)")
        st.rerun()

for _s in _auto_sources:
    _badge = "✅" if _s.is_validated else "⬜"
    _col_badge, _col_name, _col_btn = st.columns([1, 6, 2])
    with _col_badge:
        st.markdown(_badge)
    with _col_name:
        st.markdown(f"**{_s.name}**")
        st.caption(_s.url)
    with _col_btn:
        if st.button("🔌 Tester", key=f"ping_{_s.id}"):
            with st.spinner(f"Test {_s.name}…"):
                try:
                    _resp = _req.get(_s.url, timeout=8, allow_redirects=True,
                                     headers={"User-Agent": "Mozilla/5.0 DEF-OI-Checker"})
                    if _resp.status_code < 400:
                        if len(_resp.content) < 200:
                            st.warning(f"⚠️ HTTP {_resp.status_code} mais réponse vide — possible CAPTCHA ou redirection. Source non validée.")
                        else:
                            _db_v = _SL_cred()
                            try:
                                _validate_src(_db_v, _s.id)
                            finally:
                                _db_v.close()
                            st.success(f"✅ Accessible (HTTP {_resp.status_code})")
                            st.rerun()
                    else:
                        st.error(f"❌ HTTP {_resp.status_code}")
                except Exception as _exc:
                    st.error(f"❌ Inaccessible — {_exc}")

# ── Section sécurité ──────────────────────────────────────────────────────────
st.markdown("---")
st.header("🔑 Sécurité")

key_present = bool(os.getenv("CREDENTIAL_KEY"))
if key_present:
    st.success("Clé de chiffrement active — présente dans `.env`")
else:
    st.warning("Clé de chiffrement absente — elle sera générée automatiquement au 1er enregistrement d'identifiant.")

if st.button("🔄 Régénérer la clé de chiffrement"):
    st.session_state["_regen_key_confirm"] = True

if st.session_state.get("_regen_key_confirm"):
    st.warning("⚠️ Attention : régénérer la clé rendra illisibles tous les mots de passe stockés en base. Vous devrez les ressaisir.")
    _col_ok, _col_cancel = st.columns(2)
    with _col_ok:
        if st.button("✅ Confirmer la régénération", type="primary", key="regen_key_confirm_btn"):
            from cryptography.fernet import Fernet
            from dotenv import set_key
            _new_fernet_key = Fernet.generate_key().decode()
            set_key(".env", "CREDENTIAL_KEY", _new_fernet_key)
            os.environ["CREDENTIAL_KEY"] = _new_fernet_key
            st.session_state.pop("_regen_key_confirm", None)
            st.success("Nouvelle clé générée et sauvegardée dans `.env`. Relancez l'application.")
    with _col_cancel:
        if st.button("❌ Annuler", key="regen_key_cancel_btn"):
            st.session_state.pop("_regen_key_confirm", None)
            st.rerun()

# ── Blacklist ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.header("🚫 Articles ignorés (blacklist)")
st.caption("Ces éléments ont été supprimés et ne réapparaîtront plus après une collecte. Vous pouvez les réactiver ici.")

from database import SessionLocal as _SL
from models import Tender as _Tender

_db_bl = _SL()
try:
    _blacklisted = (
        _db_bl.query(_Tender)
        .filter(_Tender.is_blacklisted == True)
        .order_by(_Tender.title)
        .all()
    )
finally:
    _db_bl.close()

if not _blacklisted:
    st.info("Aucun élément blacklisté.")
else:
    st.caption(f"{len(_blacklisted)} élément(s) ignoré(s)")
    for item in _blacklisted:
        col_t, col_s, col_btn = st.columns([6, 2, 1])
        with col_t:
            st.markdown(f"**{item.title or item.id}**")
        with col_s:
            st.caption(item.secteur or "Public")
        with col_btn:
            if st.button("↩️ Réactiver", key=f"unbl_{item.id}"):
                _db_r = _SL()
                try:
                    t = _db_r.query(_Tender).filter(_Tender.id == item.id).first()
                    if t:
                        t.is_blacklisted = False
                        _db_r.commit()
                finally:
                    _db_r.close()
                st.rerun()

# ── Section maintenance ───────────────────────────────────────────────────────
st.markdown("---")
st.header("🧹 Maintenance")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("🗑️ Vider le cache Streamlit"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("Cache vidé ✓")
with col_b:
    if st.button("🔄 Réinitialiser les sources par défaut"):
        st.warning("Cette action ne supprime pas les sources existantes — elle ajoute les sources manquantes.")
        from database import SessionLocal
        from source_registry import init_sources
        db = SessionLocal()
        try:
            init_sources(db)
            st.success("Sources vérifiées et initialisées ✓")
        finally:
            db.close()

st.markdown("---")
st.header("📊 Historique de collecte")
st.caption("Les derniers runs par source. Mis à jour après chaque collecte.")

from database import SessionLocal as _SL_hist
from models import ScraperRun as _SR
_db_hist = _SL_hist()
try:
    _all_runs = (
        _db_hist.query(_SR)
        .order_by(_SR.started_at.desc())
        .limit(100)
        .all()
    )
finally:
    _db_hist.close()

if not _all_runs:
    st.info("Aucune collecte enregistrée. Lancez une collecte depuis la page principale.")
else:
    import pandas as _pd_hist
    from datetime import datetime as _dt_hist, timezone as _tz_hist
    _rows_hist = []
    for r in _all_runs:
        if not r.started_at:
            continue
        _ago = _dt_hist.now(_tz_hist.utc).replace(tzinfo=None) - r.started_at.replace(tzinfo=None)
        _d = _ago.days
        _h = int(_ago.total_seconds() // 3600)
        _m = int(_ago.total_seconds() // 60)
        _rows_hist.append({
            "Source": r.source_name,
            "Il y a": f"{_d}j" if _d >= 1 else (f"{_h}h" if _h >= 1 else f"{_m}min"),
            "Nouveaux": r.nb_new,
            "Statut": "✅" if r.status == "ok" else ("⚠️" if r.status == "error" else "🔄"),
            "Erreur": r.error or "",
        })
    st.dataframe(
        _pd_hist.DataFrame(_rows_hist),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Source": st.column_config.TextColumn(width="medium"),
            "Il y a": st.column_config.TextColumn(width="small"),
            "Nouveaux": st.column_config.NumberColumn(width="small"),
            "Statut": st.column_config.TextColumn(width="small"),
            "Erreur": st.column_config.TextColumn(width="large"),
        },
    )

# ── Détection de doublons ─────────────────────────────────────────────────────

st.header("🔍 Doublons détectés")
st.caption("Marchés collectés depuis plusieurs sources avec un titre similaire (≥ 80 %) et la même deadline (±3 jours).")

from database import detect_duplicates as _detect_dups, SessionLocal as _SL_dd
from models import Tender as _Tender_dd, DuplicateCandidate as _DC
from sqlalchemy import or_ as _or_dd, and_ as _and_dd


def _get_unresolved_pairs():
    _db = _SL_dd()
    try:
        pairs = _db.query(_DC).filter(_DC.resolved == False).all()
        result = []
        for p in pairs:
            a = _db.query(_Tender_dd).filter(_Tender_dd.id == p.tender_id_a).first()
            b = _db.query(_Tender_dd).filter(_Tender_dd.id == p.tender_id_b).first()
            if a and b:
                result.append((p, a, b))
        return result
    finally:
        _db.close()


def _merge_pair(keep_id: str, archive_id: str, pair_id: int):
    _db = _SL_dd()
    try:
        archive = _db.query(_Tender_dd).filter(_Tender_dd.id == archive_id).first()
        if archive:
            archive.is_blacklisted = True
        pair = _db.query(_DC).filter(_DC.id == pair_id).first()
        if pair:
            pair.resolved = True
        _db.commit()
    finally:
        _db.close()
    st.cache_data.clear()
    st.rerun()


def _ignore_pair(pair_id: int):
    _db = _SL_dd()
    try:
        pair = _db.query(_DC).filter(_DC.id == pair_id).first()
        if pair:
            pair.resolved = True
        _db.commit()
    finally:
        _db.close()
    st.cache_data.clear()
    st.rerun()


if st.button("🔍 Détecter les doublons", key="run_detect_duplicates"):
    with st.spinner("Analyse en cours…"):
        _db2 = _SL_dd()
        try:
            nb = _detect_dups(_db2)
        finally:
            _db2.close()
    if nb:
        st.success(f"{nb} nouvelle(s) paire(s) détectée(s).")
    else:
        st.info("Aucun nouveau doublon détecté.")

_pairs = _get_unresolved_pairs()

if not _pairs:
    st.caption("Aucun doublon à traiter.")
else:
    st.markdown(f"**{len(_pairs)} paire(s) à examiner**")
    for _pair, _a, _b in _pairs:
        with st.expander(f"Paire #{_pair.id} — similarité {_pair.similarity_score:.0%}", expanded=True):
            _recommended = _a if _a.relevance_score >= _b.relevance_score else _b
            _other = _b if _recommended.id == _a.id else _a

            _ca, _cb = st.columns(2)
            for _col, _tender, _label in [
                (_ca, _recommended, "✅ Recommandé à conserver"),
                (_cb, _other, ""),
            ]:
                with _col:
                    if _label:
                        st.success(_label)
                    st.markdown(f"**{_tender.title}**")
                    st.caption(f"Source : {_tender.source} · Score : {_tender.relevance_score}")
                    if _tender.deadline:
                        st.caption(f"Deadline : {_tender.deadline.strftime('%d/%m/%Y')}")

            _c1, _c2, _c3 = st.columns(3)
            if _c1.button(f"Garder {_a.source[:12]} — archiver {_b.source[:12]}", key=f"keep_a_{_pair.id}"):
                _merge_pair(keep_id=_a.id, archive_id=_b.id, pair_id=_pair.id)
            if _c2.button(f"Garder {_b.source[:12]} — archiver {_a.source[:12]}", key=f"keep_b_{_pair.id}"):
                _merge_pair(keep_id=_b.id, archive_id=_a.id, pair_id=_pair.id)
            if _c3.button("Ignorer", key=f"ignore_{_pair.id}"):
                _ignore_pair(_pair.id)
