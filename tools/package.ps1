param([string]$HdtPath = 'E:\Programs\HDT')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Push-Location -LiteralPath $projectRoot
try {
    python -m PyInstaller TavernLens.spec --noconfirm
    if ($LASTEXITCODE -ne 0) { throw 'Backend build failed' }
    # Compile the adapter AFTER COLLECT, which recreates the output folder.
    & (Join-Path $projectRoot 'renderers\hdt\build.ps1') -HdtPath $HdtPath
    $appFolder = Join-Path $projectRoot 'dist\TavernLens'
    foreach ($file in @('LICENSE', 'THIRD_PARTY_NOTICES.md')) {
        Copy-Item -LiteralPath (Join-Path $projectRoot $file) -Destination $appFolder
    }
    Copy-Item -LiteralPath (Join-Path $projectRoot 'renderers\hdt\INSTALL.md') -Destination (Join-Path $appFolder 'INSTALL.md')
    python tools/collect_runtime_licenses.py $appFolder
    if ($LASTEXITCODE -ne 0) { throw 'Runtime license collection failed' }
    $archive = Join-Path $projectRoot 'dist\TavernLens-HDT.zip'
    $installer = Join-Path $projectRoot 'dist\安装.cmd'
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '安装.cmd') -Destination $installer
    Compress-Archive -LiteralPath @($installer, $appFolder) -DestinationPath $archive -Force
    Get-Item -LiteralPath $archive | Select-Object FullName, Length
    Get-FileHash -LiteralPath $archive -Algorithm SHA256
} finally {
    Pop-Location
}
