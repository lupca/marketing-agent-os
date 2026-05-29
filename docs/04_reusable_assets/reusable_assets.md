# TÀI SẢN KẾT THỪA TỪ TMCP (REUSABLE INTELLECTUAL PROPERTY)

Tài liệu này lưu trữ những "tinh hoa" về thuật toán, kỹ thuật Prompting và Cấu trúc Dữ liệu từ hệ thống TMCP cũ. Chúng ta CHỈ kế thừa **Logic** và **Tri thức**, KHÔNG kế thừa Code Python cũ để đảm bảo Agent OS v2.0 hoàn toàn sạch sẽ (Clean Architecture).

---

## 1. CẤU TRÚC DỮ LIỆU CỐT LÕI (Chuyển đổi lên PostgreSQL)

Đây là các Table/Schema cốt lõi đã được chứng minh hiệu quả trong việc tracking Marketing, cần được thiết kế lại trên PostgreSQL:

### Bảng `marketing_campaigns` (Chiến dịch vĩ mô)
- `id` (UUID)
- `name` (String): Tên chiến dịch.
- `status` (Enum): `active`, `paused`, `completed`.
- **`kpi_targets` (JSONB):** Rất quan trọng. Lưu trữ target do Analyst Agent tính ra (VD: `{"target_cpa": 150000, "target_roas": 3.0}`).
- `budget_limit` (Numeric): Ngân sách tối đa được sếp cấp để test.

### Bảng `platform_variants` (Kịch bản Vi mô / A/B Testing)
- `id` (UUID)
- `campaign_id` (FK)
- `platform` (String): `tiktok`, `facebook`, `email`.
- `adapted_copy` (Text): Nội dung kịch bản AI viết.
- `publish_status` (Enum): `testing`, `killed` (Bị Performance Agent tắt), `scaled` (Được vít ngân sách).
- **`metrics` (JSONB):** Lưu trữ kết quả chạy thực tế: `views`, `clicks`, `cpa`, `spend`.

---

## 2. KỸ THUẬT PROMPTING SÁNG TẠO (The "Brain" IP)

Chúng ta giữ lại các "Hệ tư tưởng" (System Prompts) đã được mài giũa của các Agent cũ để đưa vào `Creative_Graph` mới:

### A. Ma trận chấm điểm của Brand Guardian (100-Point Scoring Logic)
*Không copy code đồ thị cũ, chỉ copy thuật toán chấm điểm này vào Node Guardian mới:*
1. **Gatekeeper (Brand Safety):** Bắt buộc Pass. Không vi phạm từ khóa cấm, không lệch Brand Voice.
2. **Hook Power (35đ):** Đánh giá sức hút 3s đầu (Có yếu tố Tò mò / Gây sốc / Xoáy sâu nỗi đau không).
3. **Retention (25đ):** Cơ chế giữ chân người xem ở phần thân bài.
4. **Emotional Escalation (25đ):** Cao trào cảm xúc trước khi bán hàng.
5. **Call to Action (15đ):** Rõ ràng, tạo sự cấp bách (Urgency).
-> *Quy tắc Sinh tồn:* Phải >= 80 điểm mới được xuất bản bản nháp chờ sếp duyệt. Dưới 80đ -> Trả về `feedback_reason` bắt Copywriter viết lại.

### B. Logic Rẽ nhánh Nền tảng (Platform Variant Logic)
*Prompt cốt lõi của Copywriter khi nhận Master Angle:*
- Nếu `platform = tiktok`: Chuyển đổi thành kịch bản Video. Bắt buộc có cột "Hình ảnh/Visual" và cột "Âm thanh/Thoại". Nhịp độ nhanh.
- Nếu `platform = facebook`: Tập trung vào Community, dài hơn một chút, có Emoji và chia đoạn dễ đọc.
- Nếu `platform = email`: Tiêu đề (Subject line) ngắn, cá nhân hóa, Call-to-action dạng Hyperlink.

### C. Logic Suy luận Nỗi đau (Angle Strategist Logic)
- **Input:** Ideal Customer Profile (ICP) + Target CPA (Từ phòng Kinh Doanh).
- **Thuật toán:** Đọc RAG Tâm lý học -> Tìm ra 1 Nhu cầu thầm kín nhất của tệp khách hàng -> Suy ra Angle tiếp cận. Tránh đụng hàng với Angle đã lưu trong `Anti-Patterns RAG`.

