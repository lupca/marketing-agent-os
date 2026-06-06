# AI Development Setup Guide (LAN Optimized)

> **Context**: This project uses Next.js 16 and FastAPI. Accessing the dev environment over a LAN requires specific network bindings and CORS configurations.

## 1. Backend Setup (FastAPI)

- **Port**: `8005` (Avoids conflict with Portainer on `8000`).
- **CORS**: Must allow `*` or explicitly the LAN IP `http://192.168.0.200:3005`.
- **Command**:
  ```bash
  export PYTHONPATH=$PYTHONPATH:.
  python3 app.py
  ```

## 2. Frontend Setup (Next.js 16)

- **Port**: `3005` (LAN access stable).
- **Environment**: `.env.local` must contain:
  ```env
  NEXT_PUBLIC_API_URL=http://192.168.0.200:8005
  ```
- **Engine**: Use **Webpack** (not Turbopack) for reliable HMR over LAN.
- **Hostname Binding**: Must bind to the specific LAN IP (`192.168.0.200`) to ensure WebSocket HMR clients connect correctly.
- **Command**:
  ```bash
  NEXT_PUBLIC_API_URL=http://192.168.0.200:8005 npx next dev -H 192.168.0.200 -p 3005
  ```

## 3. Celery Workers

- **Start Script**: `./start_workers.sh`
- **Dependencies**: Ensure `redis` is running on `192.168.0.200:6379`.

## 4. Troubleshooting for AI Agents

- **Stuck at "Verifying Session"**: This indicates a Hydration failure. Ensure the browser can reach the JS chunks on port `3005` and the API on `8005`.
- **WebSocket Failures**: If HMR fails, check if the client machine's firewall blocks port `3005`.
- **Database**: Use the existing PostgreSQL on port `5432`. Do not re-seed unless explicitly instructed, as it may affect existing data.
