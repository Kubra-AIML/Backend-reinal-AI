$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000