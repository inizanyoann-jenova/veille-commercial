"""
Worker isolé pour tester la connexion Playwright.
Lancé en sous-processus pour éviter le conflit asyncio / SelectorEventLoop sur Windows.
"""

import sys
import json
import asyncio

# Forcer ProactorEventLoop avant tout import Playwright
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def test_login(url: str, selectors: dict, email: str, password: str) -> dict:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(url, timeout=20000)
            page.wait_for_load_state("domcontentloaded", timeout=20000)
            initial_url = page.url

            # Attendre que les champs soient présents dans le DOM (gère les modales JS et le chargement async)
            for field in ("email", "password"):
                sel = selectors[field]
                try:
                    el = page.wait_for_selector(sel, timeout=10000, state="visible")
                except Exception:
                    el = None
                if not el:
                    inputs = page.query_selector_all("input, button, a[role='button']")
                    champs_trouves = []
                    for inp in inputs:
                        typ = inp.get_attribute("type") or ""
                        name = inp.get_attribute("name") or ""
                        id_ = inp.get_attribute("id") or ""
                        cls = inp.get_attribute("class") or ""
                        placeholder = inp.get_attribute("placeholder") or ""
                        tag = inp.evaluate("el => el.tagName.toLowerCase()")
                        champs_trouves.append(
                            f"<{tag} type='{typ}' name='{name}' id='{id_}' class='{cls[:40]}' placeholder='{placeholder[:30]}'>"
                        )
                    return {
                        "ok": False,
                        "champ_manquant": f"{field} → `{sel}`",
                        "url_initiale": initial_url,
                        "champs_page": champs_trouves,
                    }

            # force=True contourne les overlays qui interceptent les pointer events
            # et déclenche quand même onfocus (nécessaire pour les champs readonly-on-focus)
            page.click(selectors["email"], force=True)
            page.fill(selectors["email"], email)
            page.click(selectors["password"], force=True)
            page.fill(selectors["password"], password)

            # 1. Essayer un clic JS (contourne les overlays qui interceptent les pointer events)
            submit_sel = selectors.get("submit", "")
            clicked = False
            if submit_sel:
                try:
                    clicked = page.evaluate(
                        f"() => {{ const b = document.querySelector({repr(submit_sel)}); if (b) {{ b.click(); return true; }} return false; }}"
                    )
                except Exception:
                    pass
            # 2. Fallback : touche Entrée sur le champ mot de passe
            if not clicked:
                page.press(selectors["password"], "Enter")

            try:
                page.wait_for_load_state("networkidle", timeout=20000)
            except Exception:
                pass

            final_url = page.url
            if final_url != initial_url:
                return {"ok": True, "url_finale": final_url}

            # Attendre un court instant pour laisser les toasts/animations JS s'afficher
            try:
                page.wait_for_timeout(1500)
            except Exception:
                pass

            # Vérifier si un login AJAX a réussi (URL inchangée mais on est connecté)
            logged_in_sels = [
                "a[href*='deconnexion'], a[href*='logout'], a[href*='disconnect']",
                "[class*='deconnexion'], [class*='logout']",
                ".user-menu, .nav-user, .compte-menu, #nav-user-menu",
                "a[href*='mon-compte'], a[href*='my-account'], a[href*='profil']",
            ]
            for logged_sel in logged_in_sels:
                try:
                    if page.query_selector(logged_sel):
                        return {"ok": True, "url_finale": final_url, "ajax_login": True}
                except Exception:
                    pass

            err_sel = (
                ".error, .alert-danger, .alert-error, "
                ".login-error, .message-erreur, .erreur, "
                ".invalid-feedback, .form-error, "
                ".MooDialog, .MooDialogTitle, "
                ".toast-error, .toast.error, .notification-error, "
                "[class*='error-message'], [class*='login-error'], "
                ".alert:not(.alert-success), .flash-error"
            )
            err_texts = []
            for el in page.query_selector_all(err_sel)[:5]:
                try:
                    text = el.inner_text().strip()
                    if text and len(text) > 3:
                        err_texts.append(text[:150])
                except Exception:
                    pass
            if err_texts:
                return {
                    "ok": False,
                    "erreur_page": " | ".join(err_texts[:3]),
                    "url_finale": final_url,
                }

            page_title = ""
            try:
                page_title = page.title()
            except Exception:
                pass

            return {
                "ok": False,
                "no_redirect": True,
                "url_finale": final_url,
                "page_title": page_title,
            }
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        payload = json.loads(sys.stdin.read())
        result = test_login(
            payload["url"],
            payload["selectors"],
            payload["email"],
            payload["password"],
        )
        print(json.dumps(result))
        sys.exit(0)
    except Exception as exc:
        import traceback

        print(
            json.dumps(
                {
                    "ok": False,
                    "erreur_worker": str(exc),
                    "traceback": traceback.format_exc(),
                }
            )
        )
        sys.exit(1)
