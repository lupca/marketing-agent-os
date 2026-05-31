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
from core.parser import extract_text_from_file, semantic_chunk_text, UniversalParser
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
        access_tags_json = str(access_tags).replace("'", '"')  # Đảm bảo JSON hợp lệ
        import json
        access_tags_jsonb = json.dumps(access_tags, ensure_ascii=False)

        inserted = 0
        for idx, chunk in enumerate(chunks):
            # Lấy page_content nếu là đối tượng LangChain Document, hoặc giữ nguyên chuỗi
            chunk_content = chunk.page_content if hasattr(chunk, "page_content") else chunk
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


# ============================================================
# TASK 4: Social Media Publisher Background Job (CTO Design)
# ============================================================
@celery_app.task(
    bind=True,
    name="core.tasks.publish_to_social",
    queue="social_publisher",
    max_retries=5,
    default_retry_delay=60,
    acks_late=True,
)
def publish_to_social(self, variant_id: str):
    """
    Background job to publish a PlatformVariant to social media.
    Features:
      - Idempotency check
      - Workspace Integration config resolution (Dynamic auth/credentials)
      - Content Format / Type detection (text, carousel/photos, video)
      - Dynamic Facebook Page resolution
      - Temporary media downloading and clean up
      - Classified exception handling (Auto-Retry vs Permanent Fail)
      - Audit logging via log_decision
    """
    from db.connection import SessionLocal
    from core.models import PlatformVariant, MediaAsset
    from core.ai_clients import upload_photos, upload_text, upload_video, UploadPostAuthError, UploadPostValidationError, UploadPostRateLimitError, UploadPostServerError
    from core.decision_logger import log_decision
    from core.storage import download_file_from_minio
    import uuid
    import requests
    
    db = SessionLocal()
    variant = None
    tmp_files = []
    platform = "unknown"
    
    try:
        logger.info(f"[publish_to_social] START variant_id={variant_id}")
        
        # 1. Fetch variant data from DB (with UUID format validation)
        try:
            variant_uuid = uuid.UUID(variant_id)
        except ValueError as val_err:
            logger.error(f"[publish_to_social] Invalid variant_id UUID format: {variant_id}")
            raise UploadPostValidationError(f"Invalid variant_id UUID format: {variant_id}")
            
        variant = db.query(PlatformVariant).filter_by(id=variant_uuid).first()
        if not variant:
            logger.error(f"[publish_to_social] Variant {variant_id} not found in database!")
            return {"status": "error", "message": "Variant not found"}
            
        platform = variant.platform
        
        # 2. Idempotency Check
        if variant.publish_status == 'published':
            logger.info(f"[publish_to_social] Variant {variant_id} is already published. Skipping.")
            return {"status": "skipped", "message": "Already published"}
            
        # 3. Retrieve Credentials from Workspace Integration configs (or environment variables)
        from core.utils import get_integration_config
        integration_configs = get_integration_config(variant.workspace_id, "upload-post")
            
        api_key = integration_configs.get("api_key") or os.getenv("UPLOAD_POST_API_KEY")
        if not api_key:
            raise UploadPostAuthError("UPLOAD_POST_API_KEY is not configured in workspace integrations or env.")
            
        user = integration_configs.get("user") or "topvnsport"
        config_fb_page_id = integration_configs.get("facebook_page_id")
        
        # 4. Prepare parameters
        title = variant.adapted_copy or ""
        
        # 5. Dynamic Facebook Page Resolution
        fb_page_id = None
        if platform == "facebook":
            if config_fb_page_id:
                fb_page_id = config_fb_page_id
                logger.info(f"[publish_to_social] Using configured Facebook page ID: {fb_page_id} from integrations.")
            else:
                try:
                    headers = {"Authorization": f"Apikey {api_key}"}
                    response = requests.get("https://api.upload-post.com/api/uploadposts/facebook/pages", headers=headers, timeout=20)
                    if response.status_code == 200:
                        pages_data = response.json()
                        pages = pages_data.get("pages", [])
                        for p in pages:
                            name = p.get("name", "").lower()
                            if "top vn sport" in name or "topvnsport" in name:
                                fb_page_id = p.get("id")
                                logger.info(f"[publish_to_social] Resolved Facebook page ID: {fb_page_id} for name: {p.get('name')}")
                                break
                except Exception as e:
                    logger.warning(f"[publish_to_social] Failed to dynamically query Facebook pages: {e}")
                    
                if not fb_page_id:
                    fb_page_id = "1036098656250618"  # Hardcoded fallback
                    logger.info(f"[publish_to_social] Fallback to hardcoded Facebook page ID: {fb_page_id}")

        # Determine publishing format using Content Format / Type
        content_format = variant.content_type or "text"
        if isinstance(variant.meta_data, dict):
            content_format = variant.meta_data.get("content_type") or variant.meta_data.get("content_format") or content_format
            
        content_format = content_format.lower()
        
        # 6. Gather and download media assets if any
        photos = []
        is_video_post = "video" in content_format or "script" in content_format
        
        if variant.platform_media_ids:
            for asset_id in variant.platform_media_ids:
                asset = db.query(MediaAsset).filter_by(id=uuid.UUID(str(asset_id))).first()
                if asset:
                    if asset.file_type == "video":
                        is_video_post = True
                    # Download file from MinIO/Local storage to temporary path
                    ext = os.path.splitext(asset.file_key)[-1] or (".mp4" if asset.file_type == "video" else ".jpg")
                    tmp_fd, tmp_path = tempfile.mkstemp(suffix=ext)
                    os.close(tmp_fd) # Close file descriptor
                    
                    logger.info(f"[publish_to_social] Downloading asset {asset_id} to temporary path: {tmp_path}")
                    download_file_from_minio(asset.file_key, tmp_path)
                    photos.append(tmp_path)
                    tmp_files.append(tmp_path)
                    
        # 7. Execute Call to Upload-Post API
        if is_video_post and photos:
            # Video publishing (Use the first media file as video)
            api_res = upload_video(
                api_key=api_key,
                user=user,
                platforms=[platform],
                video_path=photos[0],
                title=title,
                facebook_page_id=fb_page_id
            )
        elif photos:
            # Photos/Carousel publishing
            api_res = upload_photos(
                api_key=api_key,
                user=user,
                platforms=[platform],
                photos=photos,
                title=title,
                facebook_page_id=fb_page_id
            )
        else:
            # Text-only publishing
            api_res = upload_text(
                api_key=api_key,
                user=user,
                platforms=[platform],
                title=title,
                facebook_page_id=fb_page_id
            )
            
        logger.info(f"[publish_to_social] API Response: {api_res}")
        
        # 8. Success: Update variant status in DB
        from sqlalchemy.sql import func
        variant.publish_status = 'published'
        variant.published_at = func.now()
        
        # If the API returned a post ID or job ID, store it in meta_data and platform_post_id
        post_id = api_res.get("post_id") or api_res.get("request_id")
        if post_id:
            variant.platform_post_id = str(post_id)
            
        # Update meta_data with API result (Idempotency/Observability)
        meta = dict(variant.meta_data) if variant.meta_data else {}
        meta["api_response"] = api_res
        if "job_id" in api_res:
            meta["api_job_id"] = api_res["job_id"]
        variant.meta_data = meta
        db.commit()
        
        # Log success decision (Observability)
        log_decision(
            workspace_id=variant.workspace_id,
            agent_name="Social Publisher Worker",
            action="API Publish Success",
            decision_status="success",
            reason=f"Đăng tải kịch bản thành công lên {platform.upper()} via Upload-Post API.",
            campaign_id=None,
            metadata={"variant_id": variant_id, "api_response": api_res}
        )
        
        return {"status": "success", "variant_id": variant_id, "api_response": api_res}
        
    except (UploadPostAuthError, UploadPostValidationError) as err:
        # Permanent Fails -> DO NOT RETRY
        logger.error(f"[publish_to_social] Permanent Failure for variant {variant_id}: {err}", exc_info=True)
        if variant:
            db.rollback()
            variant = db.query(PlatformVariant).filter_by(id=uuid.UUID(variant_id)).first()
            if variant:
                variant.publish_status = 'failed'
                meta = dict(variant.meta_data) if variant.meta_data else {}
                meta["error_message"] = str(err)
                variant.meta_data = meta
                db.commit()
                
                # Log permanent failure (Observability)
                log_decision(
                    workspace_id=variant.workspace_id,
                    agent_name="Social Publisher Worker",
                    action="API Publish Failed (Permanent)",
                    decision_status="failed",
                    reason=f"Thất bại vĩnh viễn khi đăng lên {platform.upper()}: {err}",
                    campaign_id=None,
                    metadata={"variant_id": variant_id, "error": str(err)}
                )
        return {"status": "failed", "error": str(err)}
        
    except Exception as exc:
        # Transient Failure -> Retry with backoff
        logger.warning(f"[publish_to_social] Transient Failure for variant {variant_id}, retrying: {exc}", exc_info=True)
        db.rollback()
        
        backoff_time = self.default_retry_delay * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=backoff_time)
        
    finally:
        db.close()
        # Clean up temporary media files to prevent memory/disk leak (SoC section 3.5)
        for filepath in tmp_files:
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"[publish_to_social] Deleted temporary file: {filepath}")
                except Exception as cleanup_err:
                    logger.warning(f"[publish_to_social] Failed to delete temporary file {filepath}: {cleanup_err}")

