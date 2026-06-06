# Project Instructions & AI Mandates

## Core Configuration
- **Backend**: FastAPI on port `8005`.
- **Frontend**: Next.js 16 on port `3005`.
- **API URL**: Always use `http://192.168.0.200:8005` for LAN stability.

## Development Workflow
- **Frontend**: Always run with `-H 192.168.0.200` to avoid WebSocket/HMR disconnects on LAN.
- **Hydration**: If the UI hangs on "Verifying Session", check CORS in `app.py` and ensure the frontend can reach the backend.

## Documentation
- Detailed setup instructions for AI agents: [docs/AI_DEV_SETUP.md](docs/AI_DEV_SETUP.md).
- System Architecture: [README.md](README.md).

## Critical Rules
1. **No Re-seeding**: Never run `seed.py` without user confirmation to protect existing customer data.
2. **Ports**: Stick to `8005` (API) and `3005` (Web) to avoid system service conflicts.
