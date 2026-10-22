<#
.SYNOPSIS
  Portable PostgreSQL 16 + PostGIS 3.6 for Windows, used when Docker is not
  available. Creates a self contained install under .local\ and exposes it on
  127.0.0.1:5432 with the same schema, PostGIS extension and GiST indexes as
  the docker-compose service.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File scripts\local-db.ps1 setup
  powershell -ExecutionPolicy Bypass -File scripts\local-db.ps1 start
#>
param(
  [ValidateSet("setup", "start", "stop", "status")]
  [string]$Action = "status",
  [int]$Port = 5432
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Local = Join-Path $Root ".local"
$PgRoot = Join-Path $Local "pgsql"
$PgData = Join-Path $Local "pgdata"
$PgZip = Join-Path $Local "pg16-binaries.zip"
$PostgisZip = Join-Path $Local "postgis-pg16.zip"
$PgUrl = "https://get.enterprisedb.com/postgresql/postgresql-16.15-1-windows-x64-binaries.zip"
$PostgisUrl = "https://download.osgeo.org/postgis/windows/pg16/postgis-bundle-pg16-3.6.2x64.zip"
$Curl = Join-Path $env:SystemRoot "System32\curl.exe"

function Setup {
  New-Item -ItemType Directory -Force -Path $Local | Out-Null
  if (-not (Test-Path $PgZip)) { & $Curl -sSkL -o $PgZip $PgUrl }
  if (-not (Test-Path $PostgisZip)) { & $Curl -sSkL -o $PostgisZip $PostgisUrl }

  Write-Host "Extracting PostgreSQL ..."
  if (Test-Path $PgRoot) { Remove-Item -Recurse -Force $PgRoot }
  Expand-Archive -LiteralPath $PgZip -DestinationPath (Join-Path $Local "pgtmp") -Force
  Move-Item (Join-Path $Local "pgtmp\pgsql") $PgRoot

  Write-Host "Extracting PostGIS bundle ..."
  $Bundle = Join-Path $Local "pgtmp\postgis-bundle-pg16-3.6.2x64"
  if (Test-Path $Bundle) { Remove-Item -Recurse -Force $Bundle }
  Expand-Archive -LiteralPath $PostgisZip -DestinationPath (Join-Path $Local "pgtmp") -Force

  Write-Host "Installing PostGIS into the PostgreSQL tree ..."
  Copy-Item (Join-Path $Bundle "lib\*") (Join-Path $PgRoot "lib") -Recurse -Force
  Copy-Item (Join-Path $Bundle "share\extension\*") (Join-Path $PgRoot "share\extension") -Recurse -Force
  Copy-Item (Join-Path $Bundle "share\contrib\*") (Join-Path $PgRoot "share\contrib") -Recurse -Force -ErrorAction SilentlyContinue
  Copy-Item (Join-Path $Bundle "bin\*") (Join-Path $PgRoot "bin") -Recurse -Force
  if (Test-Path (Join-Path $Bundle "gdal-data")) {
    Copy-Item -Recurse (Join-Path $Bundle "gdal-data") (Join-Path $PgRoot "share\gdal-data") -Force
  }

  Write-Host "Initialising the data directory ..."
  if (Test-Path $PgData) { Remove-Item -Recurse -Force $PgData }
  & (Join-Path $PgRoot "bin\initdb.exe") -D $PgData -U postgres -A trust -E UTF8 --locale=C | Out-Null
  Write-Host "Setup complete. Run: scripts\local-db.ps1 start"
}

function StartDb {
  if (-not (Test-Path $PgData)) { throw "No data directory. Run 'setup' first." }
  & (Join-Path $PgRoot "bin\pg_ctl.exe") -D $PgData -l (Join-Path $PgData "server.log") `
    -o "-p $Port -c listen_addresses=127.0.0.1" -w start
  & (Join-Path $PgRoot "bin\psql.exe") -h 127.0.0.1 -p $Port -U postgres -d postgres `
    -tAc "SELECT 1 FROM pg_database WHERE datname='civicsense'" | Out-Null
  & (Join-Path $PgRoot "bin\psql.exe") -h 127.0.0.1 -p $Port -U postgres -d postgres `
    -tAc "CREATE DATABASE civicsense;" | Out-Null
  Write-Host "PostgreSQL + PostGIS listening on 127.0.0.1:$Port (db: civicsense, user: postgres)"
}

function StopDb {
  & (Join-Path $PgRoot "bin\pg_ctl.exe") -D $PgData -m fast -w stop
}

function Status {
  $psql = Join-Path $PgRoot "bin\psql.exe"
  if (-not (Test-Path $psql)) { Write-Host "Not set up."; return }
  & $psql -h 127.0.0.1 -p $Port -U postgres -d civicsense -tAc "SELECT postgis_version();" 2>&1
}

switch ($Action) {
  "setup" { Setup }
  "start" { StartDb }
  "stop" { StopDb }
  "status" { Status }
}
