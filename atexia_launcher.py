"""
Point d'entrée ATEXIA Veille — EXE PyInstaller.
Lance uvicorn sur localhost:8000 et ouvre le navigateur par défaut.
"""
import os
import sys
import threading
import time
import webbrowser

if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
else:
    _base = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, _base)

_appdata = os.path.join(os.environ.get("APPDATA", "."), "ATEXIA")
os.makedirs(_appdata, exist_ok=True)

os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(_appdata, "playwright"),
)

HOST = "127.0.0.1"
PORT = 8000
URL = f"http://{HOST}:{PORT}"


def _open_browser():
    time.sleep(2.5)
    webbrowser.open(URL)


if __name__ == "__main__":
    print(f"ATEXIA Veille — démarrage sur {URL}")
    threading.Thread(target=_open_browser, daemon=True).start()

    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )
