# app.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

# Import FastAPI routers
from api.rag_routes import rag_router
from api.vault_routes import vault_router
from api.dashboard_routes import dashboard_router
from api.workspace_routes import workspace_router

# Initialize FastAPI app
fastapi_app = FastAPI(
    title="Marketing Agent OS - Autonomous Creative Engine API",
    description="Stateless Backend and BI Dashboard Server for Marketing Agent OS v3.0",
    version="3.0.0"
)

# Logger setup
logger = logging.getLogger("marketing_agent_os_app")
logging.basicConfig(level=logging.INFO)

# Include Specialized API Routers
fastapi_app.include_router(rag_router)
fastapi_app.include_router(vault_router)
fastapi_app.include_router(dashboard_router)
fastapi_app.include_router(workspace_router)

# Mount public directory for assets if it exists
public_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "public"))
if os.path.exists(public_path):
    fastapi_app.mount("/public", StaticFiles(directory=public_path), name="public")

# Serve UI template pages to preserve BI Dashboard integration
@fastapi_app.get("/", response_class=RedirectResponse)
async def root():
    return RedirectResponse(url="/dashboard")

@fastapi_app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "dashboard.html"))
    if not os.path.exists(template_path):
        return HTMLResponse(content="<h1>CMO BI Dashboard Template Not Found</h1><p>Please ensure data/templates/dashboard.html exists.</p>", status_code=404)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@fastapi_app.get("/settings", response_class=HTMLResponse)
@fastapi_app.get("/settings/integrations", response_class=HTMLResponse)
async def serve_settings_integrations():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "settings-integrations.html"))
    if not os.path.exists(template_path):
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "settings.html"))
    if not os.path.exists(template_path):
        return HTMLResponse(content="<h1>Settings Page Template Not Found</h1>", status_code=404)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@fastapi_app.get("/settings/models", response_class=HTMLResponse)
async def serve_settings_models():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "settings-models.html"))
    if not os.path.exists(template_path):
        return HTMLResponse(content="<h1>AI Models Library Template Not Found</h1>", status_code=404)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@fastapi_app.get("/vault", response_class=HTMLResponse)
@fastapi_app.get("/Vault", response_class=HTMLResponse)
async def serve_vault():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "templates", "vault.html"))
    if not os.path.exists(template_path):
        return HTMLResponse(content="<h1>Approved Asset Vault Template Not Found</h1>", status_code=404)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

@fastapi_app.get("/knowledge-base", response_class=HTMLResponse)
async def serve_knowledge_base():
    template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "public", "knowledge-base.html"))
    if not os.path.exists(template_path):
        return HTMLResponse(content="<h1>Knowledge Base UI Not Found</h1>", status_code=404)
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()
    return HTMLResponse(content=content)

# Health check endpoint
@fastapi_app.get("/api/health")
async def health():
    return {"status": "healthy", "engine": "autonomous", "version": "3.0.0"}

if __name__ == "__main__":
    uvicorn.run("app:fastapi_app", host="0.0.0.0", port=8000, reload=True)
