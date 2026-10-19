@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0INSTALL-WORKER-Utilisateur-Windows.ps1"
exit /b %errorlevel%
