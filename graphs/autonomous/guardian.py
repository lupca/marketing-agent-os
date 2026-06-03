# graphs/autonomous/guardian.py
import logging
import uuid
from sqlalchemy.orm import Session
from core.dependencies import get_session
from core.models import BrandIdentity
from core.ollama_client import generate_text
from core.utils import parse_llm_json, load_prompt
from graphs.supervisor.state import AgencyState
from graphs.autonomous.telemetry import instrument_node

logger = logging.getLogger("autonomous_nodes")
GUARDIAN_PASS_SCORE = 80


def store_sandbox_feedback_directly(db: Session, workspace_id: str, content: str):
    """
    Directly inserts Brand Guardian sandbox failures into RAG tables.
    Prevents queue delays or Celery dependency blockages.
    """
    from core.models import RAGDocument, RAGChunk
    logger.info("Directly writing sandbox feedback to RAG tables...")
    try:
        doc = RAGDocument(
            workspace_id=uuid.UUID(str(workspace_id)),
            file_name="brand_guardian_sandbox_feedback.txt",
            upload_status="ready",
            sync_status="synced",
            access_tags=["sandbox_feedback", "anti_patterns"],
            chunk_count=1
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        
        mock_emb = [0.0] * 1024
        chunk = RAGChunk(
            document_id=doc.document_id,
            workspace_id=uuid.UUID(str(workspace_id)),
            content=content,
            embedding=mock_emb,
            access_tags=["sandbox_feedback", "anti_patterns"]
        )
        db.add(chunk)
        db.commit()
        logger.info("Successfully recorded sandbox feedback chunk in pgvector RAG.")
    except Exception as e:
        logger.error(f"Error persisting sandbox feedback: {e}")


def evaluate_variant_compliance(
    workspace_id: str,
    variant: dict,
    dos: list,
    donts: list
) -> tuple[int, str]:
    """
    Evaluates the compliance of a single generated variant against Brand Safety guidelines.
    Returns (score, failed_reason).
    """
    copy = variant.get("adapted_copy", "")
    platform = variant.get("platform", "facebook")
    content_type = variant.get("content_type", "text")
    
    # Platform-specific validation rules
    if platform == "tiktok" or content_type == "video_script":
        platform_rules = load_prompt("creative", "autonomous_guardian_rules_tiktok.txt")
    else:
        platform_rules = load_prompt("creative", "autonomous_guardian_rules_facebook.txt")
    
    guardian_template = load_prompt("creative", "autonomous_guardian.txt")
    prompt = guardian_template.format(
        platform_upper=platform.upper(),
        dos=dos,
        donts=donts,
        platform_rules=platform_rules,
        copy=copy
    )
    
    try:
        res_str = generate_text(prompt, system_prompt="Output valid JSON only.", json_format=True, workspace_id=workspace_id)
        data = parse_llm_json(res_str)
        score = int(data.get("score", 90))
        reason = data.get("failed_reason") or ""
        return score, reason
    except Exception as e:
        raise RuntimeError(f"Brand Guardian LLM evaluation failed: {e}") from e


@instrument_node("guardian_sandbox")
def guardian_sandbox_node(state: AgencyState) -> dict:
    """
    Guardian Sandbox Node: Scans generated variants for Brand Safety and compliance.
    Rejects bad variants internally and auto-indexes failure reports to RAG.
    """
    logger.info("Executing Guardian Sandbox Node...")
    workspace_id = state.get("workspace_id")
    variants = state.get("generated_variants") or []
    
    dos_and_donts = {}
    with get_session() as db:
        brand = db.query(BrandIdentity).filter_by(workspace_id=uuid.UUID(str(workspace_id))).first()
        if brand:
            dos_and_donts = brand.dos_and_donts or {}
            
    dos = dos_and_donts.get("dos", [])
    donts = dos_and_donts.get("donts", [])
    
    approved_variants = []
    sandbox_feedbacks = []
    
    for v in variants:
        score, reason = evaluate_variant_compliance(workspace_id, v, dos, donts)
        angle = v.get("angle_name", "N/A")
        platform = v.get("platform", "facebook")
        copy = v.get("adapted_copy", "")
        
        if score >= GUARDIAN_PASS_SCORE:
            logger.info(f"Variant for angle '{angle}' on platform '{platform}' PASSED compliance: {score}/100")
            approved_variants.append(v)
        else:
            if not reason:
                reason = f"Lệch chuẩn Brand Voice hoặc vi phạm quy định {platform.upper()}."
            logger.warning(f"Variant for angle '{angle}' on platform '{platform}' REJECTED by Brand Safety: {score}/100. Reason: {reason}")
            
            feedback_report = (
                f"KỊCH BẢN THẤT BẠI TRONG SANDBOX ({platform.upper()}):\n"
                f"- Nội dung vi phạm: \"{copy}\"\n"
                f"- Góc tiếp cận: \"{angle}\"\n"
                f"- Lý do Brand Guardian từ chối: \"{reason}\"\n"
                f"Yêu cầu: Không được phép sử dụng lại các từ ngữ, cam kết ảo này."
            )
            sandbox_feedbacks.append({
                "angle": angle,
                "platform": platform,
                "score": score,
                "reason": reason
            })
            
            # Persist failure feedback report directly to RAG
            with get_session() as db:
                store_sandbox_feedback_directly(db, workspace_id, feedback_report)
                
    if not approved_variants:
        raise RuntimeError("All generated variants failed Brand Safety Sandbox.")
        
    return {
        "generated_variants": approved_variants,
        "sandbox_feedbacks": sandbox_feedbacks,
        "sop_stage": "insight_generator"
    }
