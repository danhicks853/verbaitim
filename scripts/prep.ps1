# VerbAItim T-30 prep entrypoint for Task Scheduler.
# Thin wrapper: sets cwd, runs prep.py, mirrors its exit code, logs a line.
# All real logic lives in prep.py / verbaitim_core.py (single source of truth).

$ErrorActionPreference = "Stop"
$repo = "D:\github\verbaitim"
$log  = Join-Path $repo "render_output\automation.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
try {
    Set-Location $repo
    # Adjust 'python' if BEAST uses the launcher: replace with 'py -3'
    & python "$repo\scripts\prep.py" *>> $log
    $code = $LASTEXITCODE
    Add-Content $log "[$stamp] prep.ps1 exit=$code"
    exit $code
} catch {
    Add-Content $log "[$stamp] prep.ps1 CRASHED: $($_.Exception.Message)"
    exit 1
}
