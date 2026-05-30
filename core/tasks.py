# core/tasks.py
"""
Celery Tasks cho hệ thống RAG Knowledge Base.

Task 1 — ingest_document    : Băm file → embed → insert rag_chunks
Task 2 — cascade_update_tags: Đồng bộ access_tags xuống tất cả chunks của 1 document
Task 3 — cascade_soft_delete: Set is_deleted=TRUE trên tất cả chunks của 1 document
"""
import logging
import tempfile
import os
from celery import shared_task
from sqlalchemy import text

from core.celery_app import celery_app
from db.connection import SessionLocal
from core.ollama_client import get_embedding
from core.parser import extract_text_from_file, semantic_chunk_text
from core.storage import download_file_from_minio

logger = logging.getLogger("core_tasks")

# ============================================================
# TASK 1: Ingestion Pipeline
# ============================================================
@celery_app.task(
    bind=True,
    name="core.tasks.ingest_document",
    queue="rag_ingestion",
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def ingest_document(self, document_id: str, file_key: str, workspace_id: str, access_tags: list):
    """
    Pipeline băm vector cho 1 tài liệu:
    1. Download file từ MinIO
    2. Extract text (PDF / TXT / DOCX / XLSX)
    3. Semantic chunking (RecursiveCharacterTextSplitter)
    4. Generate embeddings cho từng chunk (bge-m3)
    5. Batch INSERT vào rag_chunks
    6. UPDATE rag_documents: status='ready', chunk_count=N
    """
    db = SessionLocal()
    tmp_path = None
    try:
        logger.info(f"[ingest_document] START document_id={document_id}, file_key={file_key}")

        # ---- Bước 1: Download file từ MinIO ----
        tmp_dir = tempfile.mkdtemp()
        # Lấy extension từ file_key
        ext = os.path.splitext(file_key)[-1] or ".bin"
        tmp_path = os.path.join(tmp_dir, f"doc{ext}")
        download_file_from_minio(file_key, tmp_path)
        logger.info(f"[ingest_document] Downloaded to {tmp_path}")

        # ---- Bước 2: Extract text ----
        raw_text = extract_text_from_file(tmp_path)
        if not raw_text or len(raw_text.strip()) < 10:
            raise ValueError(f"File rỗng hoặc không extract được text: {file_key}")

        # ---- Bước 3: Semantic chunking ----
        chunks = semantic_chunk_text(raw_text)
        if not chunks:
            raise ValueError(f"Không tạo được chunk nào từ file: {file_key}")
        logger.info(f"[ingest_document] Created {len(chunks)} chunks")

        # ---- Bước 4+5: Embed + Batch INSERT ----
        access_tags_json = str(access_tags).replace("'", '"')  # Đảm bảo JSON hợp lệ
        import json
        access_tags_jsonb = json.dumps(access_tags, ensure_ascii=False)

        inserted = 0
        for idx, chunk_content in enumerate(chunks):
            if not chunk_content or len(chunk_content.strip()) < 5:
                continue

            vector = get_embedding(chunk_content)
            if not vector:
                logger.warning(f"[ingest_document] Embedding rỗng cho chunk {idx}, bỏ qua")
                continue

            db.execute(
                text("""
                    INSERT INTO rag_chunks
                        (document_id, workspace_id, content, embedding,
                         chunk_index, access_tags, is_deleted)
                    VALUES
                        (:document_id, :workspace_id, :content, CAST(:embedding AS vector),
                         :chunk_index, CAST(:access_tags AS jsonb), FALSE)
                """),
                {
                    "document_id":  document_id,
                    "workspace_id": workspace_id,
                    "content":      chunk_content.strip(),
                    "embedding":    f"[{','.join(str(v) for v in vector)}]",
                    "chunk_index":  idx,
                    "access_tags":  access_tags_jsonb,
                }
            )
            inserted += 1

            # Commit theo batch 20 chunks (tránh transaction quá lớn)
            if inserted % 20 == 0:
                db.commit()
                logger.info(f"[ingest_document] Committed {inserted}/{len(chunks)} chunks")

        db.commit()

        # ---- Bước 6: Cập nhật rag_documents ----
        db.execute(
            text("""
                UPDATE rag_documents
                SET upload_status = 'ready',
                    chunk_count   = :chunk_count,
                    updated_at    = NOW()
                WHERE document_id = :document_id
            """),
            {"document_id": document_id, "chunk_count": inserted}
        )
        db.commit()
        logger.info(f"[ingest_document] DONE document_id={document_id}, inserted={inserted} chunks")
        return {"status": "ok", "document_id": document_id, "chunks_inserted": inserted}

    except Exception as exc:
        db.rollback()
        logger.error(f"[ingest_document] FAILED document_id={document_id}: {exc}", exc_info=True)

        # Cập nhật trạng thái lỗi vào DB
        try:
            db.execute(
                text("UPDATE rag_documents SET upload_status='failed', updated_at=NOW() WHERE document_id=:id"),
                {"id": document_id}
            )
            db.commit()
        except Exception:
            pass

        # Retry tự động (Celery sẽ retry sau 30s, tối đa 3 lần)
        raise self.retry(exc=exc)

    finally:
        db.close()
        # Dọn file tạm
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


# ============================================================
# TASK 2: Cascade Update Tags
# ============================================================
@celery_app.task(
    bind=True,
    name="core.tasks.cascade_update_tags",
    queue="rag_cascade",
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
)
def cascade_update_tags(self, document_id: str, new_tags: list):
    """
    Đồng bộ access_tags xuống tất cả rag_chunks thuộc document_id.
    Chạy ngầm sau khi user chỉnh sửa tag trên UI.
    """
    import json
    db = SessionLocal()
    try:
        logger.info(f"[cascade_update_tags] START document_id={document_id}, new_tags={new_tags}")

        new_tags_jsonb = json.dumps(new_tags, ensure_ascii=False)

        result = db.execute(
            text("""
                UPDATE rag_chunks
                SET access_tags = CAST(:tags AS jsonb)
                WHERE document_id = :document_id
            """),
            {"document_id": document_id, "tags": new_tags_jsonb}
        )
        rows_updated = result.rowcount

        # Cập nhật sync_status về synced
        db.execute(
            text("""
                UPDATE rag_documents
                SET sync_status = 'synced',
                    access_tags = CAST(:tags AS jsonb),
                    updated_at  = NOW()
                WHERE document_id = :document_id
            """),
            {"document_id": document_id, "tags": new_tags_jsonb}
        )
        db.commit()

        logger.info(f"[cascade_update_tags] DONE document_id={document_id}, rows_updated={rows_updated}")
        return {"status": "ok", "document_id": document_id, "chunks_updated": rows_updated}

    except Exception as exc:
        db.rollback()
        logger.error(f"[cascade_update_tags] FAILED document_id={document_id}: {exc}", exc_info=True)

        try:
            db.execute(
                text("UPDATE rag_documents SET sync_status='failed', updated_at=NOW() WHERE document_id=:id"),
                {"id": document_id}
            )
            db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc)

    finally:
        db.close()


# ============================================================
# TASK 3: Cascade Soft Delete
# ============================================================
@celery_app.task(
    bind=True,
    name="core.tasks.cascade_soft_delete",
    queue="rag_cascade",
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
)
def cascade_soft_delete(self, document_id: str):
    """
    Soft-delete tất cả rag_chunks thuộc document_id (is_deleted=TRUE).
    Chunks bị deleted sẽ tự động bị loại khỏi mọi retrieval query (Zero-JOIN filter).
    """
    db = SessionLocal()
    try:
        logger.info(f"[cascade_soft_delete] START document_id={document_id}")

        result = db.execute(
            text("""
                UPDATE rag_chunks
                SET is_deleted = TRUE
                WHERE document_id = :document_id AND is_deleted = FALSE
            """),
            {"document_id": document_id}
        )
        rows_updated = result.rowcount

        db.execute(
            text("""
                UPDATE rag_documents
                SET is_deleted  = TRUE,
                    sync_status = 'synced',
                    updated_at  = NOW()
                WHERE document_id = :document_id
            """),
            {"document_id": document_id}
        )
        db.commit()

        logger.info(f"[cascade_soft_delete] DONE document_id={document_id}, rows_marked={rows_updated}")
        return {"status": "ok", "document_id": document_id, "chunks_marked": rows_updated}

    except Exception as exc:
        db.rollback()
        logger.error(f"[cascade_soft_delete] FAILED document_id={document_id}: {exc}", exc_info=True)

        try:
            db.execute(
                text("UPDATE rag_documents SET sync_status='failed', updated_at=NOW() WHERE document_id=:id"),
                {"id": document_id}
            )
            db.commit()
        except Exception:
            pass

        raise self.retry(exc=exc)

    finally:
        db.close()
