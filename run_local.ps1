$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) {
    py -3.12 -m venv .venv
}
& .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:MANAGER_KEY = "local-manager-demo-change-this"
Write-Host ""
Write-Host "FORM:    http://127.0.0.1:8000/"
Write-Host "QUAN LY: http://127.0.0.1:8000/manage/$env:MANAGER_KEY"
Write-Host ""
uvicorn app.main:app --host 0.0.0.0 --port 8000
