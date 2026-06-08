# Lance le backend FastAPI + le frontend React (Vite)
# Usage : .\start.ps1

$rootDir = $PSScriptRoot

Write-Host "=== ATEXIA - Lancement de l'application ===" -ForegroundColor Cyan

# Libérer le port 8000 si un ancien processus occupe déjà le port
$oldPid = (netstat -ano | Select-String ":8000 .*LISTENING" | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if ($oldPid) {
    Write-Host "  Port 8000 occupe (PID $oldPid) — arret en cours..." -ForegroundColor DarkYellow
    Stop-Process -Id ([int]$oldPid) -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 800
}

# Backend FastAPI
Write-Host "`n[1/2] Demarrage du backend FastAPI (port 8000)..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" `
    -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" `
    -WorkingDirectory "$rootDir\backend" `
    -PassThru -NoNewWindow

# Frontend Vite
Write-Host "[2/2] Demarrage du frontend React (Vite)..." -ForegroundColor Yellow
$frontend = Start-Process -FilePath "npm" `
    -ArgumentList "run", "dev" `
    -WorkingDirectory "$rootDir\frontend" `
    -PassThru -NoNewWindow

Write-Host "`n Application disponible sur : http://localhost:5173" -ForegroundColor Green
Write-Host " API disponible sur          : http://localhost:8000/docs" -ForegroundColor Green
Write-Host "`nAppuyez sur Ctrl+C pour arreter les deux processus..." -ForegroundColor DarkGray

try {
    Wait-Process -Id $backend.Id, $frontend.Id
} finally {
    Write-Host "`nArret des processus..." -ForegroundColor Red
    if (-not $backend.HasExited)  { Stop-Process -Id $backend.Id  -Force }
    if (-not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force }
}
