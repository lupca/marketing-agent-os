# PHÂN TÍCH TÁC ĐỘNG CỦA MÔ HÌNH AUTONOMOUS ĐẾN HỆ THỐNG RAG (RAG IMPACT ANALYSIS)

*Tài liệu này đánh giá mức độ ảnh hưởng của kiến trúc mới (Bandits + Closed-loop) lên hệ thống Retrieval-Augmented Generation (RAG) hiện có, đồng thời xác định các tính năng cần thêm hoặc sửa.*

---

## 1. Vai trò của RAG hiện tại (Trạng thái Cũ)

Qua phân tích mã nguồn (`core/rag.py` - RAG v2 Zero-JOIN), hệ thống RAG hiện tại KHÔNG dùng để lưu thông tin cấu hình sản phẩm hay Brand Voice (những dữ liệu này đã được lưu cứng trong DB và nạp trực tiếp vào `State` ban đầu). 

Vai trò thực sự của RAG hiện tại là **Kho lưu trữ tài liệu ngoại vi** và **Bộ lọc lỗi (Anti-patterns)**:
- **Xử lý tài liệu upload:** Nhận file PDF/Word từ API, dùng Celery băm vector (chunks) lưu vào bảng `rag_chunks` với các `access_tags` phân quyền.
- **Tiêm Anti-patterns:** Cung cấp hàm `inject_antipatterns_to_prompt` để LLM tự động query các chunk có tag `anti_patterns` hoặc `manager_feedback`. Mục đích là nhắc nhở AI không được lặp lại các kịch bản/lỗi sai mà Sếp đã chê trong quá khứ.

---

## 2. RAG trong Mô hình Autonomous (Trạng thái Mới)

Khi chuyển sang hệ thống tự trị không có con người duyệt, RAG tiếp tục phát huy sức mạnh cốt lõi của nó: **Trí nhớ dài hạn (Long-term Memory)** để mồi dữ liệu và lưu trữ bài học tự động.

Dưới đây là những thay đổi cụ thể:

### 2.1. Tính năng BỔ SUNG (New Features - Dùng cho Autonomous)

**A. Khởi tạo Trọng số ban đầu (RAG-Seeded Priors for Cold-Start)**
- **Vấn đề:** Thuật toán Bandit cần dữ liệu lịch sử để chạy, nếu thương hiệu mới tinh sẽ bị lỗi "Khởi động lạnh".
- **Tính năng mới:** Ở `Diagnostic Node`, hệ thống sẽ Query RAG để tìm các *Insight tương đồng* trong quá khứ (Ví dụ: Query các chunk có tag `insights` cùng chung `industry`). Kết quả trả về sẽ được dùng để mồi (seed) bộ `current_beliefs` (trọng số) ban đầu cho Bandit, giúp nó không phải test bừa bãi.

**B. Tự động Băm Vector các Bài học (Auto-Indexing Insights)**
- **Tính năng mới:** Node `insight_generator_node` ở cuối vòng lặp không chỉ in báo cáo ra Dashboard. Nó sẽ tự động gọi hàm băm vector để đẩy đoạn Insight đó vào `rag_chunks` với tag là `insights`.
- Tri thức tự sinh ra từ mẻ test A (ví dụ: "Headline ngắn hoạt động tốt hơn") sẽ trở thành vốn kiến thức trong RAG để mồi cho chiến dịch B sau này.

### 2.2. Tính năng SỬA ĐỔI (Modified Features)

**Tái cơ cấu "Manager Feedback" thành "Sandbox Feedback"**
- **Sửa đổi:** Trước đây, hàm `inject_antipatterns_to_prompt` query tag `manager_feedback` (Sếp chê). Giờ không có Sếp duyệt bài, hàm này sẽ được sửa lại để query tag `sandbox_feedback`.
- **Cơ chế:** Khi `guardian_sandbox_node` đánh trượt một nội dung vì vi phạm an toàn thương hiệu, lý do đánh trượt sẽ được băm vector vào RAG với tag `sandbox_feedback`. Copywriter ở vòng lặp sau sẽ tự động đọc được lỗi này để né.

### 2.3. Tính năng GIỮ NGUYÊN (Retained)

- **Tài liệu ngoại vi (External Knowledge):** Tính năng Upload tài liệu (PDF, báo cáo nghiên cứu thị trường) qua Celery vào `rag_chunks` bằng các API trong `rag_routes.py` vẫn giữ nguyên. Agent sẽ dùng RAG để đọc các tài liệu này nếu cần ngữ cảnh chuyên sâu ngoài cấu hình sản phẩm cơ bản có sẵn trong State.

### 2.4. Tính năng XÓA BỎ (Deprecations)

- Bỏ các Endpoint gọi RAG thẳng từ giao diện Chat (Vì Chat UI đã bị xóa). Giao tiếp với RAG giờ hoàn toàn là ngầm định (Backend-to-Backend) trong quá trình Graph chạy.

---

## 3. Lộ trình Triển khai Kỹ thuật

1. **Thêm Tags mới:** Đảm bảo hệ thống (qua `rag_routes.py` POST tags) khởi tạo sẵn các tag: `insights`, `sandbox_feedback`.
2. **Sửa `inject_antipatterns_to_prompt`:** Thay đổi logic query từ `manager_feedback` sang `sandbox_feedback` trong file `core/rag.py`.
3. **Tích hợp Cold-start:** Viết thêm hàm query RAG bằng `get_embedding` tại giai đoạn Init/Diagnostic để mồi (seed) dữ liệu cho Beliefs của Bandit.