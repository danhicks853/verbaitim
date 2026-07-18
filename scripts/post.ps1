# VerbAItim 2:14 post entrypoint for Task Scheduler.
# Thin wrapper: sets cwd, runs post.py, mirrors its exit code, logs a line.
# All real logic lives in post.py / verbaitim_core.py (single source of truth).

$ErrorActionPreference = "Stop"
$repo = "D:\github\verbaitim"
$log  = Join-Path $repo "render_output\automation.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null

$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
try {
    Set-Location $repo
    # Adjust 'python' if BEAST uses the launcher: replace with 'py -3'
    & python "$repo\scripts\post.py" *>> $log
    $code = $LASTEXITCODE
    Add-Content $log "[$stamp] post.ps1 exit=$code"
    exit $code
} catch {
    Add-Content $log "[$stamp] post.ps1 CRASHED: $($_.Exception.Message)"
    exit 1
}
