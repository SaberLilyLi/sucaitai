#Requires -Version 5.1
$ErrorActionPreference = "Stop"

$DesktopDir = $PSScriptRoot
$SkillRoot = Split-Path $DesktopDir -Parent
$Frontend = Join-Path $SkillRoot "frontend"
$Server = Join-Path $SkillRoot "server"
$DistOut = Join-Path $DesktopDir "dist"
$PackageName = [char]0x7D20 + [char]0x6750 + [char]0x53F0  # su cai tai
$PackageDir = Join-Path $DistOut $PackageName
$ServerEnv = Join-Path $Server ".env"
$TemplateEnv = Join-Path $DesktopDir ".env.template"
$SpecFile = Join-Path $DesktopDir "sucaitai.spec"
$ReadmeSrc = Join-Path $DesktopDir "README_USER.txt"

Write-Host "==> Skill root: $SkillRoot"

Write-Host "==> Building frontend..."
Push-Location $Frontend
try {
  if (-not (Test-Path "node_modules")) {
    npm ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci failed" }
  }
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "npm run build failed" }
} finally {
  Pop-Location
}

$IndexHtml = Join-Path $Frontend "dist\index.html"
if (-not (Test-Path $IndexHtml)) {
  throw "Frontend build failed: missing dist/index.html"
}

Write-Host "==> Ensuring PyInstaller..."
python -m pip install -q "pyinstaller>=6.0" -r (Join-Path $Server "requirements.txt")

Write-Host "==> Running PyInstaller..."
if (Test-Path $DistOut) {
  Remove-Item -Recurse -Force $DistOut
}
Push-Location $DesktopDir
try {
  python -m PyInstaller --noconfirm --clean $SpecFile
} finally {
  Pop-Location
}

$ExePath = Join-Path $PackageDir ($PackageName + ".exe")
if (-not (Test-Path $ExePath)) {
  throw "PyInstaller failed: exe not found in $PackageDir"
}

$dataDir = Join-Path $PackageDir "data"
New-Item -ItemType Directory -Force -Path (Join-Path $dataDir "product_media") | Out-Null
if (Test-Path $ReadmeSrc) {
  Copy-Item -Force $ReadmeSrc (Join-Path $PackageDir "README.txt")
}

$destEnv = Join-Path $PackageDir ".env"
if (Test-Path $ServerEnv) {
  Copy-Item -Force $ServerEnv $destEnv
  Write-Host "==> Copied server/.env into package"
} else {
  Copy-Item -Force $TemplateEnv $destEnv
  Write-Host "==> WARNING: server/.env missing; used template"
}

Write-Host ""
Write-Host "Build OK:"
Write-Host $PackageDir
Write-Host "Zip this folder and send to customer."
