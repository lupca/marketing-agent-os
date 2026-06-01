# BÁO CÁO TÁC ĐỘNG HỆ THỐNG VÀ CHIẾN LƯỢC CHUYỂN ĐỔI (IMPACT & MIGRATION)

*Tài liệu này đánh giá tác động của việc chuyển đổi sang mô hình Autonomous Agentic AI đối với codebase hiện tại và xác định chiến lược đập đi xây lại (In-place Refactoring) một cách dứt khoát.*

---

## 1. Dọn dẹp Rác Kỹ thuật (Deprecation & Deletion List)

Để kiến trúc được tinh gọn (Clean Architecture) và phù hợp với mô hình hoạt động ngầm qua Dashboard, các thành phần sau sẽ bị **xóa bỏ hoàn toàn** khỏi codebase (không giữ lại để tránh rác code):

**1.1. Hệ sinh thái Chat UI (Chainlit)**
- **Xóa bỏ:** `app.py` (chạy chainlit), `chainlit.md`, `chainlit_schema.sql`, thư mục `.chainlit/`.
- **Thay thế bằng:** API backend thuần túy (FastAPI) để giao tiếp trực tiếp với thư mục `public/` (Dashboard frontend).

**1.2. Các Node Đàm phán và Hội thoại phiếm**
- **Xóa bỏ:** `graphs/business/negotiator.py` và `graphs/supervisor/chat.py`.
- **Lý do:** Mô hình Autonomous tự động đánh giá và tự quay xe sửa lỗi thông qua `Scoring` và `Action Selector`. Không còn con người trong vòng lặp nên việc "đàm phán" (negotiate) hoặc "tán gẫu" (chat) trở nên thừa thãi.

**1.3. Cơ chế Phân luồng Triage**
- **Xóa bỏ:** `graphs/supervisor/triage.py` và logic Triage trong `graphs/main_router.py`.
- **Lý do:** Việc đoán ý định (Intent) từ tin nhắn chat không còn cần thiết. Người dùng tạo Campaign trực tiếp qua Form trên Dashboard (chọn Objective, Budget). Graph sẽ khởi chạy thẳng vào luồng `Analyst -> Scoring`, giúp tiết kiệm token LLM và tăng độ chính xác.

---

## 2. Hạ tầng Kỹ thuật Cần Bổ sung (Infrastructure Additions)

Để vòng lặp Học tập (Closed-loop) thực sự hoạt động, hệ thống cần bổ sung các mảnh ghép hạ tầng để kết nối thế giới ảo (AI) và vật lý (Thực tế chạy Ads):

**2.1. Hệ thống Mapping & Tracking (`Ad_Mapper`)**
- Khi AI xuất bản nhiều biến thể (Variants), hệ thống phải mapping được `Variant_ID` nội bộ với `Platform_Ad_ID` của Facebook/Google.
- **Action:** Cấu trúc lại bảng `platform_variants` trong DB để lưu giữ chuỗi mapping này. Khi có số liệu trả về, hệ thống biết chính xác số liệu đó thuộc về đoạn kịch bản nào.

**2.2. Hệ thống Tự động lấy số liệu (Data Ingestion API)**
- Việc cập nhật Metrics không nên làm bằng tay. 
- **Action:** Xây dựng thư mục `core/integrations/` (VD: `facebook_api.py`, `google_ads_api.py`). Nút "Khởi động vòng lặp tiếp theo" trên Dashboard bản chất sẽ kích hoạt hàm Pull Data từ các API này, gộp với `Ad_Mapper`, và đẩy vào `learning_update_node`.

**2.3. Tách bạch Database cho Báo cáo (OLAP Database)**
- LangGraph lưu trạng thái (Beliefs, State) dưới dạng Blob nhị phân (`checkpoint_blobs`), rất khó để Dashboard truy vấn và vẽ biểu đồ.
- **Action:** Khi AI tính toán xong Insight và Belief Weights, ngoài việc lưu vào State, hệ thống phải chạy lệnh `INSERT INTO` vào các bảng quan hệ rõ ràng (Ví dụ: `campaign_analytics`, `ai_insights`). Cần viết thêm các file migration SQL cho việc này trong thư mục `db/migrations/`.

---

## 3. Chiến lược Thực thi: Direct Replacement (Đập đi xây mới)

Đồng thuận với chỉ đạo từ CEO/Trưởng dự án, chiến lược refactor sẽ đi theo hướng **Trực tiếp thay thế (In-place Refactoring)**, tận dụng Git Branching để bảo vệ an toàn:

- **Không Build Song song:** Sẽ không tạo ra các thư mục `graphs_v1`, `graphs_v2` gây phình to (bloat) dự án.
- **Thực thi dứt khoát:** Chuyển sang một nhánh mới trên Git (vd: `feature/autonomous-engine`), thẳng tay xóa các file trong Deprecation List, và sửa trực tiếp đè lên `main_router.py`, `creative.py` hiện tại.
- **Lộ trình:**
  1. **Phase 1 (Database & Clean up):** Xóa file rác, update DB Schema cho mục tiêu OLAP và Ad Mapping.
  2. **Phase 2 (Core Logic):** Cấy thuật toán Bandits (`pybandits`) vào, viết các Node mới (Scoring, Selector, Diagnostic, Insight).
  3. **Phase 3 (API & Workflow):** Đập bỏ Chainlit, dựng FastAPI để nhận trigger từ Dashboard và test Dry-run với số liệu Mock ảo.