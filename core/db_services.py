# core/db_services.py
"""
Database Service Layer (v4.2) — Lớp dịch vụ CSDL tập trung cho Marketing Agent OS.
Gom toàn bộ các truy vấn SQL/SQLAlchemy từ các LangGraph Nodes về một mối duy nhất.
Giúp triệt tiêu sự phân tán, giảm thiểu lặp code, và tăng tính dễ bảo trì.
"""
import logging
import uuid
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from core.models import BrandIdentity, ProductService, MasterContent, PlatformVariant, MarketingCampaign

logger = logging.getLogger("core_db_services")
logging.basicConfig(level=logging.INFO)


def get_brand_context(workspace_id: uuid.UUID) -> dict:
    """
    Truy vấn thông tin thương hiệu của Workspace hiện tại.
    """
    db: Session = SessionLocal()
    brand_data = {
        "brand_name": "Không rõ (Chưa thiết lập thương hiệu)",
        "slogan": "",
        "keywords": [],
        "voice_and_tone": "",
        "dos": [],
        "donts": []
    }
    try:
        brand = db.query(BrandIdentity).filter_by(workspace_id=workspace_id).first()
        if brand:
            brand_data["brand_name"] = brand.brand_name
            if brand.core_messaging:
                brand_data["slogan"] = brand.core_messaging.get("slogan", "")
                brand_data["keywords"] = brand.core_messaging.get("keywords", [])
            brand_data["voice_and_tone"] = brand.voice_and_tone or ""
            if brand.dos_and_donts:
                brand_data["dos"] = brand.dos_and_donts.get("dos", [])
                brand_data["donts"] = brand.dos_and_donts.get("donts", [])
    except Exception as e:
        logger.error(f"Error in get_brand_context: {e}")
    finally:
        db.close()
    return brand_data


def get_product_context(product_id: uuid.UUID) -> dict:
    """
    Truy vấn thông tin chi tiết sản phẩm dịch vụ hiện tại.
    """
    db: Session = SessionLocal()
    product_data = {
        "name": "Không rõ (Chưa thiết lập sản phẩm)",
        "description": "",
        "usp": "",
        "key_features": [],
        "key_benefits": [],
        "price": 0.0,
        "cost": 0.0,
        "margin": 0.0
    }
    try:
        product = db.query(ProductService).filter_by(id=product_id).first()
        if product:
            product_data["name"] = product.name
            product_data["description"] = product.description or ""
            product_data["usp"] = product.usp or ""
            product_data["key_features"] = product.key_features or []
            product_data["key_benefits"] = product.key_benefits or []
            if product.default_offer and ";" in product.default_offer:
                try:
                    price_str, cost_str = product.default_offer.split(";")
                    product_data["price"] = float(price_str)
                    product_data["cost"] = float(cost_str)
                    product_data["margin"] = product_data["price"] - product_data["cost"]
                except Exception as pe:
                    logger.error(f"Error parsing default offer pricing: {pe}")
    except Exception as e:
        logger.error(f"Error in get_product_context: {e}")
    finally:
        db.close()
    return product_data


def get_cpa_anchor(product_id: uuid.UUID, campaign_id: uuid.UUID = None) -> tuple[float, float]:
    """
    Tính toán CPA Target và Ngân sách Test từ Product Master Data và Campaign.
    Dành cho Analyst Node.
    """
    db: Session = SessionLocal()
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
    finally:
        db.close()
        
    return target_cpa, test_budget


def get_creative_report_data(workspace_id: uuid.UUID) -> dict:
    """
    Truy vấn số liệu và chi tiết sáng tạo của các Angle và kịch bản trong Workspace.
    Dành cho Creative Reporter Node.
    """
    db: Session = SessionLocal()
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
    finally:
        db.close()
        
    return report_data


def get_performance_report_data(workspace_id: uuid.UUID) -> list[PlatformVariant]:
    """
    Truy vấn danh sách PlatformVariant đang chạy (hoặc đã tối ưu) trong Workspace hiện tại.
    Dành cho Performance Reporter Node.
    """
    db: Session = SessionLocal()
    variants = []
    try:
        variants = db.query(PlatformVariant).filter(
            PlatformVariant.workspace_id == workspace_id,
            PlatformVariant.publish_status == "published"
        ).all()
        
        # Tạo bản sao đối tượng tách biệt khỏi session để tránh lỗi DetachedInstanceError ngoài luồng session
        detached_variants = []
        for v in variants:
            # Tạo bản sao
            v_copy = PlatformVariant(
                id=v.id,
                workspace_id=v.workspace_id,
                master_content_id=v.master_content_id,
                platform=v.platform,
                adapted_copy=v.adapted_copy,
                publish_status=v.publish_status,
                metric_views=v.metric_views,
                metric_likes=v.metric_likes,
                metric_shares=v.metric_shares,
                metric_comments=v.metric_comments,
                meta_data=v.meta_data,
                created_at=v.created_at
            )
            detached_variants.append(v_copy)
        variants = detached_variants
    except Exception as e:
        logger.error(f"Error in get_performance_report_data: {e}")
    finally:
        db.close()
        
    return variants
