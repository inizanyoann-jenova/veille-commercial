@echo off
title ATEXIA - Lancement application
echo === ATEXIA - Lancement de l'application ===
echo.

cd /d "%~dp0"

echo [1/2] Demarrage du backend FastAPI (port 8000)...
start "Backend FastAPI" cmd /k "cd /d "%~dp0backend" && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 2 /nobreak >nul

echo [2/2] Demarrage du frontend React (Vite)...
start "Frontend React" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo  Ouverture du navigateur dans 5 secondes...
timeout /t 5 /nobreak >nul
start "" "http://localhost:5173"

echo.
echo  Application : http://localhost:5173
echo  API Swagger : http://localhost:8000/docs
echo.
echo Fermez les deux fenetres de commande pour arreter.
pause
