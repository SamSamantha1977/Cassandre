#requires -version 5.1
[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Source = Join-Path $Root 'setup_windows.cs'
$Output = Join-Path $Root 'setup_windows.exe'
$Log = Join-Path $Root 'build-setup-windows.cmtrace.log'

function Write-CMTraceLog {
    param([string]$Message,[ValidateSet(1,2,3)][int]$Type=1)
    $Now = Get-Date
    $Safe = ([string]$Message).Replace(']]>','] ]>')
    $Line = '<![LOG['+$Safe+']LOG]!><time="'+$Now.ToString('HH:mm:ss.fff')+'" date="'+$Now.ToString('MM-dd-yyyy')+'" component="CassandraSetupBuild" context="" type="'+$Type+'" thread="'+$PID+'" file="">'
    Add-Content -LiteralPath $Log -Value $Line -Encoding UTF8
}

try {
    Write-CMTraceLog 'Debut construction setup_windows.exe.'
    if(-not (Test-Path -LiteralPath $Source)) { throw "Source introuvable: $Source" }

    $Candidates = @(
        "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe",
        "$env:WINDIR\Microsoft.NET\Framework\v4.0.30319\csc.exe"
    )
    $Csc = $Candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if(-not $Csc) { throw 'Compilateur C# .NET Framework (csc.exe) introuvable.' }

    Remove-Item -LiteralPath $Output -Force -ErrorAction SilentlyContinue
    $Args = @(
        '/nologo',
        '/target:winexe',
        '/platform:anycpu',
        '/optimize+',
        '/reference:System.dll',
        '/reference:System.Windows.Forms.dll',
        ('/out:"'+$Output+'"'),
        ('"'+$Source+'"')
    ) -join ' '

    Write-CMTraceLog "Compilation avec $Csc"
    $StdOut = Join-Path $env:TEMP ('cassandra-setup-csc-'+[guid]::NewGuid().ToString('N')+'.out.log')
    $StdErr = Join-Path $env:TEMP ('cassandra-setup-csc-'+[guid]::NewGuid().ToString('N')+'.err.log')
    try {
        $P = Start-Process -FilePath $Csc -ArgumentList $Args -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $StdOut -RedirectStandardError $StdErr
        foreach($Line in @(Get-Content -LiteralPath $StdOut -ErrorAction SilentlyContinue)) { if($Line){ Write-CMTraceLog "csc: $Line" } }
        foreach($Line in @(Get-Content -LiteralPath $StdErr -ErrorAction SilentlyContinue)) { if($Line){ Write-CMTraceLog "csc: $Line" 3 } }
        if($P.ExitCode -ne 0) { throw "Compilation echouee, ExitCode=$($P.ExitCode)" }
    }
    finally {
        Remove-Item -LiteralPath $StdOut,$StdErr -Force -ErrorAction SilentlyContinue
    }

    if(-not (Test-Path -LiteralPath $Output)) { throw 'setup_windows.exe non genere.' }
    $Hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Output).Hash
    Write-CMTraceLog "Construction terminee. SHA256=$Hash"
    Write-Host "OK - $Output"
    Write-Host "SHA256: $Hash"
    exit 0
}
catch {
    Write-CMTraceLog ("ECHEC: "+$_.Exception.Message) 3
    Write-Error $_.Exception.Message
    exit 1
}
