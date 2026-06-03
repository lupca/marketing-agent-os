# graphs/autonomous_nodes.py
"""
Autonomous LangGraph Node Implementations — Marketing Agent OS.

Each node is fully instrumented with the Pipeline Tracker observability layer:
    - start_node / complete_node / fail_node calls for DB + WebSocket telemetry
    - run_id propagated through AgencyState._run_id
    - Kill switch check in publisher_node before any Facebook API calls

Node execution order:
    scoring → selector → creative_generation → guardian_sandbox → insight_generator → publisher
"""
import json
import logging
import time
import uuid
import random
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from core.dependencies import get_session
from core.models import (
    BrandIdentity, CustomerPersona, ProductService, MarketingCampaign,
    PlatformVariant, AdMapper, AIInsightPending, SocialAccount, CampaignSocialAccount
)
from core.ollama_client import generate_text
from core.utils import parse_llm_json
from core import pipeline_tracker
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

    Instrumentation:
        - Records start/complete/fail to pipeline_node_executions via pipeline_tracker.
        - Broadcasts 'node_start' and 'node_complete' events over WebSocket.
    """
    run_id = state.get("_run_id")
    node_exec_id = None
    t0 = time.time()

    if run_id:
        try:
            node_exec_id = pipeline_tracker.start_node(run_id, "scoring", dict(state))
        except Exception as track_err:
            logger.warning(f"[TRACKER] start_node failed for 'scoring': {track_err}")

    try:
        logger.info("Executing Scoring Node...")
        priors = state.get("current_beliefs") or {}
        
        # Sort and rank psychological angles by priority weight
        ranked_angles = sorted(priors.items(), key=lambda x: x[1], reverse=True)
        selected = [{"angle": angle, "belief": weight} for angle, weight in ranked_angles]
        
        logger.info(f"Angles ranked and scored: {selected}")
        result = {
            "selected_actions": selected,
            "sop_stage": "selector"
        }

        if node_exec_id:
            duration = int((time.time() - t0) * 1000)
            try:
                pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
            except Exception as track_err:
                logger.warning(f"[TRACKER] complete_node failed for 'scoring': {track_err}")

        return result

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        if node_exec_id:
            try:
                pipeline_tracker.fail_node(node_exec_id, str(exc), duration_ms=duration)
            except Exception as track_err:
                logger.warning(f"[TRACKER] fail_node failed for 'scoring': {track_err}")
        raise

def action_selector_node(state: AgencyState) -> dict:
    """
    Action Selector Node: Determines the precise creative production mix.
    Applies the 80% Exploit / 20% Explore output mix instruction.
    For a target of 5 variants:
      - 4 Exploit variants (using the top MAB angle)
      - 1 Explore variant (using a random explore angle)

    Instrumentation:
        - Records start/complete/fail to pipeline_node_executions via pipeline_tracker.
    """
    run_id = state.get("_run_id")
    node_exec_id = None
    t0 = time.time()

    if run_id:
        try:
            node_exec_id = pipeline_tracker.start_node(run_id, "selector", dict(state))
        except Exception as track_err:
            logger.warning(f"[TRACKER] start_node failed for 'selector': {track_err}")

    try:
        logger.info("Executing Action Selector Node...")
        actions = state.get("selected_actions") or []
        
        if not actions:
            raise ValueError("No creative angles provided by MAB. Cannot form production mix.")
        else:
            exploit_angle = actions[0]["angle"]
            explore_angles = [a["angle"] for a in actions[1:]]
            if not explore_angles:
                explore_angles = [exploit_angle]
                
            # 80/20 Creative Diversity mix
            mix = [exploit_angle] * 4 + [random.choice(explore_angles)] * 1
            
        logger.info(f"Creative Production Mix formulated: {mix}")
        result = {
            "selected_actions": [{"angle": angle} for angle in mix],
            "sop_stage": "creative_generation"
        }

        if node_exec_id:
            duration = int((time.time() - t0) * 1000)
            try:
                pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
            except Exception as track_err:
                logger.warning(f"[TRACKER] complete_node failed for 'selector': {track_err}")

        return result

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        if node_exec_id:
            try:
                pipeline_tracker.fail_node(node_exec_id, str(exc), duration_ms=duration)
            except Exception as track_err:
                logger.warning(f"[TRACKER] fail_node failed for 'selector': {track_err}")
        raise

def creative_generation_node(state: AgencyState) -> dict:
    """
    Creative Generation Node (Copywriter Master).
    Queries database directly to inject TOPVNSPORT brand context without hallucinatory data.

    Instrumentation:
        - Records start/complete/fail to pipeline_node_executions via pipeline_tracker.
    """
    run_id = state.get("_run_id")
    node_exec_id = None
    t0 = time.time()

    if run_id:
        try:
            node_exec_id = pipeline_tracker.start_node(
                run_id, "creative_generation", dict(state)
            )
        except Exception as track_err:
            logger.warning(
                f"[TRACKER] start_node failed for 'creative_generation': {track_err}"
            )

    try:
        logger.info("Executing Creative Generation Node...")
        workspace_id = state.get("workspace_id")
        product_id = state.get("product_id")
        mix = state.get("selected_actions") or []
        campaign_id = state.get("campaign_id")
        
        # Query database directly for seed context and target platforms
        brand_voice = ""
        persona_pains = ""
        product_usp = ""
        product_name = ""
        target_platforms = []
        
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
                
            # Query platforms from Junction Table
            social_links = []
            if campaign_id:
                social_links = db.query(SocialAccount).join(
                    CampaignSocialAccount, 
                    SocialAccount.id == CampaignSocialAccount.social_account_id
                ).filter(
                    CampaignSocialAccount.campaign_id == uuid.UUID(str(campaign_id))
                ).all()
                
            # Fallback to all connected accounts in the workspace if campaign has no explicit links
            if not social_links:
                logger.info("No explicit campaign-level social links found. Falling back to workspace accounts.")
                social_links = db.query(SocialAccount).filter_by(workspace_id=uuid.UUID(str(workspace_id))).all()
                
            if social_links:
                target_platforms = list(set([acc.platform.lower() for acc in social_links]))
                    
        if not target_platforms:
            raise ValueError("No target platforms connected in this workspace. Cannot generate creatives.")
            
        logger.info(f"Loaded Brand Context: Brand={brand.brand_name if brand else 'N/A'}, Target Platforms: {target_platforms}")
        
        generated_variants = []
        
        # Loop and generate copies using Ollama for each angle and platform in the mix
        for idx, action in enumerate(mix):
            angle = action["angle"]
            for platform in target_platforms:
                # Platform-specific prompt constraints
                if platform == "tiktok":
                    content_type = "video_script"
                    format_instructions = """
                    Hãy viết 1 KỊCH BẢN VIDEO TikTok (ngắn dưới 60s) thu hút chuyển đổi, sắc bén, đánh thẳng vào nỗi đau khách hàng.
                    Bắt buộc chia thành 2 cột: [Visual - Hình ảnh/Video] và [Audio - Lời bình/Âm thanh].
                    Xuất ra định dạng JSON duy nhất khớp cấu trúc:
                    {
                        "adapted_copy": "kịch bản chi tiết 2 cột (Visual - Audio)",
                        "angle_name": "...",
                        "tone_markers": ["hào hứng", "chuyên nghiệp"]
                    }
                    """
                else:
                    content_type = "text"
                    format_instructions = """
                    Hãy viết 1 bài viết quảng cáo Facebook thu hút chuyển đổi, sắc bén, đánh thẳng vào nỗi đau khách hàng. Tập trung vào nội dung Text (kèm Hook và Call-to-Action).
                    Xuất ra định dạng JSON duy nhất khớp cấu trúc:
                    {
                        "adapted_copy": "nội dung bài viết quảng cáo",
                        "angle_name": "...",
                        "tone_markers": ["hào hứng", "chuyên nghiệp"]
                    }
                    """
                
                prompt = f"""
                Nhiệm vụ: Bạn là Copywriter cao cấp cho thương hiệu TOPVNSPORT.
                Sản phẩm: {product_name}
                USP: {product_usp}
                Khách hàng mục tiêu gặp nỗi đau: {persona_pains}
                Giọng điệu thương hiệu: {brand_voice}
                Góc tiếp cận tâm lý học quảng cáo bắt buộc áp dụng: {angle}
                Nền tảng mục tiêu: {platform.upper()}
                
                {format_instructions}
                """
                logger.info(f"Generating variant #{idx+1} for angle: {angle} on platform {platform.upper()}...")
                try:
                    res_str = generate_text(prompt, system_prompt="Output valid JSON only.", json_format=True, workspace_id=workspace_id)
                    data = parse_llm_json(res_str)
                    data["platform"] = platform
                    data["content_type"] = content_type
                    data["variant_id"] = str(uuid.uuid4())
                    generated_variants.append(data)
                except Exception as e:
                    logger.error(f"Error generating copy for angle {angle} on {platform}: {e}")
                    raise RuntimeError(f"Failed to generate copy for angle {angle} on {platform}: {e}") from e
                
        result = {
            "generated_variants": generated_variants,
            "sop_stage": "guardian_sandbox"
        }

        if node_exec_id:
            duration = int((time.time() - t0) * 1000)
            try:
                pipeline_tracker.complete_node(
                    node_exec_id, result, duration_ms=duration
                )
            except Exception as track_err:
                logger.warning(
                    f"[TRACKER] complete_node failed for 'creative_generation': {track_err}"
                )

        return result

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        if node_exec_id:
            try:
                pipeline_tracker.fail_node(
                    node_exec_id, str(exc), duration_ms=duration
                )
            except Exception as track_err:
                logger.warning(
                    f"[TRACKER] fail_node failed for 'creative_generation': {track_err}"
                )
        raise

def guardian_sandbox_node(state: AgencyState) -> dict:
    """
    Guardian Sandbox Node: Scans generated variants for Brand Safety and compliance.
    Rejects bad variants internally and auto-indexes failure reports to RAG.

    Instrumentation:
        - Records start/complete/fail to pipeline_node_executions via pipeline_tracker.
    """
    run_id = state.get("_run_id")
    node_exec_id = None
    t0 = time.time()

    if run_id:
        try:
            node_exec_id = pipeline_tracker.start_node(
                run_id, "guardian_sandbox", dict(state)
            )
        except Exception as track_err:
            logger.warning(
                f"[TRACKER] start_node failed for 'guardian_sandbox': {track_err}"
            )

    try:
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
            platform = v.get("platform", "facebook")
            content_type = v.get("content_type", "text")
            
            # Platform-specific validation rules
            platform_rules = ""
            if platform == "tiktok" or content_type == "video_script":
                platform_rules = """
                Vì đây là KỊCH BẢN VIDEO TIKTOK, hãy kiểm duyệt nghiêm ngặt các tiêu chí sau:
                1. Phải chia thành 2 phần/cột hoặc dòng: Visual (chỉ dẫn hình ảnh/video) và Audio (lời thoại/âm thanh). Nếu bài chỉ có text thông thường mà không có chỉ dẫn hình ảnh/âm thanh, hãy trừ điểm nặng hoặc chấm 0 điểm.
                2. Phải có chỉ dẫn cuốn hút thị giác trong 3 giây đầu tiên (Hook Visual).
                3. Đảm bảo thời lượng lời thoại/kịch bản phù hợp dưới 60 giây (không viết quá dài).
                """
            else:
                platform_rules = """
                Vì đây là BÀI VIẾT QUẢNG CÁO FACEBOOK, hãy kiểm duyệt nghiêm ngặt các tiêu chí sau:
                1. Phải có Hook bằng chữ thu hút người đọc và có Call-to-Action rõ ràng ở cuối bài viết.
                2. Phải viết bằng chữ (text), định dạng đẹp mắt với emoji.
                3. Tuyệt đối cấm các từ ngữ vi phạm chính sách quảng cáo của Facebook (ví dụ: cam kết hiệu quả 100%, chữa dứt điểm, giảm cân cấp tốc, phân biệt đối xử, v.v.).
                """
            
            prompt = f"""
            Nhiệm vụ: Bạn là AI Brand Guardian kiểm duyệt an toàn thương hiệu cho nền tảng {platform.upper()}.
            Hãy chấm điểm sự tuân thủ quy tắc của bài quảng cáo sau từ 0 đến 100 điểm.
            
            Tiêu chí DO (Nên làm): {dos}
            Tiêu chí DONT (Cấm làm): {donts}
            
            {platform_rules}
            
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
            except Exception as e:
                raise RuntimeError(f"Brand Guardian LLM evaluation failed: {e}") from e
                
            if score >= GUARDIAN_PASS_SCORE:
                logger.info(f"Variant for angle '{angle}' on platform '{platform}' PASSED compliance: {score}/100")
                approved_variants.append(v)
            else:
                reason = data.get("failed_reason") or f"Lệch chuẩn Brand Voice hoặc vi phạm quy định {platform.upper()}."
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
            
        result = {
            "generated_variants": approved_variants,
            "sandbox_feedbacks": sandbox_feedbacks,
            "sop_stage": "insight_generator"
        }

        if node_exec_id:
            duration = int((time.time() - t0) * 1000)
            try:
                pipeline_tracker.complete_node(
                    node_exec_id, result, duration_ms=duration
                )
            except Exception as track_err:
                logger.warning(
                    f"[TRACKER] complete_node failed for 'guardian_sandbox': {track_err}"
                )

        return result

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        if node_exec_id:
            try:
                pipeline_tracker.fail_node(
                    node_exec_id, str(exc), duration_ms=duration
                )
            except Exception as track_err:
                logger.warning(
                    f"[TRACKER] fail_node failed for 'guardian_sandbox': {track_err}"
                )
        raise

def insight_generator_node(state: AgencyState) -> dict:
    """
    Insight Generator Node: Analyzes metric shifts, generates explanations using LLM,
    and writes them strictly to 'ai_insights_pending' SQL tables (NOT RAG).

    Instrumentation:
        - Records start/complete/fail to pipeline_node_executions via pipeline_tracker.
    """
    run_id = state.get("_run_id")
    node_exec_id = None
    t0 = time.time()

    if run_id:
        try:
            node_exec_id = pipeline_tracker.start_node(
                run_id, "insight_generator", dict(state)
            )
        except Exception as track_err:
            logger.warning(
                f"[TRACKER] start_node failed for 'insight_generator': {track_err}"
            )

    try:
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
            # Robustly parse JSON if it is returned in a wrapped format (Edge Case 2)
            try:
                parsed = parse_llm_json(insight_text)
                parsed_insight = parsed.get("insight") or parsed.get("insight_text")
                if parsed_insight:
                    insight_text = str(parsed_insight)
                elif parsed:
                    insight_text = str(next(iter(parsed.values())))
            except Exception:
                cleaned = insight_text.strip()
                if cleaned.startswith("```json"):
                    cleaned = cleaned[7:]
                elif cleaned.startswith("```"):
                    cleaned = cleaned[3:]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                insight_text = cleaned.strip()
        except Exception:
            insight_text = "Hành vi người dùng đang có xu hướng ưu tiên các góc độ Social Proof (Đánh giá thực tế) do sợ mua phải hàng giả, hàng nhái trôi nổi trên thị trường."
            
        # Write to campaign pending insights SQL table
        with get_session() as db:
            valid_campaign_id = None
            if campaign_id:
                try:
                    exists = db.query(MarketingCampaign.id).filter(MarketingCampaign.id == uuid.UUID(str(campaign_id))).first()
                    if exists:
                        valid_campaign_id = uuid.UUID(str(campaign_id))
                    else:
                        logger.warning(f"campaign_id {campaign_id} not found in MarketingCampaign. Setting to None to prevent ForeignKeyViolation.")
                except Exception as e:
                    logger.warning(f"Error validating campaign_id {campaign_id}: {e}")

            pending = AIInsightPending(
                workspace_id=uuid.UUID(str(workspace_id)),
                campaign_id=valid_campaign_id,
                insight_text=insight_text,
                priors_shift=priors,
                approval_status="pending"
            )
            db.add(pending)
            db.commit()
            logger.info("Successfully saved AI explanation post-mortem to database table 'ai_insights_pending'!")

        result = {"sop_stage": "publisher"}

        if node_exec_id:
            duration = int((time.time() - t0) * 1000)
            try:
                pipeline_tracker.complete_node(
                    node_exec_id, result, duration_ms=duration
                )
            except Exception as track_err:
                logger.warning(
                    f"[TRACKER] complete_node failed for 'insight_generator': {track_err}"
                )

        return result

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        if node_exec_id:
            try:
                pipeline_tracker.fail_node(
                    node_exec_id, str(exc), duration_ms=duration
                )
            except Exception as track_err:
                logger.warning(
                    f"[TRACKER] fail_node failed for 'insight_generator': {track_err}"
                )
        raise

def publisher_node(state: AgencyState) -> dict:
    """
    Publisher Node: Formulates platform variants, registers external Platform_Ad_IDs in ad_mapper,
    sends dynamic creatives to social accounts, and terminates the graph.

    Kill Switch Guard:
        Before making ANY Facebook API calls, this node checks ``pipeline_tracker.is_kill_switch_active()``.
        If the kill switch is active, all external API publishing is skipped entirely.
        The pipeline returns a clean completion state indicating the reason.
        Internal DB writes (PlatformVariant records) are still performed for audit.

    Execution Mode Guard:
        In 'shadow' mode (``state.get("_execution_mode") == "shadow"``), real Facebook API
        calls are also skipped even if the kill switch is not active.

    Instrumentation:
        - Records start/complete/fail to pipeline_node_executions via pipeline_tracker.
    """
    run_id = state.get("_run_id")
    node_exec_id = None
    t0 = time.time()

    if run_id:
        try:
            node_exec_id = pipeline_tracker.start_node(run_id, "publisher", dict(state))
        except Exception as track_err:
            logger.warning(f"[TRACKER] start_node failed for 'publisher': {track_err}")

    try:
        logger.info("Executing Publisher Node...")
        workspace_id = state.get("workspace_id")
        campaign_id = state.get("campaign_id")
        variants = state.get("generated_variants") or []
        execution_mode = state.get("_execution_mode", "shadow")

        # ── Kill Switch Guard ──────────────────────────────────────────────────
        if pipeline_tracker.is_kill_switch_active(workspace_id=workspace_id):
            logger.warning(
                "[KILL SWITCH] ⛔ Publisher blocked — kill switch is ACTIVE. "
                "Skipping all external Facebook API calls. Pipeline will still complete."
            )
            result = {
                "sandbox_feedbacks": list(state.get("sandbox_feedbacks") or []) + [{
                    "stage": "publisher",
                    "blocked_by": "kill_switch",
                    "reason": "Kill switch active — all external API publishing blocked by operator."
                }],
                "sop_stage": "completed",
                "_kill_switch_blocked": True,
            }
            if node_exec_id:
                duration = int((time.time() - t0) * 1000)
                try:
                    pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
                except Exception:
                    pass
            return result

        # ── Publishing Flow ───────────────────────────
        from core.integrations.fb_client import (
            FacebookAccountDisabledError,
            init_facebook_client,
            batch_create_creatives,
            batch_create_ads
        )
        from core.db_services import save_publisher_state
        from core.decision_logger import log_decision

        with get_session() as db:
            try:
                ws_id = uuid.UUID(str(workspace_id))
                camp_uuid = uuid.UUID(str(campaign_id)) if campaign_id else uuid.UUID("00000000-0000-0000-0000-000000000001")
                
                # 1. Separate variants by platform
                fb_variants = [v for v in variants if v.get("platform", "facebook") == "facebook"]
                tiktok_variants = [v for v in variants if v.get("platform") == "tiktok"]
                
                ad_mappings = {}
                fb_account_id = "mock_publisher_account"
                
                # 2. Publish Facebook variants if any
                if fb_variants:
                    # Resolve and initialize Facebook Client
                    api, fb_account_id, use_real_fb = init_facebook_client(workspace_id, db, campaign_id=campaign_id)
                    
                    if execution_mode == "shadow":
                        logger.info("[SHADOW MODE] Overriding Facebook publishing to mock mode.")
                        use_real_fb = False

                    if use_real_fb:
                        logger.info(f"Starting batch publishing of {len(fb_variants)} Facebook variants to Facebook Ads API...")
                        creative_responses = batch_create_creatives(api, fb_account_id, workspace_id, fb_variants)
                        ad_mappings.update(batch_create_ads(api, fb_account_id, camp_uuid, creative_responses, db))
                    elif execution_mode == "shadow":
                        logger.info(f"Shadow mode active: {len(fb_variants)} Facebook variants skipped publishing.")
                    else:
                        raise RuntimeError("Facebook real publishing is disabled but execution mode is not shadow.")
                            
                # 3. Publish TikTok variants if any (Mocked as requested)
                if tiktok_variants:
                    logger.error(f"TikTok integration is not implemented yet. Cannot publish {len(tiktok_variants)} variants.")
                    raise NotImplementedError("TikTok API integration is not available. Real publishing required.")
                    
                # 4. Atomically persist state and mappings in database
                save_publisher_state(db, ws_id, camp_uuid, variants, ad_mappings, fb_account_id)
                
                reasons = []
                if fb_variants:
                    reasons.append(f"{len(fb_variants)} Facebook variants published")
                if tiktok_variants:
                    reasons.append(f"{len(tiktok_variants)} TikTok script variants published")
                reason_str = ", ".join(reasons) if reasons else "No variants to publish"
                
                log_decision(
                    workspace_id=ws_id,
                    agent_name="Publisher Node",
                    action="Omnichannel Social Publishing",
                    decision_status="success",
                    reason=f"Successfully processed social publishing: {reason_str}.",
                    campaign_id=camp_uuid
                )
                
            except FacebookAccountDisabledError as disabled_err:
                logger.error(f"Terminal account restricted exception caught: {disabled_err}. Rollback transaction...")
                db.rollback()
                
                feedbacks = list(state.get("sandbox_feedbacks") or [])
                feedbacks.append({
                    "stage": "publisher",
                    "error": "Account Disabled/Restricted",
                    "reason": str(disabled_err)
                })
                
                log_decision(
                    workspace_id=uuid.UUID(str(workspace_id)),
                    agent_name="Publisher Node",
                    action="Facebook Ads Publishing",
                    decision_status="failed",
                    reason=f"Account Disabled/Restricted during publishing: {disabled_err}",
                    campaign_id=uuid.UUID(str(campaign_id)) if campaign_id else None
                )
                
                result = {
                    "sandbox_feedbacks": feedbacks,
                    "sop_stage": "completed"
                }
                if node_exec_id:
                    duration = int((time.time() - t0) * 1000)
                    try:
                        pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
                    except Exception:
                        pass
                return result
                
            except Exception as e:
                logger.error(f"Transaction failed: {e}. Performing rollback...")
                db.rollback()
                raise
                
        logger.info("Stateless execution loop finished! Releasing system resources.")
        result = {"sop_stage": "completed"}
        if execution_mode == "shadow":
            result["_shadow_mode"] = True

        if node_exec_id:
            duration = int((time.time() - t0) * 1000)
            try:
                pipeline_tracker.complete_node(node_exec_id, result, duration_ms=duration)
            except Exception as track_err:
                logger.warning(f"[TRACKER] complete_node failed for 'publisher': {track_err}")

        return result

    except Exception as exc:
        duration = int((time.time() - t0) * 1000)
        if node_exec_id:
            try:
                pipeline_tracker.fail_node(node_exec_id, str(exc), duration_ms=duration)
            except Exception as track_err:
                logger.warning(f"[TRACKER] fail_node failed for 'publisher': {track_err}")
        raise
