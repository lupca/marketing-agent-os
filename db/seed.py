# db/seed.py
import sys
import os
import uuid
import logging
from sqlalchemy.orm import Session

# Add project root to sys.path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal, is_mock
from core.models import User, Workspace, BrandIdentity, CustomerPersona, ProductService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_seeder")

def seed_database(db: Session):
    """Seed default workspace, user, brands, and product constraints."""
    logger.info("Starting database seeding...")
    
    # 1. Seed Default User
    admin_user = db.query(User).filter_by(email="admin@marketingos.com").first()
    if not admin_user:
        admin_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            name="CMO Admin",
            email="admin@marketingos.com",
            password_hash="pbkdf2:sha256:default_hashed_password_for_testing",
            role="admin"
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        logger.info(f"Seeded User: {admin_user.email}")
    else:
        logger.info("Admin User already exists.")

    # 2. Seed Default Workspace
    default_ws = db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
    if not default_ws:
        default_ws = Workspace(
            id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            name="Team Alpha Workspace",
            owner_id=admin_user.id,
            members=[str(admin_user.id)],
            settings={"currency": "VND", "timezone": "Asia/Ho_Chi_Minh"}
        )
        db.add(default_ws)
        db.commit()
        db.refresh(default_ws)
        logger.info(f"Seeded Workspace: {default_ws.name}")
    else:
        logger.info("Workspace already exists.")

    # 3. Seed Default Brand Identity
    default_brand = db.query(BrandIdentity).filter_by(brand_name="G-Agent Tech").first()
    if not default_brand:
        default_brand = BrandIdentity(
            id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
            workspace_id=default_ws.id,
            brand_name="G-Agent Tech",
            core_messaging={
                "slogan": "Đột phá doanh thu bằng AI Agent tự trị",
                "keywords": ["AI Agent", "Tự trị", "Tối ưu CPA", "LangGraph"]
            },
            visual_assets={
                "color_palette": ["#000000", "#1A1A1A", "#6366F1"],
                "logo_url": ""
            },
            voice_and_tone=(
                "Chuyên nghiệp, khoa học, sắc bén và thực tế. "
                "Tuyệt đối không sử dụng tiếng lóng hay các từ ngữ sáo rỗng. "
                "Tập trung sâu vào giải pháp thực tế và số liệu chứng minh."
            ),
            dos_and_donts={
                "dos": ["Nêu bật số liệu thực tế", "Nói về hiệu suất chuyển đổi", "Tạo sự tò mò"],
                "donts": ["Cam kết 100% không căn cứ", "Dùng từ ngữ quá sến súa", "Sai Brand Voice"]
            },
            content_pillars={
                "pillars": ["Đào tạo AI", "Tự động hóa Marketing", "Case Study thực chiến"]
            }
        )
        db.add(default_brand)
        db.commit()
        db.refresh(default_brand)
        logger.info(f"Seeded Brand Identity: {default_brand.brand_name}")
    else:
        logger.info("Brand Identity already exists.")

    # 4. Seed Default Customer Persona
    default_persona = db.query(CustomerPersona).filter_by(persona_name="Sếp CMO bận rộn").first()
    if not default_persona:
        default_persona = CustomerPersona(
            id=uuid.UUID("00000000-0000-0000-0000-000000000004"),
            workspace_id=default_ws.id,
            persona_name="Sếp CMO bận rộn",
            summary="Các CMO, CEO, Giám đốc doanh nghiệp SMEs chịu áp lực doanh thu lớn nhưng thiếu thời gian tối ưu chi tiết quảng cáo.",
            demographics={
                "age": "28-45",
                "gender": "All",
                "income": "High",
                "location": "Vietnam Cities"
            },
            psychographics={
                "pain_points": [
                    "CPA quảng cáo ngày càng tăng vọt vượt kiểm soát", 
                    "Không có thời gian duyệt từng kịch bản TikTok/Facebook", 
                    "Bị phụ thuộc vào Agency thủ công"
                ],
                "goals": [
                    "Tự động hóa 80% quy trình sáng tạo và tối ưu kịch bản", 
                    "Giữ chi phí chuyển đổi (CPA) ổn định dưới mức target",
                    "Xem báo cáo hiệu năng Ads tự động hằng ngày"
                ]
            }
        )
        db.add(default_persona)
        db.commit()
        db.refresh(default_persona)
        logger.info(f"Seeded Customer Persona: {default_persona.persona_name}")
    else:
        logger.info("Customer Persona already exists.")

    # 5. Seed Default Product Service (Price/Cost variables for Analyst calculation)
    default_product = db.query(ProductService).filter_by(name="Marketing Agent OS Software").first()
    if not default_product:
        default_product = ProductService(
            id=uuid.UUID("00000000-0000-0000-0000-000000000005"),
            workspace_id=default_ws.id,
            brand_id=default_brand.id,
            name="Marketing Agent OS Software",
            description="Phần mềm tích hợp LangGraph + Chainlit tự động hóa phễu quảng cáo, tối ưu chuyển đổi ads tự động.",
            usp="Giải phóng hoàn toàn 80% thời gian CMO nhờ Multi-agent tự trị và an toàn ngân sách.",
            key_features=["Ban Kinh Doanh Analyst Node", "Ban Sáng Tạo Copywriter", "Tự động tắt/vít ngân sách ads"],
            key_benefits=["Tiết kiệm thời gian", "Độ chính xác CPA 100%", "Báo cáo Realtime"],
            default_offer="5000000;1500000" # Encoded string representation: "RETAIL_PRICE;COST_PRICE" for mock parsing
        )
        db.add(default_product)
        db.commit()
        db.refresh(default_product)
        logger.info(f"Seeded Product Service: {default_product.name}")
    else:
        logger.info("Product Service already exists.")
        
    logger.info("Database seeding successfully completed!")

if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        seed_database(db_session)
    finally:
        db_session.close()
