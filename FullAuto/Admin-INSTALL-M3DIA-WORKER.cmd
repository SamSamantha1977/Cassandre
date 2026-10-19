@echo off
setlocal EnableExtensions

title Installation Cassandre Worker

rem Le script PowerShell telecharge depuis le depot public contient le journal CMTrace.
rem Ce lanceur ne contient aucune logique Cassandra : il demande seulement l'elevation
rem puis appelle le bootstrap Windows public.

fltmc >nul 2>&1
if errorlevel 1 (
    echo Demande des droits administrateur...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

echo Installation de Cassandre Worker...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create((Invoke-RestMethod -UseBasicParsing 'https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-windows.ps1')))"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo L'installation de Cassandre Worker a rencontre une erreur.
    echo Consultez le journal affiche par l'installateur.
    pause
    exit /b %RC%
)

echo.
echo Cassandre Worker est installe.
timeout /t 3 /nobreak >nul
exit /b 0
