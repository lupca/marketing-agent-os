# PHÂN TÍCH TÁC ĐỘNG CỦA MÔ HÌNH AUTONOMOUS ĐẾN HỆ THỐNG RAG (BẢN ENTERPRISE)

*Tài liệu này đánh giá mức độ ảnh hưởng của kiến trúc mới lên hệ thống Retrieval-Augmented Generation (RAG) hiện có, tập trung vào việc ngăn chặn rủi ro "Ảo giác dữ liệu" (Data Poisoning).*

---

## 1. Vai trò của RAG hiện tại (Trạng thái Cũ)

Vai trò thực sự của RAG hiện tại là **Kho lưu trữ tài liệu ngoại vi** và **Bộ lọc lỗi (Anti-patterns)**:
- **Xử lý tài liệu upload:** Nhận file PDF/Word từ API, dùng Celery băm vector.
- **Tiêm Anti-patterns:** Dùng `inject_antipatterns_to_prompt` để AI không lặp lại lỗi cũ.

---

## 2. Quản trị Rủi ro RAG trong Mô hình Autonomous (Trạng thái Mới)

Để tránh hiện tượng **"Tự đầu độc tri thức" (Epistemic Collapse)** do LLM tự suy diễn sai về dữ liệu quá khứ, hệ thống RAG được thiết kế lại với sự thận trọng tối đa.

### 2.1. Tính năng BỔ SUNG (New Features - Có kiểm soát)

**Tự động Băm Vector các Bài học (Auto-Indexing Insights) - PHẢI CÓ HITL**
- **Vấn đề:** Không được cho phép LLM tự động băm vector các bài học (Insights) do nó tự suy diễn từ số liệu.
- **Giải pháp (Human-in-the-Loop):** Node sinh Insight (hoặc LLM task chạy ngầm) sẽ chỉ lưu kết quả vào bảng tạm `pending_insights` trên PostgreSQL.
- **Thực thi:** Trên Dashboard, Quản lý (CMO) sẽ đọc các Insight này. Chỉ khi Quản lý bấm nút **[Duyệt]**, Insight mới được băm vector và đẩy vào `rag_chunks`. Các Insight rác sẽ bị xóa bỏ.

### 2.2. Tính năng BỊ LOẠI BỎ (Ngăn chặn Rủi ro)

**RAG-Seeded Priors for Cold-Start (Đã bị loại bỏ)**
- **Lý do loại bỏ:** RAG tìm kiếm dựa trên độ tương đồng ngữ nghĩa (Semantic Similarity), không mang ý nghĩa thống kê (Statistical Significance). Dùng RAG để quyết định mồi trọng số ngân sách quảng cáo là sai lầm về Data Science.
- **Giải pháp thay thế:** Bài toán Cold-Start sẽ được giải quyết bằng **SQL Query** trên bảng `campaign_analytics`. Dữ liệu cứng (Average CTR, CPA) sẽ được dùng để mồi cho thuật toán Bandit thay vì văn bản RAG.

### 2.3. Tính năng SỬA ĐỔI (Modified Features)

**Tái cơ cấu "Manager Feedback" thành "Sandbox Feedback"**
- Khi `guardian_sandbox_node` đánh trượt một nội dung vì vi phạm an toàn thương hiệu, lý do đánh trượt sẽ được băm vector vào RAG với tag `sandbox_feedback`. Copywriter ở vòng lặp sau sẽ tự động đọc được lỗi này để né.

### 2.4. Tính năng GIỮ NGUYÊN (Retained)

- **Tài liệu ngoại vi (External Knowledge):** Upload tài liệu PDF, báo cáo thị trường vào `rag_chunks` để các Agent lấy ngữ cảnh viết bài (Context Injection) nhằm chống ảo giác.

---

## Tổng Kết

RAG trong hệ thống Enterprise không được phép hoạt động không kiểm soát (Fully Autonomous). Nó là một kho lưu trữ cực kỳ nhạy cảm. Mọi thông tin (Insight) muốn lọt vào RAG để dạy AI cho các chiến dịch tương lai **bắt buộc phải đi qua chốt chặn duyệt thủ công (HITL) của con người**. Dữ liệu số liệu thì nhường lại hoàn toàn cho SQL Database quản lý.
