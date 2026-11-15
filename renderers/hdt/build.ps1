param([string]$HdtPath = 'E:\Programs\HDT')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$outputPath = Join-Path $projectRoot 'dist\TavernLens'
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$frameworkPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$compiler = Join-Path $frameworkPath 'csc.exe'
$hostAssembly = Join-Path $HdtPath 'HearthstoneDeckTracker.exe'
if (!(Test-Path -LiteralPath $hostAssembly)) { throw 'HDT executable not found' }
$references = @($hostAssembly,
    (Join-Path $frameworkPath 'WPF\PresentationFramework.dll'),
    (Join-Path $frameworkPath 'WPF\PresentationCore.dll'),
    (Join-Path $frameworkPath 'WPF\WindowsBase.dll'),
    (Join-Path $frameworkPath 'System.Xaml.dll'),
    (Join-Path $frameworkPath 'System.Web.Extensions.dll'))
$compilerArgs = @('/nologo', '/target:library', '/optimize+', '/codepage:65001',
    ('/out:' + (Join-Path $outputPath 'TavernLens.Hdt.dll')))
foreach ($reference in $references) { $compilerArgs += ('/reference:' + $reference) }
$compilerArgs += (Join-Path $PSScriptRoot 'Plugin.cs')
& $compiler @compilerArgs
if ($LASTEXITCODE -ne 0) { throw 'HDT plugin compilation failed' }
Write-Output (Join-Path $outputPath 'TavernLens.Hdt.dll')
