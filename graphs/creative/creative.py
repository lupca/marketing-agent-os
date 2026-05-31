# graphs/creative.py
import json
import logging
import uuid
from sqlalchemy.orm import Session
from core.dependencies import get_session
from core.models import ProductService
from core.ollama_client import generate_text
from graphs.research.researcher import run_research
from graphs.supervisor.state import AgencyState, CreativeState
from core.utils import parse_llm_json, trim_and_log, load_prompt
from config.settings import (
    MAX_CONTEXT_TOKENS,
    LLM_CTX_WINDOW,
    GUARDIAN_PASS_SCORE,
    DEFAULT_TARGET_CPA,
    DEFAULT_TEST_BUDGET
)

logger = logging.getLogger("graphs_creative")
logging.basicConfig(level=logging.INFO)

# ==========================================
# PROMPT BUILDERS
# ==========================================

def build_strategist_prompt(
    state: dict, 
    anti_patterns_report: str, 
    insights_str: str
) -> str:
    """Build the prompt for Strategist Agent incorporating RAG findings and dynamic brand identity."""
    business_context = state.get("business_context") or {}
    brand = business_context.get("brand") or {}
    product = business_context.get("product") or {}
    persona = business_context.get("persona") or {}
    
    brand_name = brand.get("brand_name") or ""
    brand_voice = brand.get("voice_and_tone") or ""
    
    keywords_list = brand.get("keywords") or []
    brand_keywords = ", ".join(keywords_list) if isinstance(keywords_list, list) else str(keywords_list)
    
    product_name = product.get("name") or ""
    product_usp = product.get("usp") or ""
    
    features_list = product.get("key_features") or []
    product_features = ", ".join(features_list) if isinstance(features_list, list) else str(features_list)
    
    benefits_list = product.get("key_benefits") or []
    product_benefits = ", ".join(benefits_list) if isinstance(benefits_list, list) else str(benefits_list)
    
    persona_name = persona.get("persona_name") or ""
    persona_goals = persona.get("summary") or ""
    
    pains = persona.get("psychographics", {}).get("pains") or []
    persona_pain_points = ", ".join(pains) if isinstance(pains, list) else str(pains)
    
    strategist_template = load_prompt("creative", "strategist.txt")
    base_prompt = strategist_template.format(
        num_angles=1,
        funnel_stage="Consideration",
        campaign_name=state.get("campaign_name") or "",
        campaign_goal="Tối ưu chi phí chuyển đổi ads",
        brand_name=brand_name,
        brand_voice=brand_voice,
        brand_keywords=brand_keywords,
        product_name=product_name,
        product_usp=product_usp,
        product_features=product_features,
        product_benefits=product_benefits,
        persona_name=persona_name,
        persona_goals=persona_goals,
        persona_pain_points=persona_pain_points,
        language="Vietnamese"
    )
    
    return (
        f"## BÁO CÁO BÀI HỌC THẤT BẠI CẦN TRÁNH (TỔNG HỢP BỞI BAN NGHIÊN CỨU - CẤM LẶP LẠI):\n"
        f"{anti_patterns_report}\n\n"
        f"{base_prompt}\n"
        f"**Tài liệu tri thức bổ sung thu thập từ Researcher Agent:**\n"
        f"{insights_str}\n"
    )

def build_copywriter_master_prompt(
    state: dict, 
    target_cpa: float, 
    test_budget: float
) -> str:
    """Build the prompt for Copywriter Master content generation."""
    business_context = state.get("business_context") or {}
    brand = business_context.get("brand") or {}
    persona = business_context.get("persona") or {}
    
    brand_name = brand.get("brand_name") or ""
    brand_voice = brand.get("voice_and_tone") or ""
    
    keywords_list = brand.get("keywords") or []
    brand_keywords = ", ".join(keywords_list) if isinstance(keywords_list, list) else str(keywords_list)
    brand_mission = brand.get("slogan") or ""
    
    persona_name = persona.get("persona_name") or ""
    persona_goals = persona.get("summary") or ""
    
    pains = persona.get("psychographics", {}).get("pains") or []
    persona_pain_points = ", ".join(pains) if isinstance(pains, list) else str(pains)

    angle = state.get("current_angle", {})
    feedback_loop = state.get("killed_variants_feedback", [])
    
    cpa_constraints = (
        f"\n### RÀNG BUỘC KINH TẾ (BẮT BUỘC TUÂN THỦ)\n"
        f"- Ngân sách test chiến dịch: {test_budget} VNĐ.\n"
        f"- Ngưỡng chi phí chuyển đổi (CPA Target): BẮT BUỘC DƯỚI {target_cpa} VNĐ/đơn hàng.\n"
        f"- Yêu cầu: Viết nội dung sắc bén, đánh thẳng vào USP sản phẩm để thúc đẩy chuyển đổi nhanh, bảo toàn mức CPA tối ưu này.\n"
    )
    
    feedback_injection = ""
    if feedback_loop:
        logger.warning(f"GIAO THỨC CÃI NHAU: Copywriter received {len(feedback_loop)} killed campaigns feedback!")
        feedback_injection = "\n### PHẢN HỒI THẤT BẠI TỪ PHÒNG KINH DOANH ( variant_id KILLED )\n"
        for item in feedback_loop:
            feedback_injection += (
                f"- Variant ID: {item.get('variant_id')} trên kênh {item.get('platform')} đã bị khai tử!\n"
                f"  - Nội dung hỏng: \"{item.get('failed_copy')}\"\n"
                f"  - CPA thực tế: {item.get('failed_cpa')} VNĐ (vượt xa mức target {item.get('target_cpa')} VNĐ).\n"
                f"  - Nguyên nhân: {item.get('reason_killed')}\n"
                f"👉 YÊU CẦU: Tuyệt đối KHÔNG sử dụng lại văn phong, tít hoặc lối tiếp cận cũ này. Hãy đổi sang Angle hoàn toàn khác!\n"
            )
            
    master_template = load_prompt("creative", "master_generator.txt")
    master_prompt = master_template.format(
        campaign_name=state.get("campaign_name") or "",
        campaign_goal=f"Đạt CPA dưới {target_cpa} VNĐ",
        brand_name=brand_name,
        brand_mission=brand_mission,
        brand_keywords=brand_keywords,
        brand_voice=brand_voice,
        persona_name=persona_name,
        persona_goals=persona_goals,
        persona_pain_points=persona_pain_points,
        language="Vietnamese"
    )
    
    master_prompt += cpa_constraints + feedback_injection
    master_prompt += f"\n**Góc chiến lược do Strategist định hướng:**\n{json.dumps(angle, ensure_ascii=False)}\n"
    return master_prompt

def build_copywriter_variant_prompt(
    state: dict, 
    master_content: dict, 
    target_cpa: float, 
    test_budget: float
) -> str:
    """Build the prompt for platform adaptation (Facebook variant)."""
    business_context = state.get("business_context") or {}
    brand = business_context.get("brand") or {}
    persona = business_context.get("persona") or {}
    
    brand_voice = brand.get("voice_and_tone") or ""
    
    persona_name = persona.get("persona_name") or ""
    persona_characteristics = persona.get("summary") or ""

    feedback_loop = state.get("killed_variants_feedback", [])
    
    cpa_constraints = (
        f"\n### RÀNG BUỘC KINH TẾ (BẮT BUỘC TUÂN THỦ)\n"
        f"- Ngân sách test chiến dịch: {test_budget} VNĐ.\n"
        f"- Ngưỡng chi phí chuyển đổi (CPA Target): BẮT BUỘC DƯỚI {target_cpa} VNĐ/đơn hàng.\n"
        f"- Yêu cầu: Viết nội dung sắc bén, đánh thẳng vào USP sản phẩm để thúc đẩy chuyển đổi nhanh, bảo toàn mức CPA tối ưu này.\n"
    )
    
    feedback_injection = ""
    if feedback_loop:
        feedback_injection = "\n### PHẢN HỒI THẤT BẠI TỪ PHÒNG KINH DOANH ( variant_id KILLED )\n"
        for item in feedback_loop:
            feedback_injection += (
                f"- Variant ID: {item.get('variant_id')} trên kênh {item.get('platform')} đã bị khai tử!\n"
                f"  - Nội dung hỏng: \"{item.get('failed_copy')}\"\n"
                f"  - CPA thực tế: {item.get('failed_cpa')} VNĐ (vượt xa mức target {item.get('target_cpa')} VNĐ).\n"
                f"  - Nguyên nhân: {item.get('reason_killed')}\n"
                f"👉 YÊU CẦU: Tuyệt đối KHÔNG sử dụng lại văn phong, tít hoặc lối tiếp cận cũ này. Hãy đổi sang Angle hoàn toàn khác!\n"
            )
            
    variant_template = load_prompt("creative", "platform_variant.txt")
    variant_prompt = variant_template.format(
        platform="facebook",
        core_message=master_content.get("core_message", ""),
        extended_message=master_content.get("extended_message", ""),
        tone_markers=", ".join(master_content.get("tone_markers", [])),
        call_to_action=master_content.get("call_to_action", ""),
        char_limit="63206 chars",
        platform_guidelines="Conversational, community-focused, emoji-driven, rich storytelling",
        content_format="Social Post",
        brand_voice=brand_voice,
        persona_name=persona_name,
        persona_characteristics=persona_characteristics,
        language="Vietnamese"
    )
    
    variant_prompt += cpa_constraints + feedback_injection
    return variant_prompt

def build_brand_guardian_prompt(
    state: dict, 
    master_content: dict, 
    fb_copy: str
) -> str:
    """Build the compliance check prompt for Brand Guardian."""
    business_context = state.get("business_context") or {}
    brand = business_context.get("brand") or {}
    
    brand_name = brand.get("brand_name") or ""
    brand_voice = brand.get("voice_and_tone") or ""
    
    keywords_list = brand.get("keywords") or []
    brand_keywords = ", ".join(keywords_list) if isinstance(keywords_list, list) else str(keywords_list)

    brand_guardian_template = load_prompt("creative", "brand_guardian.txt")
    guardian_prompt = brand_guardian_template.format(
        brand_name=brand_name,
        brand_voice=brand_voice,
        brand_keywords=brand_keywords
    )
    
    guardian_prompt += (
        f"\n### NỘI DUNG ĐỀ XUẤT CẦN ĐÁNH GIÁ:\n"
        f"- Master Core Message: \"{master_content.get('core_message')}\"\n"
        f"- Facebook Variant Copy: \"{fb_copy}\"\n"
    )
    return guardian_prompt


# ==========================================
# GRAPH NODES
# ==========================================

def strategist_node(state: CreativeState) -> dict:
    """
    Strategist Node (Ban Sáng Tạo).
    Reads RAG psychological/economic insights, enforces RAG anti-patterns injection,
    and creates a structured content marketing angle strategy.
    """
    logger.info("Executing Strategist Node (Marketing Angle Formulation)...")
    workspace_id = state.get("workspace_id")
    
    # Safely ensure business_context is present
    business_context = state.get("business_context")
    if not business_context:
        from core.db_services import get_unified_business_context
        product_id = state.get("product_id")
        try:
            ws_uuid = uuid.UUID(str(workspace_id)) if workspace_id else None
            p_uuid = uuid.UUID(str(product_id)) if product_id else None
            business_context = get_unified_business_context(ws_uuid, p_uuid)
            state = dict(state)
            state["business_context"] = business_context
        except Exception as e:
            logger.error(f"Error fetching unified context in strategist_node fallback: {e}")
            business_context = {}
            
    product_name = business_context.get("product", {}).get("name") or ""

    # Get customer insights from Researcher (dùng access_tags phân quyền đúng)
    logger.info("Calling Researcher Agent for customer insights...")
    try:
        # Insights tâm lý/chiến lược: truy cập cả marketing, psychology, economics
        insights_str = run_research(
            workspace_id,
            f"chiến lược marketing khách hàng nỗi đau cho {product_name}",
            access_tags=["marketing", "psychology", "economics", "global"],
        )
        # Anti-patterns: chỉ truy cập anti_patterns + manager_feedback
        anti_patterns_report = run_research(
            workspace_id,
            f"mẫu quảng cáo thất bại sai lầm sản phẩm {product_name}",
            access_tags=["anti_patterns", "manager_feedback"],
        )
    except Exception as e:
        logger.error(f"Lỗi phối hợp phòng ban: Strategist không nhận được báo cáo từ Researcher: {e}")
        raise RuntimeError(f"Lỗi phối hợp phòng ban: Strategist không thể nhận báo cáo từ Researcher: {e}") from e
    
    # 4. Build Prompt & Generate
    final_prompt = build_strategist_prompt(state, anti_patterns_report, insights_str)
    
    logger.info("Generating marketing angle strategy from Ollama...")
    system_prompt = "You are a professional marketing strategist. You MUST format output in valid JSON."
    res_str = generate_text(final_prompt, system_prompt=system_prompt, json_format=True, workspace_id=workspace_id)
    try:
        angle_data = parse_llm_json(res_str)
    except Exception as e:
        raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e

    logger.info(f"Strategist Node finished. Selected Angle: {angle_data.get('angle_name')}")

    strat_msg = (
        f"🧠 **[Phòng Sáng Tạo - Strategist]**\n"
        f"- Đã nghiên cứu RAG và tự động dán RAG bài học thất bại.\n"
        f"- **Angle đề xuất:** `{angle_data.get('angle_name')}`\n"
        f"- **Nỗi đau đánh trúng:** \"{angle_data.get('pain_point_focus')}\"\n"
        f"- **Tập trung:** {angle_data.get('psychological_angle')}"
    )

    return trim_and_log(
        state=state,
        new_state_data={
            "current_angle": angle_data,
            "sop_stage": "creative_generation"
        },
        message=strat_msg,
        log_action="Formulate Marketing Angle",
        agent_name="Strategist Agent",
        reason=f"Đề xuất góc tiếp cận sáng tạo thành công: '{angle_data.get('angle_name')}' ({angle_data.get('psychological_angle')}). Định hướng: {angle_data.get('brief')}",
        log_metadata=angle_data
    )

def copywriter_node(state: CreativeState) -> dict:
    """
    Copywriter Node (Ban Sáng Tạo).
    Constructs creative copies strictly constrained under Target CPA and Budget.
    """
    logger.info("Executing Copywriter Node (Constraint-Driven Content Generation)...")
    workspace_id = state.get("workspace_id")
    
    target_cpa = state.get("target_cpa", DEFAULT_TARGET_CPA)
    test_budget = state.get("test_budget", DEFAULT_TEST_BUDGET)
    
    # 1. Generate Master Content
    master_prompt = build_copywriter_master_prompt(state, target_cpa, test_budget)
    logger.info("Generating Master Content via Ollama...")
    try:
        master_res = generate_text(master_prompt, system_prompt="You are a master copywriter. Output JSON only.", json_format=True, workspace_id=workspace_id)
        master_content = parse_llm_json(master_res)
    except Exception as e:
        raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e

    # 2. Generate Platform Adaptation (Facebook variant)
    variant_prompt = build_copywriter_variant_prompt(state, master_content, target_cpa, test_budget)
    logger.info("Generating Facebook Platform Variant...")
    try:
        var_res = generate_text(variant_prompt, system_prompt="You are a platform optimization copywriter. Output JSON only.", json_format=True, workspace_id=workspace_id)
        fb_variant = parse_llm_json(var_res)
    except Exception as e:
        raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e
    fb_variant["platform"] = "facebook"
    
    copy_msg = (
        f"✍️ **[Phòng Sáng Tạo - Copywriter]**\n"
        f"- Đã xào nấu và tối ưu hóa kịch bản theo target CPA.\n"
        f"- **Nội dung nháp Facebook:**\n\n"
        f"```text\n{fb_variant.get('adapted_copy')}\n```\n"
        f"- **Tags:** {', '.join(fb_variant.get('hashtags', []))}"
    )
    
    return trim_and_log(
        state=state,
        new_state_data={
            "master_content": master_content,
            "variants": [fb_variant],
            "sop_stage": "creative_generation"
        },
        message=copy_msg,
        log_action="Generate Social Script",
        agent_name="Copywriter Agent",
        log_metadata={
            "hashtags": fb_variant.get("hashtags", []),
            "char_count": len(fb_variant.get("adapted_copy", ""))
        }
    )

def brand_guardian_node(state: CreativeState) -> dict:
    """
    Brand Guardian Node (Ban Sáng Tạo).
    Enforces the strict CMO 100-Point compliance check.
    """
    logger.info("Executing Brand Guardian Node (Scoring Compliance Gatekeeper)...")
    workspace_id = state.get("workspace_id")
    
    master_content = state.get("master_content", {})
    variants = state.get("variants", [])
    feedback_log = state.get("feedback_log", [])
    
    if not variants:
        return {"sop_stage": "creative_generation"}
        
    fb_copy = variants[0].get("adapted_copy", "")
    
    # Run evaluation
    guardian_prompt = build_brand_guardian_prompt(state, master_content, fb_copy)
    logger.info("Running compliance scoring via Ollama...")
    try:
        res_str = generate_text(guardian_prompt, system_prompt="You are the Brand Guardian. Score compliance in valid JSON.", json_format=True, workspace_id=workspace_id)
        eval_data = parse_llm_json(res_str)
    except Exception as e:
        raise ValueError("Dữ liệu AI trả về không hợp lệ, không thể tiếp tục") from e
    
    score = int(eval_data.get("score", 75))
    reason = eval_data.get("feedback_reason" if "feedback_reason" in eval_data else "reason", "Chưa đạt tiêu chí Hook hoặc CTA.")
    
    logger.info(f"Compliance Scoring Result: {score}/100. Feedback: {reason}")
    log_entry = f"Lượt đánh giá {len(feedback_log)+1} - Điểm: {score}/100 - Lý do: {reason}"
    new_logs = feedback_log + [log_entry]
    
    status_str = "success" if score >= GUARDIAN_PASS_SCORE else "failed"
    sop_stage = "waiting_approval" if score >= GUARDIAN_PASS_SCORE else "creative_generation"
    guardian_msg = f"🛡️ **[Phòng Sáng Tạo - Brand Guardian]**\n- Kết quả: `{log_entry}`"
    
    return trim_and_log(
        state=state,
        new_state_data={
            "feedback_log": new_logs,
            "sop_stage": sop_stage
        },
        message=guardian_msg,
        log_action="Evaluate Copy Compliance",
        agent_name="Brand Guardian Agent",
        decision_status=status_str,
        reason=f"Chấm điểm bài viết quảng cáo đạt {score}/100 điểm. Kết quả: {'VƯỢT QUA' if score >= GUARDIAN_PASS_SCORE else 'TỪ CHỐI (CẦN SỬA LẠI)'}. Feedback: {reason}",
        log_metadata={
            "score": score,
            "feedback": reason
        }
    )
