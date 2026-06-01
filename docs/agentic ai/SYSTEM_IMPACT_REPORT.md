# BÁO CÁO TÁC ĐỘNG HỆ THỐNG VÀ CHIẾN LƯỢC CHUYỂN ĐỔI (BẢN ENTERPRISE)

*Tài liệu này đánh giá tác động của việc chuyển đổi sang mô hình Autonomous Agentic AI đối với codebase hiện tại, tuân thủ các nguyên tắc thiết kế phân tán (Stateless, Event-Driven) cấp độ Enterprise.*

---

## 1. Dọn dẹp Rác Kỹ thuật (Deprecation & Deletion List)

Để kiến trúc được tinh gọn (Clean Architecture) và phù hợp với mô hình hoạt động ngầm qua Dashboard, các thành phần sau sẽ bị **xóa bỏ hoàn toàn** khỏi codebase:

**1.1. Hệ sinh thái Chat UI (Chainlit)**
- **Xóa bỏ:** `app.py` (chạy chainlit), `chainlit.md`, `chainlit_schema.sql`, thư mục `.chainlit/`.
- **Thay thế bằng:** API backend (FastAPI) để giao tiếp trực tiếp với thư mục `public/` (Dashboard frontend).

**1.2. Các Node Đàm phán và Hội thoại phiếm**
- **Xóa bỏ:** `graphs/business/negotiator.py` và `graphs/supervisor/chat.py`.

**1.3. Cơ chế Phân luồng Triage**
- **Xóa bỏ:** `graphs/supervisor/triage.py` và logic Triage trong `graphs/main_router.py`.

---

## 2. Hạ tầng Kỹ thuật Cần Bổ sung (Enterprise Infrastructure)

Để vòng lặp Học tập (Closed-loop) hoạt động an toàn mà không làm sập Graph, hệ thống cần 3 mảnh ghép hạ tầng cốt lõi:

**2.1. Tách bạch Database cho Báo cáo (OLAP Database)**
- LangGraph lưu trạng thái (Beliefs, State) dưới dạng Blob nhị phân, gây tắc nghẽn bộ nhớ.
- **Action:** Backend Python chịu trách nhiệm lưu toàn bộ History và Metrics ra các bảng quan hệ (Ví dụ: `campaign_analytics`, `ai_insights_pending`). LangGraph sẽ không giữ dữ liệu này trong State.

**2.2. Hệ thống Đồng bộ Số liệu Bất đồng bộ (Airflow / Cronjob)**
- **Xóa bỏ:** Xóa hoàn toàn lệnh `interrupt_before=["waiting_for_metrics"]` trong LangGraph. Tuyệt đối không dùng Graph làm luồng chờ thời gian thực.
- **Action:** Dựng một Task Queue (Celery/Airflow/Cronjob) độc lập với LangGraph. Queue này sẽ kéo dữ liệu API từ Facebook/Google hàng ngày. Sau khi xử lý xong toán học Bandit, Queue này mới trigger LangGraph chạy một luồng sinh Content mới hoàn toàn (Stateless Execution).

**2.3. Hệ thống Mapping & Tracking (`Ad_Mapper`)**
- Khi AI xuất bản biến thể (Variants), phải mapping được `Variant_ID` nội bộ với `Platform_Ad_ID` của Facebook/Google.

---

## 3. Chiến lược Thực thi: Direct Replacement (Đập đi xây mới)

Chiến lược refactor sẽ đi theo hướng **Trực tiếp thay thế (In-place Refactoring)** trên nhánh Git:

- **Phase 1 (Database & API):** Xóa file rác, update DB Schema để hỗ trợ OLAP (`metrics_history`) và Ad Mapping. Xây dựng Data Ingestion API độc lập.
- **Phase 2 (Toán học & Backend):** Tích hợp thuật toán Bandits (`pybandits`) vào Backend Python, không để trong LangGraph. 
- **Phase 3 (Stateless Graph):** Viết lại LangGraph chỉ đóng vai trò nhận Priors từ Backend, chạy luồng sinh Content (Diagnostic -> Analyst -> Guardian -> Publisher) và Terminate ngay lập tức.