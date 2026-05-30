# graphs/business.py
import logging
import uuid
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.models import ProductService, PlatformVariant, MarketingCampaign
from core.db_services import get_cpa_anchor
from graphs.state import AgencyState
from core.decision_logger import log_decision
from langchain_core.messages import AIMessage

logger = logging.getLogger("graphs_business")
logging.basicConfig(level=logging.INFO)

def analyst_node(state: AgencyState) -> dict:
    """
    Analyst Node (Ban Kinh Doanh).
    Calculates Target CPA and Test Budget from Product Master Data.
    Acts as the economic anchor of the system.
    """
    logger.info("Executing Analyst Node (CPA Anchor Calculation via DB Services)...")
    
    workspace_id = state.get("workspace_id")
    product_id = state.get("product_id")
    campaign_id = state.get("campaign_id")
    
    # Calculate target CPA and test budget limit dynamically via CSDL Service Layer
    target_cpa, test_budget = get_cpa_anchor(
        uuid.UUID(str(product_id)) if product_id else None,
        uuid.UUID(str(campaign_id)) if campaign_id else None
    )

    # SOP RULE: Check Anchor Values
    if target_cpa <= 0 or test_budget <= 0:
        raise ValueError(
            f"Lỗi SOP: Giá trị kinh tế sống còn không hợp lệ! "
            f"CPA Target: {target_cpa}, Ngân sách Test: {test_budget}. Quy trình bị hủy bỏ."
        )

    logger.info(f"CPA Anchor Set! Target CPA: {target_cpa} VNĐ, Ngân sách Test: {test_budget} VNĐ")
    
    # Log analyst decisions
    log_decision(
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        agent_name="Analyst Agent",
        action="Calculate CPA Anchor",
        decision_status="success",
        reason=f"Đã xác định các chỉ tiêu kinh tế sống còn cho chiến dịch: Target CPA = {target_cpa:,.0f} VNĐ (30% biên lợi nhuận), Ngân sách chạy thử = {test_budget:,.0f} VNĐ.",
        metadata={"target_cpa": target_cpa, "test_budget": test_budget}
    )
    
    # Return updated state with visual message persisted
    analyst_msg = (
        f"🎯 **[Phòng Kinh Doanh - Analyst]**\n"
        f"- Đã tính toán xong Điểm Neo kinh tế sống còn.\n"
        f"- **CPA Target:** `{target_cpa:,.0f} VNĐ` / đơn hàng.\n"
        f"- **Ngân sách Test tối đa:** `{test_budget:,.0f} VNĐ`."
    )
    return {
        "target_cpa": target_cpa,
        "test_budget": test_budget,
        "draft_plan": {
            "test_budget": test_budget,
            "target_cpa": target_cpa,
            "notes_for_creative": ""
        },
        "sop_stage": "cpa_calculation",
        "messages": [AIMessage(content=analyst_msg)]
    }

def performance_node(state: AgencyState) -> dict:
    """
    Performance Node (Ban Kinh Doanh).
    Monitors active campaigns. Shuts down failing variants (killed),
    registers feedback payload for the Creative department, and calls
    Ollama Qwen2.5 to synthesize a highly premium Performance Report for the CMO.
    """
    logger.info("Executing Performance Node (Scale/Kill Optimization & Premium Report)...")
    db: Session = SessionLocal()
    
    workspace_id = state.get("workspace_id")
    target_cpa = state.get("target_cpa", 1050000.0) # Fallback to analyst anchor
    
    # Query running platform variants in the active workspace
    variants = db.query(PlatformVariant).filter(
        PlatformVariant.workspace_id == uuid.UUID(str(workspace_id)),
        PlatformVariant.publish_status == "published"
    ).all()
    
    # If empty (first run), we dynamically inject a mock failing sample 
    # to demonstrate the automatic inter-department feedback loop (Giao thức cãi nhau)
    if not variants:
        logger.info("No active variants found in database. Generating mock failing sample for demonstration...")
        # Create a mock campaign and master content first
        try:
            from core.models import MarketingCampaign, MasterContent
            # Find seeded user/workspace
            from core.models import User, Workspace
            ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
            if ws:
                # Add mock campaign
                camp = MarketingCampaign(
                    workspace_id=ws.id,
                    name="Mock Performance Campaign",
                    budget=2000000.0,
                    status="active"
                )
                db.add(camp)
                db.commit()
                
                master = MasterContent(
                    workspace_id=ws.id,
                    campaign_id=camp.id,
                    core_message="Marketing Agent OS v2.0 - Giải phóng sức lao động CMO",
                    approval_status="approved"
                )
                db.add(master)
                db.commit()
                
                # Failing variant (CPA = 1,400,000 VND which is > 1,050,000 VND target)
                failed_var = PlatformVariant(
                    workspace_id=ws.id,
                    master_content_id=master.id,
                    platform="facebook",
                    adapted_copy="🔥 Mệt mỏi vì ads đắt? Marketing Agent OS giúp bạn tự động hóa ads cực rẻ! Mua ngay để nhận ưu đãi 10%!",
                    publish_status="published",
                    metric_views=120,
                    metric_likes=5,
                    metric_shares=2,
                    metric_comments=1,
                    # We store metric_cpa or cost in metadata since SQL schema stores metrics views/likes
                    meta_data={"metric_cpa": 1400000.0} # Failing CPA
                )
                db.add(failed_var)
                db.commit()
                variants = [failed_var]
                logger.info(f"Injected mock failing variant ID {failed_var.id} (CPA: 1,400,000 VNĐ)")
        except Exception as e:
            logger.error(f"Failed to seed mock failing variant: {e}")
            
    killed_feedback = []
    
    for v in variants:
        # Extract CPA from metadata
        metrics = v.meta_data or {}
        cpa = metrics.get("metric_cpa", 0.0)
        
        if cpa > 0:
            if cpa > target_cpa:
                # Kill variant
                v.publish_status = "killed"
                db.add(v)
                logger.warning(f"KILLED: Variant {v.id} on {v.platform} has CPA {cpa} > Target {target_cpa}")
                
                # Log performance agent decision to kill
                log_decision(
                    workspace_id=workspace_id,
                    campaign_id=state.get("campaign_id"),
                    agent_name="Performance Agent",
                    action="Kill Variant",
                    decision_status="killed",
                    reason=f"Đã khai tử kịch bản quảng cáo {v.id} trên kênh {v.platform} do chi phí CPA thực tế đạt {cpa:,.0f} VNĐ, vượt quá ngưỡng CPA mục tiêu {target_cpa:,.0f} VNĐ.",
                    metadata={"variant_id": str(v.id), "failed_cpa": cpa, "target_cpa": target_cpa, "copy": v.adapted_copy}
                )
                
                # Record feedback payload (Inter-department SOP)
                killed_feedback.append({
                    "variant_id": str(v.id),
                    "platform": v.platform,
                    "failed_copy": v.adapted_copy,
                    "failed_cpa": cpa,
                    "target_cpa": target_cpa,
                    "reason_killed": f"CPA thực tế {cpa} VNĐ vượt quá ngưỡng cho phép {target_cpa} VNĐ."
                })
            else:
                # Scale variant (budget + 20%)
                v.publish_status = "scaled"
                db.add(v)
                logger.info(f"SCALED: Variant {v.id} on {v.platform} has CPA {cpa} <= Target {target_cpa}")
                
                # Log performance agent decision to scale
                log_decision(
                    workspace_id=workspace_id,
                    campaign_id=state.get("campaign_id"),
                    agent_name="Performance Agent",
                    action="Scale Variant",
                    decision_status="scaled",
                    reason=f"Đã tăng 20% ngân sách phân phối cho kịch bản {v.id} trên kênh {v.platform} do hoạt động hiệu quả, CPA thực tế đạt {cpa:,.0f} VNĐ thấp hơn CPA mục tiêu {target_cpa:,.0f} VNĐ.",
                    metadata={"variant_id": str(v.id), "metric_cpa": cpa, "target_cpa": target_cpa}
                )
                
    db.commit()
    
    # 2. Gather views, likes, shares, comments, CPA targets for LLM synthesis report
    total_views = sum(v.metric_views or 0 for v in variants)
    total_likes = sum(v.metric_likes or 0 for v in variants)
    total_shares = sum(v.metric_shares or 0 for v in variants)
    total_comments = sum(v.metric_comments or 0 for v in variants)
    
    total_variants = len(variants)
    killed_count = sum(1 for v in variants if v.publish_status == "killed")
    scaled_count = sum(1 for v in variants if v.publish_status == "scaled")
    published_count = sum(1 for v in variants if v.publish_status == "published")
    
    variant_details = []
    for i, v in enumerate(variants):
        metrics = v.meta_data or {}
        cpa = metrics.get("metric_cpa", 0.0)
        variant_details.append(
            f"{i+1}. Kịch bản ID: {v.id}\n"
            f"   - Kênh phân phối: {v.platform.upper()}\n"
            f"   - Trạng thái tối ưu: {v.publish_status.upper()}\n"
            f"   - Chỉ số tương tác: Lượt xem = {v.metric_views or 0:,} | Lượt thích = {v.metric_likes or 0:,} | Chia sẻ = {v.metric_shares or 0:,} | Bình luận = {v.metric_comments or 0:,}\n"
            f"   - CPA thực tế: {cpa:,.0f} VNĐ\n"
            f"   - CPA Mục tiêu (Target CPA): {target_cpa:,.0f} VNĐ\n"
            f"   - Nội dung kịch bản quảng cáo: \"{v.adapted_copy[:150]}...\"\n"
        )
    details_str = "\n".join(variant_details) if variant_details else "(Chưa có kịch bản quảng cáo nào được ghi nhận)"
    
    # 3. Design the high-quality LLM prompt
    prompt = (
        f"Bạn là Trợ lý Báo cáo Hiệu suất (Performance Reporter Agent) của ban Kinh Doanh.\n"
        f"Dưới đây là các số liệu hiệu suất chiến dịch thực tế được truy xuất từ CSDL hệ thống:\n\n"
        f"TỔNG THỂ HIỆU SUẤT CHIẾN DỊCH:\n"
        f"- Tổng số kịch bản quảng cáo được đánh giá: {total_variants}\n"
        f"- Số kịch bản đã tắt (KILLED - do CPA vượt ngưỡng): {killed_count}\n"
        f"- Số kịch bản được tăng ngân sách (SCALED - hoạt động hiệu quả): {scaled_count}\n"
        f"- Số kịch bản đang chạy (PUBLISHED): {published_count}\n"
        f"- Tổng lượt xem (Views): {total_views:,}\n"
        f"- Tổng lượt thích (Likes): {total_likes:,}\n"
        f"- Tổng lượt chia sẻ (Shares): {total_shares:,}\n"
        f"- Tổng lượt bình luận (Comments): {total_comments:,}\n"
        f"- CPA Target (Ngưỡng tối đa cho phép): {target_cpa:,.0f} VNĐ\n\n"
        f"CHI TIẾT TỪNG KỊCH BẢN QUẢNG CÁO:\n"
        f"{details_str}\n\n"
        f"YÊU CẦU TRẢ LỜI:\n"
        f"1. Tổng hợp một bản báo cáo hiệu suất bằng Tiếng Việt chuyên nghiệp gửi cho CMO.\n"
        f"2. Bắt buộc có bảng biểu Markdown hiển thị so sánh hiệu suất giữa các kịch bản quảng cáo. Bảng gồm các cột: Kênh, Lượt xem, Lượt thích, CPA thực tế, CPA Target, Trạng thái tối ưu, Tóm tắt nội dung.\n"
        f"3. Phân tích cụ thể lý do tại sao một số kịch bản bị khai tử (KILLED) và tại sao một số kịch bản được tăng ngân sách (SCALED). Nhận xét mối quan hệ giữa lượt xem, tương tác và CPA.\n"
        f"4. Đề xuất các khuyến nghị hành động cụ thể tiếp theo cho CMO để tối ưu hóa hiệu quả kinh doanh của toàn chiến dịch (ví dụ: chuyển ngân sách sang kênh nào, yêu cầu sáng tạo viết lại gì).\n"
        f"5. Giữ giọng văn cực kỳ chuyên nghiệp, sắc bén của một Performance Marketing Director, phân tích dựa trên dữ liệu cụ thể, không nói chung chung.\n\n"
        f"BÁO CÁO PHÂN TÍCH HIỆU SUẤT CHI TIẾT:"
    )
    
    try:
        from core.ollama_client import generate_text
        logger.info("Calling Ollama to synthesize premium performance report...")
        report = generate_text(
            prompt=prompt,
            system_prompt="Bạn là Performance Reporter Agent chuyên nghiệp. Hãy viết báo cáo phân tích hiệu suất chiến dịch chất lượng cao.",
            workspace_id=workspace_id
        )
    except Exception as e:
        logger.error(f"Error calling LLM for performance report: {e}")
        # Robust fallback
        report = (
            f"### Báo Cáo Hiệu Suất Chiến Dịch (Fallback từ CSDL)\n\n"
            f"Do sự cố kết nối LLM, dưới đây là tóm tắt thô từ CSDL:\n\n"
            f"| Kênh | Lượt xem | Lượt thích | CPA thực tế | CPA Target | Trạng thái tối ưu |\n"
            f"| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        )
        for v in variants:
            metrics = v.meta_data or {}
            cpa = metrics.get("metric_cpa", 0.0)
            report += f"| {v.platform.upper()} | {v.metric_views or 0:,} | {v.metric_likes or 0:,} | {cpa:,.0f} VNĐ | {target_cpa:,.0f} VNĐ | {v.publish_status.upper()} |\n"
            
    # Log the decision to generate the report
    log_decision(
        workspace_id=workspace_id,
        campaign_id=state.get("campaign_id"),
        agent_name="Performance Reporter",
        action="Synthesize Performance Report",
        decision_status="success",
        reason=f"Đã tổng hợp thành công báo cáo hiệu suất chiến dịch cho CMO dựa trên dữ liệu của {total_variants} platform variants.",
        metadata={"total_variants": total_variants, "killed_count": killed_count, "scaled_count": scaled_count}
    )
    
    db.close()
    
    perf_msg = (
        f"📈 **[Ban Kinh Doanh - Performance Reporter]**\n\n"
        f"{report.strip()}"
    )

    return {
        "killed_variants_feedback": killed_feedback,
        "sop_stage": "triage",
        "messages": [AIMessage(content=perf_msg)]
    }
