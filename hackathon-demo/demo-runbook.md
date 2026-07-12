# Demo Runbook

## Start services

From the repo root:

```powershell
Start-Process -WindowStyle Hidden -FilePath python -ArgumentList @('-m','uvicorn','backend.api:app','--host','127.0.0.1','--port','8000') -WorkingDirectory .
Start-Process -WindowStyle Hidden -FilePath npm.cmd -ArgumentList @('run','dev','--','--host','127.0.0.1','--port','5173') -WorkingDirectory .\Frontend
```

Health checks:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:5173/
```

## Rehearsal check

```powershell
python -m backend.scripts.live_mode_check --require-live-llm --require-live-evidence
```

Expected current result during creation:

```text
9 PASS, 1 WARN, 0 FAIL
```

The warning is acceptable when GitHub/Slack/Notion OAuth connectors are not authenticated locally.

## Workflow shown

1. Open `http://localhost:5173`.
2. Click `Launch Program`.
3. Use sample demo data.
4. Define the portfolio positioning decision.
5. Run simulation.
6. Inspect timeline branches.
7. Switch to Memory Graph.
8. Ask Future Self for next priorities.
