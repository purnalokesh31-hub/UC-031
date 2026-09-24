# Launch CropGuard using its validated project environment.
$ErrorActionPreference = 'Stop'
$cropPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $cropPython)) { throw 'Create the Python 3.12 .venv and install backend/requirements.txt first.' }
$cropLogs = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Path $cropLogs -Force | Out-Null
Start-Process -FilePath $cropPython -ArgumentList @('-X','utf8','-m','uvicorn','main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $PSScriptRoot 'backend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $cropLogs 'backend.log') -RedirectStandardError (Join-Path $cropLogs 'backend-error.log')
Start-Process powershell.exe -ArgumentList @('-NoProfile','-Command','npm.cmd run dev -- --host 127.0.0.1 --strictPort') -WorkingDirectory (Join-Path $PSScriptRoot 'frontend') -WindowStyle Hidden -RedirectStandardOutput (Join-Path $cropLogs 'frontend.log') -RedirectStandardError (Join-Path $cropLogs 'frontend-error.log')
Write-Host 'Servers launched. Open http://127.0.0.1:5173. Check logs/ if a port is already occupied.'
