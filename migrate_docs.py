import os
import shutil
import json
import logging
from sqlalchemy import text
from fastapi.testclient import TestClient
import uuid

import sys
sys.path.insert(0, "/root/marketing-agent-os")

from app import fastapi_app
from core.dependencies import get_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mkt_migration")

def main():
    # 1. Chuyển tags các tài liệu rác ban đầu về global
    with get_session() as db:
        try:
            db.execute(text("UPDATE rag_documents SET access_tags = '[\"global\"]'::jsonb"))
            db.commit()
            logger.info("Updated existing documents tags to global.")
        except Exception as e:
            logger.error(f"Error updating tags: {e}")
            db.rollback()
        # 2. Sắp xếp tài liệu và upload
        mkt_dir = "/root/marketing-agent-os/.reference/MKT"
        allowed_exts = {".pdf", ".txt", ".docx", ".xlsx", ".pptx", ".csv"}

        def get_tag_for_file(path):
            path_lower = path.lower()
            if "hubspost" in path_lower: return "hubspot"
            if "plan mkt" in path_lower: return "planning"
            if "dgt mkt" in path_lower: return "digital_marketing"
            if "facebook" in path_lower: return "facebook_ads"
            return "general"

        # Gộp tất cả file vào dictionary tag -> danh sách file
        to_move = []
        for root, _, files in os.walk(mkt_dir):
            if "__MACOSX" in root: continue
            for f in files:
                ext = os.path.splitext(f)[-1].lower()
                if ext in allowed_exts and not f.startswith("._"):
                    full_path = os.path.join(root, f)
                    tag = get_tag_for_file(full_path)
                    to_move.append((full_path, tag, f))

        # Di chuyển file
        files_to_upload = []
        for full_path, tag, filename in to_move:
            target_dir = os.path.join(mkt_dir, tag)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)
        
            # Tránh di chuyển nếu đã ở đúng thư mục
            if full_path != target_path:
                # Xử lý trùng tên
                if os.path.exists(target_path):
                    base, ext = os.path.splitext(filename)
                    filename = f"{base}_{uuid.uuid4().hex[:4]}{ext}"
                    target_path = os.path.join(target_dir, filename)
                try:
                    shutil.move(full_path, target_path)
                    files_to_upload.append((target_path, tag))
                except Exception as e:
                    logger.error(f"Error moving file {full_path}: {e}")
            else:
                files_to_upload.append((target_path, tag))

        # Clean up empty directories
        for root, dirs, files in os.walk(mkt_dir, topdown=False):
            for d in dirs:
                dir_path = os.path.join(root, d)
                if not os.listdir(dir_path):
                    os.rmdir(dir_path)

        # 3. Upload via TestClient
        client = TestClient(fastapi_app)
    
        # Get workspace id
        db = SessionLocal()
        ws = db.execute(text("SELECT id FROM workspaces ORDER BY created_at LIMIT 1")).fetchone()
        ws_id = str(ws.id) if ws else None
    
        # Đảm bảo các tag tồn tại trong DB trước khi upload
        unique_tags = list(set([tag for _, tag in files_to_upload] + ["marketing", "global"]))
        for tag in unique_tags:
            existing = db.execute(text("SELECT tag_id FROM rag_access_tags WHERE workspace_id = CAST(:ws AS UUID) AND tag_name = :name"), {"ws": ws_id, "name": tag}).fetchone()
            if not existing:
                db.execute(
                    text("INSERT INTO rag_access_tags (tag_id, workspace_id, tag_name) VALUES (CAST(:id AS UUID), CAST(:ws AS UUID), :name)"),
                    {"id": str(uuid.uuid4()), "ws": ws_id, "name": tag}
                )
                db.commit()

        db.close()
    
        if not ws_id:
            logger.error("No workspace found. Aborting upload.")
            return

        logger.info(f"Bắt đầu upload {len(files_to_upload)} tài liệu lên RAG...")
    
        # Upload each file
        for path, tag in files_to_upload:
            try:
                with open(path, "rb") as f:
                    response = client.post(
                        "/api/rag/upload",
                        data={
                            "workspace_id": ws_id,
                            "access_tags": json.dumps([tag, "marketing"])
                        },
                        files={"file": (os.path.basename(path), f)}
                    )
                    if response.status_code == 202:
                        logger.info(f"✅ Uploaded {os.path.basename(path)} (Tag: {tag})")
                    elif response.status_code == 409:
                        logger.warning(f"⚠️ Duplicate file ignored: {os.path.basename(path)}")
                    else:
                        logger.error(f"❌ Failed to upload {os.path.basename(path)}: {response.status_code} - {response.text}")
            except Exception as e:
                logger.error(f"Exception uploading {path}: {e}")

if __name__ == "__main__":
    main()
