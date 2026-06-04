# core/ai_clients/reranker.py
import os
import requests
import logging
from db.connection import SessionLocal
from core.models import Workspace, AIModel

logger = logging.getLogger("reranker")
logging.basicConfig(level=logging.INFO)

def rerank_documents(query: str, documents: list, workspace_id: str = None) -> list:
    """
    Reranks documents using Cloud API (SiliconFlow/Qwen3 Reranker).
    """
    if not documents:
        return documents

    db = SessionLocal()
    api_key = None
    model_name = "Qwen/Qwen3-Reranker-0.6B"
    api_url = "https://api.siliconflow.com/v1/rerank"
    try:
        ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if not ws:
            ws = db.query(Workspace).first()
        if ws and ws.settings:
            if ws.settings.get("siliconflow_api_key"):
                api_key = ws.settings.get("siliconflow_api_key")
                
            custom_model_id = ws.settings.get("rerank_model")
            if custom_model_id:
                model_name = custom_model_id
                custom_model = db.query(AIModel).filter(
                    AIModel.model_id == custom_model_id,
                    AIModel.category == "Reranker"
                ).first()
                if custom_model:
                    if custom_model.api_key:
                        api_key = custom_model.api_key
                    if custom_model.api_url:
                        api_url = custom_model.api_url
    except Exception as e:
        logger.warning(f"Failed to query DB for custom reranker model: {e}")
    finally:
        db.close()

    if not api_key or api_key in ["your_api_key_here", "dummy_key_for_testing_do_not_use_cloud"]:
        error_msg = "🚨 BẮT BUỘC: Hệ thống thiếu cấu hình Reranker Model hoặc API Key. Vui lòng vào Cài đặt để thiết lập."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
        
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        texts = [doc.get("content", "") for doc in documents]
        payload = {
            "model": model_name,
            "query": query,
            "documents": texts,
            "top_n": len(documents)
        }
        
        response = requests.post(api_url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        # Results is usually a list of dicts like {"index": 0, "relevance_score": 0.8}
        results = data.get("results", [])
        score_map = {item["index"]: float(item.get("relevance_score", 0.0)) for item in results}
        
        for i, doc in enumerate(documents):
            doc["rerank_score"] = score_map.get(i, 0.0)
            
        # Log local rerank usage
        try:
            from core.decision_logger import log_decision
            log_decision(
                workspace_id=workspace_id,
                agent_name="Cloud API Reranker",
                action="Rerank Documents",
                decision_status="success",
                reason=f"Reranked {len(documents)} documents using {model_name} via API",
                metadata={"documents_count": len(documents), "model": model_name}
            )
        except Exception as r_err:
            logger.error(f"Failed to log rerank decision: {r_err}")
            
        return sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
    except Exception as e:
        logger.error(f"Error in Cloud API rerank_documents: {e}")
        raise RuntimeError(f"Error in Cloud API rerank_documents: {e}")

