# HỆ THỐNG TRÍ NHỚ VÀ QUẢN TRỊ DỮ LIỆU DÀI HẠN (Data & Memory Architecture v3.0)

Tài liệu này đặc tả cơ chế quản lý dữ liệu dài hạn của Marketing Agent OS. Hệ thống đã loại bỏ hoàn toàn việc dựa dẫm vào Checkpointer của LangGraph (`checkpoint_blobs`) để lưu trữ lịch sử nhằm chống lại hiện tượng phình to State (State Bloat).

Thay vào đó, kiến trúc bộ nhớ được tách bạch thành 2 nửa rõ rệt: **Analytical Memory (OLAP)** và **Semantic Memory (RAG + HITL)**.

---

## 1. Trí nhớ Phân tích Số liệu (Analytical Memory / OLAP)

LLM không được sinh ra để cộng trừ nhân chia hay đọc Time-series data. Việc quản lý lịch sử chiến dịch sẽ được giao hoàn toàn cho Cơ sở dữ liệu quan hệ (PostgreSQL / ClickHouse).

### A. Bảng `campaign_analytics`
*   **Mục đích:** Lưu trữ mọi chỉ số báo cáo từ Ad Networks (Facebook, Google) kéo về hằng ngày.
*   **Sử dụng cho Cold-Start:** Khi một chiến dịch mới tinh ra mắt, thay vì dùng LLM hay RAG để "đoán" ngân sách, Backend Python sẽ chạy lệnh SQL `SELECT AVG(cpa), AVG(ctr) FROM campaign_analytics WHERE industry='...' AND objective='...'`. Kết quả cứng này được dùng làm Prior gốc cho thuật toán Bandit.

### B. Bảng `ad_mapper`
*   **Mục đích:** Khớp nối (Mapping) thế giới nội bộ và thế giới bên ngoài.
*   **Sử dụng:** Lưu trữ cặp khóa `Variant_ID` (Sinh ra bởi LangGraph) $\longleftrightarrow$ `Platform_Ad_ID` (ID bài đăng thực tế trên Facebook). Từ đó, khi hệ thống kéo Metrics từ API Facebook về, nó biết chính xác điểm số đó thuộc về đoạn văn án nào để cộng/trừ Reward.

---

## 2. Trí nhớ Ngữ nghĩa và Bảo vệ Khỏi Ảo giác (Semantic Memory / RAG)

RAG (Retrieval-Augmented Generation) là một công cụ xuất sắc nhưng cực kỳ nguy hiểm nếu bị "Tự đầu độc" (Data Poisoning) bởi những suy luận sai lệch của chính LLM.

Trong v3.0, RAG hoạt động dưới quy trình bảo vệ nghiêm ngặt:

### A. RAG cho Thông tin Ngoại vi (External Context)
*   **Hoạt động tự do:** Các tài liệu PDF, Brand Guideline, báo cáo thị trường do con người chủ động Upload sẽ được băm vector thẳng vào bảng `rag_chunks`. Copywriter và Strategist sẽ liên tục Query các chunk này để tiêm ngữ cảnh (Context Injection) nhằm viết bài cho đúng giọng văn.

### B. RAG cho Bài học Kinh nghiệm (Insights) - BẮT BUỘC HITL
*   Khi chạy xong một vòng lặp, `insight_generator_node` sẽ đúc kết ra một bài học (Ví dụ: "Gen Z thích video dưới 15 giây").
*   **Chốt chặn An toàn:** Lời đúc kết này TUYỆT ĐỐI KHÔNG ĐƯỢC băm ngay vào RAG. Nó bị nhốt vào bảng tạm có tên `ai_insights_pending`.
*   **Human-in-the-Loop (HITL):** CMO hoặc Quản lý truy cập Dashboard, đọc các dòng pending này. Chỉ khi họ bấm nút **[Duyệt]**, hệ thống mới đẩy nó sang `rag_chunks` với tag `insights`. Nhờ vậy, RAG luôn sạch và toàn chứa chân lý (Truths).

### C. RAG cho Vết sẹo Khởi nghiệp (Sandbox Feedback)
*   Ngược lại với Insights, các lỗi lầm do AI Guardian phát hiện (Ví dụ: "Vi phạm từ cấm", "Nhắc đến đối thủ") sẽ được tự động băm vector vào RAG với tag `sandbox_feedback`. 
*   Ở vòng lặp sau, Copywriter sẽ tự động đọc được các "Vết sẹo" này qua hàm `inject_antipatterns_to_prompt` để không bao giờ lặp lại lỗi cũ.

---

## Tổng kết Mô hình Bộ nhớ

*   **Tính toán & Quyết định (Math & Decisions):** Dùng Database SQL (Bảng `analytics`, `mapper`).
*   **Ngữ cảnh & Viết bài (Context & Copywriting):** Dùng Vector DB (RAG).
*   **Cập nhật Tri thức mới (Knowledge Update):** Phải qua vòng kiểm duyệt của Con người (HITL - Pending Insights).

Mô hình này đảm bảo AI chạy ngầm với tốc độ cao nhất (Stateless) nhưng lại sở hữu một kho tri thức tích lũy bền vững, an toàn và thông minh nhất.