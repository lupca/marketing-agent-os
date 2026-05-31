# db/seed_vnb.py
import os
import sys
import uuid
import logging
from sqlalchemy.orm import Session

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.dependencies import get_session
from core.models import (
    Workspace, BrandIdentity, CustomerPersona, ProductService, 
    MarketingCampaign, MasterContent, PlatformVariant, 
    SocialInteraction, Lead, ContentBrief, AgentLog
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_vnb_seeder")

def seed_vnb_data():
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    
    with get_session() as db:
        logger.info(f"Targeting Workspace ID: {workspace_id}")
        
        # 1. Ensure Workspace exists
        ws = db.query(Workspace).filter_by(id=workspace_id).first()
        if not ws:
            logger.error("Workspace Team Alpha not found. Please run seed.py first.")
            return

        # 2. CLEAR EXISTING DATA (Overwrite requirement)
        # Delete in order of dependence (Cascade-like manual clear)
        logger.info("Clearing dependent marketing data to avoid FK violations...")
        db.query(SocialInteraction).filter_by(workspace_id=workspace_id).delete()
        db.query(Lead).filter_by(workspace_id=workspace_id).delete()
        db.query(PlatformVariant).filter_by(workspace_id=workspace_id).delete()
        db.query(MasterContent).filter_by(workspace_id=workspace_id).delete()
        db.query(ContentBrief).filter_by(workspace_id=workspace_id).delete()
        db.query(MarketingCampaign).filter_by(workspace_id=workspace_id).delete()
        db.query(AgentLog).filter_by(workspace_id=workspace_id).delete()
        
        # Now safe to delete products and brands
        db.query(ProductService).filter_by(workspace_id=workspace_id).delete()
        db.query(BrandIdentity).filter_by(workspace_id=workspace_id).delete()
        db.query(CustomerPersona).filter_by(workspace_id=workspace_id).delete()
        db.commit()
        logger.info("Cleared existing brand, persona, product, and campaign data.")

        # 3. SEED BRAND IDENTITY
        brand = BrandIdentity(
            workspace_id=workspace_id,
            brand_name="ShopVNB / VNB Sports",
            core_messaging={
                "slogan": "Together we can (Cùng nhau chúng ta có thể)",
                "mission": "Cam kết mang đến những sản phẩm, dịch vụ chất lượng tốt nhất phục vụ cho người chơi thể thao để nâng cao sức khỏe của chính mình.",
                "vision": "Trở thành nhà phân phối và sản xuất thể thao lớn nhất Việt Nam.",
                "business_philosophy": "Lấy chất lượng và sự sáng tạo làm bạn đồng hành; xem khách hàng là trung tâm để không ngừng cải tiến sản phẩm và dịch vụ."
            },
            visual_assets={
                "logo_design": "Chữ 'V' cách điệu cánh chim hoặc quả cầu lông đang chuyển động nhanh.",
                "colors": ["Navy Blue (Xanh dương đậm)", "Orange (Cam)"],
                "typography": "Sans-serif dày bản, mạnh mẽ, hơi nghiêng phải biểu thị tốc độ.",
                "signage": "Chất liệu Aluminium cao cấp, chữ nổi Mica gắn LED cường độ cao."
            },
            voice_and_tone=(
                "Tính chuyên gia chuyên nghiệp (Professional): Phân tích kỹ thuật, khúc chiết, thuật ngữ chính xác. "
                "Tính gần gũi, cộng đồng (Friendly & Inspiring): Gọi thân mật 'anh em lông thủ', đồng đam mê, tràn đầy cảm hứng."
            ),
            dos_and_donts={
                "dos": [
                    "Cam kết bán hàng chính hãng và minh bạch nguồn gốc.",
                    "Thực hiện video đánh giá khách quan dựa trên trải nghiệm thực tế.",
                    "Tôn trọng đạo đức kinh doanh và tuân thủ pháp luật.",
                    "Đồng bộ hóa trải nghiệm thiết kế tại mọi điểm nhượng quyền."
                ],
                "donts": [
                    "Tuyệt đối không bán hàng nhái, hàng kém chất lượng.",
                    "Không tâng bốc sản phẩm VNB phi thực tế hoặc hạ thấp đối thủ.",
                    "Tránh ngôn từ kích động, gây tranh cãi tiêu cực.",
                    "Nghiêm cấm nhượng quyền tự ý đưa sản phẩm ngoài hệ thống vào kinh doanh."
                ]
            },
            content_pillars={
                "Knowledge": "Chia sẻ Kiến thức & Kỹ thuật chơi cầu, căng vợt chuẩn.",
                "Review": "Đánh giá & Trải nghiệm Sản phẩm sâu sắc (Yonex, Lining, VNB...).",
                "Community": "Gắn kết Cộng đồng anh em lông thủ, khoảnh khắc ấn tượng.",
                "News": "Tin tức Doanh nghiệp & Khuyến mãi, khai trương chi nhánh."
            }
        )
        db.add(brand)
        db.flush() 
        logger.info("Seeded Brand Identity: VNB Sports")

        # 4. SEED CUSTOMER PERSONA
        persona = CustomerPersona(
            workspace_id=workspace_id,
            persona_name="Lông thủ phong trào và Học sinh, Sinh viên đam mê thể thao",
            summary=(
                "Người chơi cầu lông ở cấp độ phong trào từ mới bắt đầu đến trung bình. "
                "Mục tiêu rèn luyện sức khỏe, giải tỏa căng thẳng. "
                "Nhạy cảm về giá nhưng yêu cầu cao về độ bền và hỗ trợ lực."
            ),
            demographics={
                "age": "15 đến 35 tuổi",
                "gender": "Nam và Nữ (phân khúc nữ đang tăng trưởng)",
                "income": "Trung bình thấp đến trung bình khá (học sinh, sinh viên, VP trẻ)",
                "location": "Đô thị lớn và tỉnh thành có phong trào mạnh toàn quốc"
            },
            psychographics={
                "habits": "Chơi 2-4 buổi/tuần, tìm kiếm review trên YouTube/TikTok trước khi mua.",
                "secret_desires": "Nâng cao trình độ nhanh để tự tin giao lưu, sở hữu thiết kế thời thượng chuyên nghiệp.",
                "pain_points": [
                    "Lo sợ mua phải hàng giả, hàng nhái trôi nổi.",
                    "Ngân sách hạn chế, không đủ mua vợt cao cấp tiền triệu.",
                    "Dễ gặp chấn thương/mỏi tay do chọn sai vợt nặng/cứng."
                ],
                "buying_barriers": [
                    "Bối rối trước thông số kỹ thuật phức tạp (U, G, điểm cân bằng...).",
                    "Chi phí căng cước và thay thế phụ kiện định kỳ gây gánh nặng tài chính."
                ]
            }
        )
        db.add(persona)
        logger.info("Seeded Customer Persona: Lông thủ phong trào")

        # 5. SEED PRODUCTS & SERVICES
        vnb_rackets = ProductService(
            workspace_id=workspace_id,
            brand_id=brand.id,
            name="Dòng vợt cầu lông thương hiệu riêng VNB Sports (V200i, V200, V88, TC88)",
            description="Vợt cầu lông được tối ưu về thiết kế và thông số cho thể trạng người Việt, phục vụ chuyên biệt người chơi phong trào.",
            usp="Vợt chính hãng Carbon siêu bền dưới 1 triệu, đũa dẻo trợ lực tối đa, sức căng vượt trội đến 30 LBS.",
            key_features={
                "VNB V200i Hồng": "5U (75g), Nặng đầu, Đũa dẻo, Carbon High Modulus Graphite.",
                "VNB V200 Xanh/Đỏ": "4U (84g), Công thủ toàn diện hoặc Thiên công, Khung khí động học.",
                "VNB V88": "4U, Hơi nặng đầu, Đàn hồi nhanh, Smash uy lực."
            },
            key_benefits=[
                "Trợ lực tối đa cho cổ tay, phòng tránh chấn thương khớp vai.",
                "Độ bền bỉ đáng kinh ngạc, chịu mức căng cao, hạn chế nứt sập khung.",
                "Định hình và phát triển lối chơi linh hoạt cho người mới."
            ],
            default_offer="Tặng 02 quấn cán + túi đựng chuyên dụng. Đổi mới 1-đổi-1 nếu lỗi nhà sản xuất."
        )
        db.add(vnb_rackets)

        stringing_service = ProductService(
            workspace_id=workspace_id,
            brand_id=brand.id,
            name="Dịch vụ đan vợt và bảo dưỡng tiêu chuẩn kỹ thuật cao tại ShopVNB",
            description="Dịch vụ giá trị gia tăng thực hiện bởi kỹ thuật viên kinh nghiệm tại hệ thống cửa hàng vật lý.",
            usp="Quy trình căng vợt chuẩn 4 nút Yonex trên máy điện tử hiện đại, đảm bảo lực căng đồng đều tuyệt đối.",
            key_features={
                "Kỹ thuật 4 nút": "Chia dây cước riêng biệt, đan đều từ tâm ra hai bên bảo vệ khung.",
                "Máy điện tử": "Đồng bộ hóa tốc độ kéo dây, loại bỏ sai số cảm tính.",
                "Kiểm soát lực kẹp": "Sử dụng máy 2-6 kẹp giữ khung khoa học, chống nứt/sập mặt vợt."
            },
            key_benefits=[
                "Bảo vệ tối đa tuổi thọ khung vợt, triệt tiêu nguy cơ biến dạng.",
                "Tối ưu hóa hiệu suất chơi với vùng điểm ngọt (sweet spot) rộng.",
                "Độ bền dây cước vượt trội, hạn chế xước xoắn dây."
            ],
            default_offer="Thay gen hỏng miễn phí + Lưu trữ lịch sử thông số cá nhân cho lần tư vấn sau."
        )
        db.add(stringing_service)
        
        db.commit()
        logger.info("Successfully seeded all VNB Sports data!")

if __name__ == "__main__":
    seed_vnb_data()
