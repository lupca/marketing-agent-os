# TÀI LIỆU QUẢN LÝ DỰ ÁN: 02_SCOPE STATEMENT (PHẠM VI DỰ ÁN)
*Dự án: Marketing Agent OS v2.0*
*Người lập: Project Manager (PM)*

**Project Goal:** 
Xây dựng một "Hệ Điều Hành Tác Tử" (Agent OS v2.0) tự trị chuyên biệt cho lĩnh vực Marketing nhằm tự động hóa quy trình phân tích số liệu, sáng tạo nội dung, và tối ưu hóa quảng cáo (A/B Testing). Mục tiêu cốt lõi là giải phóng CEO/CMO khỏi các tác vụ vi mô, chỉ tập trung duyệt chiến lược và ngân sách vĩ mô thông qua một giao diện quản trị đa kênh minh bạch.

**Scope Description:** 
Hệ thống Agent OS v2.0 sẽ bao gồm việc phát triển và tích hợp các tính năng sau:
- Xây dựng Giao diện Điều hành Trung tâm (UI Workspace) dựa trên Chainlit, phân chia thành các kênh giao tiếp nội bộ (`#phong-kinh-doanh`, `#phong-sang-tao`).
- Tích hợp cơ chế "Human-in-the-loop", cho phép tạm dừng luồng AI để chờ CEO phê duyệt (Approve/Reject) các đề xuất chiến lược và kịch bản.
- Phát triển Luồng điều phối Multi-Agent (LangGraph) gồm 2 phân hệ độc lập: Business Graph (Phân tích, KPI, Auto Scale/Kill) và Creative Graph (Lên Angle, Viết copy, Kiểm duyệt).
- Chuyển đổi và thiết kế lại toàn bộ Cơ sở dữ liệu từ PocketBase sang PostgreSQL, hỗ trợ lưu trữ dữ liệu quan hệ, JSONB tracking, và Vector RAG (`pgvector`).
- Xây dựng hệ thống "Ký ức 3 lớp" (Tri-Layer Memory): Summarization bằng Code, RAG Chuyên môn (Tâm lý, Kinh tế, Bài học xương máu).

**Deliverables:** 
Sản phẩm bàn giao của dự án sẽ bao gồm:
- **Source Code:** Mã nguồn hoàn chỉnh của Agent OS v2.0 (Python/LangGraph/Chainlit).
- **Database Schema:** Script khởi tạo CSDL PostgreSQL (DDL/DML) và pgvector.
- **Infra:** Cấu hình Docker Compose để khởi chạy toàn bộ môi trường local (PostgreSQL, LangGraph App, Chainlit UI).
- **UT (Unit Tests/Integration Tests):** Các kịch bản test đảm bảo Agent không bị ảo giác vượt quá ngân sách.
- **Tài liệu:** System Design, Setup Guide, và User Manual cho CEO.

**Challenges / Constraints:** 
Các rào cản và giới hạn cần lưu ý trong quá trình triển khai:
- **Hạn chế phần cứng:** Hệ thống (đặc biệt là LLM Qwen 14B) phải chạy mượt mà trên giới hạn phần cứng 1 GPU RTX 4060 Ti 16GB VRAM.
- **Giới hạn Context Window:** Rủi ro tràn bộ nhớ của LLM nếu đưa vào quá nhiều dữ liệu lịch sử thô (Raw Data).
- **Chất lượng đầu ra của LLM Local:** Đảm bảo Qwen 14B luôn xuất đúng định dạng Structured Output (JSON) để các LangGraph Node có thể parse được mà không bị crash.
- **Độ trễ (Latency):** Việc nhiều Agent hội thoại nội bộ có thể gây độ trễ trước khi kết quả cuối cùng được hiển thị lên UI cho CEO duyệt.

**Acceptance criteria:** 
Dự án sẽ được coi là hoàn thành (Sign-off) khi đáp ứng các tiêu chí sau:
- **Tính năng UI:** Chainlit hiển thị đúng các kênh, Sếp có thể click nút [Duyệt] và hệ thống LangGraph resume thành công.
- **Độ ổn định AI:** Hệ thống chạy liên tục 24h không bị lỗi "Infinite Loop" (vòng lặp vô hạn) giữa Thợ viết và Kiểm duyệt viên.
- **Chính xác Dữ liệu:** Analyst Agent tính toán Target CPA chính xác 100% dựa trên công thức Biên lợi nhuận lưu trong PostgreSQL, không bị ảo giác số học.
- **Tự trị vĩ mô:** Performance Agent có khả năng tự động cập nhật trạng thái "Killed" hoặc "Scaled" xuống Database cho các chiến dịch A/B testing vi phạm/đạt KPI.
- **Bảo mật Ngân sách:** Database Constraint ngăn chặn thành công bất kỳ query nào cố tình lưu ngân sách vượt mức sếp cấp.

**Assumptions:** 
Các giả định chính được coi là đúng trong suốt vòng đời dự án:
- Schema Database cũ từ PocketBase có thể migrate 100% sang PostgreSQL mà không làm mất mát dữ liệu quan hệ.
- Model Qwen2.5 14B có đủ năng lực suy luận (Reasoning) để thực thi logic phân loại Intent của Main Router và chấm điểm 100-point của Brand Guardian.
