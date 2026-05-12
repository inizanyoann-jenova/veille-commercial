import os
import streamlit as st
from dotenv import load_dotenv
from credential_manager import CredentialManager
from database import init_db

load_dotenv()
init_db()

st.set_page_config(page_title="Paramètres — DEF OI", page_icon="⚙️", layout="wide")
st.title("⚙️ Paramètres")

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

# ── Section identifiants ──────────────────────────────────────────────────────
st.header("🔐 Identifiants des sources")
st.caption("Les mots de passe sont chiffrés en base de données. Les variables `.env` ont la priorité.")

configured = {c["site"]: c for c in CredentialManager.list_configured()}

for site_key, (site_label, category) in _SITE_LABELS.items():
    cred = configured.get(site_key)
    icon = "✅" if cred else "⬜"
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
                        try:
                            from playwright.sync_api import sync_playwright
                            from playwright_base import login
                            _TEST_URLS = {
                                "marches_securises": ("https://www.marches-securises.fr/entreprise/?page=connexion",
                                                      {"email": "input[name='login']", "password": "input[name='pass']", "submit": "input[type='submit']"}),
                                "instao":            ("https://www.instao.fr/connexion",
                                                      {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                                "tendersgo":         ("https://app.tendersgo.com/login",
                                                      {"email": "input[type='email']", "password": "input[type='password']", "submit": "button[type='submit']"}),
                            }
                            if site_key in _TEST_URLS:
                                url, selectors = _TEST_URLS[site_key]
                                with sync_playwright() as pw:
                                    browser = pw.chromium.launch(headless=True)
                                    page = browser.new_page()
                                    ok = login(page, url, new_email or cred["email"], new_pwd or "", selectors)
                                    browser.close()
                                if ok:
                                    st.success("✅ Connexion réussie")
                                else:
                                    st.error("❌ Connexion échouée — vérifiez vos identifiants")
                            else:
                                st.info("Test de connexion non disponible pour cette source (accès public).")
                        except Exception as e:
                            st.error(f"Erreur : {e}")

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
