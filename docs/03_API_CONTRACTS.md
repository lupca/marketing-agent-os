# 03_API_CONTRACTS.md

Hệ thống sử dụng **FastAPI** chia thành nhiều module routers. Dưới đây là các giao thức API quan trọng cần nắm rõ.

## 1. Cockpit Observability WebSocket (`/api/ws/cockpit`)

- **Protocol**: WebSocket
- **Purpose**: Truyền tải sự kiện real-time từ LangGraph Nodes (Pipeline Tracker) tới Next.js frontend (The Autopilot Cockpit).
- **Message Schema (JSON Outbound)**:
  ```json
  {
      "event": "node_start",
      "run_id": "uuid-v4",
      "node": "creative_generation",
      "timestamp": "2026-06-04T15:00:00Z",
      "data": { ... }
  }
  ```
  *(Các loại event: `pipeline_start`, `node_start`, `node_complete`, `run_fail`, `quarantine`)*

## 2. Workspace Management (`/api/workspace/...`)

- Các API cơ bản chuẩn REST để quản lý Workspace (CRUD).
- **Lưu ý**: Client (Next.js) phải đính kèm Header `X-Workspace-Id` trong các request để xác thực scope.

## 3. RAG System (`/api/rag/...`)

Quản lý vector database và upload tài liệu.
- `POST /api/rag/upload`: Upload file (PDF, TXT, Excel). Backend dùng `markitdown` để parse, sau đó chunking và vector hóa bằng `bge-m3` để insert vào `rag_chunks` (pgvector).
- `POST /api/rag/test-retrieval`: 
  - **Body (JSON)**: `{"query": "...", "workspace_id": "...", "limit": 5}`
  - Trả về danh sách chunks (Zero-JOIN retrieval) có độ tương đồng Cosine cao nhất.

## 4. Diagnostics (`/api/diagnostics/readiness`)

- **Method**: GET
- Kiểm tra toàn bộ hệ thống (DB, LLM, Redis/MinIO) trước khi cho phép chạy Pipeline. Trả về JSON chứa trạng thái từng hệ thống con.
