# PHÂN TÍCH THIẾT KẾ HỆ THỐNG (SYSTEM DESIGN ANALYSIS) - AGENT OS v2.0
*Tài liệu nội bộ - Soạn thảo bởi Giám đốc Kỹ thuật (CTO)*

## 1. TỔNG QUAN HỆ THỐNG (SYSTEM OVERVIEW)
Agent OS v2.0 là một hệ thống Multi-Agent phân tán, định hướng sự kiện (event-driven) và được thiết kế theo chuẩn Enterprise. Hệ thống giải quyết bài toán tự động hóa Marketing thông qua việc tách bạch rõ ràng giữa Tầng Giao Diện Giao Tiếp (Chainlit), Tầng Xử Lý Ngữ Cảnh & Luồng (LangGraph), Tầng Dữ Liệu Tập Trung (PostgreSQL).

**Mục tiêu thiết kế (Design Goals):**
- **Khả năng quan sát (Observability):** Mọi quyết định của AI phải có trace (vết) rõ ràng, giải thích được.
- **Tính tự trị an toàn (Safe Autonomy):** Hệ thống tự chạy A/B testing nhưng luôn tuân thủ ngân sách cứng (hard-limits) được gài trong Database.
- **Scalability:** Dễ dàng thêm các phòng ban (Sub-graphs) mới mà không ảnh hưởng luồng hiện tại.

---

## 2. KIẾN TRÚC THÀNH PHẦN (COMPONENT ARCHITECTURE)

Hệ thống tuân thủ mô hình **N-Tier Architecture**, chia thành 4 lớp chính:

### 2.1. Tầng Trình Diễn (Presentation Layer) - `Chainlit`
- **Chức năng:** Đóng vai trò là "Workspace" giả lập các kênh giao tiếp nội bộ (Department Channels).
- **Cơ chế:** Khởi tạo WebSockets để kết nối realtime với backend. Sử dụng cơ chế `UserSession` của Chainlit để duy trì trạng thái của người dùng (CEO) và ánh xạ nó với `Thread_ID` của LangGraph.
- **Tính năng cốt lõi:**
  - Hỗ trợ luồng `interrupt_before` (Human-in-the-loop): Render giao diện chứa Action Buttons (Approve/Reject) khi LangGraph bị pause.
  - Streaming trực tiếp các messages nội bộ của Agent vào các kênh `#phong-kinh-doanh`, `#phong-sang-tao`.

### 2.2. Tầng Điều Phối (Orchestration Layer) - `LangGraph`
Đây là lõi xử lý logic (OS Kernel), áp dụng mô hình **Hierarchical State Graph**.

- **Global State (`AgencyState`):** Chứa các biến dùng chung toàn cục như `campaign_id`, `global_budget`, `current_cpa_target`.
- **Main Router (Supervisor):** LLM Node đóng vai trò CPU Scheduler. Nhận input từ giao diện, phân loại Intent (Ý định) và route tác vụ xuống Sub-graphs.
- **Sub-graphs (Tiến trình độc lập):**
  - `business_graph`: Khởi tạo state nội bộ (`BusinessState`). Chứa `Analyst Node` (dùng Tool gọi DB tính toán) và `Performance Node` (dùng Tool để CRUD trạng thái Kill/Scale).
  - `creative_graph`: Khởi tạo state nội bộ (`CreativeState`). Chứa `Strategist Node`, `Copywriter Node` (sinh text) và `Guardian Node` (Hàm evaluation logic python thuần + LLM chấm điểm).

### 2.3. Tầng Dữ Liệu & Kiến Thức (Data & Knowledge Layer) - `PostgreSQL`
Sử dụng duy nhất 1 cụm PostgreSQL để giải quyết 3 bài toán:
- **Relational Data:** Quản lý cấu trúc chặt chẽ của `users`, `products`, `marketing_campaigns`, `platform_variants`. Áp dụng ACID properties để đảm bảo tính nhất quán của ngân sách.
- **Document Data (JSONB):** Trường `metrics`, `kpi_targets` sử dụng định dạng JSONB để tối ưu cho việc Query và Indexing linh hoạt khi cấu trúc tracking thay đổi.
- **Vector Search (`pgvector`):** Tạo các bảng `rag_economics`, `rag_psychology`, `rag_anti_patterns`. Các cột `embedding` kiểu `vector(1536)` (tùy model nhúng) kết hợp index HNSW để truy xuất ngữ nghĩa (Semantic Search) tốc độ cao.

### 2.4. Tầng Thực Thi & Tích Hợp (Execution & Integration Layer)
- **Ollama Engine:** Host cục bộ model `Qwen2.5 14B/9B`. Cung cấp OpenAI-compatible API cho LangGraph/LangChain. Áp dụng Strict JSON mode / Tool Calling.

---

## 3. LUỒNG DỮ LIỆU & GIAO TIẾP (DATA & COMMUNICATION FLOW)

### 3.1. Luồng Tự Động Tối Ưu (Auto A/B Testing Flow)
Đây là quy trình khép kín, không cần Sếp can thiệp:
1. **Trigger:** Celery Cronjob kích hoạt mỗi giờ.
2. **Fetch:** Node `Performance` (trong `business_graph`) truy vấn PostgreSQL lấy data `metrics` của các `platform_variants` trạng thái `testing`.
3. **Evaluate:**
   - Nếu `CPA > Target` -> UPDATE `publish_status = 'killed'`. Gọi Golang Service tắt Ads. Ghi log lý do vào bảng `rag_anti_patterns`.
   - Nếu `CPA <= Target` -> UPDATE `publish_status = 'scaled'`. Gọi Golang Service tăng ngân sách.
4. **Report:** Node `Performance` format kết quả thành đoạn text ngắn, push message lên WebSocket của kênh `#phong-kinh-doanh` cho Sếp xem.

### 3.2. Luồng Sáng Tạo Chờ Duyệt (Human-in-the-loop Flow)
1. Sếp gõ lệnh trên UI: *"Làm content cho SP X"*.
2. **Main Router** nhận diện intent, kích hoạt `business_graph`.
3. `Analyst Node` truy vấn DB tính `Target CPA` -> Trả kết quả về Main Router.
4. **Main Router** kích hoạt `creative_graph`, truyền `Target CPA` vào State.
5. Vòng lặp Sáng tạo: `Strategist` -> `Copywriter` -> `Guardian`. (Các text trung gian được stream lên kênh `#phong-sang-tao`).
6. Khi `Guardian` đánh giá >= 80 điểm. LangGraph raise event `interrupt_before`.
7. Chainlit UI bắt event, hiển thị UI chờ.
8. Sếp bấm `[Duyệt]`. Chainlit resume graph.
9. LangGraph kết thúc luồng, lưu Variant vào DB và gọi Golang Service để publish.

---

## 4. CHIẾN LƯỢC QUẢN TRỊ BỘ NHỚ (MEMORY MANAGEMENT STRATEGY)
Để giải quyết bài toán giới hạn Context Window của LLM (14B parameter model):

- **Data Summarization:** Cấm Agent truy vấn trực tiếp bảng `metrics` raw. Python Backend sẽ viết sẵn các Custom Tools (vd: `get_weekly_campaign_summary()`). Tool này thực thi SQL aggregation (`AVG`, `SUM`, `GROUP BY`) và trả về chuỗi string cực ngắn (VD: "CPA 150k, ROI 2.5").
- **State Cleanup:** Trong `AgencyState`, chỉ giữ lại thông điệp của 5 steps gần nhất. Các message cũ sẽ bị lược bỏ trước khi invoke LLM.
- **RAG Top-K Limit:** Khi `Strategist` truy vấn `RAG_AntiPatterns`, Tool chỉ được cấu hình lấy lại `K=3` kết quả phù hợp nhất, giới hạn tổng tokens inject vào prompt < 1000 tokens.

---

## 5. BẢO MẬT & MỞ RỘNG (SECURITY & SCALABILITY)
- **Bảo mật Ngân Sách:** Cấu hình constraints trực tiếp ở tầng Database (PostgreSQL constraints) để đảm bảo không một Agent nào có thể lưu một chiến dịch vượt quá `global_budget`.
- **Stateless LLM Calls:** Agent Nodes không lưu trạng thái nội tại. Toàn bộ trạng thái nằm ở PostgreSQL (Thread Checkpointing của LangGraph). Do đó, có thể scale ngang (Horizontal scaling) các process chạy LangGraph worker độc lập.
