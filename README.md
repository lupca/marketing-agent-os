# Marketing Agent OS v2.0 - Hướng dẫn Vận hành & Phát triển (Developer Guide)

Chào mừng bạn đến với **Marketing Agent OS v2.0** — Hệ điều hành Multi-Agent tự trị điều phối quy trình sáng tạo và tối ưu chiến dịch quảng cáo. Hệ thống tích hợp **LangGraph**, **Chainlit**, **PostgreSQL (pgvector)** và **Ollama LLM** chạy thực tế 100% không giả lập.

Tài liệu này hướng dẫn chi tiết cách thiết lập, chạy thử nghiệm (tests) và vận hành giao diện Chainlit UI cho lập trình viên.

---

## 1. Kiến Trúc Luồng Vận Hành & Bản Nâng Cấp v2.1 (Department SOP Flow)

Hệ thống được nâng cấp lên **phiên bản v2.1** tích hợp **Semantic Router** bằng Vector và **Researcher Agent** chạy ngầm để tối ưu hóa việc phân loại ý định cửa ngõ và nghiên cứu chính sách quảng cáo tự trị:

```mermaid
sequenceDiagram
    autonumber
    actor Sếp as CEO / CMO (Chainlit UI)
    participant Supervisor as Triage Node (Semantic Router)
    participant Researcher as Ban Nghiên Cứu (Researcher Agent)
    participant Biz as Ban Kinh Doanh (Analyst / Performance)
    participant DB as PostgreSQL (pgvector)
    participant Creative as Ban Sáng Tạo (Strategist / Copywriter / Guardian)

    %% BƯỚC 1: TRIAGE
    Sếp->>Supervisor: Nhập tin nhắn / Yêu cầu
    Note over Supervisor: Tính tương đồng Cosine ngữ nghĩa qua vector bge-m3
    
    alt Yêu cầu tra cứu tri thức / Luật quảng cáo (Intent: research)
        Supervisor->>Researcher: Chuyển tiếp luồng đến Researcher Node
        Researcher->>DB: Gọi Tool chọc DB truy xuất chính sách (pgvector)
        Researcher-->>Sếp: Phản hồi báo cáo nghiên cứu chi tiết dưới định danh [Ban Nghiên Cứu]
        
    alt Tạo chiến dịch quảng cáo mới (Intent: create_campaign)
        Supervisor->>Biz: Kích hoạt Analyst Node (CPA Anchor)
        Biz->>DB: Truy vấn Giá bán & Giá vốn sản phẩm
        Note over Biz: Tính toán CPA Target (30% Biên lợi nhuận) & Ngân sách thử nghiệm
        
        Biz->>Creative: Kích hoạt Creative Graph (Truyền CPA Target & Budget)
        Note over Creative: Strategist giao việc sang Researcher Agent!
        Creative->>Researcher: Gọi run_research (yêu cầu báo cáo tri thức & bài học thất bại)
        Researcher-->>Creative: Trả về bản tóm tắt tri thức khách hàng & anti-patterns
        
        Note over Creative: Copywriter: Viết kịch bản ép trong khung CPA Target<br/>Guardian: Chấm điểm Matrix 100 điểm nghiêm ngặt
        
        alt Điểm số < 80/100
            Note over Creative: Brand Guardian từ chối!<br/>Tự động trả lại Copywriter kèm feedback sửa đổi.
        else Điểm số >= 80/100
            Creative-->>Sếp: Gửi kịch bản đạt chuẩn và dừng chờ duyệt (CMO Interrupt)
        end
        
        Sếp->>Supervisor: Bấm [Duyệt và Đăng 🚀]
        Supervisor->>DB: Lưu kịch bản với trạng thái 'scheduled' thành công!
    end
```

---

## 2. Yêu Cầu Cấu Hình Hệ Thống (Prerequisites)

*   **Hệ điều hành:** Linux hoặc Windows (khuyến nghị chạy trên **WSL2 Ubuntu**).
*   **Python:** Phiên bản `3.10` trở lên.
*   **Docker & Docker Compose** đã được cài đặt và kích hoạt.
*   **Ollama** đã cài đặt và đang chạy tại IP host (Ví dụ: `http://172.22.45.28:11434` hoặc `http://localhost:11434`).

---

## 3. Các Bước Cài Đặt Chi Tiết (Step-by-Step Setup)

### Bước 1: Khởi Động Các Dịch Vụ Docker
Hệ thống sử dụng PostgreSQL tích hợp tiện ích mở rộng `pgvector` và MinIO S3 để quản lý tài liệu RAG.

1. Di chuyển vào thư mục dự án và khởi chạy Docker Compose:
   ```bash
   docker-compose up -d
   ```
2. Kiểm tra trạng thái các container đang chạy:
   ```bash
   docker ps
   ```
   *Kỳ vọng:* Hai container `agent_postgres` (cổng `5432`) và `agent_minio` (cổng `9000-9001`) phải ở trạng thái **Up**.

### Bước 2: Tạo Cấu Trúc Bảng CSDL (Apply Schema)
Khởi tạo cấu trúc 20 bảng dữ liệu và kích hoạt extension `vector` trên PostgreSQL:
```bash
docker exec -i agent_postgres psql -U postgres -d marketing_agent_db < db/schema.sql
```

### Bước 3: Chuẩn Bị Mô Hình Trên Ollama
Đảm bảo máy chủ Ollama của bạn đã tải sẵn 3 mô hình cốt lõi sau:
```bash
# Mô hình ngôn ngữ chính (LLM) để suy luận và viết kịch bản
ollama pull qwen2.5:14b-instruct

# Mô hình Vector Embeddings để mã hóa văn bản nạp RAG
ollama pull bge-m3:latest

# Mô hình Reranker tối ưu kết quả tìm kiếm RAG
ollama pull qllama/bge-reranker-large:latest
```

### Bước 4: Cài Đặt Thư Viện Python
Cài đặt tất cả các thư viện cần thiết trong môi trường của bạn (bao gồm thư viện `markitdown` để chuyển đổi các định dạng tài liệu phức tạp sang Markdown cấu trúc):
```bash
pip install -r requirements.txt
pip install pgvector json_repair
pip install "markitdown[pdf,docx,pptx,xlsx]"
```

---

## 4. Chạy Thử Nghiệm Hệ Thống (Running Tests)

Để đảm bảo toàn bộ kết nối CSDL PostgreSQL, RAG và Ollama LLM hoạt động chính xác trước khi vận hành thực tế, hãy chạy bộ kiểm thử tự động:

### 1. Kiểm tra kết nối CSDL và Seeding dữ liệu:
```bash
export PYTHONPATH=.
python3 tests/test_database.py
```
*Kỳ vọng:* CSDL kết nối thành công, tự động nạp dữ liệu mẫu và in ra dòng chữ: `[INFO] Test Database Fallback Active: False` (Chạy trên PostgreSQL thật).

### 2. Kiểm tra luồng xử lý văn bản (Parser):
```bash
python3 tests/test_parser.py
```

### 3. Kiểm tra Luồng Multi-Agent tự trị (LangGraph + Ollama):
```bash
python3 tests/test_workflow.py
```
*Kỳ vọng:* 
*   Hệ thống chạy qua đầy đủ các phòng ban: Triage $\rightarrow$ Analyst $\rightarrow$ Strategist $\rightarrow$ Copywriter $\rightarrow$ Guardian.
*   Nếu copywriter viết chưa hay, Brand Guardian tự từ chối (<80đ) và kích hoạt vòng lặp tối ưu lại.
*   Dừng chờ duyệt thành công tại nút thắt CMO Approval.
*   Sau khi resume, ghi nhận lưu trữ kịch bản thành công vào PostgreSQL.

### 4. Kiểm tra trích xuất MarkItDown & Chống trùng lặp:
```bash
# Chạy trong container Docker hoặc môi trường máy chủ
python3 -m unittest tests/test_markitdown.py
```
*Kỳ vọng:*
*   Trích xuất bảng dữ liệu Excel (.xlsx) thành cấu trúc bảng Markdown có định dạng đẹp mắt.
*   Nhận diện trùng lặp mã băm SHA-256 chính xác khi tải lên cùng một file nội dung 2 lần, chặn thành công lần tải thứ 2.

---

## 5. Khởi Chạy Giao Diện Web Chainlit UI (Run Application)

Khi tất cả các bài thử nghiệm đã vượt qua thành công, khởi động giao diện điều hành chính thức dành cho CEO / CMO:

```bash
chainlit run app.py --port 8000
```

### Cách Sử Dụng Trên UI:
1.  Mở trình duyệt truy cập: `http://localhost:8000`.
2.  Hệ thống chào mừng và hiển thị 2 kênh bên sidebar: `#phong-kinh-doanh` và `#phong-sang-tao`.
3.  **Tạo Chiến Dịch Mới:** Nhập tin nhắn ví dụ: *"Lên camp mới cho sản phẩm G-Agent Tech"*. Quan sát tiến trình suy luận và phản hồi của các Agent xuất hiện theo thời gian thực.
4.  **Phê duyệt kịch bản (Human-in-the-loop):** Khi kịch bản đạt chất lượng, giao diện sẽ xuất hiện 2 nút bấm: `Duyệt và Đăng 🚀` hoặc `Yêu cầu sửa ✍️`.
    *   Nếu chọn *Duyệt và Đăng*, hệ thống tự động lưu vào CSDL PostgreSQL với trạng thái `scheduled`.
    *   Nếu chọn *Yêu cầu sửa*, bạn nhập phản hồi chi tiết để Copywriter tự động viết bản thảo mới tốt hơn.
5.  **Vector hóa tài liệu (Interactive RAG):** Kéo thả file PDF/TXT hướng dẫn sản phẩm vào khung chat. Tiến trình RAG tự động vector hóa và lưu trữ phân đoạn tri thức vào CSDL PostgreSQL. Ban Sáng Tạo sẽ tự học và áp dụng cho các bài viết tiếp theo!
