<# Author/download locally first; transfer and compute only after packaging. #>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('Upload','Submit','Status','Fetch')][string]$Action,
    [Parameter(Mandatory)][string]$Run,
    [string]$Bundle,
    [string]$RemoteUser = $env:GQH_REMOTE_USER,
    [string]$RemoteHost = 'hpg.rc.ufl.edu'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runPath = (Resolve-Path -LiteralPath $Run).Path
$jobConfig = Get-Content -LiteralPath (Join-Path $runPath 'hpg/job-config.json') -Raw | ConvertFrom-Json
$remotePath = [string]$jobConfig.remote_root
if ($RemoteUser -notmatch '^[A-Za-z0-9_-]+$' -or $RemoteHost -notmatch '^[A-Za-z0-9.-]+$' -or $remotePath -notmatch '^/blue/[A-Za-z0-9_./-]+$' -or $remotePath.Split('/') -contains '..') {
    throw 'Invalid remote identity/path.'
}
$remoteTarget = "$RemoteUser@$RemoteHost"
$relativeRun = [System.IO.Path]::GetRelativePath($projectRoot, $runPath).Replace('\','/')
if ($relativeRun -notmatch '^[A-Za-z0-9_./-]+$' -or $relativeRun.StartsWith('..')) {
    throw 'Keep runs inside the project using simple run names.'
}
function Invoke-CheckedSsh([string]$CommandText) {
    & ssh -o StrictHostKeyChecking=yes $remoteTarget $CommandText
    if ($LASTEXITCODE -ne 0) { throw "Remote command failed ($LASTEXITCODE)." }
}
switch ($Action) {
    'Upload' {
        if (-not $Bundle) { throw 'Upload requires -Bundle.' }
        $bundlePath = (Resolve-Path -LiteralPath $Bundle).Path
        $bundleReceipt = Get-Content -LiteralPath "$bundlePath.receipt.json" -Raw | ConvertFrom-Json
        $actualHash = (Get-FileHash -LiteralPath $bundlePath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualHash -ne $bundleReceipt.archive_sha256) { throw 'Local bundle hash mismatch.' }
        Invoke-CheckedSsh "test ! -e '$remotePath' && mkdir -p '$remotePath'"
        & scp $bundlePath "${remoteTarget}:$remotePath/package.tar.gz"
        if ($LASTEXITCODE -ne 0) { throw 'Upload failed.' }
        Invoke-CheckedSsh "cd '$remotePath' && printf '%s  %s\n' '$actualHash' 'package.tar.gz' | sha256sum -c - && tar -xzf package.tar.gz"
        Write-Output "Verified package uploaded to $remotePath. Jobs have not been submitted."
    }
    'Submit' {
        Invoke-CheckedSsh "cd '$remotePath' && test ! -e submission-ids.txt && bash '$relativeRun/hpg/submit.sh'"
    }
    'Status' {
        Invoke-CheckedSsh "cd '$remotePath' && cat submission-ids.txt && squeue -u '$RemoteUser'"
    }
    'Fetch' {
        $archive = Join-Path $runPath 'returned-results.zip'
        & scp "${remoteTarget}:$remotePath/returned-results.zip" $archive
        if ($LASTEXITCODE -ne 0) { throw 'Results unavailable or transfer failed.' }
        & (Join-Path $projectRoot '.venv/Scripts/python.exe') -m discovery import --run $runPath --archive $archive
        if ($LASTEXITCODE -ne 0) { throw 'Returned-result validation failed.' }
        & (Join-Path $projectRoot '.venv/Scripts/python.exe') -m discovery record --run $runPath
        if ($LASTEXITCODE -ne 0) { throw 'Local experiment-history update failed.' }
        Write-Output "Verified results returned to $runPath. Open REPORT.md and summary.csv."
    }
}
