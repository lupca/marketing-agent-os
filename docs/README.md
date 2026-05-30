# 📚 HỆ THỐNG TÀI LIỆU DỰ ÁN: MARKETING AGENT OS v3.0
*Chịu trách nhiệm cấu trúc: Chief Technology Officer (CTO)*

Tài liệu dự án đã được sắp xếp lại theo một **Kiến trúc Phân cấp Tiêu chuẩn Doanh nghiệp (Enterprise-grade Documentation Taxonomy)**. Cấu trúc được chia thành 5 danh mục được đánh số thứ tự khoa học để sếp và đội ngũ phát triển dễ dàng tra cứu, truy vết:

---

## 🗺️ BẢN ĐỒ TÀI LIỆU (DOCUMENTATION INDEX)

### 📂 [01. Kế Hoạch Vĩ Mô & Phạm Vi (Project Planning)](file:///wsl.localhost/server/root/marketing-agent-os/docs/01_planning/)
Chứa các văn bản về mục tiêu, phạm vi bàn giao và các tiêu chí nghiệm thu vĩ mô của hệ thống.
*   📄 **[scope_statement.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/01_planning/scope_statement.md):** Bản đặc tả phạm vi dự án, rào cản phần cứng và tiêu chí nghiệm thu (Sign-off Criteria) của CEO.

---

### 📂 [02. Kiến Trúc Hệ Thống (System Architecture)](file:///wsl.localhost/server/root/marketing-agent-os/docs/02_architecture/)
Đặc tả thiết kế sơ đồ khối, phân quyền chuyên môn giữa các phòng ban AI, và cơ chế tích hợp giao diện.
*   📄 **[core_architecture.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/02_architecture/core_architecture.md):** 6 tinh túy kiến trúc của Agent OS v3.0 (Phân quyền Business/Creative, A/B Testing tự trị, RAG phân tầng).
*   📄 **[chainlit_integration.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/02_architecture/chainlit_integration.md):** Hướng dẫn tích hợp luồng websocket Chainlit và giao thức Human-in-the-loop.
*   📄 **[chainlit.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/02_architecture/chainlit.md):** Tài liệu cấu hình giao diện Chainlit.

---

### 📂 [03. Thiết Kế Chi Tiết & Giải Thuật (System Design & Features)](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/)
Chứa phân tích thiết kế chi tiết ở tầng kỹ thuật, thuật toán đo lường và các phân hệ chức năng chuyên sâu.
*   📄 **[system_design_analysis.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/system_design_analysis.md):** Phân tích thiết kế hệ thống N-Tier, giải thuật quản trị bộ nhớ tránh tràn Context Window, và cơ chế lưu checkpoint của LangGraph.
*   📄 **[cmo_bi_dashboard_design.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/cmo_bi_dashboard_design.md):** Đặc tả thiết kế phân hệ CMO BI Dashboard, công thức toán học tính Paid/Blended CAC, đèn báo LTV:CAC, và giải thuật phát hiện Creative Fatigue sớm.
*   📄 **[semantic_router_researcher_v2.1.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/semantic_router_researcher_v2.1.md):** Bản nâng cấp v2.1 tích hợp Bộ định tuyến Ngữ nghĩa CSDL (pgvector Cosine distance) và Tác tử Nghiên cứu chính sách chạy ngầm tự trị. *(Legacy — đã được nâng cấp lên v3.0)*
*   📄 **[intelligent_triage_design.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/intelligent_triage_design.md):** ✨ **(v3.0 — MỚI)** Thiết kế 4-Layer Intelligent Supervisor Hub: Context Aggregator, Dynamic Few-Shot, LLM CoT Router, State Injector. Bao gồm Pydantic schema, sơ đồ luồng, bảng so sánh v2.1 vs v3.0.
*   📄 **[creative_report_design.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/03_design/creative_report_design.md):** ✨ **(v3.0 — MỚI)** Thiết kế Tác tử Báo cáo Sáng tạo (Creative Reporter) và Tác tử Báo cáo Hiệu suất (Performance Reporter) nâng cấp, bao gồm các cấu trúc prompt LLM nâng cao, liên kết thực thể CSDL (MasterContent, PlatformVariant), và giải pháp đồng bộ hóa trạng thái qua LangGraph.

---

### 📂 [04. Tài Sản Sáng Tạo & Prompting (Reusable Assets & IP)](file:///wsl.localhost/server/root/marketing-agent-os/docs/04_reusable_assets/)
Lưu trữ những "tinh hoa" kế thừa về prompting sáng tạo, ma trận chấm điểm và logic rẽ nhánh nền tảng.
*   📄 **[reusable_assets.md](file:///wsl.localhost/server/root/marketing-agent-os/docs/04_reusable_assets/reusable_assets.md):** Đặc tả bảng dữ liệu quan hệ PostgreSQL và ma trận chấm điểm 100-Point tự trị của Brand Guardian Agent.

---

### 📂 [05. Tài Liệu Tham Khảo (Reference Materials)](file:///wsl.localhost/server/root/marketing-agent-os/docs/05_reference_materials/)
Chứa toàn bộ các tài liệu hướng dẫn marketing chính thức và kịch bản mẫu được sử dụng để vector hóa và nạp tri thức ngữ nghĩa vào CSDL pgvector:
*   📁 *Choose Your Objective, Platforms, Content Marketing Guidelines (PDFs)*
*   📁 *Nội dung văn bản trích xuất Content Marketing Transcript (TXT)*
*   📁 *Image, Text, Video Content và Bản kế hoạch (Plan)*
