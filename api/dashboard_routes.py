from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from core.dependencies import get_db
from core.dashboard import get_dashboard_analytics, simulate_scenario
import logging

logger = logging.getLogger("dashboard_routes")

dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@dashboard_router.get("/metrics")
async def get_metrics(db: Session = Depends(get_db)):
    """
    Retrieve high-fidelity analytics for the CMO BI Dashboard.
    """
    try:
        data = get_dashboard_analytics(db)
        return data
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.post("/sync-metrics")
async def sync_metrics():
    """
    Trigger manual synchronization of metrics via background job.
    """
    try:
        from core.celery_app import celery_app
        celery_app.send_task(
            "core.tasks.sync_own_media_metrics",
            queue="social_publisher"
        )
        return {"status": "success", "message": "Đã đẩy lệnh đồng bộ metrics vào hàng đợi ngầm. Vui lòng F5 sau ít phút."}
    except Exception as e:
        logger.error(f"Error triggering metrics sync: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@dashboard_router.post("/simulate")
async def simulate(request: Request, db: Session = Depends(get_db)):
    """
    Simulate business scenarios using the What-If Simulator.
    """
    try:
        body = await request.json()
        test_budget = float(body.get("test_budget", 0))
        price = float(body.get("price", 0))
        cost = float(body.get("cost", 0))
        res = simulate_scenario(test_budget, price, cost, db)
        return res
    except Exception as e:
        logger.error(f"Error simulating scenario: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
