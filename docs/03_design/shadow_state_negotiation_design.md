# TÀI LIỆU THIẾT KẾ KỸ THUẬT: STATE SCHEMA TRANSFORMATION & TIME TRAVEL (v3.2)
**Chức vụ chịu trách nhiệm:** Chief Technology Officer (CTO)  
**Dành cho:** Đội ngũ Kỹ sư Phát triển (Core Developers)  
**Mục tiêu:** Nâng cấp cấu trúc LangGraph lên Agent OS v3.2, áp dụng mô hình "State Schema Transformation" (Chuyển đổi Cấu trúc State) tách biệt không gian đàm phán và sáng tạo, kết hợp tính năng Time Travel để quản lý phiên bản Bản nháp.

---

## 1. Triết Lý Kiến Trúc (Architecture Philosophy)

Hệ thống v3.2 giải quyết triệt để vấn đề phình to bộ nhớ (State Bloat) và rơi rớt ngữ cảnh (Context Loss) bằng triết lý **State Schema Transformation (Phân lập & Chuyển đổi Trạng thái)**:
1. **Phân lập (Isolation):** Tách đồ thị thành các Sub-graphs độc lập (`Negotiation_Graph` và `Creative_Graph`).
2. **Khử rác (Garbage Collection tại Biên giới):** Khi chuyển từ Đàm phán sang Sáng tạo, hệ thống chỉ trích xuất dữ liệu "cứng" (Brief), vứt bỏ toàn bộ lịch sử chat (`messages`) cồng kềnh.
3. **Chủ động hóa (Proactive Context):** Tác tử Đàm phán chủ động truy xuất Case Studies (RAG) và đề xuất số liệu, ép các "ý chỉ ngầm" của CMO thành dữ liệu tĩnh.
4. **Du hành thời gian (Time Travel):** Không tự build hệ thống versioning cồng kềnh, sử dụng nguyên bản Checkpointer của LangGraph (`thread_ts`) để tua ngược trạng thái (Rewind) thay vì lưu nhiều object Draft.

---

## 2. Sơ Đồ Luồng Hoạt Động (Data & Control Flow)

```mermaid
graph TD
    %% TẦNG UI
    subgraph UI_Layer ["Giao Diện Sếp (Chainlit Workspace)"]
        CEO((CMO / CEO))
        Channel_Biz["#phong-kinh-doanh"]
        Channel_Creative["#phong-sang-tao"]
        CEO <-->|Đàm phán & Tua thời gian| Channel_Biz
        CEO -.-|Quan sát Bản nháp| Channel_Creative
    end

    %% TẦNG LANGGRAPH
    subgraph LangGraph_OS ["Agent OS v3.2 (State Schema Transformation)"]
        
        %% Negotiation Sub-graph
        subgraph Negotiation_Graph ["Vùng Đệm Đàm Phán (NegotiationState)"]
            Triage[Triage Router]
            Analyst[Analyst: Tính KPI Cơ Sở]
            Barrier{Draft Approval Barrier <br/> interrupt_before}
            Negotiator[Negotiator Agent: Proactive ReAct]
            
            Triage --> Analyst
            Analyst --> Barrier
            Barrier <=>|CMO Chat / Gọi Tool| Negotiator
        end

        %% Trạm Biên Giới
        CommitNode[Node Commit: Chuyển Đổi State]
        
        %% Creative Sub-graph
        subgraph Creative_Graph ["Ban Sáng Tạo (CreativeState)"]
            Dir[Strategist / Director]
            Wri[Copywriter]
            Gua[Brand Guardian]
            Dir --> Wri
            Wri <-->|Auto Review| Gua
        end
    end

    %% LUỒNG CHUYỂN ĐỔI
    Barrier -->|Sếp bấm Duyệt Khởi Chạy| CommitNode
    CommitNode -->|Đúc JSON Brief & Xóa Lịch sử| Dir

    %% KẾT NỐI
    Channel_Biz <==> Negotiation_Graph
    Channel_Creative <==> Creative_Graph
```

---

## 3. Cấu Trúc Dữ Liệu Bộ Nhớ (State Structure)

Hệ thống sử dụng các Schema tách biệt. Cần cập nhật vào `graphs/state.py`:

```python
from typing import TypedDict, List
from langchain_core.messages import BaseMessage

class DraftPlan(TypedDict):
    test_budget: float
    target_cpa: float
    notes_for_creative: str

class NegotiationState(TypedDict):
    """State này chứa mảng messages đàm phán cồng kềnh"""
    messages: List[BaseMessage]
    draft_plan: DraftPlan
    campaign_id: str
    product_id: str

class BusinessBrief(TypedDict):
    """Cấu trúc dữ liệu sạch, ĐÃ LỌC BỎ RÁC TIN NHẮN"""
    campaign_id: str
    product_id: str
    final_budget: float
    final_cpa: float
    strategic_notes: str

class CreativeState(TypedDict):
    """State khởi tạo của phòng Sáng Tạo - Siêu nhẹ"""
    messages: List[BaseMessage] # Bắt đầu với mảng rỗng
    business_brief: BusinessBrief
```

---

## 4. Đặc Tả Tác Tử Đàm Phán Chủ Động (Proactive Negotiator)

Để chống "Rơi rớt ngữ cảnh" (Implicit Context Loss), Agent không được chờ hỏi mới đáp.
- **Tích hợp RAG (Case Studies):** Agent tự gọi Tool tìm kiếm các Case Study từ chiến dịch quá khứ.
- **Gợi ý ép kiểu:** Agent tự hỏi ngược lại Sếp. Ví dụ: *"Case study tháng trước CPA là 120k, sếp có muốn chốt mức 100k cho đợt này, kèm định hướng 'nhấn mạnh công năng sản phẩm' không?"*
- **Lưu trữ triệt để:** Khi CMO "Say Yes", Agent gọi `UpdateDraftPlanTool` để ghi đè số liệu `test_budget`, `target_cpa`, và đặc biệt là gom mọi chỉ đạo ngữ cảnh vào `notes_for_creative`.

---

## 5. Xử Lý "Quay Xe" Bằng Time Travel & UX Chainlit

Thay vì tạo mảng `List[DraftPlan]` cồng kềnh, áp dụng **LangGraph Time Travel (Thread Timestamp - `thread_ts`)**.
*Ghi chú: Ở giai đoạn MVP hiện tại, tạm thời bỏ qua vấn đề Data Schema Migration khi rollback.*

### A. Tầng Backend (LangGraph)
- Sử dụng Checkpointer (`AsyncPostgresSaver`).
- Mỗi node thực thi đều tự động lưu lại snapshot. Khi có yêu cầu lấy bản nháp cũ, gọi API lấy state bằng `thread_ts` trong quá khứ và LangGraph sẽ tự động fork ra nhánh (branch) mới.

### B. Tầng Frontend (Chainlit UI/UX - Cảm hứng từ "Google Vibe Code")
Để tránh việc người dùng bị lạc trong các dòng thời gian khi Rewind, UI/UX cần xử lý triệt để như cách các code editor thông minh quản lý version:
- **Menu Lịch sử:** Trên Draft Card hiện tại có dropdown "Lịch sử bản nháp".
- **Visual Feedback Rõ Ràng:** Khi Sếp tua về quá khứ:
  - Bắn event từ Backend sang Chainlit báo trạng thái "Đã Rewind".
  - UI làm mờ (dim), gạch ngang (strikethrough) hoặc co gọn các tin nhắn thuộc "dòng thời gian tương lai đã bị hủy bỏ".
  - Vẽ một **Đường phân cách (Divider)** nổi bật báo hiệu sự rẽ nhánh: *"Bắt đầu rẽ nhánh thời gian từ đây"*.
  - Vô hiệu hóa (disable) tất cả các action button cũ không thuộc nhánh hiện tại để chặn mọi click nhầm.
  - Mang lại cảm giác an toàn tuyệt đối khi điều hướng qua lại giữa các phiên bản.
