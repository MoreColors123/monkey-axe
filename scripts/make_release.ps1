# Build the shippable monkeyaxe.jar (game classes + assets) into the repo root.
# The result needs only a Java 17 runtime on the target machine.
param()
$ErrorActionPreference = 'Stop'

# This file lives in scripts/; the repo root is its parent directory.
$root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$proj   = Join-Path $root 'JavaGoldenAxe'
$src    = Join-Path $proj 'src'
$assets = Join-Path $proj 'assets\res'
$work   = Join-Path $root 'build-release'
$jar    = Join-Path $root 'monkeyaxe.jar'

Write-Host "Compiling Java sources..."
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
New-Item -ItemType Directory -Force -Path $work | Out-Null
$files = Get-ChildItem $src -Recurse -Filter *.java | ForEach-Object { $_.FullName }
& javac -encoding UTF-8 -d $work $files
if ($LASTEXITCODE -ne 0) { throw "javac failed with exit code $LASTEXITCODE" }

Write-Host "Copying resources (res/)..."
Copy-Item -Recurse -Force $assets (Join-Path $work 'res')

Write-Host "Packaging $jar ..."
if (Test-Path $jar) { Remove-Item -Force $jar }
& jar --create --file $jar --main-class main.Main -C $work .
if ($LASTEXITCODE -ne 0) { throw "jar failed with exit code $LASTEXITCODE" }
Remove-Item -Recurse -Force $work

Write-Host ""
Write-Host "Done. monkeyaxe.jar rebuilt in the repo root."
Write-Host "Commit it, then double-click Play.bat to test."
