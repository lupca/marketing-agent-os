# core/rag.py
"""
RAG Core v2 — Hệ thống truy xuất tri thức Zero-JOIN.

Kiến trúc Pool-Tags-Keys:
  - Pool    : Bảng rag_chunks chứa toàn bộ vectors
  - Tags    : JSONB access_tags filter (Pre-Retrieval, không JOIN)
  - Keys    : workspace_id + access_tags xác định quyền của Agent

Thay thế hoàn toàn rag.py cũ (đã dùng bảng rag_knowledgebase flat).
"""
import json
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from core.models import RAGDocument
from core.ollama_client import get_embedding, rerank_documents
from workers.rag_worker.tasks import ingest_document as ingest_document_task
from config.settings import RAG_RETRIEVAL_LIMIT, RAG_CANDIDATE_LIMIT

logger = logging.getLogger("core_rag")


# ============================================================
# WRITE: Tạo document record + kích hoạt Celery ingestion
# ============================================================
def store_document(
    db: Session,
    workspace_id: str,
    file_name: str,
    file_key: str,
    access_tags: list,
    file_size_bytes: int = 0,
    file_hash: str = None,
    metadata: dict = None
) -> RAGDocument:
    """
    Tạo record rag_documents (upload_status='processing') và
    đẩy Celery task ingest_document để băm vector ngầm.

    Returns: RAGDocument ORM record (status='processing')
    """
    tags = access_tags if access_tags else ["global"]

    doc = RAGDocument(
        workspace_id=str(workspace_id),
        file_name=file_name,
        file_key=file_key,
        access_tags=tags,
        upload_status="processing",
        sync_status="synced",
        file_size_bytes=file_size_bytes,
        file_hash=file_hash,
        meta_data=metadata or {}
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Kick off async Celery task
    try:
        ingest_document_task.delay(
            document_id=str(doc.document_id),
            file_key=file_key,
            workspace_id=str(workspace_id),
            access_tags=tags,
        )
    except Exception as queue_err:
        logger.error(f"[store_document] Celery task dispatch failed: {queue_err}", exc_info=True)
        doc.upload_status = "failed"
        db.commit()
        raise queue_err

    logger.info(f"[store_document] Created document_id={doc.document_id}, task pushed to Celery.")
    return doc


# ============================================================
# READ: Zero-JOIN vector retrieval
# ============================================================
def retrieve_chunks(
    db: Session,
    workspace_id: str,
    query: str,
    access_tags: list = None,
    limit: int = None,
) -> list[dict]:
    """
    Truy xuất top-K chunks liên quan nhất bằng cosine similarity.

    Zero-JOIN: Query thẳng vào rag_chunks với:
      - workspace_id filter    (cách ly multi-tenant)
      - access_tags ?| filter  (phân quyền Agent, GIN Index)
      - is_deleted = FALSE     (bỏ qua đã xóa mềm)
      - ORDER BY embedding <=> (HNSW cosine distance)

    Args:
        access_tags: Danh sách tag Agent có quyền truy cập.
                     VD: ["marketing", "global"] — trả về chunk có BẤT KỲ tag nào khớp.
    """
    if not query:
        return []

    tags = access_tags if access_tags else ["global"]
    k = limit or RAG_CANDIDATE_LIMIT

    logger.info(f"[retrieve_chunks] query='{query[:60]}...', tags={tags}, limit={k}")

    query_vector = get_embedding(query)
    if not query_vector:
        logger.error("[retrieve_chunks] Embedding rỗng, bỏ qua retrieval.")
        return []

    vector_str = f"[{','.join(str(v) for v in query_vector)}]"
    tags_array = "{" + ",".join(tags) + "}"  # PostgreSQL array literal

    try:
        rows = db.execute(
            text("""
                SELECT
                    CAST(chunk_id AS TEXT),
                    CAST(document_id AS TEXT),
                    content,
                    chunk_index,
                    access_tags,
                    1 - (embedding <=> CAST(:vector AS vector)) AS similarity_score
                FROM rag_chunks
                WHERE workspace_id = CAST(:workspace_id AS uuid)
                  AND access_tags ?| CAST(:tags_array AS text[])
                  AND is_deleted = FALSE
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:vector AS vector)
                LIMIT :limit
            """),
            {
                "vector":       vector_str,
                "workspace_id": str(workspace_id),
                "tags_array":   tags_array,
                "limit":        k,
            }
        ).fetchall()

        results = [
            {
                "id":               row.chunk_id,
                "document_id":      row.document_id,
                "content":          row.content,
                "chunk_index":      row.chunk_index,
                "access_tags":      row.access_tags if isinstance(row.access_tags, list) else json.loads(row.access_tags),
                "similarity_score": float(row.similarity_score) if row.similarity_score else 0.0,
            }
            for row in rows
        ]

        logger.info(f"[retrieve_chunks] Found {len(results)} chunks.")
        return results

    except Exception as e:
        logger.error(f"[retrieve_chunks] Query failed: {e}", exc_info=True)
        return []


def retrieve_chunks_reranked(
    db: Session,
    workspace_id: str,
    query: str,
    access_tags: list = None,
    limit: int = None,
) -> list[dict]:
    """
    Retrieval nâng cao: top-K cosine similarity → rerank bằng bge-reranker-large → top-N.

    Pipeline:
      1. Lấy RAG_CANDIDATE_LIMIT (10) candidates từ HNSW
      2. Rerank bằng cross-encoder bge-reranker-large
      3. Trả về top RAG_RETRIEVAL_LIMIT (5) sau rerank
    """
    candidates = retrieve_chunks(
        db=db,
        workspace_id=workspace_id,
        query=query,
        access_tags=access_tags,
        limit=RAG_CANDIDATE_LIMIT,
    )
    if not candidates:
        return []

    logger.info(f"[retrieve_chunks_reranked] Reranking {len(candidates)} candidates...")
    reranked = rerank_documents(query, candidates, workspace_id=str(workspace_id))

    final_limit = limit or RAG_RETRIEVAL_LIMIT
    return reranked[:final_limit]


# ============================================================
# Utility: Anti-pattern injection (backward-compatible)
# ============================================================
def inject_antipatterns_to_prompt(
    db: Session,
    workspace_id: str,
    product_name: str,
    base_prompt: str,
) -> str:
    """
    Tự động fetch và inject các kịch bản quảng cáo thất bại (anti_patterns)
    vào prompt của Agent. Đảm bảo LLM không lặp lại lỗi cũ (SOP discipline).
    """
    logger.info(f"[inject_antipatterns_to_prompt] product='{product_name}'")

    query = f"mẫu quảng cáo thất bại sai lầm sản phẩm {product_name}"
    failed_cases = retrieve_chunks_reranked(
        db=db,
        workspace_id=workspace_id,
        query=query,
        access_tags=["anti_patterns", "sandbox_feedback"],
        limit=2,
    )

    if not failed_cases:
        logger.info("[inject_antipatterns_to_prompt] Không có anti-pattern nào — bỏ qua.")
        return base_prompt

    logger.info(f"[inject_antipatterns_to_prompt] Injecting {len(failed_cases)} anti-patterns.")
    injection_md = "\n\n## CÁC BÀI HỌC THẤT BẠI CẦN TRÁNH (TUÂN THỦ SẤP SOP — CẤM LẶP LẠI)\n"
    for i, item in enumerate(failed_cases):
        injection_md += f"{i+1}. KỊCH BẢN THẤT BẠI TRƯỚC ĐÂY (chunk_id: {item.get('id')}):\n"
        injection_md += f"   - Nội dung: \"{item.get('content', '')[:300]}...\"\n"
        tags = item.get("access_tags", [])
        if "manager_feedback" in tags:
            injection_md += "   - Nguồn: Feedback từ CMO.\n"

    injection_md += "Tuyệt đối KHÔNG ĐƯỢC lặp lại các lối tư duy, cách giật tít, hay từ khóa từ những kịch bản thất bại trên!\n\n"

    return injection_md + base_prompt
