$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$outputPath = Join-Path $projectRoot 'work\hdt-test'
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$frameworkPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319'
$compiler = Join-Path $frameworkPath 'csc.exe'
$references = @((Join-Path $frameworkPath 'WPF\PresentationFramework.dll'),
    (Join-Path $frameworkPath 'WPF\PresentationCore.dll'),
    (Join-Path $frameworkPath 'WPF\WindowsBase.dll'),
    (Join-Path $frameworkPath 'System.Xaml.dll'),
    (Join-Path $frameworkPath 'System.Web.Extensions.dll'))
$commonArgs = @('/nologo','/codepage:65001')
foreach ($reference in $references) { $commonArgs += ('/reference:' + $reference) }
$stubPath = Join-Path $outputPath 'HearthstoneDeckTracker.exe'
& $compiler @commonArgs /target:library ('/out:' + $stubPath) (Join-Path $PSScriptRoot 'StubHost.cs')
if ($LASTEXITCODE -ne 0) { throw 'Test host failed to compile' }
$pluginPath = Join-Path $outputPath 'TavernLens.Hdt.dll'
& $compiler @commonArgs /target:library ('/reference:' + $stubPath) ('/out:' + $pluginPath) (Join-Path $projectRoot 'renderers\hdt\Plugin.cs')
if ($LASTEXITCODE -ne 0) { throw 'Test plugin failed to compile' }
$harnessPath = Join-Path $outputPath 'RenderTests.exe'
& $compiler @commonArgs /target:exe ('/reference:' + $stubPath) ('/reference:' + $pluginPath) ('/out:' + $harnessPath) (Join-Path $PSScriptRoot 'RenderTests.cs')
if ($LASTEXITCODE -ne 0) { throw 'Test harness failed to compile' }
& $harnessPath
if ($LASTEXITCODE -ne 0) { throw 'HDT renderer tests failed' }
