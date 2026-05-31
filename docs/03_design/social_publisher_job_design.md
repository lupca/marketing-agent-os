# BẢN THIẾT KẾ KIẾN TRÚC: HỆ THỐNG SOCIAL PUBLISHER (BACKGROUND JOB)

**Chịu trách nhiệm thiết kế:** Chief Technology Officer (CTO)
**Mục tiêu:** Xây dựng hệ thống đăng bài mạng xã hội bất đồng bộ thông qua Celery, giao tiếp với Upload-Post API, đảm bảo tính ổn định, không block UI và có khả năng phục hồi lỗi (Fault Tolerance).
**Đối tượng tài liệu:** Development Team. Không bao gồm timeline, chỉ tập trung vào Architecture, Logic, và Coding Standards.

---

## 1. TỔNG QUAN KIẾN TRÚC (HIGH-LEVEL ARCHITECTURE)

Việc gọi trực tiếp Upload-Post API (nhất là upload video, media lớn) bên trong LangGraph node (synchronous) là **Anti-pattern** vì:
- Dễ gây timeout (504 Gateway Timeout) cho ứng dụng Chainlit.
- Gặp Rate Limit (HTTP 429) sẽ làm chết toàn bộ thread LangGraph đang chạy.
- Khó xử lý retry khi network chập chờn.

**Giải pháp:** Chuyển dịch tác vụ đăng tải sang mô hình **Event-Driven Background Job** sử dụng hệ sinh thái có sẵn: **Celery + Redis**.

### Sơ đồ tương tác (Flow)
1. **LangGraph (Publisher Node):** Lưu dữ liệu vào PostgreSQL (`PlatformVariant` với `publish_status = 'scheduled'`) $\rightarrow$ Gọi `celery_app.send_task()` truyền vào ID của bản ghi $\rightarrow$ Trả kết quả ngay cho CEO trên Chainlit.
2. **Redis Broker:** Nhận Task Message và đưa vào hàng đợi `social_publisher`.
3. **Celery Worker:** Lấy Task $\rightarrow$ Construct Payload (Xử lý ảnh/video, mapping parameters) $\rightarrow$ Call Upload-Post API.
4. **Task Logic & DB Update:**
   - **Thành công (200 OK):** Update `publish_status = 'published'`, lưu `job_id` nếu là upload bất đồng bộ từ bên API 3rd-party.
   - **Lỗi Rate Limit (429) / Timeout (50x):** Celery tự động Retry với cơ chế Exponential Backoff.
   - **Lỗi Auth (Session Expired / 400 Bad Request):** Chuyển `publish_status = 'failed'`, ghi lỗi chi tiết vào Database để hiển thị lên Dashboard.

---

## 2. THIẾT KẾ LOGIC CHI TIẾT (MODULE LEVEL)

### 2.1. Nâng cấp Schema Database (Nếu cần)
Mặc định bảng `PlatformVariant` đã có trường `publish_status` (`draft`, `scheduled`, `published`, `killed`, `scaled`).
Cần bổ sung hoặc sử dụng trường `meta_data` (JSONB) để lưu vết:
- `api_job_id`: Dùng để tracking tiến trình nếu phía Upload-Post API trả về job ID cho tác vụ upload lớn.
- `error_message`: Lưu chuỗi lỗi chi tiết (vd: "Your Instagram session has expired") để hiển thị UI.

### 2.2. Celery Configuration (`core/celery_app.py`)
Định tuyến hàng đợi rõ ràng, **không** để chung với task băm vector RAG (ngốn CPU).

```python
# Thêm vào task_routes
task_routes={
    "core.tasks.ingest_document":      {"queue": "rag_ingestion"},
    "core.tasks.publish_to_social":    {"queue": "social_publisher"}, # NEW QUEUE
}
```
Khuyến nghị chạy Worker riêng cho queue này:
`celery -A core.celery_app worker -Q social_publisher -c 2 --loglevel=info`

### 2.3. Task Logic (`core/tasks.py`)
Tạo hàm `publish_to_social(variant_id: str)` với các tiêu chuẩn sau:
- Sử dụng cơ chế Auto-Retry của Celery cho các lỗi rớt mạng hoặc 429.
- Giới hạn Max Retries (vd: 5 lần) với khoảng thời gian Backoff.

```python
@celery_app.task(
    bind=True, 
    max_retries=5, 
    default_retry_delay=60, # 1 phút cho lần đầu
    autoretry_for=(ConnectionError, Timeout, HTTPError429, HTTPError50x)
)
def publish_to_social(self, variant_id: str):
    # 1. Fetch variant data from DB
    # 2. Build HTTP request to api.upload-post.com
    # 3. Handle specific Response Codes
    # 4. Update DB status and log decision
```

### 2.4. LangGraph Trigger (`graphs/publisher.py`)
Publisher node chỉ đơn thuần insert DB và gọi Task:
```python
# ... DB commit ...
celery_app.send_task(
    "core.tasks.publish_to_social", 
    args=[str(pv.id)], 
    queue="social_publisher"
)
```

---

## 3. TIÊU CHUẨN MÃ NGUỒN (CODING STANDARDS)

Để đảm bảo hệ thống dễ bảo trì và mở rộng, Dev Team cần tuân thủ nghiêm ngặt các quy tắc sau:

### 3.1. Separation of Concerns (SoC)
- **Không nhồi nhét Logic gọi API vào Celery Task:** Tạo một client module riêng (vd: `core/ai_clients/upload_post_client.py` hoặc tương tự) chứa các hàm tương tác HTTP thuần túy với Upload-Post API. Celery task chỉ đóng vai trò Orchestrator (lấy DB $\rightarrow$ gọi Client $\rightarrow$ ghi DB).

### 3.2. Error Handling & Retry Policies (Xử lý lỗi)
Tuân theo chuẩn phân loại lỗi của Upload-Post API:
- **Lỗi 401/403 (Session Expired, Unauthorized):** **KHÔNG RETRY**. Update thẳng `status = 'failed'` và cảnh báo qua `decision_logger.py` để Sếp biết tài khoản bị văng.
- **Lỗi 400 (Validation/Format):** **KHÔNG RETRY**. Do config sai kích thước ảnh, thiếu username... Ghi log lỗi chi tiết.
- **Lỗi 429 (Rate Limit) & 50x (Server Error):** **RETRY**. Sử dụng cơ chế backoff của Celery `self.retry(exc=e, countdown=backoff_time)`.

### 3.3. Observability (Tính minh bạch & Truy vết)
- Bất kỳ trạng thái `failed`, `published` nào được Celery cập nhật cũng **PHẢI** được ghi log thông qua hàm `log_decision()` (trong `core/decision_logger.py`) để lưu dấu vết minh bạch vào Dashboard.
- **Ví dụ gọi log:**
  `log_decision(..., agent_name="Social Publisher Worker", action="API Publish Failed", reason="Instagram session expired", ...)`

### 3.4. Idempotency (Tính Lũy Đẳng)
Task của Celery có thể bị chạy lại hai lần trong trường hợp worker rớt mạng giữa chừng.
- Trước khi thực hiện gọi Upload-Post API, task cần kiểm tra lại trong Database `publish_status` có đang là `published` hay không. Nếu đã đăng rồi $\rightarrow$ Skip để tránh spam bài lên Facebook/Tiktok.

### 3.5. Xử lý File & Memory
- Khi đăng video/ảnh từ URL hoặc file nhị phân, đảm bảo luồng HTTP Streaming hoặc giải phóng bộ nhớ (garbage collection) sau khi POST file xong để Celery Worker không bị Memory Leak.
- Tận dụng cờ `async_upload=true` mà API cung cấp nếu dung lượng file lớn.

---

**Nhiệm vụ cho Dev Team:** Dựa vào thiết kế này, bắt đầu Refactor Node Publisher và cấu hình Celery Queue. Tái cấu trúc chuẩn xác theo các layer đã định nghĩa.
