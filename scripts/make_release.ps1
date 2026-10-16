# Build the shippable game: monkeyaxe.zip in the repo root, holding monkeyaxe.jar
# plus Play.bat and HowToPlay.txt (all at the zip root). The jar itself is only an
# intermediate and is git-ignored - the zip is what gets committed and published.
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
$play   = Join-Path $root 'scripts\Play.bat'
$zip    = Join-Path $root 'monkeyaxe.zip'

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

Write-Host "Packaging $zip (jar + Play.bat + HowToPlay.txt, all at the zip root) ..."
if (Test-Path $zip) { Remove-Item -Force $zip }
$stage = Join-Path $root 'build-release-zip'
if (Test-Path $stage) { Remove-Item -Recurse -Force $stage }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item $jar $stage
Copy-Item $play $stage
Copy-Item (Join-Path $root 'HowToPlay.txt') $stage
Compress-Archive -Path (Join-Path $stage '*') -DestinationPath $zip -CompressionLevel Optimal
Remove-Item -Recurse -Force $stage
if (-not (Test-Path $zip)) { throw "Compress-Archive did not produce $zip" }

Write-Host ""
Write-Host "Done:"
Write-Host "  monkeyaxe.jar  build intermediate (git-ignored)"
Write-Host "  monkeyaxe.zip  the shipped game - COMMIT IT (unzip, then double-click Play.bat)"
