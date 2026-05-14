import os
import streamlit as st
from dotenv import load_dotenv
from credential_manager import CredentialManager
from database import init_db

load_dotenv()
init_db()

st.set_page_config(page_title="Paramètres — DEF OI", page_icon="⚙️", layout="wide")
st.title("⚙️ Paramètres")

# ── Section clé API Claude ────────────────────────────────────────────────────
st.header("🤖 Intelligence Artificielle — Clé API Claude")
st.caption("Claude analyse les appels d'offres et produit des scores de pertinence enrichis (70 % IA + 30 % règles métier).")

current_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
_key_ok = bool(current_key and not current_key.startswith("sk-ant-...") and len(current_key) > 20)

if _key_ok:
    st.success(f"✅ Clé API Claude configurée (`{current_key[:16]}…`)")
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
                            model="claude-haiku-4-5",
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
from source_registry import Source as _SrcCred

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
            st.success(f"Configuré via `.env` — email : `{cred['email']}`")
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
                                        [_sys.executable, worker, payload],
                                        capture_output=True, text=True, timeout=60,
                                    )
                                    if proc.returncode != 0 and not proc.stdout.strip():
                                        st.error(f"❌ Erreur du worker Playwright :\n{proc.stderr[:500]}")
                                    else:
                                        diag = json.loads(proc.stdout)
                                        if diag.get("ok"):
                                            st.success(f"✅ Connexion réussie — redirigé vers `{diag.get('url_finale', '—')}`")
                                            _src_name = _SITE_TO_SOURCE_NAME.get(site_key)
                                            if _src_name:
                                                _db_val = _SL_cred()
                                                try:
                                                    _src = _db_val.query(_SrcCred).filter(_SrcCred.name == _src_name).first()
                                                    if _src:
                                                        _val3(_db_val, _src.id)
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
                                    st.error("❌ Timeout — la page de connexion n'a pas répondu en 60 secondes.")

# ── Section sources automatiques (HTTP ping) ──────────────────────────────────
st.markdown("---")
st.header("📡 Sources automatiques")
st.caption("Un test HTTP vérifie que chaque source est accessible. Valider une source la fait apparaître dans la sidebar de collecte.")

import requests as _req
from database import SessionLocal as _SL3
from source_registry import Source as _Src3, validate_source as _val3

_db_auto = _SL3()
try:
    _auto_sources = (
        _db_auto.query(_Src3)
        .filter(_Src3.is_manual == False)
        .order_by(_Src3.display_order, _Src3.name)
        .all()
    )
finally:
    _db_auto.close()

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
                        _db_v3 = _SL3()
                        try:
                            _val3(_db_v3, _s.id)
                        finally:
                            _db_v3.close()
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
    st.warning("⚠️ Attention : régénérer la clé rendra illisibles tous les mots de passe stockés en base. Vous devrez les ressaisir.")
    if st.checkbox("Je comprends, procéder quand même"):
        from cryptography.fernet import Fernet
        from dotenv import set_key
        new_key = Fernet.generate_key().decode()
        set_key(".env", "CREDENTIAL_KEY", new_key)
        os.environ["CREDENTIAL_KEY"] = new_key
        st.success("Nouvelle clé générée et sauvegardée dans `.env`. Relancez l'application.")

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
