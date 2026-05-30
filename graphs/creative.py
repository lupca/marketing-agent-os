# graphs/creative.py
import json
import logging
import uuid
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.models import ProductService
from core.ollama_client import generate_text
from graphs.researcher import run_research
from graphs.state import AgencyState
from reference.prompt.prompts import (
    ANGLE_STRATEGIST_PROMPT,
    MASTER_CONTENT_GENERATOR_PROMPT,
    PLATFORM_VARIANT_GENERATOR_PROMPT,
    EDITOR_BRAND_GUARDIAN_PROMPT
)
from core.utils import parse_llm_json, trim_and_log
from reference.prompt.fallbacks import (
    STRATEGIST_FALLBACK,
    COPYWRITER_MASTER_FALLBACK,
    FB_VARIANT_FALLBACK,
    GUARDIAN_FALLBACK
)
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
    state: AgencyState, 
    product_name: str, 
    product_usp: str, 
    anti_patterns_report: str, 
    insights_str: str
) -> str:
    """Build the prompt for Strategist Agent incorporating RAG findings."""
    base_prompt = ANGLE_STRATEGIST_PROMPT.format(
        num_angles=1,
        funnel_stage="Consideration",
        campaign_name="Chiến dịch tăng doanh số",
        campaign_goal="Tối ưu chi phí chuyển đổi ads",
        brand_name="G-Agent Tech",
        brand_voice="Chuyên nghiệp, sắc bén, số liệu thực tế",
        brand_keywords="AI Agent, LangGraph, Tối ưu CPA",
        product_name=product_name,
        product_usp=product_usp,
        product_features="Analyst Node, Copywriter Node, Auto scale/kill ads",
        product_benefits="Tối ưu CPA 100%, Giải phóng 80% thời gian",
        persona_name="Sếp CMO bận rộn",
        persona_goals="Tự động hóa ads, Vít ngân sách ổn định",
        persona_pain_points="CPA tăng vọt, Thiếu thời gian duyệt kịch bản",
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
    state: AgencyState, 
    target_cpa: float, 
    test_budget: float
) -> str:
    """Build the prompt for Copywriter Master content generation."""
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
            
    master_prompt = MASTER_CONTENT_GENERATOR_PROMPT.format(
        campaign_name="Tối ưu chuyển đổi Ads bằng AI",
        campaign_goal=f"Đạt CPA dưới {target_cpa} VNĐ",
        brand_name="G-Agent Tech",
        brand_mission="Tự động hóa 80% Marketing doanh nghiệp",
        brand_keywords="AI Agent, LangGraph, Tối ưu CPA",
        brand_voice="Chuyên nghiệp, sắc bén, số liệu thực tế",
        persona_name="Sếp CMO bận rộn",
        persona_goals="Vít ads ổn định, tự động hóa duyệt bài",
        persona_pain_points="CPA ads tăng vọt, tốn thời gian",
        language="Vietnamese"
    )
    
    master_prompt += cpa_constraints + feedback_injection
    master_prompt += f"\n**Góc chiến lược do Strategist định hướng:**\n{json.dumps(angle, ensure_ascii=False)}\n"
    return master_prompt

def build_copywriter_variant_prompt(
    state: AgencyState, 
    master_content: dict, 
    target_cpa: float, 
    test_budget: float
) -> str:
    """Build the prompt for platform adaptation (Facebook variant)."""
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
            
    variant_prompt = PLATFORM_VARIANT_GENERATOR_PROMPT.format(
        platform="facebook",
        core_message=master_content.get("core_message", ""),
        extended_message=master_content.get("extended_message", ""),
        tone_markers=", ".join(master_content.get("tone_markers", [])),
        call_to_action=master_content.get("call_to_action", ""),
        char_limit="63206 chars",
        platform_guidelines="Conversational, community-focused, emoji-driven, rich storytelling",
        content_format="Social Post",
        brand_voice="Chuyên nghiệp, sắc bén, số liệu thực tế",
        persona_name="Sếp CMO bận rộn",
        persona_characteristics="Không có thời gian, đau đầu vì CPA tăng vọt",
        language="Vietnamese"
    )
    
    variant_prompt += cpa_constraints + feedback_injection
    return variant_prompt

def build_brand_guardian_prompt(
    state: AgencyState, 
    master_content: dict, 
    fb_copy: str
) -> str:
    """Build the compliance check prompt for Brand Guardian."""
    guardian_prompt = EDITOR_BRAND_GUARDIAN_PROMPT.format(
        brand_name="G-Agent Tech",
        brand_voice="Chuyên nghiệp, sắc bén, số liệu thực tế",
        brand_keywords="AI Agent, LangGraph, Tối ưu CPA"
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

def strategist_node(state: AgencyState) -> dict:
    """
    Strategist Node (Ban Sáng Tạo).
    Reads RAG psychological/economic insights, enforces RAG anti-patterns injection,
    and creates a structured content marketing angle strategy.
    """
    logger.info("Executing Strategist Node (Marketing Angle Formulation)...")
    db: Session = SessionLocal()
    
    workspace_id = state.get("workspace_id")
    product_id = state.get("product_id")
    
    # 1. Fetch Product details
    product = None
    if product_id:
        try:
            product = db.query(ProductService).filter_by(id=uuid.UUID(str(product_id))).first()
        except Exception:
            pass
    if not product:
        product = db.query(ProductService).filter_by(name="Marketing Agent OS Software").first()
        
    product_name = product.name if product else "Sản phẩm AI"
    product_usp = product.usp if product else "Công nghệ AI Agent tự động hóa tối ưu"
    
    # 2. Get customer insights from Researcher
    logger.info("Calling Researcher Agent for customer insights...")
    try:
        insights_str = run_research(workspace_id, f"chiến lược marketing khách hàng nỗi đau cho {product_name}")
        anti_patterns_report = run_research(workspace_id, f"mẫu quảng cáo thất bại sai lầm sản phẩm {product_name}")
    except Exception as e:
        logger.error(f"Lỗi phối hợp phòng ban: Strategist không nhận được báo cáo từ Researcher: {e}")
        db.close()
        raise RuntimeError(f"Lỗi phối hợp phòng ban: Strategist không thể nhận báo cáo từ Researcher: {e}") from e
    finally:
        db.close()
        
    # 3. Build Prompt & Generate
    final_prompt = build_strategist_prompt(state, product_name, product_usp, anti_patterns_report, insights_str)
    
    logger.info("Generating marketing angle strategy from Ollama...")
    system_prompt = "You are a professional marketing strategist. You MUST format output in valid JSON."
    res_str = generate_text(final_prompt, system_prompt=system_prompt, json_format=True)
    angle_data = parse_llm_json(res_str, fallback_data=STRATEGIST_FALLBACK)
    
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

def copywriter_node(state: AgencyState) -> dict:
    """
    Copywriter Node (Ban Sáng Tạo).
    Constructs creative copies strictly constrained under Target CPA and Budget.
    """
    logger.info("Executing Copywriter Node (Constraint-Driven Content Generation)...")
    
    target_cpa = state.get("target_cpa", DEFAULT_TARGET_CPA)
    test_budget = state.get("test_budget", DEFAULT_TEST_BUDGET)
    
    # 1. Generate Master Content
    master_prompt = build_copywriter_master_prompt(state, target_cpa, test_budget)
    logger.info("Generating Master Content via Ollama...")
    master_res = generate_text(master_prompt, system_prompt="You are a master copywriter. Output JSON only.", json_format=True)
    master_content = parse_llm_json(master_res, fallback_data=COPYWRITER_MASTER_FALLBACK)

    # 2. Generate Platform Adaptation (Facebook variant)
    variant_prompt = build_copywriter_variant_prompt(state, master_content, target_cpa, test_budget)
    logger.info("Generating Facebook Platform Variant...")
    var_res = generate_text(variant_prompt, system_prompt="You are a platform optimization copywriter. Output JSON only.", json_format=True)
    fb_variant = parse_llm_json(var_res, fallback_data=FB_VARIANT_FALLBACK)
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

def brand_guardian_node(state: AgencyState) -> dict:
    """
    Brand Guardian Node (Ban Sáng Tạo).
    Enforces the strict CMO 100-Point compliance check.
    """
    logger.info("Executing Brand Guardian Node (Scoring Compliance Gatekeeper)...")
    
    master_content = state.get("master_content", {})
    variants = state.get("variants", [])
    feedback_log = state.get("feedback_log", [])
    
    if not variants:
        return {"sop_stage": "creative_generation"}
        
    fb_copy = variants[0].get("adapted_copy", "")
    
    # Run evaluation
    guardian_prompt = build_brand_guardian_prompt(state, master_content, fb_copy)
    logger.info("Running compliance scoring via Ollama...")
    res_str = generate_text(guardian_prompt, system_prompt="You are the Brand Guardian. Score compliance in valid JSON.", json_format=True)
    eval_data = parse_llm_json(res_str, fallback_data=GUARDIAN_FALLBACK)
    
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
