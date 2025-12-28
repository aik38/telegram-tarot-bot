param (
    [string]$Port = "8000"
)

Set-Location (Join-Path $PSScriptRoot "..")

.\.venv\Scripts\Activate.ps1

python -m uvicorn api.main:app --host 0.0.0.0 --port $Port
