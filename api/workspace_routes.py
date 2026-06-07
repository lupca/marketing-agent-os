from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
import uuid
import logging
from core.dependencies import get_db, get_current_user
from core.models import User, Workspace, WorkspaceIntegration, AIModel, SocialAccount, MarketingCampaign
from core.schemas import WorkspaceIntegrationSchema, AIModelSchema
from typing import List

logger = logging.getLogger("workspace_routes")

def get_active_workspace_id(request: Request, db: Session = None) -> uuid.UUID:
    ws_id_str = request.query_params.get("workspace_id") or request.headers.get("x-workspace-id")
    
    # Extract authenticated user UUID if present
    auth_header = request.headers.get("authorization")
    user_uuid = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        from core.auth import decode_access_token
        payload = decode_access_token(token)
        if payload:
            user_id_str = payload.get("sub")
            if user_id_str:
                try:
                    user_uuid = uuid.UUID(user_id_str)
                except ValueError:
                    pass

    # Resolve workspace ID
    resolved_ws_uuid = None
    if ws_id_str:
        try:
            resolved_ws_uuid = uuid.UUID(ws_id_str)
        except ValueError:
            pass

    # If workspace ID is explicitly resolved, verify authorization
    if resolved_ws_uuid:
        if user_uuid:
            close_db = False
            if db is None:
                from db.connection import SessionLocal
                db = SessionLocal()
                close_db = True
            try:
                ws = db.query(Workspace).filter(Workspace.id == resolved_ws_uuid).first()
                if ws:
                    is_owner = (ws.owner_id == user_uuid)
                    is_member = (str(user_uuid) in [str(m) for m in (ws.members or [])])
                    if not (is_owner or is_member):
                        raise HTTPException(status_code=403, detail="Access to this workspace is forbidden")
                    return resolved_ws_uuid
            finally:
                if close_db:
                    db.close()
        else:
            return resolved_ws_uuid

    # If no workspace ID was passed, find a default workspace associated with the authenticated user
    if user_uuid:
        close_db = False
        if db is None:
            from db.connection import SessionLocal
            db = SessionLocal()
            close_db = True
        try:
            # 1. Search for a workspace owned by this user
            ws = db.query(Workspace).filter(Workspace.owner_id == user_uuid).first()
            if not ws:
                # 2. Check if the user is a member of any workspace
                workspaces = db.query(Workspace).all()
                for w in workspaces:
                    if str(user_uuid) in [str(m) for m in (w.members or [])]:
                        ws = w
                        break
            if ws:
                return ws.id
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to query workspace for authorized user: {e}")
        finally:
            if close_db:
                db.close()

    close_db = False
    if db is None:
        from db.connection import SessionLocal
        db = SessionLocal()
        close_db = True
    try:
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if not ws:
            ws = db.query(Workspace).first()
        if ws:
            return ws.id
    except Exception as e:
        logger.error(f"Failed to dynamically query default workspace: {e}")
    finally:
        if close_db:
            db.close()
        
    return uuid.UUID("00000000-0000-0000-0000-000000000002")  # absolute final fallback if DB empty

workspace_router = APIRouter(prefix="/api/workspace", tags=["Workspace"])

@workspace_router.get("/settings")
async def get_settings(request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
        ws = db.query(Workspace).filter_by(id=ws_id).first()
        return ws.settings if (ws and ws.settings) else {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/settings")
async def update_settings(request: Request, db: Session = Depends(get_db)):
    ALLOWED_SETTINGS = {"ai_model", "embed_model", "rerank_model", "temperature", "max_tokens", "recursion_limit",
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
            
        ws_id = get_active_workspace_id(request, db)
        ws = db.query(Workspace).filter_by(id=ws_id).first()
        if ws:
            current_settings = dict(ws.settings) if ws.settings else {}
            current_settings.update(filtered)
            ws.settings = current_settings
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(ws, "settings")
            db.commit()
            return {"status": "success"}
        raise HTTPException(status_code=404, detail="Workspace not found")
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving workspace settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/integrations")
async def get_integrations(request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace integrations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/integrations")
async def update_integration(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        ws_id = get_active_workspace_id(request, db)
    
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
    except HTTPException:
        raise
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
        
        ws_id = get_active_workspace_id(request, db)
        integration = db.query(WorkspaceIntegration).filter_by(id=uuid.UUID(integration_id), workspace_id=ws_id).first()
        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found or access denied")
        db.delete(integration)
        db.commit()
        return {"status": "success", "message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting workspace integration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/models")
async def get_models(request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
        models = db.query(AIModel).filter_by(workspace_id=ws_id).order_by(AIModel.created_at.desc()).all()
        # Note: Logic to seed default models could be moved to a service or seed script.
        # For now, let's keep it here but using the new response model.
        if not models:
             # Just return empty list or handle seeding if absolutely necessary
             return {"status": "success", "data": []}

        # Use mode="json" to automatically convert UUIDs and other objects to strings for JS
        data = [AIModelSchema.model_validate(m).model_dump(mode="json") for m in models]
            
        return {"status": "success", "data": data}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching workspace models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/models")
async def add_model(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        ws_id = get_active_workspace_id(request, db)
        
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding custom model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.put("/models/{model_uuid}")
async def update_model(model_uuid: str, request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        ws_id = get_active_workspace_id(request, db)
        model = db.query(AIModel).filter_by(id=uuid.UUID(model_uuid), workspace_id=ws_id).first()
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
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.delete("/models/{model_uuid}")
async def delete_model(model_uuid: str, request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
        model = db.query(AIModel).filter_by(id=uuid.UUID(model_uuid), workspace_id=ws_id).first()
        if not model:
            raise HTTPException(status_code=404, detail="Model not found")
        
        db.delete(model)
        db.commit()
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting model: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/social-accounts")
async def get_social_accounts(request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
        accounts = db.query(SocialAccount).filter_by(workspace_id=ws_id).order_by(
            SocialAccount.platform, SocialAccount.account_name
        ).all()
        data = []
        for a in accounts:
            data.append({
                "id": str(a.id),
                "platform": a.platform,
                "account_name": a.account_name,
                "account_id": a.account_id,
                "app_id": a.app_id,
                "app_secret": a.app_secret,
                "access_token": a.access_token,
                "status": a.status or "active",
                "created_at": a.created_at.strftime('%Y-%m-%d %H:%M:%S') if a.created_at else None
            })
        return {"status": "success", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching social accounts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.post("/social-accounts")
async def save_social_account(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        ws_id = get_active_workspace_id(request, db)
        
        record_id = body.get("id")
        platform = body.get("platform")
        account_name = body.get("account_name")
        account_id = body.get("account_id")
        app_id = body.get("app_id")
        app_secret = body.get("app_secret")
        access_token = body.get("access_token")
        status = body.get("status", "active")
        
        if not platform or not account_name or not account_id:
            raise HTTPException(status_code=400, detail="Missing required fields: platform, account_name, account_id")
            
        existing = None
        if record_id:
            try:
                existing = db.query(SocialAccount).filter_by(id=uuid.UUID(record_id)).first()
            except Exception:
                pass
                
        if not existing:
            # Check by workspace, platform, account_id
            existing = db.query(SocialAccount).filter_by(
                workspace_id=ws_id,
                platform=platform,
                account_id=account_id
            ).first()
            
        if existing:
            existing.account_name = account_name
            existing.account_id = account_id
            existing.app_id = app_id
            existing.app_secret = app_secret
            existing.access_token = access_token
            existing.status = status
            existing.updated_at = func.now()
            db.commit()
            return {"status": "success", "message": "Updated successfully"}
        else:
            new_social = SocialAccount(
                workspace_id=ws_id,
                platform=platform,
                account_name=account_name,
                account_id=account_id,
                app_id=app_id,
                app_secret=app_secret,
                access_token=access_token,
                status=status
            )
            db.add(new_social)
            db.commit()
            return {"status": "success", "message": "Created successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving social account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.delete("/social-accounts/{account_uuid}")
async def delete_social_account(account_uuid: str, request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
        account = db.query(SocialAccount).filter_by(id=uuid.UUID(account_uuid), workspace_id=ws_id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Social Account not found")
            
        db.delete(account)
        db.commit()
        return {"status": "success", "message": "Deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting social account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/list")
async def list_workspaces(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        workspaces = db.query(Workspace).all()
        data = []
        for w in workspaces:
            is_owner = (w.owner_id == current_user.id)
            user_uuid_str = str(current_user.id)
            members_str_list = [str(m) for m in (w.members or [])]
            is_member = (user_uuid_str in members_str_list)
            
            if is_owner or is_member:
                data.append({"id": str(w.id), "name": w.name})
                
        data.sort(key=lambda x: x["name"])
        return {"status": "success", "data": data}
    except Exception as e:
        logger.error(f"Error listing workspaces: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@workspace_router.get("/campaigns")
async def list_campaigns(request: Request, db: Session = Depends(get_db)):
    try:
        ws_id = get_active_workspace_id(request, db)
        query = db.query(MarketingCampaign).filter_by(workspace_id=ws_id)
        campaigns = query.order_by(MarketingCampaign.name).all()
        data = [{
            "id": str(c.id),
            "name": c.name,
            "workspace_id": str(c.workspace_id),
            "product_id": str(c.product_id) if c.product_id else None,
            "campaign_type": c.campaign_type
        } for c in campaigns]
        return {"status": "success", "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing campaigns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
