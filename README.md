# Marketing Agent OS v3.0 - AI Repository Map

> [!WARNING]
> Repo này đã được định dạng và cấu trúc dành riêng cho **AI Agent**. Nếu bạn là con người (Human), vui lòng nhờ AI đọc và giải thích.

Dự án này là hệ thống **Autonomous Creative Intelligence Engine**, xây dựng trên kiến trúc **FastAPI**, **Next.js** và **Stateless LangGraph**, dùng PostgreSQL (pgvector) cho bộ nhớ dài hạn.

## Bản đồ Tài Liệu (Directory Map)

Vui lòng tham chiếu các file sau trong thư mục `docs/` để tải Context làm việc:

- [01_SYSTEM_PROMPT.md](docs/01_SYSTEM_PROMPT.md): Các Hard Rules và giới hạn bắt buộc (ví dụ: cấm dùng Stateful memory).
- [02_GRAPH_STATE_SCHEMA.md](docs/02_GRAPH_STATE_SCHEMA.md): Định nghĩa `AgencyState` TypeDict và Data flow của các Node.
- [03_API_CONTRACTS.md](docs/03_API_CONTRACTS.md): Cấu trúc giao thức WebSocket và các Endpoints chính.
- [04_DATABASE_SCHEMA.md](docs/04_DATABASE_SCHEMA.md): Cấu trúc CSDL cốt lõi (pgvector, Campaigns, Analytics).

## Tài liệu Lịch sử & Thư viện thứ 3 (Historical & 3rd-Party Context)

Nếu bạn (AI) cần tìm hiểu sâu hơn về kiến trúc ban đầu, cách thức giao tiếp với API Facebook, Shopee, cấu trúc Celery Tasks, hay lý do vì sao một số công nghệ được chọn, vui lòng đọc các tài liệu gốc trong thư mục:
- `docs/legacy/`
  - `02_architecture/FACEBOOK_INTEGRATION_GUIDE.md`
  - `03_design/` (Các thiết kế chi tiết về RAG, Bi Dashboard, MarkItDown)

## Cấu hình Hạ tầng (Infrastructure Setup)

Hạ tầng cơ sở dữ liệu và lưu trữ đã được chuyển lên remote server (`192.168.0.200`) sử dụng Docker:
- **PostgreSQL (pgvector)**: Cổng `5432`
- **Redis**: Cổng `6379`
- **MinIO**: Cổng `9000` & `9001`

Các file cấu hình và dữ liệu trên server được lưu trữ tại thư mục `/home/tung/app-infra/`.

## Khởi động hệ thống (System Start)

1. **Backend (FastAPI)**:
   ```bash
   python app.py
   ```
2. **Celery Workers (Worker & Beat)**:
   Chạy script khởi động các workers song song dưới Ubuntu:
   ```bash
   ./start_workers.sh
   ```
3. **Frontend (Next.js)**:
   ```bash
   cd frontend
   npm run dev
   ```

*Lưu ý: Đảm bảo đã khai báo các biến môi trường chính xác trong tệp `.env` hướng tới IP của server `192.168.0.200` trước khi khởi chạy.*

