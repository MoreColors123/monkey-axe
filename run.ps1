# Build and run the Golden Axe remake (incl. the Guybrush Threepwood mod)
# without needing Apache Ant.
param([switch]$Rebuild)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$proj = Join-Path $root 'JavaGoldenAxe'
$src  = Join-Path $proj 'src'
$out  = Join-Path $proj 'build-custom'

$mainClass = Join-Path $out 'main\Main.class'

if ($Rebuild -or -not (Test-Path $mainClass)) {
    Write-Host "Compiling Java sources..."
    if (Test-Path $out) { Remove-Item -Recurse -Force $out }
    New-Item -ItemType Directory -Force -Path $out | Out-Null
    $files = Get-ChildItem $src -Recurse -Filter *.java | ForEach-Object { $_.FullName }
    & javac -d $out $files
    if ($LASTEXITCODE -ne 0) { throw "javac failed with exit code $LASTEXITCODE" }
}
else {
    Write-Host "Using existing build (pass -Rebuild to recompile)."
}

# Always refresh resources so edited sprites/animations are picked up.
# NOTE: Copy-Item -Recurse into an existing destination directory nests the
# source folder (build-custom\res\res) instead of merging its contents, which
# silently left the game running stale assets. Remove the destination first.
Write-Host "Copying resources..."
$resSrc = Join-Path $proj 'assets\res'
$resDst = Join-Path $out 'res'
if (Test-Path $resDst) { Remove-Item -Recurse -Force $resDst }
Copy-Item -Recurse -Force $resSrc $resDst

Write-Host "Starting Golden Axe..."
& java -cp $out main.Main
