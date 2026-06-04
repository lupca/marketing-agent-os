# 05_TESTING_ARCHITECTURE.md

Tài liệu này quy hoạch chi tiết kiến trúc kiểm thử (Testing Architecture) mới của **Marketing Agent OS (v3.0)**, tập trung vào tính cô lập môi trường tối đa và nguyên lý **Fail-fast** (thất bại ngay lập tức khi phát hiện lỗi cấu hình hạ tầng).

---

## 1. Nguyên Tắc Cốt Lõi (Core Principles)

Để đảm bảo an toàn tuyệt đối cho dữ liệu production và tính ổn định khi kiểm thử tự động (CI/CD), hệ thống áp dụng 3 nguyên tắc sau:

1. **Cô lập môi trường hoàn toàn (Environment Isolation):** Chạy test trên cơ sở dữ liệu riêng biệt (`marketing_agent_test_db`) được nạp qua cấu hình `.env.test`. Không dùng chung dữ liệu với môi trường Development hay Production.
2. **Giao dịch lồng nhau (Nested Transactions / Savepoints):** Mọi thao tác ghi vào Database trong lúc chạy test đều được bao bọc bởi một Transaction lớn và tự động **Rollback** khi kết thúc test. Database luôn sạch sẽ 100%.
3. **Chặn kết nối bên ngoài (Block Network Requests):** Tự động mock các API Cloud (Facebook Ads, Ollama, Embeddings, Reranker) và sử dụng thư viện `responses` để chặn toàn bộ outbound HTTP requests ra ngoài internet, tránh phát sinh chi phí hoặc ghi đè dữ liệu trên các API cloud thật.
4. **Không sử dụng Fallback ảo hóa (Fail-fast Infrastructure):** Loại bỏ hoàn toàn cơ chế tự động giả lập SQLite hay Local Storage nếu hạ tầng gặp lỗi. Nếu PostgreSQL hoặc MinIO S3 không chạy, hệ thống sẽ **báo lỗi ngay lập tức**.

---

## 2. Loại Bỏ Các Cơ Chế Giả Lập Ngầm (Removed Fallback Logic)

Trong phiên bản cũ, hệ thống chứa các cơ chế fallback tạm thời để hỗ trợ chạy thử không cần cấu hình. Trong phiên bản mới, các cơ chế này đã bị loại bỏ hoàn toàn:

### A. Loại bỏ Mock Database (`IS_MOCK_DATABASE` / `is_mock()`)
*   **Trước đây:** Nếu kết nối PostgreSQL thất bại, hệ thống tự động fallback sang SQLite in-memory.
*   **Lý do loại bỏ:** SQLite không hỗ trợ extension `pgvector` và các truy vấn vector search độ chính xác cao. Việc pass test trên SQLite nhưng crash trên PostgreSQL (do sai cú pháp hoặc thiếu index vector) tạo ra lỗi nguy hiểm.
*   **Hiện tại:** Hệ thống kết nối trực tiếp PostgreSQL và fail ngay lập tức nếu database không khả dụng.

### B. Xóa bỏ Local Storage Fallback (`IS_MOCK_STORAGE` / `is_mock_storage()`)
*   **Trước đây:** Nếu MinIO S3 bị lỗi kết nối, hệ thống tự động dùng `shutil.copy2` để copy file tạm vào thư mục local `data/storage`.
*   **Lý do loại bỏ:** Rủi ro "Mock Drift". Khi chạy thật trên cloud, hệ thống sử dụng boto3 và URL S3 thật. Nếu chỉ test trên local copy, ta không thể phát hiện các lỗi phân quyền bucket, sai credentials, hay sai endpoint URL của MinIO.
*   **Hiện tại:** Bắt buộc MinIO S3 phải hoạt động. Lệnh upload/download file sẽ crash ngay lập tức nếu kết nối đến MinIO bị ngắt.

---

## 3. Cấu Hình & Môi Trường Kiểm Thử (Configuration)

### A. File cấu hình `.env.test`
File `.env.test` được lưu tại thư mục gốc của dự án và tự động được load đầu tiên khi chạy `pytest` thông qua cấu hình trong `tests/conftest.py`.

```env
DATABASE_URL=postgresql+psycopg://postgres:secret_password@localhost:5433/marketing_agent_test_db
IS_TEST_ENV=true
```

> [!IMPORTANT]
> Driver được khuyến nghị là `postgresql+psycopg://` (psycopg v3) tương thích hoàn toàn với thư viện kết nối không trạng thái của LangGraph.

### B. Cơ chế Transactions cô lập trong `tests/conftest.py`
```python
@pytest.fixture(scope="function")
def db_session(db_engine):
    """Cung cấp session DB riêng biệt cho mỗi test case."""
    connection = db_engine.connect()
    transaction = connection.begin()
    
    TestingSessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    
    # Ghi đè hàm dependency get_db_base trong hệ thống
    def override_get_db_base():
        yield session
        
    with patch("core.dependencies.get_db_base", side_effect=override_get_db_base):
        yield session

    session.close()
    transaction.rollback() # Hoàn tác toàn bộ thay đổi dữ liệu sau khi kết thúc test
    connection.close()
```

---

## 4. Chạy Kiểm Thử (Running Tests)

### Yêu cầu hệ thống
Trước khi chạy test, đảm bảo các dịch vụ Docker đã được khởi động:
- **PostgreSQL** (chạy trên port `5433` cho môi trường test/dev local)
- **MinIO S3** (chạy trên port `9000`)

### Lệnh chạy test thủ công
Chạy toàn bộ test suite từ thư mục gốc của dự án:
```bash
# Chạy toàn bộ test
wsl pytest

# Chạy riêng nhóm test database
wsl pytest tests/test_database.py

# Xem output chi tiết và in log debug
wsl pytest -s -v
```

### Chạy test trong môi trường CI/CD (GitHub Actions / GitLab CI)
Sử dụng docker-compose chuyên dụng để chạy kiểm thử tự động, cô lập hoàn toàn hạ tầng:
```bash
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```
Lệnh này sẽ tự động dựng DB Postgres trắng, Redis, MinIO S3, chạy test suite và dọn dẹp sạch sẽ toàn bộ tài nguyên container sau khi hoàn thành.
