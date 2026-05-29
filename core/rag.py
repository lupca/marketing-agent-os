# core/rag.py
import math
import logging
from sqlalchemy import text
from sqlalchemy.orm import Session
from db.connection import is_mock
from core.models import RAGKnowledgebase
from core.ollama_client import get_embedding, rerank_documents

logger = logging.getLogger("core_rag")
logging.basicConfig(level=logging.INFO)

def python_cosine_similarity(v1: list, v2: list) -> float:
    """Compute cosine similarity of two vectors in pure Python."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)

def store_knowledge(db: Session, workspace_id, category: str, source_name: str, content: str, metadata: dict = None) -> RAGKnowledgebase:
    """Generate embedding for text content and save to database."""
    if not content or len(content.strip()) < 5:
        return None
        
    logger.info(f"Generating embedding for chunk from '{source_name}' ({category})...")
    vector = get_embedding(content)
    
    # Create model record
    kb_record = RAGKnowledgebase(
        workspace_id=workspace_id,
        category=category,
        source_name=source_name,
        content=content,
        meta_data=metadata or {},
        embedding=vector
    )
    
    db.add(kb_record)
    db.commit()
    db.refresh(kb_record)
    logger.info(f"Saved RAG record: ID {kb_record.id}")
    return kb_record

def retrieve_knowledge(db: Session, workspace_id, query: str, categories: list = None, limit: int = 10) -> list:
    """
    Retrieve top-K similar text chunks using vector similarity.
    Works natively on both pgvector and SQLite mock fallback.
    """
    if not query:
        return []
        
    logger.info(f"Querying RAG: '{query}' (Categories: {categories})...")
    query_vector = get_embedding(query)
    
    # 1. PostgreSQL with pgvector cosine similarity
    if not is_mock():
        try:
            # Construct standard pgvector cosine distance query (represented by <=>)
            query_obj = db.query(RAGKnowledgebase)
            if workspace_id:
                query_obj = query_obj.filter(RAGKnowledgebase.workspace_id == workspace_id)
            if categories:
                query_obj = query_obj.filter(RAGKnowledgebase.category.in_(categories))
                
            # pgvector ordering
            query_obj = query_obj.order_by(RAGKnowledgebase.embedding.cosine_distance(query_vector))
            records = query_obj.limit(limit).all()
            
            results = []
            for r in records:
                results.append({
                    "id": str(r.id),
                    "category": r.category,
                    "source_name": r.source_name,
                    "content": r.content,
                    "metadata": r.meta_data,
                    "score": 1.0  # Cosine distance doesn't map directly to 0-1 similarity but works for ranking
                })
            return results
        except Exception as e:
            logger.error(f"PostgreSQL pgvector query failed: {e}. Falling back to Python similarity.")
            
    # 2. SQLite / Mock fallback with Python-calculated cosine similarity
    logger.info("Computing vector similarity in memory (SQLite fallback active)...")
    query_obj = db.query(RAGKnowledgebase)
    if workspace_id:
        query_obj = query_obj.filter(RAGKnowledgebase.workspace_id == workspace_id)
    if categories:
        query_obj = query_obj.filter(RAGKnowledgebase.category.in_(categories))
        
    all_records = query_obj.all()
    scored_records = []
    
    for r in all_records:
        if r.embedding:
            # Load stored embedding vector (handles text/json parsing via SQLite type decoders)
            emb = r.embedding
            similarity = python_cosine_similarity(query_vector, emb)
            scored_records.append((r, similarity))
            
    # Sort by similarity descending
    scored_records.sort(key=lambda x: x[1], reverse=True)
    
    results = []
    for r, score in scored_records[:limit]:
        results.append({
            "id": str(r.id),
            "category": r.category,
            "source_name": r.source_name,
            "content": r.content,
            "metadata": r.meta_data,
            "score": score
        })
    logger.info(f"Retrieved {len(results)} mock records.")
    return results

def retrieve_knowledge_reranked(db: Session, workspace_id, query: str, categories: list = None, limit: int = 3) -> list:
    """Retrieve top documents with cosine similarity (K=10) and rerank (Top-3) using bge-reranker-large."""
    # Retrieve top 10 first
    candidates = retrieve_knowledge(db, workspace_id, query, categories, limit=10)
    if not candidates:
        return []
        
    logger.info(f"Reranking {len(candidates)} candidates for query '{query}'...")
    reranked = rerank_documents(query, candidates)
    
    # Return top K
    return reranked[:limit]

def inject_antipatterns_to_prompt(db: Session, workspace_id, product_name: str, base_prompt: str) -> str:
    """
    Python-enforced prompt injection (SOP discipline).
    Automatically fetches failed marketing kịch bản (anti-patterns) and appends to prompt.
    """
    logger.info(f"Enforcing RAG Anti-patterns injection for product '{product_name}'...")
    
    # Search RAG specifically for failed campaigns (anti_patterns category)
    query = f"mẫu quảng cáo thất bại sai lầm sản phẩm {product_name}"
    failed_cases = retrieve_knowledge_reranked(
        db, 
        workspace_id, 
        query, 
        categories=["anti_patterns"], 
        limit=2
    )
    
    if not failed_cases:
        logger.info("No previous anti-patterns found. Skipping injection.")
        return base_prompt
        
    logger.info(f"Found {len(failed_cases)} failures! Prepending to prompt.")
    injection_md = "\n\n## CÁC BÀI HỌC THẤT BẠI CẦN TRÁNH (TUÂN THỦ SẤP SOP - CẤM LẶP LẠI)\n"
    for i, item in enumerate(failed_cases):
        injection_md += f"{i+1}. KỊCH BẢN THẤT BẠI TRƯỚC ĐÂY (variant_id: {item.get('id')}):\n"
        injection_md += f"   - Nội dung: \"{item.get('content')}\"\n"
        meta = item.get("metadata", {})
        injection_md += f"   - Lý do bị tắt: CPA {meta.get('failed_cpa', 'vượt ngưỡng')} VNĐ > Target CPA {meta.get('target_cpa', '')} VNĐ.\n"
        
    injection_md += "Tuyệt đối KHÔNG ĐƯỢC lặp lại các lối tư duy, cách giật tít, hay từ khóa từ những kịch bản thất bại trên!\n\n"
    
    return injection_md + base_prompt
