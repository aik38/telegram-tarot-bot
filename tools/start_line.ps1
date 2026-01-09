$ErrorActionPreference="Stop"
$repo = Split-Path -Parent $PSScriptRoot   # tools -> repo
Set-Location $repo

if(Test-Path ".\.venv\Scripts\Activate.ps1"){ . .\.venv\Scripts\Activate.ps1 }

function Test-LineApiRunning {
  try {
    $r = Invoke-WebRequest "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 1
    return ($r.StatusCode -eq 200)
  } catch { return $false }
}

$has8000 = Test-LineApiRunning
$hasNgrok = @(Get-Process ngrok -ErrorAction SilentlyContinue).Count -gt 0

if(-not $has8000){
  Start-Process pwsh -ArgumentList @('-NoExit','-Command', "cd `"$repo`"; . .\.venv\Scripts\Activate.ps1; .\tools\run_line_api.ps1") | Out-Null
} else {
  Write-Host "LINE API is already running (http://127.0.0.1:8000/docs)."
}

if(-not $hasNgrok){
  Start-Process pwsh -ArgumentList @('-NoExit','-Command', "cd `"$repo`"; . .\.venv\Scripts\Activate.ps1; .\tools\run_ngrok.ps1") | Out-Null
} else {
  Write-Host "ngrok is already running (http://127.0.0.1:4040)."
}

Write-Host "Started. Check: http://127.0.0.1:8000/docs  /  http://127.0.0.1:4040"
