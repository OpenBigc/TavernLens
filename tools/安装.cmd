@echo off
setlocal
if not exist "%~dp0TavernLens\TavernLensBackend.exe" goto missing
"%~dp0TavernLens\TavernLensBackend.exe" --install
exit /b %errorlevel%
:missing
chcp 65001 >nul
echo 请完整解压安装包后，再运行安装.cmd。
pause
exit /b 1
