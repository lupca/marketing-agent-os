# KẾ HOẠCH TÍCH HỢP MARKITDOWN: NÂNG CẤP HỆ THỐNG RAG ĐA ĐỊNH DẠNG
**Dành cho:** Đội ngũ Kỹ thuật (Developers)
**Phê duyệt bởi:** CTO

---

## 1. Mục Tiêu (Objective)
Nâng cấp module `core/parser.py` hiện tại bằng thư viện [Microsoft MarkItDown](https://github.com/microsoft/markitdown). Việc này nhằm chuyển đổi kiến trúc xử lý tài liệu từ việc trích xuất "văn bản thô" (plain text) sang "văn bản có cấu trúc" (Markdown).

**Lợi ích chiến lược:**
*   Hỗ trợ ngay lập tức các định dạng Office phức tạp: Excel (Bảng giá), PowerPoint (Báo cáo thị trường), Word (Chính sách).
*   Giữ nguyên cấu trúc ngữ nghĩa (Tables, Headers, Lists), giúp LLM và Vector Database (bge-m3) hiểu chính xác số liệu tài chính thay vì bị cắt xén lộn xộn.
*   Tăng tính Token-efficient cho LLM.

---

## 2. Quản Lý Dependencies & Tối Ưu Hệ Thống
**Tuyệt đối KHÔNG sử dụng `markitdown[all]`** để tránh phình to Docker image với các dependencies xử lý Audio/Video/Azure không cần thiết.

Bổ sung vào `requirements.txt` đúng các gói sau:
```text
markitdown[pdf,docx,pptx,xlsx]
```

**Ràng buộc Kiến trúc (System Constraint):**
Việc parse các file Excel/PDF lớn bằng MarkItDown cực kỳ tốn CPU/RAM. Bắt buộc: Hàm `convert_local()` **chỉ được phép thực thi bên trong Celery Worker** (background task), tuyệt đối không được gọi trực tiếp trên luồng chính của FastAPI (`app.py`) để tránh treo ứng dụng.

---

## 3. Thiết Kế Kiến Trúc & Vấn Đề Bảo Mật (Security)

Theo tài liệu gốc, `MarkItDown` thực thi I/O với quyền của tiến trình hiện tại. Để tránh SSRF hoặc Path Traversal, tuân thủ nguyên tắc **"Least Privilege"**:

1.  **Sanitize Input:** Tại giao diện `app.py`, chỉ cho phép upload các định dạng file được whitelist (pdf, docx, xlsx, pptx, txt, csv).
2.  **Lưu File Tạm:** File upload được lưu vào `/data/temp/` với tên file được tạo bằng UUID.
3.  **Sử Dụng API Thu Hẹp (Narrow API):** Bắt buộc sử dụng **`convert_local()`** thay vì hàm `convert()` chung chung.

**Mã Nguồn Đề Xuất (`core/parser.py`):**
```python
import os
import logging
from markitdown import MarkItDown
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class UniversalParser:
    def __init__(self):
        self.md = MarkItDown(enable_plugins=False)

    def extract_markdown(self, safe_local_file_path: str) -> str:
        """Trích xuất Markdown an toàn từ file local. BẮT BUỘC CHẠY TRONG CELERY."""
        if not os.path.exists(safe_local_file_path):
            raise FileNotFoundError(f"File không tồn tại: {safe_local_file_path}")
        try:
            result = self.md.convert_local(safe_local_file_path)
            return result.text_content
        except Exception as e:
            logger.error(f"Lỗi khi parse file bằng MarkItDown: {e}")
            raise e

    def chunk_markdown(self, markdown_text: str):
        """
        Chiến lược Chunking 2 Bước (2-Step Pipeline):
        Bước 1: Chặt theo Header để giữ ngữ cảnh cấu trúc.
        Bước 2: Cắt nhỏ các chunk quá dài để fit Context Limit.
        """
        # Bước 1: Header Splitting
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
        md_header_splits = markdown_splitter.split_text(markdown_text)
        
        # Bước 2: Recursive Character Splitting (Safety Net)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200
        )
        final_splits = text_splitter.split_documents(md_header_splits)
        return final_splits
```

---

## 4. Cơ Chế Chống Trùng Lặp Tài Liệu (Deduplication Logic)
Để ngăn chặn tình trạng "ô nhiễm vector space" (skewed search results) và tiết kiệm tài nguyên băm vector vô ích khi user upload file nhiều lần, hệ thống bắt buộc áp dụng cơ chế File Hashing.

### Lộ trình chỉnh sửa Database & Logic:
1.  **Cập nhật Schema:** Bổ sung cột `file_hash VARCHAR(64)` vào bảng `rag_documents`. (Cần tạo Migration script).
2.  **Quy trình Upload tại `app.py`:**
    *   Khi file stream về `/data/temp/`, tính mã **SHA-256** của toàn bộ file content.
    *   Query DB: `SELECT document_id FROM rag_documents WHERE workspace_id = ? AND file_hash = ?`.
    *   **Nếu trùng (Tồn tại):** 
        *   Xóa file tạm ở `/data/temp/`.
        *   KHÔNG upload lên MinIO, KHÔNG trigger Celery.
        *   Trả về thông báo UI: *"Tài liệu này đã tồn tại trong Knowledge Base. Bỏ qua quá trình xử lý để tiết kiệm tài nguyên."* (Có thể thiết kế thêm nút cập nhật Tags nếu cần).
    *   **Nếu mới (Không tồn tại):** 
        *   Upload lên MinIO.
        *   Tạo record mới với `file_hash` vừa sinh.
        *   Đẩy Task vào Celery như bình thường.

---

## 5. Lộ Trình Triển Khai (Trạng thái: HOÀN THÀNH 100%)

1.  **[HOÀN THÀNH] Task 1:** Cập nhật `requirements.txt` (`markitdown[pdf,docx,pptx,xlsx]`).
2.  **[HOÀN THÀNH] Task 2:** Cập nhật DB Schema thêm trường `file_hash`. Implement logic tính mã SHA-256 và chặn upload trùng lặp tại `app.py`.
3.  **[HOÀN THÀNH] Task 3:** Refactor `core/parser.py`, thay thế code extract cũ bằng Class `UniversalParser`. Implement chiến lược Chunking 2 bước.
4.  **[HOÀN THÀNH] Task 4:** Đảm bảo luồng xử lý `UniversalParser.extract_markdown()` chỉ được gọi bên trong task Celery (`core/tasks.py`).
5.  **[HOÀN THÀNH] Task 5:** Viết Unit Test kiểm tra: (a) RAG có chặn được file trùng lặp; (b) Nạp thử 1 file `.xlsx` và xác minh output Markdown có sinh ra `| Table | Format |`.

*Tất cả hạng mục đã được kiểm thử tự động đạt kết quả OK (100% Passed) vào ngày 2026-05-30.*