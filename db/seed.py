# db/seed.py
import sys
import os
import uuid
import logging
from sqlalchemy.orm import Session

# Add project root to sys.path for direct execution
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal, is_mock
from core.models import User, Workspace, BrandIdentity, CustomerPersona, ProductService, RAGKnowledgebase, IntentRoutingKnowledge

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
        
    # 6. Seed Default RAG Knowledgebase entries for Facebook / TikTok Ad Policy
    from core.rag import store_knowledge
    
    policies_exist = db.query(RAGKnowledgebase).filter_by(category="policies").first()
    if not policies_exist:
        logger.info("Seeding Facebook and TikTok advertising policy guidelines...")
        fb_policy = (
            "Chính sách Quảng cáo Facebook (Meta Ads Policy) về Từ khóa cấm và Hạn chế:\n"
            "- Các từ khóa cấm tuyệt đối liên quan đến cam kết phi thực tế: 'cam kết 100%', 'trị dứt điểm', 'thuốc trị', 'tăng cân', 'giảm cân', 'vĩnh viễn', 'hoàn tiền', 'chữa trị', 'bác sĩ khuyên dùng', 'hiệu quả tức thì'.\n"
            "- Các lĩnh vực bị hạn chế đặc biệt: Tiền mã hóa (cryptocurrency), tài chính cá nhân/cho vay, sản phẩm người lớn, các vấn đề xã hội/chính trị, hình ảnh so sánh Trước/Sau (Before/After) khi sử dụng sản phẩm giảm cân/mỹ phẩm.\n"
            "- Cơ chế hoạt động: Facebook sử dụng các mô hình AI NLP (Xử lý ngôn ngữ tự nhiên) để quét văn bản trong bài viết quảng cáo, tiêu đề, mô tả và công cụ OCR (Nhận dạng ký tự quang học) để đọc chữ xuất hiện trên ảnh hoặc video. Bất kỳ sự vi phạm nào cũng dẫn đến việc từ chối phê duyệt quảng cáo (ad rejection) hoặc vô hiệu hóa tài khoản quảng cáo của bạn (banned ad account)."
        )
        
        tiktok_policy = (
            "Chính sách Quảng cáo TikTok (TikTok Ads Policy) về Từ khóa cấm và Hạn chế:\n"
            "- Các từ ngữ bị cấm hoặc hạn chế tối đa: 'nhất', 'số 1', 'tuyệt đối', '100%', 'hoàn hảo', 'cam đoan', 'điều trị', 'cam kết sạch mụn'.\n"
            "- Các chủ đề nhạy cảm: Tài chính cá nhân & vay tín chấp, sản phẩm y tế/sức khỏe, thay đổi hình thể quá mức, cờ bạc, hàng giả/hàng nhái thương hiệu lớn.\n"
            "- Cơ chế hoạt động: TikTok quét cả văn bản caption bài đăng, chữ hiển thị đè trên video (text overlays) và đặc biệt là giọng nói lồng trong video (voiceover) thông qua công nghệ chuyển đổi giọng nói thành văn bản tự động (ASR - Automatic Speech Recognition). Do đó, việc chèn chữ hoặc nói các từ cấm đều bị hệ thống phát hiện ngay lập tức."
        )
        
        store_knowledge(
            db=db,
            workspace_id=default_ws.id,
            category="policies",
            source_name="Facebook_Ad_Policy_Guidelines.txt",
            content=fb_policy,
            metadata={"platform": "facebook", "type": "policy"}
        )
        
        store_knowledge(
            db=db,
            workspace_id=default_ws.id,
            category="policies",
            source_name="TikTok_Ad_Policy_Guidelines.txt",
            content=tiktok_policy,
            metadata={"platform": "tiktok", "type": "policy"}
        )
        logger.info("Successfully seeded advertising policy guidelines in pgvector!")
    else:
        logger.info("Advertising policy guidelines already seeded.")
        
    # 7. Seed Semantic Router Utterances
    seed_semantic_router(db)
        
    logger.info("Database seeding successfully completed!")

def seed_semantic_router(db: Session):
    logger.info("Seeding Intent Routing Knowledge...")

    # Kiểm tra xem đã có dữ liệu chưa
    existing = db.query(IntentRoutingKnowledge).first()
    if existing:
        logger.info("Intent Routing Data already exists. Skipping.")
        return

    from core.ollama_client import get_embedding

    DEFAULT_UTTERANCES = {
        "create_campaign": [
            "Lên chiến dịch quảng cáo mới cho sản phẩm",
            "Viết cho tôi 3 kịch bản tiktok",
            "Tạo nội dung chạy ads tối ưu chuyển đổi",
            "Lên camp mới"
        ],
        "show_metrics": [
            "Báo cáo hiệu suất quảng cáo tuần này",
            "CPA của chiến dịch hôm qua là bao nhiêu?",
            "Kiểm tra xem kịch bản nào đang đốt tiền",
            "Xem số liệu ads"
        ],
        "research": [
            "Tại sao quảng cáo bị Facebook quét từ khóa cấm?",
            "Chính sách cấm của TikTok đối với ngành dược",
            "Trong tài liệu hướng dẫn viết gì về đánh vào nỗi sợ?",
            "Làm sao để kháng nghị tài khoản bị khóa"
        ],
        "chat": [
            "Chào buổi sáng",
            "Hello hệ thống",
            "Bạn có khỏe không"
        ]
    }

    for intent, sentences in DEFAULT_UTTERANCES.items():
        for sentence in sentences:
            logger.info(f"Generating embedding for intent router utterance: '{sentence}'...")
            try:
                vector = get_embedding(sentence)
                record = IntentRoutingKnowledge(
                    intent_category=intent,
                    utterance=sentence,
                    embedding=vector
                )
                db.add(record)
            except Exception as e:
                logger.error(f"Error seeding utterance '{sentence}': {e}")
                raise

    db.commit()
    logger.info("Successfully seeded semantic router data!")

if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        seed_database(db_session)
    finally:
        db_session.close()
