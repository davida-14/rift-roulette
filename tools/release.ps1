# Publish a new Rift Roulette version to GitHub Releases. Installed copies update themselves on next launch.
#
#   1. Bump "version" in app/package.json (for example 1.3.0 -> 1.3.1) and commit your changes.
#   2. Run from the project folder:   & .\tools\release.ps1
#      First time only, to create the GitHub repository:   & .\tools\release.ps1 -CreateRepo
#
# Uses your GitHub CLI sign-in; the token is only held in this window's environment while publishing.
param([switch]$CreateRepo)
$ErrorActionPreference = "Stop"
$gh = "C:\Program Files\GitHub CLI\gh.exe"
Set-Location (Split-Path -Parent $PSScriptRoot)

$version = (Get-Content app\package.json -Raw | ConvertFrom-Json).version
Write-Host "Releasing Rift Roulette $version" -ForegroundColor Yellow

python -I tools\assemble.py
if ($LASTEXITCODE -ne 0) { throw "Page build failed" }
$dirty = git status --porcelain
if ($dirty) { throw "You have uncommitted changes. Commit them first, then run this again." }

if ($CreateRepo) {
    & $gh repo create rift-roulette --public --source . --remote origin --description "Random League of Legends item builds for Summoner's Rift and ARAM"
    if ($LASTEXITCODE -ne 0) { throw "Could not create the GitHub repository" }
}
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw "git push failed" }

# Create the release (and its tag) up front, so the build only has to upload files into it.
# (Windows PowerShell treats gh's "release not found" message as an error, so relax that just for this check.)
$ErrorActionPreference = "Continue"
& $gh release view "v$version" *> $null
$releaseExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
if (-not $releaseExists) {
    & $gh release create "v$version" --title "Rift Roulette $version" --notes "Installed copies update themselves the next time they open." --target main
    if ($LASTEXITCODE -ne 0) { throw "Could not create the GitHub release" }
}

$env:GH_TOKEN = & $gh auth token
try {
    Push-Location app
    npm run release
    if ($LASTEXITCODE -ne 0) { throw "Build or upload failed" }
} finally {
    Pop-Location
    Remove-Item Env:GH_TOKEN -ErrorAction SilentlyContinue
}
Write-Host "Published $version. Friends get it the next time they open Rift Roulette." -ForegroundColor Green
