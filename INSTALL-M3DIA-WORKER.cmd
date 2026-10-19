@echo off
setlocal EnableExtensions

title Installation Cassandre Worker

echo Installation de Cassandre Worker pour l'utilisateur courant...
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "& ([scriptblock]::Create((Invoke-RestMethod -UseBasicParsing 'https://raw.githubusercontent.com/SamSamantha1977/Cassandre/main/install-windows.ps1')))"
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo.
    echo L'installation de Cassandre Worker a rencontre une erreur.
    echo Consultez le journal dans %%LOCALAPPDATA%%\CassandreWorker\Logs\install.cmtrace.log
    pause
    exit /b %RC%
)

echo.
echo Cassandre Worker est installe pour l'utilisateur courant.
timeout /t 3 /nobreak >nul
exit /b 0
