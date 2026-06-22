param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Creating virtual environment..."
    python -m venv ".venv"
}

if (-not $SkipInstall) {
    Write-Host "Installing dependencies..."
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r "requirements.txt"
}

$DataSeparator = ";"
if ($env:OS -ne "Windows_NT") {
    $DataSeparator = ":"
}

Write-Host "Building DesktopPet.exe..."
& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onefile `
    --name "DesktopPet" `
    --add-data "assets$DataSeparatorassets" `
    "main.py"

Write-Host ""
Write-Host "Done: $ProjectRoot\dist\DesktopPet.exe"
