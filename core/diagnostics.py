# core/diagnostics.py
import os
import logging
from sqlalchemy.orm import Session
from core.models import Workspace, AIModel

logger = logging.getLogger("diagnostics")

import uuid

def check_system_readiness(db: Session, workspace_id: str = None) -> dict:
    """
    Kiểm tra tính toàn vẹn của hệ thống tự trị.
    Bắt buộc phải có đủ cấu hình (API Key, model selection) cho Embeddings, Reranker và LLM.
    """
    missing_components = []
    
    ws = None
    if workspace_id:
        try:
            ws = db.query(Workspace).filter(Workspace.id == uuid.UUID(workspace_id)).first()
        except Exception:
            pass
    if not ws:
        try:
            ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        except Exception:
            pass

    if not ws:
        # Fallback to the first created workspace dynamically
        try:
            ws = db.query(Workspace).order_by(Workspace.created_at).first()
        except Exception:
            pass
            
    if not ws:
        # Final fallback to first workspace ordered by name
        ws = db.query(Workspace).order_by(Workspace.name).first()
        
    if not ws:
        return {
            "is_ready": False,
            "missing_components": ["Workspace (Chưa khởi tạo)"]
        }
        
    settings = ws.settings or {}
    
    # helper function to check if a key is a dummy placeholder
    def is_invalid_key(key):
        return not key or key in ["your_api_key_here", "dummy_key_for_testing_do_not_use_cloud"]

    # 1. Check Embeddings
    embed_model_id = settings.get("embed_model")
    if not embed_model_id:
        missing_components.append("Embedding Model (Chưa được chọn trong Cài đặt)")
    else:
        embed_api_key = settings.get("siliconflow_api_key")
        embed_model = db.query(AIModel).filter(
            AIModel.model_id == embed_model_id,
            AIModel.category == "Embedding"
        ).first()
        if embed_model and embed_model.api_key:
            embed_api_key = embed_model.api_key
            
        if is_invalid_key(embed_api_key):
            missing_components.append("Embedding Model (Thiếu cấu hình API Key)")
        
    # 2. Check Reranker
    rerank_model_id = settings.get("rerank_model")
    if not rerank_model_id:
        missing_components.append("Reranker Model (Chưa được chọn trong Cài đặt)")
    else:
        rerank_api_key = settings.get("siliconflow_api_key")
        rerank_model = db.query(AIModel).filter(
            AIModel.model_id == rerank_model_id,
            AIModel.category == "Reranker"
        ).first()
        if rerank_model and rerank_model.api_key:
            rerank_api_key = rerank_model.api_key
                
        if is_invalid_key(rerank_api_key):
            missing_components.append("Reranker Model (Thiếu cấu hình API Key)")
        
    # 3. Check LLM
    ai_model_id = settings.get("ai_model")
    if not ai_model_id:
        missing_components.append("LLM/Chat Model (Chưa được chọn trong Cài đặt)")
    else:
        llm_ready = False
        if "gpt-" in ai_model_id.lower() or "claude-" in ai_model_id.lower() or "gemini-" in ai_model_id.lower():
            llm_model = db.query(AIModel).filter(AIModel.model_id == ai_model_id).first()
            if llm_model and llm_model.api_key and not is_invalid_key(llm_model.api_key):
                llm_ready = True
            elif not is_invalid_key(os.getenv("OPENAI_API_KEY")):
                llm_ready = True
        elif "/" in ai_model_id:
            # Model from Hub / SiliconFlow etc.
            llm_model = db.query(AIModel).filter(AIModel.model_id == ai_model_id).first()
            if llm_model and llm_model.api_key and not is_invalid_key(llm_model.api_key):
                llm_ready = True
            elif not is_invalid_key(settings.get("siliconflow_api_key")):
                llm_ready = True
        else:
            # Ollama or Local
            llm_ready = True
            
        if not llm_ready:
            missing_components.append("LLM/Chat Model (Thiếu cấu hình API Key)")
            
    is_ready = len(missing_components) == 0
    
    if not is_ready:
        logger.critical(f"SYSTEM READINESS FAILED! Missing components: {', '.join(missing_components)}")
    else:
        logger.info("System diagnostics passed. All autonomous core components are ready.")
        
    return {
        "is_ready": is_ready,
        "missing_components": missing_components
    }
