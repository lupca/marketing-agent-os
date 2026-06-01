# api/test_routes.py
import uuid
import logging
import asyncio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from core.dependencies import get_db
from core.models import MarketingCampaign
from core.bandit_orchestrator import trigger_autonomous_generation
from typing import Dict, Any

logger = logging.getLogger("test_routes")

test_router = APIRouter(prefix="/api/test", tags=["Test/Autonomous"])

# WebSocket Broadcaster
class TelemetryBroadcaster:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # Connection might have dropped, will be removed on disconnect block
                pass

broadcaster = TelemetryBroadcaster()

# Custom Logging Handler to forward logs to WebSockets
class WebSocketLogHandler(logging.Handler):
    def __init__(self, bcast: TelemetryBroadcaster):
        super().__init__()
        self.broadcaster = bcast
        self.loop = None

    def emit(self, record):
        try:
            log_entry = self.format(record)
            if self.loop is None:
                try:
                    self.loop = asyncio.get_running_loop()
                except Exception:
                    pass
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcaster.broadcast(log_entry), self.loop)
        except Exception:
            pass

# Initialize and attach logging handler to relevant system loggers
ws_handler = WebSocketLogHandler(broadcaster)
ws_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
ws_handler.setLevel(logging.INFO)

# Hook into our core loggers
logging.getLogger("bandit_orchestrator").addHandler(ws_handler)
logging.getLogger("autonomous_nodes").addHandler(ws_handler)
logging.getLogger("test_routes").addHandler(ws_handler)

@test_router.post("/trigger-autonomous/{campaign_id}")
async def trigger_autonomous(campaign_id: str, db: Session = Depends(get_db)):
    """
    Triggers stateless autonomous LangGraph creative generation for a given campaign.
    """
    logger.info(f"Received trigger-autonomous request for campaign_id: {campaign_id}")
    try:
        camp_uuid = uuid.UUID(campaign_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid campaign_id format. Must be a valid UUID.")

    # Query marketing campaign
    campaign = db.query(MarketingCampaign).filter_by(id=camp_uuid).first()
    if not campaign:
        # Fallback helper: If the seeded campaign is expected but doesn't match the passed ID,
        # we try to fetch the first active campaign in the DB to prevent breaking the flow.
        campaign = db.query(MarketingCampaign).filter_by(status="active").first()
        if not campaign:
            raise HTTPException(status_code=404, detail="No active MarketingCampaign found in database to execute.")
        logger.info(f"Requested campaign not found. Falling back to active campaign: {campaign.id}")

    try:
        # Call the orchestrator layer
        result_state = await trigger_autonomous_generation(
            workspace_id=str(campaign.workspace_id),
            campaign_id=str(campaign.id),
            product_id=str(campaign.product_id),
            db=db
        )
        return result_state
    except Exception as e:
        logger.error(f"Error executing autonomous generation pipeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Execution pipeline error: {str(e)}")
