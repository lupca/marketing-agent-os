import logging
import tempfile
import os
import uuid
from sqlalchemy import func
from core.celery_app import celery_app
from core.dependencies import get_session
from core.ollama_client import get_embedding
from core.parser import UniversalParser
from core.storage import download_file_from_minio
from core.models import RAGDocument, RAGChunk

logger = logging.getLogger("rag_worker_tasks")

# ============================================================
# TASK 1: Ingestion Pipeline
# ============================================================
@celery_app.task(
    bind=True,
    name="workers.rag_worker.tasks.ingest_document",
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
    5. Lưu vào PostgreSQL pgvector
    """
    with get_session() as db:
        tmp_path = None
        try:
            logger.info(f"[ingest_document] START document_id={document_id}, file_key={file_key}")

            # Fetch parent document to read metadata
            doc = db.query(RAGDocument).filter_by(document_id=uuid.UUID(str(document_id))).first()
            doc_metadata = doc.meta_data if (doc and doc.meta_data) else {}

            # ---- Bước 1: Download file từ MinIO ----
            tmp_dir = tempfile.mkdtemp()
            # Lấy extension từ file_key
            ext = os.path.splitext(file_key)[-1] or ".bin"
            tmp_path = os.path.join(tmp_dir, f"doc{ext}")
            download_file_from_minio(file_key, tmp_path)
            logger.info(f"[ingest_document] Downloaded to {tmp_path}")

            # ---- Bước 2: Extract text (Sử dụng UniversalParser tích hợp MarkItDown) ----
            parser = UniversalParser()
            raw_markdown = parser.extract_markdown(tmp_path)
            if not raw_markdown or len(raw_markdown.strip()) < 10:
                raise ValueError(f"File rỗng hoặc không trích xuất được Markdown: {file_key}")

            # ---- Bước 3: Semantic chunking (Chiến lược chunking 2 bước) ----
            chunks = parser.chunk_markdown(raw_markdown)
            if not chunks:
                raise ValueError(f"Không tạo được chunk nào từ file: {file_key}")
            logger.info(f"[ingest_document] Created {len(chunks)} chunks")

            # ---- Bước 4+5: Embed + Batch INSERT ----
            inserted = 0
            chunk_objects = []
            for idx, chunk_content in enumerate(chunks):
                if not chunk_content or len(chunk_content.strip()) < 5:
                    continue

                vector = get_embedding(chunk_content)
                if not vector:
                    logger.warning(f"[ingest_document] Embedding rỗng cho chunk {idx}, bỏ qua")
                    continue

                new_chunk = RAGChunk(
                    document_id=uuid.UUID(str(document_id)),
                    workspace_id=uuid.UUID(str(workspace_id)),
                    content=chunk_content.strip(),
                    embedding=vector,
                    chunk_index=idx,
                    access_tags=access_tags,
                    is_deleted=False,
                    meta_data=doc_metadata
                )
                chunk_objects.append(new_chunk)
                inserted += 1

                # Commit theo batch 20 chunks (tránh transaction quá lớn)
                if len(chunk_objects) >= 20:
                    db.bulk_save_objects(chunk_objects)
                    db.commit()
                    chunk_objects = []
                    logger.info(f"[ingest_document] Committed {inserted}/{len(chunks)} chunks")

            if chunk_objects:
                db.bulk_save_objects(chunk_objects)
                db.commit()

            # ---- Bước 6: Cập nhật rag_documents ----
            doc = db.query(RAGDocument).filter_by(document_id=uuid.UUID(str(document_id))).first()
            if doc:
                doc.upload_status = 'ready'
                doc.chunk_count = inserted
                doc.updated_at = func.now()
                db.commit()
            
            logger.info(f"[ingest_document] DONE document_id={document_id}, inserted={inserted} chunks")
            return {"status": "ok", "document_id": document_id, "chunks_inserted": inserted}

        except Exception as exc:
            db.rollback()
            logger.error(f"[ingest_document] FAILED document_id={document_id}: {exc}", exc_info=True)

            # Cập nhật trạng thái lỗi vào DB
            try:
                error_doc = db.query(RAGDocument).filter_by(document_id=uuid.UUID(str(document_id))).first()
                if error_doc:
                    error_doc.upload_status = 'failed'
                    error_doc.updated_at = func.now()
                    db.commit()
            except Exception:
                pass

            # Retry tự động (Celery sẽ retry sau 30s, tối đa 3 lần)
            raise self.retry(exc=exc)
        finally:
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
    name="workers.rag_worker.tasks.cascade_update_tags",
    queue="rag_cascade",
    max_retries=3,
    default_retry_delay=15,
    acks_late=True,
)
def cascade_update_tags(self, document_id: str, new_tags: list):
    """
    Đồng bộ tag từ rag_documents xuống toàn bộ rag_chunks liên quan.
    Dùng ORM để đảm bảo tính nhất quán.
    """
    with get_session() as db:
        try:
            logger.info(f"[cascade_update_tags] START document_id={document_id}, new_tags={new_tags}")

            doc_uuid = uuid.UUID(str(document_id))
            
            # Cập nhật rag_chunks
            db.query(RAGChunk).filter(RAGChunk.document_id == doc_uuid).update(
                {RAGChunk.access_tags: new_tags},
                synchronize_session=False
            )

            # Cập nhật rag_documents sync_status và tags
            doc = db.query(RAGDocument).filter_by(document_id=doc_uuid).first()
            if doc:
                doc.sync_status = 'synced'
                doc.access_tags = new_tags
                doc.updated_at = func.now()
            
            db.commit()
            logger.info(f"[cascade_update_tags] DONE document_id={document_id}")
            return {"status": "ok", "document_id": document_id}

        except Exception as exc:
            db.rollback()
            logger.error(f"[cascade_update_tags] FAILED document_id={document_id}: {exc}", exc_info=True)

            try:
                error_doc = db.query(RAGDocument).filter_by(document_id=uuid.UUID(str(document_id))).first()
                if error_doc:
                    error_doc.sync_status = 'failed'
                    error_doc.updated_at = func.now()
                    db.commit()
            except Exception:
                pass

            raise self.retry(exc=exc)

# ============================================================
# TASK 3: Cascade Soft Delete
# ============================================================
@celery_app.task(
    bind=True,
    name="workers.rag_worker.tasks.cascade_soft_delete",
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
    with get_session() as db:
        try:
            logger.info(f"[cascade_soft_delete] START document_id={document_id}")

            doc_uuid = uuid.UUID(str(document_id))
            
            # Xóa mềm rag_chunks
            db.query(RAGChunk).filter(
                RAGChunk.document_id == doc_uuid,
                RAGChunk.is_deleted == False
            ).update(
                {RAGChunk.is_deleted: True},
                synchronize_session=False
            )

            # Xóa mềm rag_documents
            doc = db.query(RAGDocument).filter_by(document_id=doc_uuid).first()
            if doc:
                doc.is_deleted = True
                doc.sync_status = 'synced'
                doc.updated_at = func.now()
            
            db.commit()
            logger.info(f"[cascade_soft_delete] DONE document_id={document_id}")
            return {"status": "ok", "document_id": document_id}

        except Exception as exc:
            db.rollback()
            logger.error(f"[cascade_soft_delete] FAILED document_id={document_id}: {exc}", exc_info=True)

            try:
                error_doc = db.query(RAGDocument).filter_by(document_id=uuid.UUID(str(document_id))).first()
                if error_doc:
                    error_doc.sync_status = 'failed'
                    error_doc.updated_at = func.now()
                    db.commit()
            except Exception:
                pass

            raise self.retry(exc=exc)
