# Build the shippable monkeyaxe.jar (game classes + assets) into the repo root,
# plus monkeyaxe.zip - the single-download release artifact bundling the jar,
# Play.bat and HowToPlay.txt. Needs only a Java 17 runtime on the target machine.
param()
$ErrorActionPreference = 'Stop'

# This file lives in scripts/; the repo root is its parent directory.
$root   = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$proj   = Join-Path $root 'JavaGoldenAxe'
$src    = Join-Path $proj 'src'
$assets = Join-Path $proj 'assets\res'
$work   = Join-Path $root 'build-release'
$jar    = Join-Path $root 'monkeyaxe.jar'
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

Write-Host "Packaging $zip (jar + Play.bat + HowToPlay.txt) ..."
if (Test-Path $zip) { Remove-Item -Force $zip }
Compress-Archive -Path @($jar, (Join-Path $root 'Play.bat'), (Join-Path $root 'HowToPlay.txt')) `
                 -DestinationPath $zip -CompressionLevel Optimal
if (-not (Test-Path $zip)) { throw "Compress-Archive did not produce $zip" }

Write-Host ""
Write-Host "Done. Rebuilt in the repo root:"
Write-Host "  monkeyaxe.jar  - play it with Play.bat (or: java -jar monkeyaxe.jar)"
Write-Host "  monkeyaxe.zip  - single-download release asset (jar + Play.bat + HowToPlay.txt)"
Write-Host "Commit the jar; the zip is a release artifact and stays untracked."
Write-Host "Then double-click Play.bat to test."
