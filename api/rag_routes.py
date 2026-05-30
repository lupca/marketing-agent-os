# api/rag_routes.py
"""
FastAPI Router: RAG Knowledge Base API (8 endpoints)

Mount vào app.py:
    from api.rag_routes import rag_router
    app.include_router(rag_router, prefix="")

Endpoints:
  GET  /api/rag/tags                      — Master tags của workspace
  POST /api/rag/tags                      — Tạo tag mới
  POST /api/rag/upload                    — Upload + kick off Celery ingestion
  GET  /api/rag/documents                 — Danh sách documents (paginated)
  GET  /api/rag/documents/{id}/status     — Status ingestion/sync
  PUT  /api/rag/documents/{id}/tags       — Cập nhật tags (Celery cascade)
  DELETE /api/rag/documents/{id}          — Soft delete (Celery cascade)
  POST /api/rag/test-retrieval            — Test Zero-JOIN retrieval
"""
import json
import logging
import os
import tempfile
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.connection import SessionLocal
from core.rag import store_document, retrieve_chunks_reranked
from core.tasks import cascade_update_tags, cascade_soft_delete
from core.storage import upload_file
from core.models import RAGAccessTag, RAGDocument

logger = logging.getLogger("api_rag_routes")

rag_router = APIRouter()


# ============================================================
# Dependency: DB Session
# ============================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# Pydantic schemas
# ============================================================
class CreateTagRequest(BaseModel):
    workspace_id: str
    tag_name: str
    description: Optional[str] = None
    color: Optional[str] = "#6366f1"

class UpdateTagsRequest(BaseModel):
    access_tags: List[str]

class TestRetrievalRequest(BaseModel):
    workspace_id: str
    query: str
    access_tags: Optional[List[str]] = ["global"]
    limit: Optional[int] = 5


# ============================================================
# Helpers
# ============================================================
def _get_workspace_id_from_request(workspace_id: Optional[str], db: Session) -> str:
    """Lấy workspace_id. Nếu không truyền → lấy workspace đầu tiên."""
    if workspace_id:
        return workspace_id
    row = db.execute(text("SELECT id FROM workspaces ORDER BY created_at LIMIT 1")).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="Chưa có workspace nào trong hệ thống.")
    return str(row.id)


def _validate_tags_exist(db: Session, workspace_id: str, tags: List[str]) -> None:
    """Validate tất cả tags phải tồn tại trong bảng rag_access_tags của workspace."""
    if not tags:
        return
    rows = db.execute(
        text("SELECT tag_name FROM rag_access_tags WHERE workspace_id = :ws_id::uuid"),
        {"ws_id": workspace_id}
    ).fetchall()
    valid_tags = {r.tag_name for r in rows}
    invalid = [t for t in tags if t not in valid_tags]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Tag không hợp lệ: {invalid}. Tạo tag trước tại POST /api/rag/tags"
        )


# ============================================================
# GET /api/rag/tags — Danh sách Master Tags của workspace
# ============================================================
@rag_router.get("/api/rag/tags")
async def list_tags(
    workspace_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    ws_id = _get_workspace_id_from_request(workspace_id, db)
    rows = db.execute(
        text("""
            SELECT tag_id::TEXT, tag_name, description, color, created_at
            FROM rag_access_tags
            WHERE workspace_id = :ws_id::uuid
            ORDER BY tag_name
        """),
        {"ws_id": ws_id}
    ).fetchall()

    return JSONResponse({
        "workspace_id": ws_id,
        "tags": [
            {
                "tag_id":      r.tag_id,
                "tag_name":    r.tag_name,
                "description": r.description,
                "color":       r.color,
                "created_at":  r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    })


# ============================================================
# POST /api/rag/tags — Tạo tag mới
# ============================================================
@rag_router.post("/api/rag/tags", status_code=201)
async def create_tag(payload: CreateTagRequest, db: Session = Depends(get_db)):
    # Kiểm tra unique
    existing = db.execute(
        text("SELECT tag_id FROM rag_access_tags WHERE workspace_id=:ws::uuid AND tag_name=:name"),
        {"ws": payload.workspace_id, "name": payload.tag_name}
    ).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail=f"Tag '{payload.tag_name}' đã tồn tại trong workspace.")

    tag_id = str(uuid.uuid4())
    db.execute(
        text("""
            INSERT INTO rag_access_tags (tag_id, workspace_id, tag_name, description, color)
            VALUES (:tag_id::uuid, :ws::uuid, :name, :desc, :color)
        """),
        {
            "tag_id": tag_id,
            "ws":     payload.workspace_id,
            "name":   payload.tag_name,
            "desc":   payload.description,
            "color":  payload.color or "#6366f1",
        }
    )
    db.commit()
    logger.info(f"[create_tag] Created tag '{payload.tag_name}' for workspace {payload.workspace_id}")
    return JSONResponse({"tag_id": tag_id, "tag_name": payload.tag_name}, status_code=201)


# ============================================================
# POST /api/rag/upload — Upload file + Kick off Celery ingestion
# ============================================================
@rag_router.post("/api/rag/upload", status_code=202)
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = Form(None),
    access_tags: str = Form('["global"]'),   # JSON string
    db: Session = Depends(get_db)
):
    ws_id = _get_workspace_id_from_request(workspace_id, db)

    # Parse access_tags
    try:
        tags = json.loads(access_tags)
        if not isinstance(tags, list):
            tags = ["global"]
    except Exception:
        tags = ["global"]

    # Validate file type
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[-1].lower()
    allowed_exts = {".pdf", ".txt", ".docx", ".xlsx"}
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Định dạng '{ext}' không được hỗ trợ. Chấp nhận: {', '.join(allowed_exts)}"
        )

    # Validate tags exist in master
    _validate_tags_exist(db, ws_id, tags)

    # Save file tạm → upload MinIO
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, filename)
    content = await file.read()
    file_size = len(content)

    with open(tmp_path, "wb") as f:
        f.write(content)

    # Upload lên MinIO
    object_key = f"rag/{ws_id}/{uuid.uuid4()}{ext}"
    try:
        upload_file(tmp_path, object_key)
    except Exception as e:
        logger.error(f"[upload_document] MinIO upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload file thất bại: {str(e)}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

    # Tạo DB record + kick Celery (trong store_document)
    try:
        doc = store_document(
            db=db,
            workspace_id=ws_id,
            file_name=filename,
            file_key=object_key,
            access_tags=tags,
            file_size_bytes=file_size,
        )
    except Exception as e:
        logger.error(f"[upload_document] store_document failed: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi tạo document record: {str(e)}")

    logger.info(f"[upload_document] Accepted document_id={doc.document_id}, file={filename}")
    return JSONResponse(
        {
            "message":     "File đã được nhận. Đang xử lý embedding ngầm.",
            "document_id": str(doc.document_id),
            "file_name":   filename,
            "access_tags": tags,
            "status":      "processing",
        },
        status_code=202,
    )


# ============================================================
# GET /api/rag/documents — Danh sách documents (paginated)
# ============================================================
@rag_router.get("/api/rag/documents")
async def list_documents(
    workspace_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    ws_id = _get_workspace_id_from_request(workspace_id, db)
    offset = (page - 1) * limit

    rows = db.execute(
        text("""
            SELECT
                document_id::TEXT, file_name, file_key,
                access_tags, upload_status, sync_status,
                chunk_count, file_size_bytes,
                created_at, updated_at
            FROM rag_documents
            WHERE workspace_id = :ws_id::uuid
              AND is_deleted = FALSE
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"ws_id": ws_id, "limit": limit, "offset": offset}
    ).fetchall()

    total_row = db.execute(
        text("SELECT COUNT(*) FROM rag_documents WHERE workspace_id=:ws::uuid AND is_deleted=FALSE"),
        {"ws": ws_id}
    ).scalar()

    return JSONResponse({
        "workspace_id": ws_id,
        "page": page,
        "limit": limit,
        "total": total_row,
        "documents": [
            {
                "document_id":    r.document_id,
                "file_name":      r.file_name,
                "file_key":       r.file_key,
                "access_tags":    r.access_tags if isinstance(r.access_tags, list) else json.loads(r.access_tags),
                "upload_status":  r.upload_status,
                "sync_status":    r.sync_status,
                "chunk_count":    r.chunk_count,
                "file_size_bytes":r.file_size_bytes,
                "created_at":     r.created_at.isoformat() if r.created_at else None,
                "updated_at":     r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in rows
        ]
    })


# ============================================================
# GET /api/rag/documents/{id}/status — Poll ingestion/sync status
# ============================================================
@rag_router.get("/api/rag/documents/{document_id}/status")
async def get_document_status(document_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            SELECT upload_status, sync_status, chunk_count, file_name, updated_at
            FROM rag_documents
            WHERE document_id = :doc_id::uuid AND is_deleted = FALSE
        """),
        {"doc_id": document_id}
    ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail=f"Document không tồn tại: {document_id}")

    return JSONResponse({
        "document_id":   document_id,
        "file_name":     row.file_name,
        "upload_status": row.upload_status,
        "sync_status":   row.sync_status,
        "chunk_count":   row.chunk_count,
        "updated_at":    row.updated_at.isoformat() if row.updated_at else None,
    })


# ============================================================
# PUT /api/rag/documents/{id}/tags — Cập nhật access_tags
# ============================================================
@rag_router.put("/api/rag/documents/{document_id}/tags", status_code=202)
async def update_document_tags(
    document_id: str,
    payload: UpdateTagsRequest,
    db: Session = Depends(get_db)
):
    # Kiểm tra document tồn tại
    row = db.execute(
        text("SELECT workspace_id FROM rag_documents WHERE document_id=:id::uuid AND is_deleted=FALSE"),
        {"id": document_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Document không tồn tại: {document_id}")

    ws_id = str(row.workspace_id)
    _validate_tags_exist(db, ws_id, payload.access_tags)

    # Cập nhật sync_status → syncing ngay lập tức
    db.execute(
        text("UPDATE rag_documents SET sync_status='syncing', updated_at=NOW() WHERE document_id=:id::uuid"),
        {"id": document_id}
    )
    db.commit()

    # Kick off Celery cascade task
    cascade_update_tags.delay(document_id=document_id, new_tags=payload.access_tags)

    logger.info(f"[update_document_tags] document_id={document_id}, new_tags={payload.access_tags}")
    return JSONResponse(
        {
            "message":     "Đang cập nhật tags ngầm. Poll /status để kiểm tra tiến độ.",
            "document_id": document_id,
            "new_tags":    payload.access_tags,
            "sync_status": "syncing",
        },
        status_code=202,
    )


# ============================================================
# DELETE /api/rag/documents/{id} — Soft delete
# ============================================================
@rag_router.delete("/api/rag/documents/{document_id}", status_code=202)
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    row = db.execute(
        text("SELECT file_name FROM rag_documents WHERE document_id=:id::uuid AND is_deleted=FALSE"),
        {"id": document_id}
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Document không tồn tại hoặc đã xóa: {document_id}")

    # Đặt syncing trước
    db.execute(
        text("UPDATE rag_documents SET sync_status='syncing', updated_at=NOW() WHERE document_id=:id::uuid"),
        {"id": document_id}
    )
    db.commit()

    # Kick Celery cascade soft-delete
    cascade_soft_delete.delay(document_id=document_id)

    logger.info(f"[delete_document] Soft-delete kicked for document_id={document_id}")
    return JSONResponse(
        {
            "message":     "Đang xóa tài liệu ngầm. Sẽ biến mất khỏi retrieval ngay khi Celery xử lý xong.",
            "document_id": document_id,
            "sync_status": "syncing",
        },
        status_code=202,
    )


# ============================================================
# POST /api/rag/test-retrieval — Test Zero-JOIN retrieval
# ============================================================
@rag_router.post("/api/rag/test-retrieval")
async def test_retrieval(payload: TestRetrievalRequest, db: Session = Depends(get_db)):
    if not payload.query or len(payload.query.strip()) < 3:
        raise HTTPException(status_code=400, detail="Query phải có ít nhất 3 ký tự.")

    import time
    start_ms = time.time()

    results = retrieve_chunks_reranked(
        db=db,
        workspace_id=payload.workspace_id,
        query=payload.query,
        access_tags=payload.access_tags or ["global"],
        limit=payload.limit or 5,
    )

    elapsed_ms = round((time.time() - start_ms) * 1000, 2)

    return JSONResponse({
        "query":        payload.query,
        "access_tags":  payload.access_tags,
        "elapsed_ms":   elapsed_ms,
        "result_count": len(results),
        "results": [
            {
                "chunk_id":         r.get("id"),
                "document_id":      r.get("document_id"),
                "content_preview":  r.get("content", "")[:300],
                "content_full":     r.get("content", ""),
                "similarity_score": round(r.get("similarity_score", 0.0), 4),
                "access_tags":      r.get("access_tags", []),
            }
            for r in results
        ]
    })
