graph TD
    %% 1. TẦNG DATA & TRIGGER
    subgraph Data_Layer ["Tầng Dữ Liệu & Nền Tảng (PocketBase & APIs)"]
        PB_Products[(Sản phẩm & Tỷ suất Lợi nhuận)]
        PB_Metrics[(KPI & Số liệu thực tế: Views, CPA...)]
        Trigger((Worker Daemon: Bật hệ thống 24/7))
    end

    %% 2. TẦNG MAIN ROUTER (CEO)
    subgraph CEO_Layer ["Tầng Quản Trị Trung Tâm (Main Router / Supervisor)"]
        State[/"Agency Global State"/]
        CEO_Node{CEO Router Node}
    end

    %% 3. TẦNG KINH DOANH (BUSINESS GRAPH)
    subgraph Business_Graph ["Phòng Phân Tích Kinh Doanh & Số Liệu (business_graph)"]
        RAG_Econ[(RAG: Chiến lược Kinh doanh & Phễu)]
        Analyst[BA Agent: Tính Target CPA & ROAS]
        Performance[Performance Agent: Đọc Số liệu & Đánh giá]

        Analyst -.Đọc tài liệu.-> RAG_Econ
    end

    %% 4. TẦNG SÁNG TẠO (CREATIVE GRAPH)
    subgraph Creative_Graph ["Phòng Sáng Tạo & Sản Xuất (creative_graph)"]
        RAG_Psych[(RAG: Tâm lý học & Insight)]
        RAG_Swipe[(RAG: Winning Patterns - Swipe File)]
        RAG_Anti[(RAG: Anti-Patterns - Lỗi từng gặp)]

        Strategist[Creative Director: Đẻ Angle dựa trên Target]
        Generator[Variant Generator: Viết Kịch bản]
        Guardian[Brand Guardian: Chấm điểm & Feedback]

        Strategist -.Tham khảo.-> RAG_Psych
        Strategist -.Tránh lỗi.-> RAG_Anti
        Generator -.Copy cấu trúc.-> RAG_Swipe
    end

    %% FLOW KẾT NỐI (DATA FLOW)
    Trigger --> State
    State --> CEO_Node

    %% CEO Chia việc
    CEO_Node -- "1. Kiểm tra Sức khỏe Hệ thống" --> Performance
    CEO_Node -- "2. Yêu cầu tạo Chiến dịch mới" --> Analyst
    CEO_Node -- "3. Yêu cầu sản xuất Content" --> Strategist

    %% Flow Phòng Kinh Doanh
    PB_Metrics --> Performance
    PB_Products --> Analyst
    Performance -- "Phân tích xong -> Gắn cờ (Optimize/Kill/Scale)" --> CEO_Node
    Analyst -- "Tính xong -> Trả Target KPI" --> CEO_Node

    %% Flow Phòng Sáng Tạo (Micro-Loop)
    Strategist --> Generator
    Generator --> Guardian

    %% Vòng lặp sửa bài
    Guardian -- "Điểm < 80 (Sửa bài)" --> Generator
    Guardian -- "Thất bại 3 lần -> Báo cáo Fail" --> CEO_Node
    Guardian -- "Điểm >= 80 -> Duyệt xuất bản" --> PocketBase_Out[(PocketBase: Lưu Nháp / Đăng Ads)]
    PocketBase_Out --> CEO_Node

    %% Kết thúc phiên
    CEO_Node -- "Tạm nghỉ / Chờ chu kỳ sau" --> END((Nghỉ chờ Data mới))

    %% Định dạng màu sắc để dễ nhìn
    classDef data fill:#f9f,stroke:#333,stroke-width:2px;
    classDef router fill:#f96,stroke:#333,stroke-width:4px,color:#fff,font-weight:bold;
    classDef agent fill:#bbf,stroke:#333,stroke-width:2px;
    classDef rag fill:#dfd,stroke:#333,stroke-width:2px,stroke-dasharray: 5 5;

    class PB_Products,PB_Metrics,PocketBase_Out data;
    class CEO_Node router;
    class Analyst,Performance,Strategist,Generator,Guardian agent;
    class RAG_Econ,RAG_Psych,RAG_Swipe,RAG_Anti rag;
