<#
.SYNOPSIS
    Build complet ATEXIA Veille — frontend + exe PyInstaller
.DESCRIPTION
    1. Installe les dependances npm et compile le frontend React
    2. Installe PyInstaller si absent
    3. Lance le build PyInstaller
#>

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "=== BUILD ATEXIA VEILLE ===" -ForegroundColor Cyan
Write-Host ""

Write-Host ">> Etape 1/3 : Build frontend React..." -ForegroundColor Yellow
Set-Location "$Root\frontend"
npm install --silent
npm run build
if (-not (Test-Path "$Root\frontend\dist\index.html")) {
    Write-Error "Echec du build frontend"
    exit 1
}
Write-Host "   Frontend build OK" -ForegroundColor Green
Set-Location $Root

Write-Host ""
Write-Host ">> Etape 2/3 : Verification PyInstaller..." -ForegroundColor Yellow
python -m pip install pyinstaller --quiet
Write-Host "   PyInstaller OK" -ForegroundColor Green

Write-Host ""
Write-Host ">> Etape 3/3 : Build PyInstaller (peut prendre 2-5 minutes)..." -ForegroundColor Yellow
python build_exe.py
if ($LASTEXITCODE -ne 0) {
    Write-Error "Echec PyInstaller"
    exit 1
}

Write-Host ""
Write-Host "=== BUILD TERMINE ===" -ForegroundColor Green
Write-Host ""
Write-Host "Executable : $Root\dist\atexia_veille\" -ForegroundColor Cyan
Write-Host "Double-cliquez sur dist\atexia_veille\atexia_veille.exe pour lancer." -ForegroundColor White
Write-Host ""
Write-Host "Note : Au premier lancement, Playwright telecharge Chromium (~130 Mo)" -ForegroundColor DarkYellow
Write-Host "       dans %APPDATA%\ATEXIA\playwright\" -ForegroundColor DarkYellow
