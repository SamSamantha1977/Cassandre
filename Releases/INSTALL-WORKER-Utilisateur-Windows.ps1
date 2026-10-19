#requires -Version 5.1
$ErrorActionPreference='Stop'
$ProgressPreference='SilentlyContinue'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$LogDir = Join-Path $env:LOCALAPPDATA 'Cassandre\Worker\Logs'
$Log = Join-Path $LogDir 'lanceur.cmtrace.log'
function Write-CMTraceLog([string]$Message,[int]$Type=1) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    $now=Get-Date
    $safe=$Message.Replace(']]>','] ]>')
    $line='<![LOG['+$safe+']LOG]!><time="'+$now.ToString('HH:mm:ss.fff')+'" date="'+$now.ToString('MM-dd-yyyy')+'" component="CassandreUserLauncher" context="" type="'+$Type+'" thread="'+$PID+'" file="INSTALL-WORKER-Utilisateur-Windows.ps1">'
    Add-Content -LiteralPath $Log -Value $line -Encoding UTF8
}
function Find-Python {
    foreach($candidate in @('python.exe','py.exe')) {
        $command = Get-Command $candidate -ErrorAction SilentlyContinue
        if(-not $command){continue}
        if($candidate -eq 'py.exe') {
            foreach($v in @('-3.14','-3.13','-3.12','-3.11')) {
                try {
                    $p = & $command.Source $v -c 'import sys;print(sys.executable)' 2>$null
                    if($LASTEXITCODE -eq 0 -and $p -and (Test-Path -LiteralPath ([string]$p).Trim())) {return ([string]$p).Trim()}
                }catch{}
            }
        }else{
            try {
                $ok=& $command.Source -c 'import sys;print(sys.version_info >= (3,11))' 2>$null
                if($LASTEXITCODE -eq 0 -and ([string]$ok).Trim() -eq 'True'){return $command.Source}
            }catch{}
        }
    }
    foreach($version in @('Python314','Python313','Python312','Python311')){
        $f=Join-Path $env:LOCALAPPDATA ('Programs\Python\'+$version+'\python.exe')
        if(Test-Path -LiteralPath $f){return $f}
    }
    return $null
}
try{
    Write-CMTraceLog 'Installation WORKER Windows utilisateur, sans UAC.'
    $python=Find-Python
    if(-not $python){
        Write-CMTraceLog 'Python absent : installation officielle dans le profil utilisateur.' 2
        [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
        $architecture = if($env:PROCESSOR_ARCHITECTURE -match 'ARM64'){'arm64'}else{'amd64'}
        $filename='python-3.14.7-'+$architecture+'.exe'
        $url='https://www.python.org/ftp/python/3.14.7/'+$filename
        $path=Join-Path $env:TEMP $filename
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $path
            $signature=Get-AuthenticodeSignature -FilePath $path
            if($signature.Status -ne 'Valid'){throw 'Signature numerique de Python invalide ou invérifiable.'}
            $installer=Start-Process -FilePath $path -ArgumentList @(
                '/quiet','InstallAllUsers=0','PrependPath=0','Include_pip=1',
                'Include_launcher=0','Include_test=0','Shortcuts=0'
            ) -Wait -PassThru -WindowStyle Hidden
            if($installer.ExitCode -ne 0){throw "Installation Python utilisateur en echec : $($installer.ExitCode)"}
            $python=Find-Python
        } finally {
            Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
        }
    }
    if(-not $python){throw 'Python 3.11+ introuvable apres tentative installation utilisateur.'}
    $backend=Join-Path $Here 'bootstrap_user.py'
    if(-not (Test-Path -LiteralPath $backend)){throw 'bootstrap_user.py absent du dossier du lanceur.'}
    & $python $backend --family windows --mode install
    if($LASTEXITCODE -ne 0){throw "Installation WORKER en echec, code $LASTEXITCODE."}
    Write-CMTraceLog 'Installation WORKER Windows utilisateur terminee.'
    Write-Host 'WORKER utilisateur installe.'
    exit 0
}catch{
    Write-CMTraceLog $_.Exception.Message 3
    Write-Error $_.Exception.Message
    exit 1
}
