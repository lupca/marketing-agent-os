-- Seed data for TOPVNSPORT brand analysis
-- Assuming a default user and workspace will be created or exist, we use a fixed UUID for workspace

DO $$
DECLARE
    v_workspace_id UUID := '00000000-0000-0000-0000-000000000002';
    v_brand_id UUID := uuid_generate_v4();
    v_persona_id UUID := uuid_generate_v4();
    v_product_1_id UUID := uuid_generate_v4();
    v_product_2_id UUID := uuid_generate_v4();
    v_product_88play_id UUID := uuid_generate_v4();
BEGIN

    -- 1. Create a Workspace for this data
    INSERT INTO workspaces (id, name, settings)
    VALUES (v_workspace_id, 'TOPVNSPORT Workspace', '{}')
    ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

    -- 2. Insert Brand Identity
    INSERT INTO brand_identities (
        id, workspace_id, brand_name, core_messaging, visual_assets, voice_and_tone, dos_and_donts, content_pillars
    ) VALUES (
        v_brand_id,
        v_workspace_id,
        'TOPVNSPORT',
        '{
            "slogan": "Together we can (Cùng nhau chúng ta có thể).",
            "mission": "Cam kết mang đến những sản phẩm, dịch vụ chất lượng tốt nhất phục vụ cho người chơi thể thao để nâng cao sức khỏe của chính mình.",
            "vision": "Trở thành nhà phân phối và sản xuất thể thao lớn nhất Việt Nam.",
            "philosophy": "Lấy chất lượng và sự sáng tạo làm bạn đồng hành; xem khách hàng là trung tâm để không ngừng cải tiến sản phẩm và dịch vụ."
        }'::jsonb,
        '{
            "logo": "Chữ T và V cách điệu mạnh mẽ, gợi hình ảnh quả cầu lông đang chuyển động nhanh.",
            "colors": "Sự kết hợp giữa Xanh dương đậm (Navy Blue) và Cam rực rỡ (Orange).",
            "typography": "Sans-serif dày bản, mạnh mẽ, hơi nghiêng về phía bên phải để biểu thị cho tốc độ chuyển động.",
            "signage": "Bảng hiệu Alu cao cấp kết hợp chữ nổi Mica gắn LED pha chiếu sáng cường độ cao."
        }'::jsonb,
        'Duy trì một giọng điệu truyền thông song hành: Tính chuyên gia chuyên nghiệp (Professional) khi cung cấp kiến thức kỹ thuật và tính gần gũi, cộng đồng (Friendly & Inspiring) khi tương tác với "anh em lông thủ".',
        '{
            "dos": [
                "Luôn khẳng định và cam kết bán hàng chính hãng, cung cấp đầy đủ thông tin nguồn gốc sản phẩm.",
                "Thực hiện các video đánh giá sản phẩm một cách khách quan, dựa trên trải nghiệm thực tế.",
                "Thể hiện sự tôn trọng tối đa đối với đạo đức kinh doanh.",
                "Đồng bộ hóa trải nghiệm thiết kế tại mọi điểm chạm."
            ],
            "donts": [
                "Tuyệt đối không bán hàng nhái, hàng kém chất lượng.",
                "Không tâng bốc sản phẩm của nhãn hàng riêng TOPVNSPORT một cách phi thực tế.",
                "Tránh sử dụng ngôn từ mang tính kích động hoặc gây tranh cãi tiêu cực.",
                "Nghiêm cấm các chi nhánh tự ý đưa sản phẩm ngoài danh mục vào kinh doanh."
            ]
        }'::jsonb,
        '{
            "pillars": [
                "Chia sẻ Kiến thức & Kỹ thuật: Hướng dẫn kỹ thuật chơi cầu, bài tập thể lực và quy trình căng vợt chuẩn.",
                "Đánh giá & Trải nghiệm Sản phẩm: Phân tích sâu các dòng vợt TOPVNSPORT, Yonex, Lining, Victor.",
                "Gắn kết Cộng đồng: Chia sẻ khoảnh khắc thi đấu, tạo lập không gian thảo luận cho lông thủ.",
                "Tin tức Doanh nghiệp & Khuyến mãi: Cập nhật chiến dịch ưu đãi và sự kiện hệ thống."
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
        'Người chơi cầu lông phong trào từ mới bắt đầu đến trung bình. Nhạy cảm về giá nhưng đòi hỏi cao về độ bền và tính năng hỗ trợ lực.',
        '{
            "age": "15 đến 35 tuổi.",
            "gender": "Cả nam và nữ.",
            "income": "Trung bình thấp đến trung bình khá (học sinh, sinh viên, nhân viên văn phòng trẻ).",
            "location": "Các đô thị lớn và các tỉnh thành có phong trào phát triển mạnh mẽ."
        }'::jsonb,
        '{
            "hobbies_habits": [
                "Thường xuyên chơi cầu lông tại các sân phong trào từ 2 đến 4 buổi/tuần.",
                "Thói quen tìm kiếm thông tin, xem các bài đánh giá vợt trên YouTube, TikTok."
            ],
            "pain_points": [
                "Lo sợ mua phải hàng giả, hàng nhái.",
                "Ngân sách cá nhân hạn chế.",
                "Dễ gặp chấn thương khi chọn sai loại vợt."
            ],
            "secret_desires": [
                "Nâng cao trình độ nhanh để tự tin giao lưu.",
                "Sở hữu trang thiết bị có thiết kế thời thượng, chuyên nghiệp."
            ],
            "buying_barriers": [
                "Sự bối rối trước quá nhiều thông số kỹ thuật phức tạp.",
                "Chi phí căng cước và thay thế phụ kiện định kỳ."
            ]
        }'::jsonb
    );

    -- 4. Insert Products & Services
    -- Product 1: Vợt cầu lông TOPVNSPORT
    INSERT INTO products_services (
        id, workspace_id, brand_id, name, description, usp, key_features, key_benefits, default_offer
    ) VALUES (
        v_product_1_id,
        v_workspace_id,
        v_brand_id,
        'Dòng vợt cầu lông thương hiệu riêng TOPVNSPORT (V200i, V200, V88, TC88)',
        'Dòng sản phẩm vợt cầu lông được thiết kế tối ưu cho thể trạng người Việt, phục vụ chuyên biệt cho người chơi phong trào.',
        'Vợt cầu lông chính hãng Carbon siêu bền có giá thành bình dân dưới 1 triệu đồng, đũa dẻo trợ lực tối đa.',
        '[
            {"name": "TOPVNSPORT V200i Hồng", "specs": "5U (75 ± 2g), Nặng đầu 300mm, Dẻo, Carbon High Modulus Graphite."},
            {"name": "TOPVNSPORT V200 Xanh/Đỏ", "specs": "4U (84 ± 2g), Nặng đầu 300mm, Swing weight 83 kg/cm², Trung bình dẻo."},
            {"name": "TOPVNSPORT V88 Cam/Xanh", "specs": "4U, Hơi nặng đầu, Cứng trung bình. Đũa vợt đàn hồi nhanh."}
        ]'::jsonb,
        '[
            "Trợ lực tối đa cho cổ tay: Đũa dẻo, trọng lượng nhẹ giúp dễ dàng đưa cầu sâu.",
            "Độ bền bỉ đáng kinh ngạc: Khung sợi carbon chịu sức căng cao, chống sập khung.",
            "Định hình và phát triển lối chơi: Nhiều phiên bản màu sắc và thông số hỗ trợ các lối đánh khác nhau."
        ]'::jsonb,
        'Tặng ngay 02 quấn cán vợt cao cấp cùng túi đựng vợt chuyên dụng.'
    );

    -- Product 2: Dịch vụ căng cước
    INSERT INTO products_services (
        id, workspace_id, brand_id, name, description, usp, key_features, key_benefits, default_offer
    ) VALUES (
        v_product_2_id,
        v_workspace_id,
        v_brand_id,
        'Dịch vụ đan vợt và bảo dưỡng tiêu chuẩn kỹ thuật cao tại TOPVNSPORT',
        'Dịch vụ giá trị gia tăng thực hiện trực tiếp bởi kỹ thuật viên tại cửa hàng.',
        'Quy trình căng vợt chuẩn kỹ thuật 4 nút Yonex trên máy căng điện tử hiện đại, đảm bảo lực căng đồng đều tuyệt đối.',
        '[
            "Kỹ thuật đan 4 nút chuyên nghiệp: Tối ưu cho cấu trúc lỗ gen, bảo vệ khung.",
            "Đồng bộ hóa tốc độ kéo dây bằng máy điện tử: Đảm bảo hằng số lực đồng đều, loại bỏ sai số."
        ]'::jsonb,
        '[
            "Bảo vệ tối đa tuổi thọ vợt: Ngăn ngừa biến dạng nứt vỡ khung.",
            "Tối ưu hóa hiệu suất chơi cầu: Vùng điểm ngọt (sweet spot) rộng hơn.",
            "Độ bền dây cước vượt trội."
        ]'::jsonb,
        'Dịch vụ chăm sóc định kỳ miễn phí: Hỗ trợ kiểm tra tình trạng gen vợt, thay thế gen hỏng miễn phí.'
    );

    -- Product 3: Yonex Astrox 88 Play
    INSERT INTO products_services (
        id, workspace_id, brand_id, name, description, usp, key_features, key_benefits, default_offer
    ) VALUES (
        v_product_88play_id,
        v_workspace_id,
        v_brand_id,
        'Yonex Astrox 88D Play (3rd Gen 2024)',
        'Phiên bản entry-level của dòng 88D nổi tiếng, thiết kế mới nhất 2024.',
        'Công nghệ Rotational Generator System giúp chuyển đổi linh hoạt giữa tấn công và phòng thủ.',
        '[
            {"name": "Trọng lượng", "value": "4U (Avg. 83g)"},
            {"name": "Độ dẻo", "value": "Medium"},
            {"name": "Điểm cân bằng", "value": "Head Heavy"},
            {"name": "Sức căng", "value": "20-28 lbs"}
        ]'::jsonb,
        '[
            "Dễ chơi cho người mới: Phù hợp với người chơi phong trào muốn trải nghiệm công nghệ Yonex.",
            "Thương hiệu đẳng cấp: Sản phẩm chính hãng từ Yonex.",
            "Thiết kế hiện đại: Tông màu Black/Silver/Blue sang trọng."
        ]'::jsonb,
        'Bảo hành chính hãng 3 tháng, hỗ trợ căng cước tại chỗ.'
    );

END $$;
