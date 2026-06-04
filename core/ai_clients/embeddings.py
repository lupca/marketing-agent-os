# core/ai_clients/embeddings.py
import os
import requests
import logging
from db.connection import SessionLocal
from core.models import Workspace, AIModel

logger = logging.getLogger("embeddings")
logging.basicConfig(level=logging.INFO)

def get_embedding(text_content: str) -> list:
    """Generate vector embedding (1024-dim) using Cloud API (SiliconFlow/Qwen3)."""
    db = SessionLocal()
    api_key = None
    model_name = "Qwen/Qwen3-Embedding-0.6B"
    api_url = "https://api.siliconflow.com/v1/embeddings"
    
    try:
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if not ws:
            ws = db.query(Workspace).first()
        if ws and ws.settings:
            if ws.settings.get("siliconflow_api_key"):
                api_key = ws.settings.get("siliconflow_api_key")
                
            custom_model_id = ws.settings.get("embed_model")
            if custom_model_id:
                model_name = custom_model_id
                # Attempt to find the AIModel config to get custom API keys if provided
                custom_model = db.query(AIModel).filter(
                    AIModel.model_id == custom_model_id,
                    AIModel.category == "Embedding"
                ).first()
                if custom_model:
                    if custom_model.api_key:
                        api_key = custom_model.api_key
                    if custom_model.api_url:
                        api_url = custom_model.api_url
    except Exception as e:
        logger.warning(f"Failed to query DB for custom embedding model: {e}")
    finally:
        db.close()

    if not api_key or api_key in ["your_api_key_here", "dummy_key_for_testing_do_not_use_cloud"]:
        error_msg = "🚨 BẮT BUỘC: Hệ thống thiếu cấu hình Embedding Model hoặc API Key. Vui lòng vào Cài đặt để thiết lập."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "input": text_content,
            "encoding_format": "float"
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        return data["data"][0]["embedding"]
    except Exception as e:
        logger.error(f"Error in Cloud API get_embedding: {e}")
        raise RuntimeError(f"Error in Cloud API get_embedding: {e}")

