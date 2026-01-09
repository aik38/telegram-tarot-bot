$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

$env:DOTENV_FILE = ".env.arisa"

& "$PSScriptRoot\windows_bootstrap.ps1" -DotenvFile $env:DOTENV_FILE
