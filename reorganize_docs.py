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
from db.connection import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mkt_reorganize")

def main():
    mkt_dir = "/root/marketing-agent-os/.reference/MKT"
    allowed_exts = {".pdf", ".txt", ".docx", ".xlsx", ".pptx", ".csv"}

    def determine_tag(filename):
        name = filename.lower()
        if any(w in name for w in ["price", "budget", "roi", "cac", "ltv", "finance", "cost", "economic"]):
            return "economics"
        if any(w in name for w in ["audience", "psychology", "persona", "customer", "upset", "identity", "behavior"]):
            return "psychology"
        if any(w in name for w in ["guideline", "disclaimer", "policy", "rule", "terms"]):
            return "policies"
        if any(w in name for w in ["fail", "mistake", "killed", "shame", "anti_pattern", "bad", "lesson"]):
            return "anti_patterns"
        if any(w in name for w in ["feedback", "review", "cmo"]):
            return "manager_feedback"
        return "marketing"

    to_move = []
    for root, _, files in os.walk(mkt_dir):
        if "__MACOSX" in root: continue
        for f in files:
            ext = os.path.splitext(f)[-1].lower()
            if ext in allowed_exts and not f.startswith("._"):
                full_path = os.path.join(root, f)
                tag = determine_tag(f)
                to_move.append((full_path, tag, f))

    # Move files
    files_to_upload = []
    for full_path, tag, filename in to_move:
        target_dir = os.path.join(mkt_dir, tag)
        os.makedirs(target_dir, exist_ok=True)
        
        target_path = os.path.join(target_dir, filename)
        if full_path != target_path:
            if os.path.exists(target_path):
                base, ext = os.path.splitext(filename)
                filename = f"{base}_{uuid.uuid4().hex[:4]}{ext}"
                target_path = os.path.join(target_dir, filename)
            try:
                shutil.move(full_path, target_path)
                files_to_upload.append((target_path, tag))
            except Exception as e:
                logger.error(f"Error moving {full_path}: {e}")
        else:
            files_to_upload.append((target_path, tag))

    # Clean up empty directories
    for root, dirs, files in os.walk(mkt_dir, topdown=False):
        for d in dirs:
            dir_path = os.path.join(root, d)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)

    # Upload via TestClient
    client = TestClient(fastapi_app)
    
    db = SessionLocal()
    ws = db.execute(text("SELECT id FROM workspaces ORDER BY created_at LIMIT 1")).fetchone()
    ws_id = str(ws.id) if ws else None
    db.close()
    
    if not ws_id:
        logger.error("No workspace found. Aborting upload.")
        return

    logger.info(f"Bắt đầu upload {len(files_to_upload)} tài liệu lên RAG với các tags chuẩn...")
    
    for path, tag in files_to_upload:
        try:
            with open(path, "rb") as f:
                response = client.post(
                    "/api/rag/upload",
                    data={
                        "workspace_id": ws_id,
                        # Attach the specific tag + global so it's accessible globally if needed,
                        # but typically we just attach the specific tag and marketing.
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
