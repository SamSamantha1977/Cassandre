#requires -version 5.1
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Repo = 'SamSamantha1977/Cassandre'
$Asset = 'M3DIA-Worker-Windows.zip'
$BaseRelease = "https://github.com/$Repo/releases/latest/download"
$AssetUrl = "$BaseRelease/$Asset"
$HashesUrl = "$BaseRelease/SHA256SUMS.txt"
$TempRoot = Join-Path $env:TEMP ("M3DIA-Worker-Install-" + [guid]::NewGuid().ToString('N'))
$ZipPath = Join-Path $TempRoot $Asset
$ExtractRoot = Join-Path $TempRoot 'payload'
$BootstrapLog = Join-Path $env:TEMP 'M3DIA-Worker-Installer.cmtrace.log'

function Write-CMTraceLog { param([string]$Message,[ValidateSet(1,2,3)][int]$Type=1,[string]$Component='PublicInstaller') try { $now=Get-Date; $safe=[string]$Message -replace '\]\]>','] ]>'; $line='<![LOG['+$safe+']LOG]!><time="'+$now.ToString('HH:mm:ss.fff')+'" date="'+$now.ToString('MM-dd-yyyy')+'" component="'+$Component+'" context="" type="'+$Type+'" thread="'+$PID+'" file="">'; Add-Content -LiteralPath $BootstrapLog -Value $line -Encoding UTF8 } catch {} }

function Test-IsAdministrator { try { $identity=[Security.Principal.WindowsIdentity]::GetCurrent(); $principal=New-Object Security.Principal.WindowsPrincipal($identity); return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) } catch { return $false } }

if (-not (Test-IsAdministrator)) {
    Write-CMTraceLog 'Elevation UAC demandee.' 1
    $cmd = "& ([scriptblock]::Create((Invoke-RestMethod -UseBasicParsing 'https://raw.githubusercontent.com/$Repo/main/install-windows.ps1')))"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($cmd))
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -Verb RunAs -Wait -PassThru
    exit $p.ExitCode
}

try {
    New-Item -ItemType Directory -Path $TempRoot,$ExtractRoot -Force | Out-Null
    Write-CMTraceLog "Telechargement de $Asset depuis GitHub."
    Invoke-WebRequest -UseBasicParsing -Uri $AssetUrl -OutFile $ZipPath

    try {
        $hashText = (Invoke-WebRequest -UseBasicParsing -Uri $HashesUrl).Content
        $expected = $null
        foreach ($line in ($hashText -split "`r?`n")) { if ($line -match '^\s*([0-9A-Fa-f]{64})\s+\*?(.+?)\s*$' -and $Matches[2].Trim() -eq $Asset) { $expected=$Matches[1].ToUpperInvariant(); break } }
        if ($expected) { $actual=(Get-FileHash -Algorithm SHA256 -LiteralPath $ZipPath).Hash.ToUpperInvariant(); if ($actual -ne $expected) { throw "Empreinte SHA-256 invalide pour $Asset" }; Write-CMTraceLog 'Empreinte SHA-256 validee.' } else { Write-CMTraceLog 'SHA256SUMS.txt ne contient pas encore une entree exploitable pour cet asset; poursuite.' 2 }
    } catch { Write-CMTraceLog ("Controle SHA-256 non disponible: " + $_.Exception.Message) 2 }

    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractRoot -Force
    $launcher = Get-ChildItem -LiteralPath $ExtractRoot -Filter 'lanceur.cmd' -File -Recurse | Select-Object -First 1
    if ($launcher) { Write-CMTraceLog "Execution du lanceur package: $($launcher.FullName)"; $p=Start-Process -FilePath 'cmd.exe' -ArgumentList @('/d','/c',('"'+$launcher.FullName+'"')) -WorkingDirectory $launcher.DirectoryName -Wait -PassThru; if ($p.ExitCode -ne 0) { throw "Le lanceur du package a retourne $($p.ExitCode)." } }
    else { $bootstrap=Get-ChildItem -LiteralPath $ExtractRoot -Filter 'bootstrap.ps1' -File -Recurse | Select-Object -First 1; if (-not $bootstrap) { throw 'Aucun lanceur.cmd ni bootstrap.ps1 trouve dans le package Windows.' }; Write-CMTraceLog "Execution bootstrap package: $($bootstrap.FullName)"; & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $bootstrap.FullName; if ($LASTEXITCODE -ne 0) { throw "Le bootstrap du package a retourne $LASTEXITCODE." } }

    Write-CMTraceLog 'Installation publique Windows terminee avec succes.'
    exit 0
}
catch { Write-CMTraceLog ("ECHEC installation Windows: " + $_.Exception.Message) 3; Write-Host ''; Write-Host 'Installation Cassandre Worker impossible.' -ForegroundColor Red; Write-Host $_.Exception.Message -ForegroundColor Red; Write-Host "Journal : $BootstrapLog"; exit 1 }
finally { Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue }
