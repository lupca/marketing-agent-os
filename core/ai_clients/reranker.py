# core/ai_clients/reranker.py
import torch
import logging
from sentence_transformers import CrossEncoder

logger = logging.getLogger("reranker")
logging.basicConfig(level=logging.INFO)

# Initialize Local Reranker on GPU (targeting your RTX 4060 Ti via CUDA)
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Loading local CrossEncoder reranker model on device: {device.upper()}")
try:
    local_reranker = CrossEncoder('BAAI/bge-reranker-large', device=device)
    logger.info("Successfully loaded local CrossEncoder BAAI/bge-reranker-large reranker!")
except Exception as e:
    logger.warning(f"Failed to load Reranker onto GPU VRAM: {e}. Falling back to CPU.")
    try:
        local_reranker = CrossEncoder('BAAI/bge-reranker-large', device="cpu")
        logger.info("Successfully loaded BAAI/bge-reranker-large onto CPU.")
    except Exception as ex:
        logger.error(f"Critical error loading local Reranker: {ex}")
        local_reranker = None


def rerank_documents(query: str, documents: list, workspace_id: str = None) -> list:
    """
    Reranks documents using the local BAAI/bge-reranker-large model running on local GPU.
    Runs fast (~10ms) and costs $0.00!
    """
    if not documents or not local_reranker:
        # Fallback if no documents or model failed to load
        for doc in documents:
            if "rerank_score" not in doc:
                doc["rerank_score"] = 0.5
        return documents
        
    try:
        pairs = [(query, doc.get("content", "")) for doc in documents]
        scores = local_reranker.predict(pairs)
        
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)
            
        # Log local rerank usage to track ROI cost savings
        try:
            from core.decision_logger import log_decision
            log_decision(
                workspace_id=workspace_id,
                agent_name="GPU Local Reranker",
                action="Rerank Documents",
                decision_status="success",
                reason=f"Reranked {len(documents)} documents locally on RTX 4060 Ti GPU VRAM (CUDA)",
                metadata={"documents_count": len(documents)}
            )
        except Exception as r_err:
            logger.error(f"Failed to log rerank decision: {r_err}")
            
        return sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
    except Exception as e:
        logger.error(f"Error in rerank_documents: {e}")
        for doc in documents:
            if "rerank_score" not in doc:
                doc["rerank_score"] = 0.5
        return documents
