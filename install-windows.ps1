#requires -version 5.1
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Repo = 'SamSamantha1977/Cassandre'
$InstallerUrl = "https://raw.githubusercontent.com/$Repo/main/install-user.py"
$InstallRoot = Join-Path $env:LOCALAPPDATA 'CassandreWorker'
$LogPath = Join-Path $InstallRoot 'Logs\bootstrap.cmtrace.log'
$TempRoot = Join-Path $env:TEMP ('CassandreWorker-Install-' + [guid]::NewGuid().ToString('N'))
$PythonInstaller = Join-Path $TempRoot 'install-user.py'

function Write-CMTraceLog {
    param([string]$Message,[ValidateSet(1,2,3)][int]$Type=1,[string]$Component='PublicInstaller')
    try {
        $dir = Split-Path -Parent $LogPath
        if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        $now=Get-Date
        $safe=[string]$Message -replace '\]\]>','] ]>'
        $line='<![LOG['+$safe+']LOG]!><time="'+$now.ToString('HH:mm:ss.fff')+'" date="'+$now.ToString('MM-dd-yyyy')+'" component="'+$Component+'" context="" type="'+$Type+'" thread="'+$PID+'" file="">'
        Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    } catch {}
}

function Test-Python311 {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $false }
    try {
        & $Path -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" 2>$null
        return ($LASTEXITCODE -eq 0)
    } catch { return $false }
}

function Find-Python311 {
    $candidates = New-Object System.Collections.Generic.List[string]
    foreach ($name in @('python.exe','python3.exe')) {
        try {
            $cmd = Get-Command $name -ErrorAction Stop
            if ($cmd.Source) { $candidates.Add([string]$cmd.Source) }
        } catch {}
    }
    foreach ($base in @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Python'),
        (Join-Path $env:APPDATA 'uv\data\python'),
        (Join-Path $env:LOCALAPPDATA 'uv\python')
    )) {
        if (Test-Path -LiteralPath $base) {
            Get-ChildItem -LiteralPath $base -Filter python.exe -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object { $candidates.Add($_.FullName) }
        }
    }
    foreach ($candidate in ($candidates | Select-Object -Unique)) {
        if (Test-Python311 $candidate) { return $candidate }
    }
    return $null
}

function Install-UserPython {
    $toolDir = Join-Path $InstallRoot 'Tools\uv'
    $uv = Join-Path $toolDir 'uv.exe'
    if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) {
        New-Item -ItemType Directory -Path $toolDir -Force | Out-Null
        $uvScript = Join-Path $TempRoot 'uv-install.ps1'
        Write-CMTraceLog 'Python 3.11+ absent : installation utilisateur de uv.'
        Invoke-WebRequest -UseBasicParsing -Uri 'https://astral.sh/uv/install.ps1' -OutFile $uvScript
        $oldInstallDir = $env:UV_INSTALL_DIR
        $oldNoModify = $env:UV_NO_MODIFY_PATH
        try {
            $env:UV_INSTALL_DIR = $toolDir
            $env:UV_NO_MODIFY_PATH = '1'
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $uvScript
            if ($LASTEXITCODE -ne 0) { throw "Installation uv en echec: code $LASTEXITCODE" }
        } finally {
            $env:UV_INSTALL_DIR = $oldInstallDir
            $env:UV_NO_MODIFY_PATH = $oldNoModify
        }
    }
    if (-not (Test-Path -LiteralPath $uv -PathType Leaf)) { throw 'uv.exe introuvable apres installation utilisateur.' }
    Write-CMTraceLog 'Installation/verfication de Python 3.12 utilisateur via uv.'
    & $uv python install 3.12 --no-progress
    if ($LASTEXITCODE -ne 0) { throw "uv python install a retourne $LASTEXITCODE" }
    $python = (& $uv python find '>=3.11' --system 2>$null | Select-Object -First 1)
    if (-not $python) { $python = (& $uv python find '>=3.11' 2>$null | Select-Object -First 1) }
    $python = ([string]$python).Trim()
    if (-not (Test-Python311 $python)) { throw 'Python 3.11+ introuvable apres installation uv.' }
    return $python
}

try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    New-Item -ItemType Directory -Path $TempRoot -Force | Out-Null
    Write-CMTraceLog 'Installation Windows utilisateur commencee; aucune elevation UAC ne sera demandee.'
    $python = Find-Python311
    if (-not $python) { $python = Install-UserPython }
    Write-CMTraceLog "Python retenu: $python"
    Invoke-WebRequest -UseBasicParsing -Uri $InstallerUrl -OutFile $PythonInstaller
    Write-CMTraceLog 'install-user.py telecharge depuis le depot public.'
    & $python $PythonInstaller
    if ($LASTEXITCODE -ne 0) { throw "install-user.py a retourne $LASTEXITCODE" }
    Write-CMTraceLog 'Installation Windows utilisateur terminee avec succes.'
    exit 0
}
catch {
    Write-CMTraceLog ("ECHEC installation Windows utilisateur: " + $_.Exception.Message) 3
    Write-Host ''
    Write-Host 'Installation Cassandre Worker impossible.' -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host "Journal : $LogPath"
    exit 1
}
finally {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
