-- Seed data for TOP VN SPORTS brand analysis
-- Assuming a default user and workspace will be created or exist, we use a fixed UUID for workspace

DO $$
DECLARE
    v_workspace_id UUID := uuid_generate_v4();
    v_brand_id UUID := uuid_generate_v4();
    v_persona_id UUID := uuid_generate_v4();
    v_product_1_id UUID := uuid_generate_v4();
    v_product_2_id UUID := uuid_generate_v4();
BEGIN

    -- 1. Create a Workspace for this data
    INSERT INTO workspaces (id, name, settings)
    VALUES (v_workspace_id, 'TOP VN SPORTS Workspace', '{}')
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING id INTO v_workspace_id;

    -- If workspace existed, we might have gotten null back from the conflict if we didn't use returning right, let's just do a clean insert if not exists or select
    SELECT id INTO v_workspace_id FROM workspaces WHERE name = 'TOP VN SPORTS Workspace';
    IF NOT FOUND THEN
        v_workspace_id := uuid_generate_v4();
        INSERT INTO workspaces (id, name, settings) VALUES (v_workspace_id, 'TOP VN SPORTS Workspace', '{}');
    END IF;

    -- 2. Insert Brand Identity
    INSERT INTO brand_identities (
        id, workspace_id, brand_name, core_messaging, visual_assets, voice_and_tone, dos_and_donts, content_pillars
    ) VALUES (
        v_brand_id,
        v_workspace_id,
        'TOP VN SPORTS (ShopVNB)',
        '{
            "slogan": "Together we can (Cùng nhau chúng ta có thể).",
            "mission": "Cam kết mang đến những sản phẩm, dịch vụ chất lượng tốt nhất phục vụ cho người chơi thể thao để nâng cao sức khỏe của chính mình.",
            "vision": "Trở thành nhà phân phối và sản xuất thể thao lớn nhất Việt Nam.",
            "philosophy": "Lấy chất lượng và sự sáng tạo làm bạn đồng hành; xem khách hàng là trung tâm để không ngừng cải tiến sản phẩm và dịch vụ."
        }'::jsonb,
        '{
            "logo": "Chữ V được cách điệu với hai cánh uốn cong mềm mại hướng lên trên, tạo hình dáng tương đồng với đôi cánh chim đang bay hoặc quả cầu lông đang chuyển động nhanh trên không trung.",
            "colors": "Sự kết hợp tương phản động giữa màu Xanh dương đậm (Navy Blue) và màu Cam rực rỡ (Orange). Trong các ứng dụng tối giản, logo chữ trắng được đặt trên nền xanh dương đậm.",
            "typography": "Sử dụng font chữ Sans-serif (không chân) dày bản, mạnh mẽ, hơi nghiêng về phía bên phải để biểu thị cho tốc độ chuyển động và tinh thần thể thao hiện đại.",
            "signage": "Sử dụng bảng hiệu chất liệu Aluminium (Alu) cao cấp kết hợp chữ nổi Mica gắn hệ thống đèn LED pha chiếu sáng cường độ cao để tối ưu nhận diện ban đêm."
        }'::jsonb,
        'Duy trì một giọng điệu truyền thông song hành: Tính chuyên gia chuyên nghiệp (Professional) khi cung cấp kiến thức kỹ thuật, mang tính phân tích, khúc chiết. Tính gần gũi, cộng đồng (Friendly & Inspiring) khi tương tác mạng xã hội, dùng từ thân mật như "anh em lông thủ", thể hiện sự đồng hành, thân thiện.',
        '{
            "dos": [
                "Luôn khẳng định và cam kết bán hàng chính hãng, cung cấp đầy đủ thông tin nguồn gốc sản phẩm.",
                "Thực hiện các video đánh giá sản phẩm một cách khách quan, dựa trên trải nghiệm thực tế và thông số kỹ thuật rõ ràng.",
                "Thể hiện sự tôn trọng tối đa đối với đạo đức kinh doanh và tuân thủ pháp luật trong mọi chiến dịch tiếp thị.",
                "Đồng bộ hóa trải nghiệm thiết kế và chất lượng phục vụ tại mọi điểm chạm nhượng quyền."
            ],
            "donts": [
                "Tuyệt đối không bán hoặc mập mờ thông tin về hàng nhái, hàng kém chất lượng làm ảnh hưởng lòng tin khách hàng.",
                "Không tâng bốc sản phẩm của nhãn hàng riêng VNB một cách phi thực tế; tránh hạ thấp uy tín của các hãng đối thủ.",
                "Tránh sử dụng ngôn từ mang tính kích động, phân biệt hoặc gây tranh cãi tiêu cực trong cộng đồng người chơi.",
                "Nghiêm cấm các chi nhánh nhượng quyền tự ý đưa sản phẩm ngoài danh mục hệ thống của công ty vào kinh doanh tại cửa hàng."
            ]
        }'::jsonb,
        '{
            "pillars": [
                "Chia sẻ Kiến thức & Kỹ thuật: Các nội dung chuyên sâu hướng dẫn kỹ thuật chơi cầu, bài tập thể lực bổ trợ, luật thi đấu và hướng dẫn chi tiết quy trình căng vợt, quấn cán đúng chuẩn.",
                "Đánh giá & Trải nghiệm Sản phẩm: Phân tích sâu các dòng vợt, giày và phụ kiện của các hãng lớn và thương hiệu riêng VNB.",
                "Gắn kết Cộng đồng: Chia sẻ khoảnh khắc thi đấu, tạo lập không gian thảo luận cho anh em lông thủ.",
                "Tin tức Doanh nghiệp & Khuyến mãi: Cập nhật chiến dịch ưu đãi, giới thiệu ứng dụng, sự kiện khai trương."
            ]
        }'::jsonb
    );

    -- 3. Insert Customer Persona
    INSERT INTO customer_personas (
        id, workspace_id, persona_name, summary, demographics, psychographics
    ) VALUES (
        v_persona_id,
        v_workspace_id,
        'Lông thủ phong trào và Học sinh, Sinh viên đam mê thể thao',
        'Người chơi cầu lông phong trào từ mới bắt đầu đến trung bình (dưới 6 tháng - trên 2 năm). Mục tiêu rèn luyện sức khỏe, giải tỏa căng thẳng và mở rộng quan hệ. Nhạy cảm về giá nhưng đòi hỏi cao về độ bền và tính năng hỗ trợ lực do thể lực và kỹ thuật chưa hoàn thiện.',
        '{
            "age": "15 đến 35 tuổi.",
            "gender": "Cả nam và nữ (phân khúc nữ giới đang tăng trưởng mạnh mẽ).",
            "income": "Trung bình thấp đến trung bình khá (học sinh, sinh viên, nhân viên văn phòng trẻ).",
            "location": "Các đô thị lớn và các tỉnh thành có phong trào cầu lông phát triển mạnh mẽ.",
            "marital_status": "Phần lớn là người trẻ độc thân hoặc mới lập gia đình."
        }'::jsonb,
        '{
            "hobbies_habits": [
                "Thường xuyên chơi cầu lông tại các sân phong trào từ 2 đến 4 buổi/tuần.",
                "Thói quen tìm kiếm thông tin, xem các bài đánh giá vợt và video hướng dẫn kỹ thuật trên YouTube, TikTok trước khi mua sắm."
            ],
            "pain_points": [
                "Lo sợ mua phải hàng giả, hàng nhái trôi nổi trên thị trường do thiếu kiến thức chuyên môn.",
                "Ngân sách cá nhân hạn chế, không đủ tài chính sở hữu dòng vợt cao cấp vài triệu đồng.",
                "Dễ gặp chấn thương hoặc mỏi cổ tay khi chọn sai loại vợt quá cứng hoặc quá nặng so với thể trạng."
            ],
            "secret_desires": [
                "Mong muốn nhanh chóng nâng cao trình độ chơi để tự tin giao lưu, kết nối.",
                "Muốn sở hữu trang thiết bị có thiết kế thời thượng, chuyên nghiệp để thể hiện phong cách cá nhân."
            ],
            "buying_barriers": [
                "Sự bối rối trước quá nhiều thông số kỹ thuật phức tạp (U, G, điểm cân bằng, độ dẻo).",
                "Chi phí căng cước và thay thế phụ kiện hao mòn định kỳ dễ trở thành gánh nặng tài chính lâu dài."
            ]
        }'::jsonb
    );

    -- 4. Insert Products & Services
    -- Product 1: Vợt cầu lông VNB
    INSERT INTO products_services (
        id, workspace_id, brand_id, name, description, usp, key_features, key_benefits, default_offer
    ) VALUES (
        v_product_1_id,
        v_workspace_id,
        v_brand_id,
        'Dòng vợt cầu lông thương hiệu riêng TOP VN SPORTS (V200i, V200, V88, TC88)',
        'Dòng sản phẩm vợt cầu lông được thiết kế và đặt hàng gia công riêng. Tối ưu hóa thiết kế và thông số kỹ thuật phục vụ chuyên biệt cho người chơi phong trào, học sinh, sinh viên tại Việt Nam.',
        'Vợt cầu lông chính hãng làm từ Carbon siêu bền có giá thành bình dân dưới 1 triệu đồng, được thiết kế với đũa dẻo trợ lực tối đa và có sức căng khung vượt trội lên đến 30 LBS (khoảng 13.6 kg), mang lại sự an tâm tuyệt đối về độ bền cho người mới chơi.',
        '[
            {"name": "VNB V200i Hồng", "specs": "5U (75 ± 2g), Nặng đầu 300mm, Dẻo, G5. Carbon High Modulus Graphite, sức căng 28-30 LBS."},
            {"name": "VNB V200 Xanh", "specs": "4U (84 ± 2g), Nặng đầu 300mm, Swing weight 83 kg/cm², Trung bình dẻo. Khung khí động học."},
            {"name": "VNB V200 Đỏ", "specs": "4U (84 ± 2g), Cân bằng 295mm, Swing weight 83 kg/cm², Trung bình dẻo. Gia cố chịu lực tốt."},
            {"name": "VNB V88 Cam/Xanh", "specs": "4U, Hơi nặng đầu, Cứng trung bình. Đũa vợt đàn hồi nhanh."}
        ]'::jsonb,
        '[
            "Trợ lực tối đa cho cổ tay: Đũa dẻo, trọng lượng nhẹ giúp dễ dàng đưa cầu sâu mà không tốn sức, phòng chấn thương.",
            "Độ bền bỉ đáng kinh ngạc trong tầm giá: Khung sợi carbon chịu sức căng cao, chống sập khung khi đánh hụt.",
            "Định hình và phát triển lối chơi: Nhiều phiên bản màu sắc và thông số hỗ trợ các lối đánh khác nhau (bỏ nhỏ, công thủ toàn diện, phản tạt, smash uy lực)."
        ]'::jsonb,
        'Tặng ngay 02 quấn cán vợt cao cấp cùng túi đựng vợt chuyên dụng. Hỗ trợ giao hàng COD toàn quốc, kiểm tra trước khi thanh toán, đổi mới 1-đổi-1 nếu lỗi nhà sản xuất.'
    );

    -- Product 2: Dịch vụ căng cước
    INSERT INTO products_services (
        id, workspace_id, brand_id, name, description, usp, key_features, key_benefits, default_offer
    ) VALUES (
        v_product_2_id,
        v_workspace_id,
        v_brand_id,
        'Dịch vụ đan vợt và bảo dưỡng tiêu chuẩn kỹ thuật cao tại ShopVNB',
        'Dịch vụ giá trị gia tăng thực hiện trực tiếp bởi kỹ thuật viên tại cửa hàng. Bao gồm đan cước mới theo số ký yêu cầu và tư vấn bảo dưỡng khung, thay gen vợt.',
        'Quy trình căng vợt chuẩn kỹ thuật 4 nút khuyến nghị bởi các hãng lớn như Yonex, được thực hiện bởi các kỹ thuật viên giàu kinh nghiệm trên hệ thống máy căng điện tử hiện đại, đảm bảo phân bổ lực căng đồng đều tuyệt đối và bảo vệ tối đa tuổi thọ khung vợt.',
        '[
            "Kỹ thuật đan 4 nút chuyên nghiệp (Two-Pieces): Chia dây 2 sợi, đan từ trung tâm ra hai bên, tối ưu cho cấu trúc 76 lỗ gen.",
            "Kiểm soát lực kẹp khung khoa học: Hệ thống máy căng 2-6 kẹp, duy trì khoảng hở để khung giãn nở tự nhiên, ngăn đùn sơn, sập mặt vợt.",
            "Đồng bộ hóa tốc độ kéo dây bằng máy điện tử: Lập trình sẵn 3 mức tốc độ kéo, đảm bảo hằng số lực đồng đều, loại bỏ sai số máy cơ."
        ]'::jsonb,
        '[
            "Bảo vệ tối đa tuổi thọ vợt: Loại bỏ điểm tập trung ứng suất đột ngột, triệt tiêu nguy cơ biến dạng nứt vỡ khung.",
            "Tối ưu hóa hiệu suất chơi cầu: Độ căng đồng đều tạo vùng điểm ngọt (sweet spot) rộng hơn, nảy ổn định.",
            "Độ bền dây cước vượt trội: Kiểm soát lực kẹp cước vừa vặn, không phá vỡ lõi dây, hạn chế đứt cước sớm."
        ]'::jsonb,
        'Dịch vụ chăm sóc định kỳ miễn phí: Hỗ trợ kiểm tra tình trạng gen vợt, thay thế gen hỏng hoàn toàn miễn phí. Chính sách lưu trữ thông số cá nhân: Lưu lịch sử số ký căng và loại dây cước ưa thích của từng khách hàng.'
    );

END $$;
