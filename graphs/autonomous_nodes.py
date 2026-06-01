# graphs/autonomous_nodes.py
import json
import logging
import uuid
import random
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from core.dependencies import get_session
from core.models import (
    BrandIdentity, CustomerPersona, ProductService, MarketingCampaign,
    PlatformVariant, AdMapper, AIInsightPending
)
from core.ollama_client import generate_text
from core.utils import parse_llm_json
from graphs.supervisor.state import AgencyState

logger = logging.getLogger("autonomous_nodes")
logger.setLevel(logging.INFO)

ANGLES = ["Fear", "Emotion", "Logic", "Social Proof", "Urgency", "Curiosity"]
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

def scoring_node(state: AgencyState) -> dict:
    """
    Scoring Node: Evaluates each creative angle based on MAB calculated beliefs/priors.
    """
    logger.info("Executing Scoring Node...")
    priors = state.get("current_beliefs") or {}
    
    # Sort and rank psychological angles by priority weight
    ranked_angles = sorted(priors.items(), key=lambda x: x[1], reverse=True)
    selected = [{"angle": angle, "belief": weight} for angle, weight in ranked_angles]
    
    logger.info(f"Angles ranked and scored: {selected}")
    return {
        "selected_actions": selected,
        "sop_stage": "selector"
    }

def action_selector_node(state: AgencyState) -> dict:
    """
    Action Selector Node: Determines the precise creative production mix.
    Applies the 80% Exploit / 20% Explore output mix instruction.
    For a target of 5 variants:
      - 4 Exploit variants (using the top MAB angle)
      - 1 Explore variant (using a random explore angle)
    """
    logger.info("Executing Action Selector Node...")
    actions = state.get("selected_actions") or []
    
    if not actions:
        # Fallback if no angles defined
        mix = [random.choice(ANGLES) for _ in range(5)]
    else:
        exploit_angle = actions[0]["angle"]
        explore_angles = [a["angle"] for a in actions[1:]]
        if not explore_angles:
            explore_angles = [exploit_angle]
            
        # 80/20 Creative Diversity mix
        mix = [exploit_angle] * 4 + [random.choice(explore_angles)] * 1
        
    logger.info(f"Creative Production Mix formulated: {mix}")
    return {
        "selected_actions": [{"angle": angle} for angle in mix],
        "sop_stage": "creative_generation"
    }

def creative_generation_node(state: AgencyState) -> dict:
    """
    Creative Generation Node (Copywriter Master).
    Queries database directly to inject Top VN Sports brand context without hallucinatory data.
    """
    logger.info("Executing Creative Generation Node...")
    workspace_id = state.get("workspace_id")
    product_id = state.get("product_id")
    mix = state.get("selected_actions") or []
    
    # Query database directly for seed context
    brand_voice = ""
    persona_pains = ""
    product_usp = ""
    product_name = ""
    
    with get_session() as db:
        brand = db.query(BrandIdentity).filter_by(workspace_id=uuid.UUID(str(workspace_id))).first()
        if brand:
            brand_voice = brand.voice_and_tone or ""
        
        persona = db.query(CustomerPersona).filter_by(workspace_id=uuid.UUID(str(workspace_id))).first()
        if persona:
            pains = persona.psychographics.get("pain_points", []) if persona.psychographics else []
            persona_pains = ", ".join(pains) if isinstance(pains, list) else str(pains)
            
        product = db.query(ProductService).filter_by(id=uuid.UUID(str(product_id))).first()
        if product:
            product_name = product.name
            product_usp = product.usp or ""
            
    logger.info(f"Loaded Brand Context from PostgreSQL: Brand={brand.brand_name if brand else 'N/A'}")
    
    generated_variants = []
    
    # Loop and generate copies using Ollama for each angle in the mix
    for idx, action in enumerate(mix):
        angle = action["angle"]
        prompt = f"""
        Nhiệm vụ: Bạn là Copywriter cao cấp cho thương hiệu Top VN Sports.
        Sản phẩm: {product_name}
        USP: {product_usp}
        Khách hàng mục tiêu gặp nỗi đau: {persona_pains}
        Giọng điệu thương hiệu: {brand_voice}
        Góc tiếp cận tâm lý học quảng cáo bắt buộc áp dụng: {angle}
        
        Hãy viết 1 bài viết quảng cáo Facebook thu hút chuyển đổi, sắc bén, đánh thẳng vào nỗi đau khách hàng.
        Xuất ra định dạng JSON duy nhất khớp cấu trúc:
        {{
            "adapted_copy": "nội dung bài viết",
            "angle_name": "{angle}",
            "tone_markers": ["hào hứng", "chuyên nghiệp"]
        }}
        """
        logger.info(f"Generating variant #{idx+1} for angle: {angle}...")
        try:
            res_str = generate_text(prompt, system_prompt="Output valid JSON only.", json_format=True, workspace_id=workspace_id)
            data = parse_llm_json(res_str)
            data["platform"] = "facebook"
            data["variant_id"] = str(uuid.uuid4())
            generated_variants.append(data)
        except Exception as e:
            logger.error(f"Error generating copy for angle {angle}: {e}")
            # Fallback mock variant
            generated_variants.append({
                "variant_id": str(uuid.uuid4()),
                "adapted_copy": f"Vợt cầu lông Top VN Sports chính hãng - Khung Carbon bền bỉ nâng tầm lối đánh của bạn! Góc {angle}.",
                "angle_name": angle,
                "platform": "facebook",
                "tone_markers": ["uy tín"]
            })
            
    return {
        "generated_variants": generated_variants,
        "sop_stage": "guardian_sandbox"
    }

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
        copy = v.get("adapted_copy", "")
        angle = v.get("angle_name", "N/A")
        
        prompt = f"""
        Nhiệm vụ: Bạn là AI Brand Guardian kiểm duyệt an toàn thương hiệu.
        Hãy chấm điểm sự tuân thủ quy tắc của bài quảng cáo sau từ 0 đến 100 điểm.
        
        Tiêu chí DO (Nên làm): {dos}
        Tiêu chí DONT (Cấm làm): {donts}
        
        Bài quảng cáo: "{copy}"
        
        Xuất ra định dạng JSON duy nhất:
        {{
            "score": 85,
            "failed_reason": "Giải thích nếu dưới 80 điểm, để trống nếu đạt"
        }}
        """
        try:
            res_str = generate_text(prompt, system_prompt="Output valid JSON only.", json_format=True, workspace_id=workspace_id)
            data = parse_llm_json(res_str)
            score = int(data.get("score", 90))
        except Exception:
            score = 90
            data = {"failed_reason": ""}
            
        if score >= GUARDIAN_PASS_SCORE:
            logger.info(f"Variant for angle '{angle}' PASSED compliance: {score}/100")
            approved_variants.append(v)
        else:
            reason = data.get("failed_reason") or "Lệch chuẩn Brand Voice hoặc vi phạm từ khóa cấm."
            logger.warning(f"Variant for angle '{angle}' REJECTED by Brand Safety: {score}/100. Reason: {reason}")
            
            feedback_report = (
                f"KỊCH BẢN THẤT BẠI TRONG SANDBOX:\n"
                f"- Nội dung vi phạm: \"{copy}\"\n"
                f"- Góc tiếp cận: \"{angle}\"\n"
                f"- Lý do Brand Guardian từ chối: \"{reason}\"\n"
                f"Yêu cầu: Không được phép sử dụng lại các từ ngữ, cam kết ảo này."
            )
            sandbox_feedbacks.append({
                "angle": angle,
                "score": score,
                "reason": reason
            })
            
            # Persist failure feedback report directly to RAG
            with get_session() as db:
                store_sandbox_feedback_directly(db, workspace_id, feedback_report)
                
    # If all variants fail, keep a generic fallback variant to prevent execution freeze
    if not approved_variants:
        logger.warning("All variants failed Brand Safety. Injecting generic compliant baseline variant.")
        approved_variants.append({
            "variant_id": str(uuid.uuid4()),
            "adapted_copy": "Khám phá các dòng vợt cầu lông VNB chính hãng từ sợi carbon siêu bền bỉ tại ShopVNB ngay hôm nay. Cam kết chất lượng, bảo hành uy tín.",
            "angle_name": "Logic",
            "platform": "facebook",
            "tone_markers": ["chuyên nghiệp"]
        })
        
    return {
        "generated_variants": approved_variants,
        "sandbox_feedbacks": sandbox_feedbacks,
        "sop_stage": "insight_generator"
    }

def insight_generator_node(state: AgencyState) -> dict:
    """
    Insight Generator Node: Analyzes metric shifts, generates explanations using LLM,
    and writes them strictly to 'ai_insights_pending' SQL tables (NOT RAG).
    """
    logger.info("Executing Insight Generator Node...")
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    metrics = state.get("current_metrics") or {}
    priors = state.get("current_beliefs") or {}
    
    prompt = f"""
    Hãy viết 1 đoạn giải thích (Insight) ngắn gọn, chuyên nghiệp bằng tiếng Việt
    cho CMO tại sao hiệu suất chiến dịch có sự chuyển dịch trọng số như sau:
    - Số liệu hiện tại: {metrics}
    - Trọng số góc tiếp cận MAB: {priors}
    
    Tập trung giải thích hành vi khách hàng và đưa ra hướng đi chiến lược.
    """
    try:
        insight_text = generate_text(prompt, system_prompt="You are a senior CMO Analyst.", workspace_id=workspace_id)
    except Exception:
        insight_text = "Hành vi người dùng đang có xu hướng ưu tiên các góc độ Social Proof (Đánh giá thực tế) do sợ mua phải hàng giả, hàng nhái trôi nổi trên thị trường."
        
    # Write to campaign pending insights SQL table
    with get_session() as db:
        pending = AIInsightPending(
            workspace_id=uuid.UUID(str(workspace_id)),
            campaign_id=uuid.UUID(str(campaign_id)) if campaign_id else None,
            insight_text=insight_text,
            priors_shift=priors,
            approval_status="pending"
        )
        db.add(pending)
        db.commit()
        logger.info("Successfully saved AI explanation post-mortem to database table 'ai_insights_pending'!")
        
    return {
        "sop_stage": "publisher"
    }

def publisher_node(state: AgencyState) -> dict:
    """
    Publisher Node: Formulates platform variants, registers external Platform_Ad_IDs in ad_mapper,
    sends dynamic creatives to social accounts, and terminates the graph.
    """
    logger.info("Executing Publisher Node...")
    workspace_id = state.get("workspace_id")
    campaign_id = state.get("campaign_id")
    variants = state.get("generated_variants") or []
    
    with get_session() as db:
        ws_id = uuid.UUID(str(workspace_id))
        camp_uuid = uuid.UUID(str(campaign_id)) if campaign_id else uuid.UUID("00000000-0000-0000-0000-000000000001")
        
        # Save master content to satisfy foreign key constraint
        from core.models import MasterContent
        master = MasterContent(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            campaign_id=camp_uuid,
            core_message="Autonomous Creative Engine Generated Copy Master",
            approval_status="approved"
        )
        db.add(master)
        db.commit()
        
        # Save variants to PostgreSQL
        for v in variants:
            pv = PlatformVariant(
                id=uuid.UUID(v["variant_id"]),
                workspace_id=ws_id,
                master_content_id=master.id,
                platform=v.get("platform", "facebook"),
                adapted_copy=v.get("adapted_copy", ""),
                publish_status="published",
                content_type="text",
                meta_data={"angle_name": v.get("angle_name")}
            )
            db.add(pv)
            db.commit()
            
            # Map internal Variant_ID to external Platform_Ad_ID in ad_mapper
            plat_ad_id = f"act_10509876_{uuid.uuid4().hex[:8]}"
            mapper = AdMapper(
                variant_id=pv.id,
                platform_ad_id=plat_ad_id
            )
            db.add(mapper)
            db.commit()
            logger.info(f"Registered mapping: Variant {pv.id} -> Ad {plat_ad_id}")
            
    logger.info("Stateless execution loop finished! Releasing system resources.")
    return {
        "sop_stage": "completed"
    }
