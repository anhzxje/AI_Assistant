# Development Hot Reload

Use this mode while editing Python or Next.js code.

## Start Dev

```powershell
cd D:\OmniAssistant_Workspace\project-root
.\scripts\dev_all.ps1
```

This starts Docker infra, the backend reload server, the frontend reload server, and opens the browser at the printed login URL.

The script detects busy ports. If an old OmniAssistant dev server owns the port, it stops that process. If another app owns the port, it leaves that process alone and selects a fallback port.

Default ports:

- Backend: `8000`, then `8010`, `8011`, `8012`
- Frontend: `3002`, then `3003`, `3004`, `3010`

If the browser opens on a different port, use the printed `Login` URL.

## Stop Dev

```powershell
.\scripts\stop_dev.ps1
```

This stops local backend/frontend dev servers for this project and leaves Docker running.

To stop Docker infra too:

```powershell
.\scripts\stop_dev.ps1 -StopDocker
```

## Individual Servers

Backend only:

```powershell
.\scripts\dev_backend.ps1 -Port 8000
```

Frontend only:

```powershell
.\scripts\dev_frontend.ps1 -Port 3002 -BackendPort 8000
```

## Behavior

- Backend reloads automatically on Python changes.
- Frontend reloads automatically on React/Next changes.
- `frontend/.env.local` is updated with the selected backend URL.
- Browser refreshes automatically for most frontend edits.
- Keep the backend and frontend PowerShell windows open while developing.

## Production/Demo Mode

Use this when you want a stable demo build:

```powershell
python scripts/run_backend.py
npm.cmd --prefix frontend run build
cd frontend
npm.cmd run start -- --hostname 127.0.0.1 --port 3002
```
