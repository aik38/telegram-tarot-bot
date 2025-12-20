Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repo = Join-Path $env:USERPROFILE "OneDrive\デスクトップ\telegram-tarot-bot"
Set-Location $repo

Write-Host "== git pull (rebase) ==" -ForegroundColor Cyan
git pull --rebase origin main

# venv python を優先
$venvPy = Join-Path $repo ".venv\Scripts\python.exe"

if (!(Test-Path $venvPy)) {
  Write-Host "== .venv not found. Creating venv ==" -ForegroundColor Yellow
  py -3.13 -m venv .venv
  $venvPy = Join-Path $repo ".venv\Scripts\python.exe"
}

# pytest がなければ入れる（requirements に入ってる前提）
try {
  & $venvPy -c "import pytest" | Out-Null
} catch {
  Write-Host "== Installing requirements (pytest missing) ==" -ForegroundColor Yellow
  & $venvPy -m pip install -r requirements.txt
}

Write-Host "== pytest ==" -ForegroundColor Cyan
& $venvPy -m pytest -q

# ローカル変更があればコミット＆プッシュ（安全運転）
$changes = git status --porcelain
if ($changes) {
  # Windows junk のみなら commit/push しない
  $filtered = $changes | Where-Object { $_ -notmatch '(Thumbs\.db|Desktop\.ini)$' }

  if ($filtered) {
    Write-Host "== Local changes detected. Commit & push ==" -ForegroundColor Yellow
    git add -A
    $msg = "Update from local ($(Get-Date -Format 'yyyy-MM-dd HH:mm'))"
    git commit -m $msg
    git push origin main
  }
  else {
    Write-Host "== Only Windows junk detected. Skip commit/push ==" -ForegroundColor Yellow
  }
} else {
  Write-Host "== No local changes. Skip commit/push ==" -ForegroundColor Green
}

Write-Host "Done." -ForegroundColor Green
pause
