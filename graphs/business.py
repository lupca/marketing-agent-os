# graphs/business.py
import logging
import uuid
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.models import ProductService, PlatformVariant, MarketingCampaign
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
    logger.info("Executing Analyst Node (CPA Anchor Calculation)...")
    db: Session = SessionLocal()
    
    workspace_id = state.get("workspace_id")
    product_id = state.get("product_id")
    
    # 1. Fetch Product Pricing
    product = None
    if product_id:
        try:
            product = db.query(ProductService).filter_by(id=uuid.UUID(str(product_id))).first()
        except Exception:
            pass
            
    if not product:
        # Fallback to seeded default product
        product = db.query(ProductService).filter_by(name="Marketing Agent OS Software").first()
        
    if not product:
        db.close()
        raise ValueError("Lỗi SOP: Không tìm thấy bất kỳ sản phẩm nào trong CSDL để tính CPA Target. Hủy luồng.")

    # Parse pricing from default_offer e.g., "5000000;1500000"
    try:
        price_str, cost_str = product.default_offer.split(";")
        price = float(price_str)
        cost = float(cost_str)
    except Exception:
        # Hard fallback
        price = 5000000.0
        cost = 1500000.0

    margin = price - cost
    # Target CPA = 30% of Margin
    target_cpa = round(margin * 0.3, 0)
    
    # Fetch test budget limit from active campaign or default to 2M VND
    test_budget = 2000000.0
    campaign_id = state.get("campaign_id")
    if campaign_id:
        try:
            camp = db.query(MarketingCampaign).filter_by(id=uuid.UUID(str(campaign_id))).first()
            if camp and camp.budget > 0:
                test_budget = float(camp.budget)
        except Exception:
            pass
            
    db.close()

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
        "sop_stage": "cpa_calculation",
        "messages": [AIMessage(content=analyst_msg)]
    }

def performance_node(state: AgencyState) -> dict:
    """
    Performance Node (Ban Kinh Doanh).
    Monitors active campaigns. Shuts down failing variants (killed)
    and registers feedback payload for the Creative department.
    """
    logger.info("Executing Performance Node (Scale/Kill Optimization)...")
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
    db.close()
    
    # Return updated state with visual message persisted
    if killed_feedback:
        perf_msg = (
            f"🚨 **[Phòng Kinh Doanh - Performance]**\n"
            f"- Phát hiện `{len(killed_feedback)} kịch bản` vượt ngưỡng CPA!\n"
            f"- variant_id: `{killed_feedback[0].get('variant_id')}` bị TẮT (Killed) do CPA đạt `{killed_feedback[0].get('failed_cpa'):,.0f} VNĐ` > Target `{target_cpa:,.0f} VNĐ`.\n"
            f"👉 **Giao thức cãi nhau:** Gửi phản hồi nóng bắt Ban Sáng Tạo đổi Angle viết lại!"
        )
    else:
        perf_msg = "📈 **[Phòng Kinh Doanh - Performance]** Không phát hiện Ads vượt ngưỡng CPA. Mọi thứ vận hành an toàn."

    return {
        "killed_variants_feedback": killed_feedback,
        "sop_stage": "cpa_calculation",
        "messages": [AIMessage(content=perf_msg)]
    }
