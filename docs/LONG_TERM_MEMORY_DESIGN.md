# TÀI LIỆU THIẾT KẾ KỸ THUẬT: HỆ THỐNG TRÍ NHỚ DÀI HẠN VÀ QUẢN LÝ TÀI SẢN (LONG-TERM MEMORY & ASSET VAULT)

## 1. Mục Tiêu (Objectives)
Tài liệu này đặc tả thiết kế kiến trúc và giải pháp kỹ thuật để đáp ứng 5 yêu cầu từ Ban Giám đốc (CMO) về quản lý trí nhớ dài hạn và tài sản marketing của hệ thống Marketing Agent OS v2.0. Mục tiêu là biến hệ thống từ một chatbot xử lý trên RAM thành một **Hệ điều hành (OS) thực thụ** có "ký ức", tính truy vết và lưu trữ tài sản bền vững.

---

## 2. Phân Tích & Thiết Kế Chi Tiết

### 2.1. Quản lý Luồng chiến dịch theo Thread ID (Persistent State)
**Vấn đề:** Hiện tại LangGraph sử dụng `MemorySaver` lưu State hội thoại trên RAM. Khi restart hệ thống, toàn bộ ngữ cảnh và quá trình làm việc của Agent (như các bản nháp, ngân sách đang giữ) bị mất.

**Giải pháp Kỹ thuật:**
- **Thư viện:** Thay thế `MemorySaver` bằng **`PostgresSaver`** từ thư viện `langgraph-checkpoint-postgres`.
- **Cấu trúc lưu trữ:** PostgresSaver tự động tạo các bảng `checkpoints`, `checkpoint_blobs`, `checkpoint_writes` trong PostgreSQL để lưu trữ state của LangGraph.
- **Quy trình:**
  1. Khi người dùng bắt đầu một yêu cầu tạo chiến dịch mới trên Chainlit UI, hệ thống khởi tạo một `Thread_ID` (tương ứng với `Campaign_ID`).
  2. Tại mỗi bước chuyển Node (Triage -> Analyst -> Copywriter -> Guardian), State được lưu tự động xuống PostgreSQL.
  3. Khi resume (phê duyệt hoặc tiếp tục ở một phiên làm việc khác), hệ thống dùng `Thread_ID` load lại State và tiếp tục luồng một cách liền mạch.

### 2.2. Thư viện Tài sản Phê duyệt (Approved Asset Vault)
**Vấn đề:** Kịch bản sau khi được phê duyệt bị trôi trong lịch sử tin nhắn, rất khó tìm lại để bàn giao cho đội ngũ media (Quay phim/Chạy Ads).

**Giải pháp Kỹ thuật:**
- **Database:** Tận dụng bảng `master_contents` và `platform_variants` đã có sẵn trong `db/schema.sql`.
- **Quy trình:**
  1. Tại `Publisher Node` (Node chạy ngay sau bước Human-in-the-loop phê duyệt của CMO).
  2. Kịch bản cuối cùng trong State sẽ được trích xuất và insert/update vào bảng `master_contents` với `approval_status = 'approved'`.
  3. Xây dựng một tính năng trên Chainlit UI (Ví dụ: Menu `/vault` hoặc Sidebar) để truy vấn bảng `master_contents` và hiển thị trực quan các kịch bản sẵn sàng mang đi sản xuất.

### 2.3. "Thủ thư AI" - Biến Feedback thành Vector Memory (Semantic History Search)
**Vấn đề:** CMO muốn AI nhớ được các phản hồi (feedback), lời chê bai trong quá khứ và có khả năng tìm kiếm lại theo ngữ nghĩa để tránh lặp lại sai lầm.

**Giải pháp Kỹ thuật:**
- **Database:** Sử dụng bảng CSDL Vector `rag_knowledgebase`.
- **Quy trình lưu trữ (Write):**
  1. Mỗi khi CMO nhấn nút `[Yêu cầu sửa]` và cung cấp lý do (Feedback), nội dung này kèm text kịch bản cũ sẽ được nối thành một đoạn văn bản.
  2. Gọi tool sinh Vector Embedding (Sử dụng model `bge-m3` qua Ollama).
  3. Lưu vào `rag_knowledgebase` với `category = 'manager_feedback'` và gán đúng `workspace_id`.
- **Quy trình tìm kiếm (Read):**
  1. Researcher Agent (khi nhận intent `research`) sử dụng công cụ tìm kiếm nội bộ.
  2. Truy vấn Cosine Similarity trên bảng `rag_knowledgebase` để tìm kiếm và trả lời các câu hỏi dựa trên lịch sử làm việc của đội ngũ.

### 2.4. Nhật ký Ra quyết định (Decision Audit Log)
**Vấn đề:** Thiếu khả năng truy vết các quyết định kinh doanh trên hệ thống để đo lường, rút kinh nghiệm và quy trách nhiệm.

**Giải pháp Kỹ thuật:**
- **Database:** Sử dụng bảng `agent_logs`.
- **Quy trình:**
  1. Viết một helper function `log_decision(workspace_id, agent_name, action, status, reason)`.
  2. Bất kỳ khi nào một Agent Node kết thúc tác vụ chính hoặc CMO nhấn nút Action (Duyệt / Yêu cầu sửa / Scale / Kill), gọi hàm log này.
  3. Dữ liệu này (Timestamp, Quyết định gì, Ai ra quyết định, Vì sao) sẽ phục vụ cho Node Performance sau này đọc và đánh giá tại sao chiến dịch bị lỗ.

### 2.5. Trích xuất Báo cáo Kế hoạch Marketing (Exporting to Markdown/PDF)
**Vấn đề:** CMO cần tài liệu tổng hợp để đi họp trình bày cho Ban giám đốc hoặc cổ đông, không thể dùng lịch sử chat.

**Giải pháp Kỹ thuật:**
- **Công nghệ:** Sử dụng Markdown generation từ State và Chainlit Elements (File attachment).
- **Quy trình:**
  1. Ở bước cuối của luồng `create_campaign` (sau khi trạng thái là Approved), hệ thống tổng hợp dữ liệu từ State: Insight Persona, CPA Anchor Target, Ngân sách Test, và các Kịch bản đã duyệt.
  2. Format tự động thành một file văn bản chuẩn (vd: `marketing_plan_CampaignABC.md`).
  3. Gửi lại user thông qua component `cl.File` của Chainlit, hiển thị dưới dạng nút "Tải xuống báo cáo" ngay trong khung chat để Sếp tải về máy tính với 1 click.

---

## 3. Lộ Trình Triển Khai (Implementation Roadmap)

Để hiện thực hóa bản thiết kế này, đội ngũ Dev cần thực hiện các bước sau:

1. **Cài đặt thư viện State:** `pip install langgraph-checkpoint-postgres`
2. **Cập nhật Database Connection:** Sửa file `db/connection.py` đảm bảo connection pool khỏe để phục vụ Checkpointer.
3. **Thay thế Checkpointer:** Trong `graphs/main_router.py`, cấu hình `PostgresSaver` cho builder của LangGraph thay thế cho `MemorySaver`.
4. **Viết tính năng Vault & Logs:** Cập nhật `publisher_node` để đẩy dữ liệu đã duyệt vào Asset Vault và gọi hàm Audit Log.
5. **Đóng gói RAG Feedback:** Bắt sự kiện trên Chainlit UI mỗi khi CMO reject kịch bản, vector hóa phản hồi này và lưu thẳng vào bảng RAG.
6. **Xây dựng Báo cáo:** Cấu hình Chainlit Element gửi file Markdown tổng hợp ở thông báo cuối cùng.

*Bản thiết kế này đảm bảo hệ thống vừa giữ được kỷ luật luồng chạy (SOP), vừa thông minh hơn từng ngày nhờ cơ chế Self-improving từ Vector Memory.*