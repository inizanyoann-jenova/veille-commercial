@echo off
cd /d "%~dp0"
title DEF OI — Veille Marches

:: Vérifier que Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERREUR : Python n'est pas installe sur ce PC.
    echo.
    echo  Installez Python depuis : https://www.python.org/downloads/
    echo  Cochez bien "Add Python to PATH" pendant l'installation.
    echo.
    pause
    exit /b 1
)

:: Installer les dépendances si nécessaire
echo Verification des dependances...
pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo.
    echo  ERREUR lors de l'installation des dependances.
    echo  Verifiez votre connexion internet et relancez.
    echo.
    pause
    exit /b 1
)

:: Installer le navigateur Playwright (silencieux si déjà installé)
echo Installation du navigateur (premiere fois uniquement)...
playwright install chromium --quiet >nul 2>&1

:: Créer le fichier .env s'il n'existe pas
if not exist ".env" (
    copy ".env.example" ".env" >nul
)

:: Lancer l'application
echo.
echo  Lancement de DEF OI - Veille Marches...
echo  L'application va s'ouvrir dans votre navigateur.
echo  Pour fermer l'application, fermez cette fenetre.
echo.
python -m streamlit run app.py --server.headless false
pause
