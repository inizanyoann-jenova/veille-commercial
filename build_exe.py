"""
Script de build PyInstaller pour ATEXIA Veille.
Exécuter depuis la racine du projet :
    python build_exe.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST = os.path.join(ROOT, "frontend", "dist")
DIST_NAME = "atexia_veille"


def check_frontend_built():
    if not os.path.isdir(FRONTEND_DIST):
        print("frontend/dist/ introuvable. Lancez d'abord : cd frontend && npm run build")
        sys.exit(1)
    print("frontend/dist/ trouve")


def run_pyinstaller():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--name", DIST_NAME,
        "--add-data", f"{FRONTEND_DIST}{os.pathsep}frontend/dist",
        "--add-data", f"{ROOT}{os.pathsep}.",
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "apscheduler",
        "--hidden-import", "sqlalchemy.dialects.sqlite",
        "--hidden-import", "mistralai",
        "--collect-all", "playwright",
        "atexia_launcher.py",
    ]
    print("Lancement PyInstaller...")
    subprocess.run(cmd, check=True, cwd=ROOT)
    print(f"\nBuild termine -> dist/{DIST_NAME}/")


if __name__ == "__main__":
    check_frontend_built()
    run_pyinstaller()
