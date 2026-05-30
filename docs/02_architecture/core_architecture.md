# BẢN THIẾT KẾ KIẾN TRÚC: MARKETING AGENT OS v3.0

**Định hướng:** Chuyển đổi từ hệ thống tự động hóa cứng nhắc sang một **Hệ Điều Hành Tác Tử (Agent OS)** linh hoạt cấp doanh nghiệp.
**Triết lý cốt lõi:** Trợ lý chuyên môn (LangGraph) tự chủ thực thi ở tầng Vi mô (Micro). Sếp (CEO/CMO) giám sát qua Giao diện Đa Kênh (Chainlit) và quản trị ở tầng Vĩ mô (Macro - Chiến lược & Ngân sách).
**Changelog:** v2.0 → v3.0: Nâng cấp Triage Node thành **Intelligent Supervisor Hub (4-Layer)**. Thêm **Chat Agent** node. Tích hợp **Creative Reporter** agent và nâng cấp **Performance Reporter** để tổng hợp báo cáo dữ liệu lớn bằng LLM.

---

## 6 TINH TÚY KIẾN TRÚC (GÓC NHÌN CMO & CTO)

### 1. Nguyên lý "Human-in-the-Loop Vĩ Mô" (Sếp không làm thợ duyệt bài)
Sếp (CMO/CEO) không phải là người đi check lỗi chính tả hay duyệt từng kịch bản TikTok. Đó là việc của Brand Guardian Agent. Quản trị của con người nằm ở tầng cao nhất:
- **Duyệt Ngân sách & Định hướng:** Hệ thống chỉ "Tag" sếp để xin phép khi bắt đầu một Campaign mới (Xin cấp quỹ test A/B) hoặc khi cần thay đổi chiến lược lớn.
- **Quan sát Đa Kênh (Department Channels):** Giao diện Chainlit chia thành `#phong-kinh-doanh`, `#phong-sang-tao`. Sếp có thể vào "đọc lén" để biết AI đang vận hành đúng quỹ đạo không, nhưng **không can thiệp** vào tiểu tiết chuyên môn nếu số liệu vẫn đang tốt.

### 2. Nguyên lý "Phân quyền Chuyên môn" (Separation of Concerns)
Tách biệt thành các Sub-graphs và các Agent chuyên biệt để LLM không bị tẩu hỏa nhập ma:
- **Phòng Phân Tích (Business Graph):** Gồm Analyst Agent & Performance Agent. Tính Target CPA, theo dõi số liệu, và **tự động ra quyết định Kill/Scale** các chiến dịch dựa trên luật do Sếp đặt ra.
- **Phòng Sáng Tạo (Creative Graph):** Gồm Strategist, Copywriter, Guardian. Tự động nhận đề bài từ Phòng Phân Tích, tự viết, tự cãi nhau, tự sửa bài và tự xuất bản bản nháp.
- **Ban Nghiên Cứu (Researcher Agent - v2.1):** Chuyên gia độc quyền tra cứu tài liệu tri thức (policies, từ khóa cấm) và pgvector RAG. Các phòng ban khác (như Strategist) sẽ giao việc và gọi ngầm Researcher Agent để lấy báo cáo tri thức thô thay vì tự chọc database trực tiếp, đảm bảo tính kỷ luật SOP tuyệt đối.

### 3. Nguyên lý "Dữ liệu Quyết định Hành động" (Data-Driven KPI)
Không đẻ ý tưởng suông bằng cảm tính.
- Toàn bộ dữ liệu (Sản phẩm, Margin, Lịch sử Ads, Target KPI) lưu tại **PostgreSQL**.
- Mọi chiến dịch bắt đầu từ Phòng Kinh Doanh: Gọi Database tính ra `CPA Tối đa`. Phòng sáng tạo bị ép buộc bám vào con số này để làm mồi nhử truyền thông (Hook).

### 4. Nguyên lý "Ký ức Phân tầng & RAG Chuyên Môn" (Tri-Layer Memory)
LLM không đọc Raw Data để tránh tràn bộ nhớ:
- **Ký ức Ngắn hạn:** Code gom nhóm dữ liệu PostgreSQL thành báo cáo 7 ngày (VD: "CPA tuần này tăng 20%") để AI đưa ra action.
- **RAG Chuyên Môn (pgvector):** Sử dụng PostgreSQL để lưu `RAG_KinhTe` (cho Analyst), `RAG_TamLyHoc` (cho Strategist), và `RAG_AntiPatterns` (lưu tự động các kịch bản bị Performance Agent đánh trượt để rút kinh nghiệm).

### 5. Nguyên lý "Thử nghiệm Sinh tồn Tự Trị" (Autonomous A/B Testing) - *[Góc nhìn CMO]*
Marketing là trò chơi xác suất, không ai đoán trước được mẫu nào sẽ Win.
- Sếp chỉ cấp **"Ngân sách Test"** (Ví dụ: 2 triệu VNĐ cho chiến dịch X).
- Phòng Sáng tạo tự động đẻ ra tối thiểu 3 Variants (3 Angles khác nhau).
- Hệ thống tự động push lên chạy Ads. Sau 24-48h, **Performance Agent tự động đọc Data PostgreSQL**:
  - Tự động TẮT (Kill) các mẫu vượt quá CPA Target.
  - Tự động VÍT (Scale) ngân sách cho mẫu Win.
  - Sau đó mới xuất Báo cáo tổng kết gửi lên kênh `#phong-kinh-doanh` cho Sếp xem kết quả. (Sếp quản lý bằng kết quả, không quản lý quy trình test).

### 6. Nguyên lý "Minh bạch & Truy vết" (Observability & Auditability) - *[Góc nhìn CTO]*
Mọi quyết định tự động của AI phải giải thích được (Explainable AI).
- Nếu Performance Agent tự tắt một chiến dịch, nó phải để lại log: *"Tự động Kill Variant B vì [Trích dẫn ID dòng Data PostgreSQL: CPA đạt 200k, vượt ngưỡng 150k trong 2 ngày]"*.
- Sếp có thể trace (truy vết) lại mọi suy nghĩ của AI bất cứ lúc nào nếu thấy có dấu hiệu đốt tiền sai lệch.

---

## TECH STACK CHÍNH THỨC

1. **Giao diện (UI/UX):** `Chainlit` (Mô phỏng Workspace dạng Channels).
2. **Orchestration:** `LangGraph` (Quản lý State và Thread ID cho từng kênh).
3. **Database:** `PostgreSQL` (Lưu data quan hệ + JSONB + Vector RAG qua `pgvector`).
4. **Bộ não (LLM):** `Qwen2.5 14B` (Chạy local qua Ollama).
5. **Intelligent Routing:** `Intelligent Supervisor Hub` (4-Layer: Context Aggregator + Dynamic Few-Shot + LLM CoT Router + State Injector).

---

## SƠ ĐỒ KIẾN TRÚC (v3.0 — INTELLIGENT SUPERVISOR HUB)

```mermaid
graph TD
    %% TẦNG UI
    subgraph UI_Layer ["Giao Diện CEO (Chainlit Workspace)"]
        CEO(("CEO / Sếp"))
        Channel_Biz["#phong-kinh-doanh"]
        Channel_Creative["#phong-sang-tao"]
        CEO <-->|Duyệt Ngân Sách / Xem Report| Channel_Biz
        CEO -.-|Chỉ Đọc/Quan Sát| Channel_Creative
    end

    %% TẦNG LANGGRAPH
    subgraph LangGraph_OS ["Agent OS v3.0 (LangGraph)"]

        %% Intelligent Supervisor Hub
        subgraph ISH ["Intelligent Supervisor Hub (Triage v3.0)"]
            L1["L1: Context Aggregator\n10 messages + sop_stage"]
            L2["L2: Few-Shot Retrieval\npgvector top-3"]
            L3["L3: LLM Router\nQwen2.5 CoT + JSON"]
            L4["L4: State Injector\nPydantic validate"]
            L1 --> L2 --> L3 --> L4
        end

        %% Business Graph
        subgraph Business_Graph ["Ban Kinh Doanh"]
            Analyst["Analyst: Tính KPI"]
            Perf["Performance Reporter: Auto Scale/Kill & Premium Report"]
            Analyst <--> Perf
        end

        %% Creative Graph
        subgraph Creative_Graph ["Ban Sáng Tạo"]
            Dir["Strategist / Director"]
            Wri["Copywriter"]
            Gua["Brand Guardian"]
            Dir --> Wri
            Wri <-->|Auto Review| Gua
        end

        %% Researcher
        subgraph Researcher_Sub ["Ban Nghiên Cứu"]
            Res["Researcher: RAG QA"]
        end

        %% Creative Reporter (v3.0 NEW)
        subgraph Creative_Report_Sub ["Creative Reporter (v3.0)"]
            CreativeReport["Creative Reporter: Báo cáo sáng tạo DB"]
        end

        %% Chat Agent (v3.0 NEW)
        subgraph Chat_Sub ["Chat Agent (v3.0)"]
            Chat["Chat: Hội thoại thông thường"]
        end
    end

    %% TẦNG DATABASE
    subgraph DB_Layer ["Tầng Dữ liệu Tập trung (PostgreSQL)"]
        PG_Relational[("Data: Products, Ads Metrics, Budgets")]
        PG_Vector[("pgvector:\nRAG + Intent Few-Shot KB")]
    end

    %% KẾT NỐI
    Channel_Biz <===> Business_Graph
    Channel_Creative <===> Creative_Graph
    Channel_Creative <===> Creative_Report_Sub

    L4 -->|create_campaign| Business_Graph
    L4 -->|show_metrics| Business_Graph
    L4 -->|creative_report| Creative_Report_Sub
    L4 -->|research| Researcher_Sub
    L4 -->|chat| Chat_Sub

    ISH --> CEO

    %% Phối hợp ngang ngầm
    Dir -->|Giao việc RAG| Res

    Business_Graph <===> PG_Relational
    Creative_Graph <===> PG_Vector
    Researcher_Sub <===> PG_Vector
    Creative_Report_Sub <===> PG_Relational
    L2 -->|"Cosine Search\nFew-Shot"| PG_Vector
```

---

## GHI CHÚ THAY ĐỔI (v3.0)

### Intelligent Supervisor Hub thay thế Main Router
Triage Node được nâng cấp từ Vector-Only Router (v2.1) lên **4-Layer Intelligent Supervisor Hub**:
- **Layer 1:** Context Aggregator — gom 10 tin nhắn gần nhất + `sop_stage`
- **Layer 2:** Dynamic Few-Shot — pgvector tìm 3 mẫu câu gợi ý cho LLM
- **Layer 3:** LLM Router — Qwen2.5 chạy Chain-of-Thought → `RoutingDecision` JSON
- **Layer 4:** State Injector — validate Pydantic → cập nhật `AgencyState`

> Đọc thiết kế chi tiết tại: [intelligent_triage_design.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/intelligent_triage_design.md)

### Chat Agent (mới)
Node `chat_agent` xử lý intent `chat` thay vì để hệ thống im lặng (behavior cũ: `chat → END`).
