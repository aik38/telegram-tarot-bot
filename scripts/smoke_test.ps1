Param(
    [string]$DotenvFile
)

$ErrorActionPreference = "Stop"

function Mask-Secret {
    param([string]$Value)
    if (-not $Value) {
        return "<not set>"
    }
    $len = $Value.Length
    if ($len -le 8) {
        return ("*" * $len)
    }
    $prefix = $Value.Substring(0, 4)
    $suffix = $Value.Substring($len - 4)
    return "$prefix...$suffix"
}

function Get-EnvDisplay {
    param([string]$Value)
    if (-not $Value) {
        return "<not set>"
    }
    return $Value
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $DotenvFile) {
    $DotenvFile = $env:DOTENV_FILE
}
if (-not $DotenvFile) {
    $DotenvFile = ".env"
}
$env:DOTENV_FILE = $DotenvFile

$PythonExe = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

Write-Host "Loading dotenv from: $DotenvFile"
& $PythonExe -c "from dotenv import load_dotenv; import os; path=os.getenv('DOTENV_FILE', '.env'); loaded=load_dotenv(path, override=False); print(f'DOTENV_FILE={path} loaded={loaded}')"

Write-Host "Environment status:"
Write-Host "  TELEGRAM_BOT_TOKEN: $(Mask-Secret $env:TELEGRAM_BOT_TOKEN)"
Write-Host "  OPENAI_API_KEY: $(Mask-Secret $env:OPENAI_API_KEY)"
Write-Host "  SQLITE_DB_PATH: $(Get-EnvDisplay $env:SQLITE_DB_PATH)"
Write-Host "  CHARACTER: $(Get-EnvDisplay $env:CHARACTER)"
Write-Host "  PAYWALL_ENABLED: $(Get-EnvDisplay $env:PAYWALL_ENABLED)"

Write-Host "aiogram version:"
& $PythonExe -c "import aiogram; print(aiogram.__version__)"

if (-not $env:TELEGRAM_BOT_TOKEN) {
    Write-Host "TELEGRAM_BOT_TOKEN is not set. Skipping Telegram API checks."
    exit 0
}

$BaseUrl = "https://api.telegram.org/bot$($env:TELEGRAM_BOT_TOKEN)"

Write-Host "Calling getMe..."
$me = Invoke-RestMethod -Method Get -Uri "$BaseUrl/getMe"
Write-Host "getMe ok: $($me.result.username)"

Write-Host "Calling getWebhookInfo..."
$webhook = Invoke-RestMethod -Method Get -Uri "$BaseUrl/getWebhookInfo"
Write-Host "getWebhookInfo ok: $($webhook.result.url)"
