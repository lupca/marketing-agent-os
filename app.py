# app.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import logging
import uvicorn
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Import FastAPI routers
from api.rag_routes import rag_router
from api.vault_routes import vault_router
from api.dashboard_routes import dashboard_router
from api.workspace_routes import workspace_router
from api.test_routes import test_router, broadcaster
from api.cockpit_routes import cockpit_router
from api.auth_routes import auth_router
from core.pipeline_tracker import set_cockpit_broadcaster
from core.diagnostics import check_system_readiness
from db.connection import SessionLocal

# Initialize FastAPI app
fastapi_app = FastAPI(
    title="Marketing Agent OS - Autonomous Creative Engine API",
    description="Stateless Backend and BI Dashboard Server for Marketing Agent OS v3.0",
    version="3.0.0"
)

# Logger setup
logger = logging.getLogger("marketing_agent_os_app")
logging.basicConfig(level=logging.INFO)

# Configure CORS Middleware
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register cockpit broadcaster at application startup
@fastapi_app.on_event("startup")
async def register_cockpit_broadcaster():
    """
    Startup event: wire the shared WebSocket broadcaster into the pipeline_tracker module.
    This allows all node execution events to be pushed in real-time to connected Cockpit clients.
    """
    set_cockpit_broadcaster(broadcaster)
    logger.info("[COCKPIT] Broadcaster registered with pipeline_tracker on startup.")
    
    # Run System Diagnostics
    db = SessionLocal()
    try:
        check_system_readiness(db)
    finally:
        db.close()

# Include Specialized API Routers
fastapi_app.include_router(rag_router)
fastapi_app.include_router(vault_router)
fastapi_app.include_router(dashboard_router)
fastapi_app.include_router(workspace_router)
fastapi_app.include_router(test_router)
fastapi_app.include_router(cockpit_router)
fastapi_app.include_router(auth_router)

# Real-time Telemetry WebSocket endpoint
@fastapi_app.websocket("/api/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await broadcaster.connect(websocket)
    try:
        while True:
            # Keep connection alive by waiting for messages (though logs are mainly outbound)
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        broadcaster.disconnect(websocket)

# Dedicated Cockpit WebSocket endpoint for real-time pipeline observability
@fastapi_app.websocket("/api/ws/cockpit")
async def cockpit_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for The Autopilot Cockpit frontend.

    Shares the same broadcaster instance as /api/ws/telemetry so that all
    pipeline events (node_start, node_complete, run_fail, quarantine, kill_switch, etc.)
    are pushed to both the legacy telemetry consumers and the new Cockpit UI simultaneously.
    """
    await broadcaster.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"Cockpit WebSocket connection error: {e}")
        broadcaster.disconnect(websocket)

# Serve redirects to Next.js UI frontend
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")

# Mount storage directory under /public/storage for media files (mock storage compatibility)
storage_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "storage"))
os.makedirs(storage_path, exist_ok=True)
fastapi_app.mount("/public/storage", StaticFiles(directory=storage_path), name="storage")

@fastapi_app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url=f"{FRONTEND_URL}/")

@fastapi_app.get("/dashboard", response_class=RedirectResponse)
async def serve_dashboard():
    return RedirectResponse(url=f"{FRONTEND_URL}/")

@fastapi_app.get("/settings", response_class=RedirectResponse)
@fastapi_app.get("/settings/integrations", response_class=RedirectResponse)
async def serve_settings_integrations():
    return RedirectResponse(url=f"{FRONTEND_URL}/")

@fastapi_app.get("/settings/models", response_class=RedirectResponse)
async def serve_settings_models():
    return RedirectResponse(url=f"{FRONTEND_URL}/")

@fastapi_app.get("/vault", response_class=RedirectResponse)
@fastapi_app.get("/Vault", response_class=RedirectResponse)
async def serve_vault():
    return RedirectResponse(url=f"{FRONTEND_URL}/")

@fastapi_app.get("/knowledge-base", response_class=RedirectResponse)
async def serve_knowledge_base():
    return RedirectResponse(url=f"{FRONTEND_URL}/")

# Health check endpoint
@fastapi_app.get("/api/health")
async def health():
    return {"status": "healthy", "engine": "autonomous", "version": "3.0.0"}

# Diagnostics readiness endpoint
@fastapi_app.get("/api/diagnostics/readiness")
async def readiness(request: Request):
    ws_id = request.query_params.get("workspace_id") or request.headers.get("x-workspace-id")
    db = SessionLocal()
    try:
        status = check_system_readiness(db, workspace_id=ws_id)
        return status
    finally:
        db.close()

if __name__ == "__main__":
    uvicorn.run("app:fastapi_app", host="0.0.0.0", port=8005, reload=True)
