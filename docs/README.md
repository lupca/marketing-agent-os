# Marketing Agent OS (v3.0 Enterprise Edition)

**Marketing Agent OS** là một Hệ điều hành Marketing tự trị (Autonomous Creative Intelligence Engine), được xây dựng chuyên biệt để giải quyết bài toán sản xuất và tối ưu hóa nội dung quảng cáo ở quy mô lớn (Enterprise-scale).

Dự án đã chính thức chuyển đổi từ mô hình "Chatbot tương tác" (Human-in-the-loop / Chainlit) sang **Mô hình Tự trị (Autonomous)** sử dụng Động cơ ra quyết định Toán học (Multi-Armed Bandits) và Kiến trúc Phân tán Không trạng thái (Stateless Event-Driven Architecture).

---

## 1. Tầm nhìn Kiến trúc (Core Vision)

Hệ thống hoạt động dựa trên 3 trụ cột kỹ thuật:

1.  **Creative Intelligence Engine (Không can thiệp Bidding):** Hệ thống không cố gắng tranh giành quyền phân bổ ngân sách với Meta/Google Ads. Thay vào đó, nó đóng vai trò là nhà máy sản xuất nguyên liệu: đẻ ra N biến thể nội dung cực kỳ chất lượng (Dynamic Creatives) và nhường quyền tiêu tiền cho thuật toán của Ad Network.
2.  **Stateless LangGraph Execution:** Đồ thị LangGraph chỉ đóng vai trò là "Execution Layer". Nó nhận lệnh, chạy một lèo để đẻ bài viết, sau đó tự hủy (Terminate) ngay lập tức để giải phóng RAM. Chấm dứt hoàn toàn tình trạng State Bloat (phình to bộ nhớ do ngâm Graph chờ số liệu).
3.  **Toán học hóa Quyết định (Multi-Armed Bandits):** Ứng dụng thuật toán Epsilon-Greedy / Thompson Sampling để quyết định sản lượng nội dung: Bao nhiêu % nội dung đi theo lối mòn an toàn (Exploit), bao nhiêu % dũng cảm thử nghiệm góc độ tâm lý mới (Explore).

---

## 2. Hệ sinh thái Kỹ thuật (Tech Stack)

*   **Backend & Orchestration:** FastAPI, Python, Celery/Airflow (Task Queue & Sync).
*   **Agentic Framework:** LangGraph v0.2+ (Stateless Mode), LangChain.
*   **Database (OLTP & OLAP):** PostgreSQL, pgvector (cho RAG).
*   **Decision Math:** `pybandits`, Numpy, Bayesian Statistics.
*   **LLM Providers:** OpenAI, Anthropic, Local Ollama.

---

## 3. Cấu trúc Tài liệu Kỹ thuật Mới nhất

Toàn bộ tài liệu quy hoạch kiến trúc mới nhất nằm trong thư mục **`docs/agentic ai/`**. Đây là Nguồn sự thật duy nhất (Single Source of Truth) cho đội ngũ phát triển:

*   [Bản thiết kế cốt lõi & Vòng lặp Học tập](agentic%20ai/AUTONOMOUS_REFACTOR_PLAN.md)
*   [Thiết kế Nghiệp vụ & Cân bằng Ngân sách Nội dung](agentic%20ai/CMO_CTO_ALIGNMENT.md)
*   [Phân tích Tác động Hệ thống & Lộ trình đập đi xây lại](agentic%20ai/SYSTEM_IMPACT_REPORT.md)
*   [Kiến trúc RAG an toàn & Chống ảo giác](agentic%20ai/RAG_IMPACT_ANALYSIS.md)
*   [Prompt tự động hóa dành cho AI Coder](agentic%20ai/AI_CODER_PROMPT.md)

---

## 4. Workflow Vận hành (Event-Driven)

1.  **Data Ingestion:** Backend (Cronjob) kéo số liệu thực tế từ nền tảng Ads về lưu vào OLAP Database.
2.  **Decision Making:** Backend chạy toán học Bandit để tính toán trọng số niềm tin (Priors) cho các góc độ sáng tạo dựa trên Campaign Objective (Mục tiêu chiến dịch).
3.  **Graph Trigger:** Backend gọi API đánh thức LangGraph, bơm Priors vào.
4.  **Stateless Execution:** Graph chạy qua các Node (Diagnostic $\rightarrow$ Scoring $\rightarrow$ Selector $\rightarrow$ Guardian $\rightarrow$ Publisher).
5.  **Termination:** Graph xuất file Dynamic Creatives, ghi Log, lưu Insight chờ duyệt (HITL) và tắt hoàn toàn. 
6.  **Human-in-the-Loop (HITL):** Quản lý vào Dashboard duyệt các AI Insights. Nếu pass, Insight mới được băm vector vào RAG để mồi kiến thức cho các chiến dịch sau.