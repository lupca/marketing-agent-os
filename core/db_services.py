# core/db_services.py
"""
Database Service Layer (v4.2) — Lớp dịch vụ CSDL tập trung cho Marketing Agent OS.
Gom toàn bộ các truy vấn SQL/SQLAlchemy từ các LangGraph Nodes về một mối duy nhất.
Giúp triệt tiêu sự phân tán, giảm thiểu lặp code, và tăng tính dễ bảo trì.
"""
import logging
import uuid
from sqlalchemy.orm import Session
from core.dependencies import get_session
from core.models import BrandIdentity, ProductService, MasterContent, PlatformVariant, MarketingCampaign, CustomerPersona

logger = logging.getLogger("core_db_services")
logging.basicConfig(level=logging.INFO)


def get_brand_context(workspace_id: uuid.UUID) -> dict:
    """
    Truy vấn thông tin thương hiệu của Workspace hiện tại.
    """
    with get_session() as db:
        try:
            brand = db.query(BrandIdentity).filter_by(workspace_id=workspace_id).first()
            if brand:
                return {
                    "brand_name": brand.brand_name or "",
                    "slogan": brand.core_messaging.get("slogan", "") if brand.core_messaging else "",
                    "keywords": brand.core_messaging.get("keywords", []) if brand.core_messaging else [],
                    "voice_and_tone": brand.voice_and_tone or "",
                    "dos": brand.dos_and_donts.get("dos", []) if brand.dos_and_donts else [],
                    "donts": brand.dos_and_donts.get("donts", []) if brand.dos_and_donts else []
                }
        except Exception as e:
            logger.error(f"Error in get_brand_context: {e}")
        return {}


def get_product_context(product_id: uuid.UUID) -> dict:
    """
    Truy vấn thông tin chi tiết sản phẩm dịch vụ hiện tại.
    """
    with get_session() as db:
        try:
            product = db.query(ProductService).filter_by(id=product_id).first()
            if product:
                product_data = {
                    "name": product.name or "",
                    "description": product.description or "",
                    "usp": product.usp or "",
                    "key_features": product.key_features or [],
                    "key_benefits": product.key_benefits or [],
                    "price": 0.0,
                    "cost": 0.0,
                    "margin": 0.0
                }
                if product.default_offer and ";" in product.default_offer:
                    try:
                        price_str, cost_str = product.default_offer.split(";")
                        product_data["price"] = float(price_str)
                        product_data["cost"] = float(cost_str)
                        product_data["margin"] = product_data["price"] - product_data["cost"]
                    except Exception as pe:
                        logger.error(f"Error parsing default offer pricing: {pe}")
                return product_data
        except Exception as e:
            logger.error(f"Error in get_product_context: {e}")
        return {}


def get_cpa_anchor(product_id: uuid.UUID, campaign_id: uuid.UUID = None) -> tuple[float, float]:
    """
    Tính toán CPA Target và Ngân sách Test từ Product Master Data và Campaign.
    Dành cho Analyst Node.
    """
    with get_session() as db:
        target_cpa = 1050000.0  # Default fallback
        test_budget = 2000000.0  # Default fallback
    
        try:
            product = None
            if product_id:
                product = db.query(ProductService).filter_by(id=product_id).first()
            
            if not product:
                # Fallback to default product
                product = db.query(ProductService).filter_by(name="Marketing Agent OS Software").first()
            
            if product:
                try:
                    price_str, cost_str = product.default_offer.split(";")
                    price = float(price_str)
                    cost = float(cost_str)
                    margin = price - cost
                    target_cpa = round(margin * 0.3, 0)
                except Exception as pe:
                    logger.error(f"Failed to parse product offer: {pe}")
                
            if campaign_id:
                camp = db.query(MarketingCampaign).filter_by(id=campaign_id).first()
                if camp and camp.budget > 0:
                    test_budget = float(camp.budget)
        except Exception as e:
            logger.error(f"Error in get_cpa_anchor: {e}")
        return target_cpa, test_budget


def get_creative_report_data(workspace_id: uuid.UUID) -> dict:
    """
    Truy vấn số liệu và chi tiết sáng tạo của các Angle và kịch bản trong Workspace.
    Dành cho Creative Reporter Node.
    """
    with get_session() as db:
        report_data = {
            "total_angles": 0,
            "scheduled_copies": 0,
            "published_copies": 0,
            "killed_copies": 0,
            "scaled_copies": 0,
            "creative_details_str": ""
        }
    
        try:
            master_contents = db.query(MasterContent).filter(
                MasterContent.workspace_id == workspace_id
            ).order_by(MasterContent.created_at.desc()).all()
        
            variants = db.query(PlatformVariant).filter(
                PlatformVariant.workspace_id == workspace_id
            ).all()
        
            report_data["total_angles"] = len(master_contents)
            report_data["scheduled_copies"] = sum(1 for v in variants if v.publish_status == "scheduled")
            report_data["published_copies"] = sum(1 for v in variants if v.publish_status == "published")
            report_data["killed_copies"] = sum(1 for v in variants if v.publish_status == "killed")
            report_data["scaled_copies"] = sum(1 for v in variants if v.publish_status == "scaled")
        
            details = []
            for i, mc in enumerate(master_contents):
                platform_info = []
                matching_variants = [v for v in variants if v.master_content_id == mc.id]
                for v in matching_variants:
                    platform_info.append(f"   * Kênh: {v.platform.upper()} | Trạng thái: {v.publish_status} | Copy: \"{v.adapted_copy[:150]}...\"")
                
                details.append(
                    f"{i+1}. Thông điệp cốt lõi: \"{mc.core_message}\"\n"
                    f"   - Ngày tạo: {mc.created_at.strftime('%d/%m/%Y %H:%M') if mc.created_at else 'Chưa rõ'}\n"
                    f"   - Trạng thái phê duyệt: {mc.approval_status}\n"
                    + "\n".join(platform_info)
                )
            
            report_data["creative_details_str"] = "\n\n".join(details) if details else "(Chưa có kịch bản hoặc thông điệp cốt lõi nào được khởi tạo trong CSDL)"
        except Exception as e:
            logger.error(f"Error in get_creative_report_data: {e}")
        return report_data


def get_performance_report_data(workspace_id: uuid.UUID) -> list[dict]:
    """
    Truy vấn danh sách PlatformVariant đang chạy (hoặc đã tối ưu) trong Workspace hiện tại.
    Dành cho Performance Reporter Node.
    """
    from core.schemas import PlatformVariantSchema
    with get_session() as db:
        try:
            variants = db.query(PlatformVariant).filter(
                PlatformVariant.workspace_id == workspace_id,
                PlatformVariant.publish_status == "published"
            ).all()
        
            # Sử dụng Pydantic Schema để tách biệt dữ liệu khỏi session
            return [PlatformVariantSchema.model_validate(v).model_dump() for v in variants]
        except Exception as e:
            logger.error(f"Error in get_performance_report_data: {e}")
            return []


def get_persona_context(workspace_id: uuid.UUID) -> dict:
    """
    Truy vấn thông tin chân dung khách hàng của Workspace hiện tại.
    """
    with get_session() as db:
        try:
            persona = db.query(CustomerPersona).filter_by(workspace_id=workspace_id).first()
            if persona:
                return {
                    "persona_name": persona.persona_name or "",
                    "summary": persona.summary or "",
                    "demographics": persona.demographics or {},
                    "psychographics": persona.psychographics or {}
                }
        except Exception as e:
            logger.error(f"Error in get_persona_context: {e}")
        return {}


def get_unified_business_context(workspace_id: uuid.UUID, product_id: uuid.UUID = None) -> dict:
    """
    Tổng hợp Brand Identity, Product/Service và Customer Persona thành một business_context hoàn chỉnh.
    """
    # 1. Lấy Brand Context
    brand = get_brand_context(workspace_id)
    
    # 2. Lấy Product Context
    p_id = product_id
    if not p_id:
        with get_session() as db:
            try:
                prod = db.query(ProductService).filter_by(workspace_id=workspace_id).first()
                if prod:
                    p_id = prod.id
            except Exception as e:
                logger.error(f"Error finding product in get_unified_business_context: {e}")
    
    product = get_product_context(p_id) if p_id else {}
    
    # 3. Lấy Persona Context
    persona = get_persona_context(workspace_id)
    
    return {
        "brand": brand,
        "product": product,
        "persona": persona
    }


def save_publisher_state(
    db: Session,
    ws_id: uuid.UUID,
    camp_uuid: uuid.UUID,
    variants: list[dict],
    ad_mappings: dict[str, str],
    fb_account_id: str
) -> None:
    """
    Saves master content, platform variants, and ad mappings atomically to PostgreSQL.
    """
    from core.models import MasterContent, PlatformVariant, AdMapper
    
    master = MasterContent(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        campaign_id=camp_uuid,
        core_message="Autonomous Creative Engine Generated Copy Master",
        approval_status="approved"
    )
    db.add(master)
    
    for v in variants:
        v_id = v["variant_id"]
        pv = PlatformVariant(
            id=uuid.UUID(v_id),
            workspace_id=ws_id,
            master_content_id=master.id,
            platform=v.get("platform", "facebook"),
            adapted_copy=v.get("adapted_copy", ""),
            publish_status="published",
            content_type=v.get("content_type", "text"),
            meta_data={"angle_name": v.get("angle_name")}
        )
        db.add(pv)
        db.flush() # Force parent inserts to flush so Postgres registers and locks the foreign key before child insert
        
        # Get the external Platform_Ad_ID
        plat_ad_id = ad_mappings.get(v_id) or f"{fb_account_id}_{uuid.uuid4().hex[:8]}"
        logger.info(f"Mapping Variant {pv.id} -> Ad {plat_ad_id}")
        
        mapper = AdMapper(
            variant_id=pv.id,
            platform_ad_id=plat_ad_id
        )
        db.add(mapper)
        
    db.commit()
    logger.info("Successfully persisted all published campaign contents atomically in database!")
