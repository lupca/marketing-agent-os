from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import uuid
import logging
from core.dependencies import get_db
from core.models import Workspace, WorkspaceIntegration, AIModel
from core.schemas import WorkspaceIntegrationSchema, AIModelSchema
from typing import List

logger = logging.getLogger("workspace_routes")

workspace_router = APIRouter(prefix="/api/workspace", tags=["Workspace"])

@workspace_router.get("/settings")
async def get_settings(db: Session = Depends(get_db)):
    try:
        ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        ws = db.query(Workspace).filter_by(id=ws_id).first()
        return ws.settings if (ws and ws.settings) else {}
    except Exception as e:
        logger.error(f"Error fetching workspace settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/settings")
async def update_settings(request: Request, db: Session = Depends(get_db)):
    ALLOWED_SETTINGS = {"ai_model", "temperature", "max_tokens", "recursion_limit",
                       "reranker_mode", "siliconflow_api_key", "enable_thinking", "ai_api_url"}
    try:
        body = await request.json()
        filtered = {k: v for k, v in body.items() if k in ALLOWED_SETTINGS}
        if not filtered:
            raise HTTPException(status_code=400, detail="No valid settings provided")
        
        if "temperature" in filtered:
            filtered["temperature"] = max(0.0, min(1.0, float(filtered["temperature"])))
        if "max_tokens" in filtered:
            filtered["max_tokens"] = max(4000, min(20000, int(filtered["max_tokens"])))
        if "recursion_limit" in filtered:
            filtered["recursion_limit"] = max(2, min(15, int(filtered["recursion_limit"])))
        if "enable_thinking" in filtered:
            filtered["enable_thinking"] = bool(filtered["enable_thinking"])
            
        ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        ws = db.query(Workspace).filter_by(id=ws_id).first()
        if ws:
            current_settings = dict(ws.settings) if ws.settings else {}
            current_settings.update(filtered)
            ws.settings = current_settings
            db.commit()
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Workspace not found")
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving workspace settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/integrations")
async def get_integrations(db: Session = Depends(get_db)):
    try:
        ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        integrations = db.query(WorkspaceIntegration).filter_by(workspace_id=ws_id).order_by(
            WorkspaceIntegration.platform_name, WorkspaceIntegration.config_key
        ).all()
        data = []
        for i in integrations:
            data.append({
                "id": str(i.id),
                "platform_name": i.platform_name,
                "config_key": i.config_key,
                "config_value": i.config_value,
                "is_active": i.is_active,
                "created_at": i.created_at.strftime('%Y-%m-%d %H:%M:%S') if i.created_at else None
            })
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"Error fetching workspace integrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/integrations")
async def update_integration(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    
        record_id = body.get("id")
        platform_name = body.get("platform_name")
        config_key = body.get("config_key")
        config_value = body.get("config_value")
        is_active = body.get("is_active", True)
    
        if not platform_name or not config_key or config_value is None:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        existing = None
        if record_id:
            try:
                existing = db.query(WorkspaceIntegration).filter_by(id=uuid.UUID(record_id)).first()
            except Exception:
                pass
    
        if not existing:
            existing = db.query(WorkspaceIntegration).filter_by(
                workspace_id=ws_id,
                platform_name=platform_name,
                config_key=config_key
            ).first()
    
        if existing:
            existing.platform_name = platform_name
            existing.config_key = config_key
            existing.config_value = str(config_value)
            existing.is_active = bool(is_active)
            existing.updated_at = func.now()
            db.commit()
            return {"status": "success", "message": "Updated successfully"}
        else:
            new_integration = WorkspaceIntegration(
                workspace_id=ws_id,
                platform_name=platform_name,
                config_key=config_key,
                config_value=str(config_value),
                is_active=bool(is_active)
            )
            db.add(new_integration)
            db.commit()
            return {"status": "success", "message": "Created successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving workspace integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/integrations/delete")
async def delete_integration(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        integration_id = body.get("id")
        if not integration_id:
            raise HTTPException(status_code=400, detail="Missing integration id")
        
        db.query(WorkspaceIntegration).filter_by(id=uuid.UUID(integration_id)).delete()
        db.commit()
        return {"status": "success", "message": "Deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting workspace integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/models")
async def get_models(db: Session = Depends(get_db)):
    try:
        ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        models = db.query(AIModel).filter_by(workspace_id=ws_id).order_by(AIModel.created_at.desc()).all()
        # Note: Logic to seed default models could be moved to a service or seed script.
        # For now, let's keep it here but using the new response model.
        if not models:
             # Just return empty list or handle seeding if absolutely necessary
             return {"status": "success", "data": []}

        # Use mode="json" to automatically convert UUIDs and other objects to strings for JS
        data = [AIModelSchema.model_validate(m).model_dump(mode="json") for m in models]
            
        return {"status": "success", "data": data}

    except Exception as e:
        logger.error(f"Error fetching workspace models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/models")
async def add_model(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        ws_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        
        new_model = AIModel(
            workspace_id=ws_id,
            model_id=body.get("model_id"),
            name=body.get("name"),
            provider=body.get("provider"),
            description=body.get("description"),
            category=body.get("category"),
            tags=body.get("tags", []),
            series=body.get("series"),
            context_window=body.get("context_window"),
            model_size=body.get("model_size"),
            special_badge=body.get("special_badge"),
            api_url=body.get("api_url"),
            api_key=body.get("api_key"),
            is_custom=True,
            is_new=True
        )
        db.add(new_model)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding custom model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.put("/models/{model_uuid}")
async def update_model(model_uuid: str, request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        model = db.query(AIModel).filter_by(id=uuid.UUID(model_uuid)).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        # Update fields
        model.name = body.get("name", model.name)
        model.model_id = body.get("model_id", model.model_id)
        model.provider = body.get("provider", model.provider)
        model.description = body.get("description", model.description)
        model.category = body.get("category", model.category)
        model.tags = body.get("tags", model.tags)
        model.series = body.get("series", model.series)
        model.context_window = body.get("context_window", model.context_window)
        model.model_size = body.get("model_size", model.model_size)
        model.special_badge = body.get("special_badge", model.special_badge)
        model.api_url = body.get("api_url", model.api_url)
        model.api_key = body.get("api_key", model.api_key)
        
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.delete("/models/{model_uuid}")
async def delete_model(model_uuid: str, db: Session = Depends(get_db)):
    try:
        model = db.query(AIModel).filter_by(id=uuid.UUID(model_uuid)).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        db.delete(model)
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
