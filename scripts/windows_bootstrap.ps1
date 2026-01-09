Param(
    [string]$DotenvFile
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $DotenvFile) {
    $DotenvFile = $env:DOTENV_FILE
}
if (-not $DotenvFile) {
    $DotenvFile = ".env"
}
$env:DOTENV_FILE = $DotenvFile

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment in .venv..."
    python -m venv .venv
}

$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found at $PythonExe"
}

Write-Host "Upgrading pip/setuptools/wheel..."
& $PythonExe -m pip install -U pip setuptools wheel

if (Test-Path "requirements.txt") {
    Write-Host "Installing dependencies from requirements.txt..."
    & $PythonExe -m pip install -r "requirements.txt"
} elseif (Test-Path "requirements") {
    Write-Host "Installing dependencies from requirements..."
    & $PythonExe -m pip install -r "requirements"
}

Write-Host "Starting Telegram bot with DOTENV_FILE=$DotenvFile"
& $PythonExe -m bot.main
