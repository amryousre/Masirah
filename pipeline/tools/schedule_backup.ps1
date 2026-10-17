# Registers the daily backup with Windows Task Scheduler (T110). Run once, in PowerShell, from the
# pipeline folder of a checkout kept on main for this purpose (Docs/runbooks/backup-recovery.md):
#
#     powershell -ExecutionPolicy Bypass -File tools\schedule_backup.ps1
#
# The task runs `python -m tools.backup run` at 02:00 every day, and as soon as the PC is on if it
# was off then, so a backup is never more than a day old while the PC is used daily (NFR-15). It
# also runs on battery. It runs only while you are signed in, because the dump needs Docker
# Desktop, which runs in your session: set Docker Desktop to start when you sign in. The tool waits
# up to ten minutes for Docker to come up. Each run's output goes to
# %LOCALAPPDATA%\Masirah\backup.log, which holds no secret. A failure also posts to Slack when
# MASIRAH_SLACK_WEBHOOK_URL is set in .env.

$ErrorActionPreference = "Stop"
$pipeline = Split-Path -Parent $PSScriptRoot
$logFolder = Join-Path $env:LOCALAPPDATA "Masirah"
New-Item -ItemType Directory -Force -Path $logFolder | Out-Null
$log = Join-Path $logFolder "backup.log"
$uv = (Get-Command uv).Source

# The quotes around PYTHONUTF8=1 matter: without them cmd keeps the space before &&, and Python
# refuses to start with PYTHONUTF8 set to "1 ".
$command = "cd /d `"$pipeline`" && set `"PYTHONUTF8=1`" && `"$uv`" run --env-file .env python -m tools.backup run >> `"$log`" 2>&1"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c $command"
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)
Register-ScheduledTask -TaskName "Masirah backup" -Action $action -Trigger $trigger -Settings $settings `
    -Description "Daily encrypted backup of the hosted Masirah project (T110)" -Force | Out-Null
Write-Output "Registered 'Masirah backup': daily at 02:00, or at the next sign-in after a missed run."
Write-Output "Check it now with: Start-ScheduledTask -TaskName 'Masirah backup'; then read $log"
