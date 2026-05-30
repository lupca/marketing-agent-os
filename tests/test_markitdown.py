# tests/test_markitdown.py
import os
import sys
import uuid
import unittest
import tempfile
import openpyxl
import asyncio
from unittest.mock import MagicMock, patch

# Thêm thư mục gốc vào đường dẫn hệ thống để import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parser import UniversalParser, semantic_chunk_text
from db.connection import SessionLocal
from db.seed import seed_database
from core.models import RAGDocument
from app import run_vectorization_pipeline

class TestMarkitdownAndDeduplication(unittest.TestCase):

    def setUp(self):
        self.db = SessionLocal()
        # Đảm bảo database đã được seed dữ liệu cơ bản
        seed_database(self.db)
        self.workspace_id = "00000000-0000-0000-0000-000000000002"

        # Dọn dẹp bất kỳ tài liệu thử nghiệm cũ nào
        self.db.execute(
            RAGDocument.__table__.delete().where(
                RAGDocument.file_name.like("test_md_excel_%")
            )
        )
        self.db.commit()

    def tearDown(self):
        # Dọn dẹp tài liệu thử nghiệm sau khi chạy xong
        self.db.execute(
            RAGDocument.__table__.delete().where(
                RAGDocument.file_name.like("test_md_excel_%")
            )
        )
        self.db.commit()
        self.db.close()

    def test_excel_table_parsing(self):
        """Xác minh rằng UniversalParser có thể trích xuất cấu trúc bảng chuẩn Markdown từ file Excel (.xlsx)."""
        # 1. Tạo file Excel tạm thời bằng openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Báo Cáo Doanh Thu"

        # Ghi một bảng dữ liệu tiêu biểu
        ws.append(["Sản Phẩm", "Số Lượng", "Doanh Thu"])
        ws.append(["G-Agent OS", 10, 50000000])
        ws.append(["AI Consultant", 5, 25000000])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            wb.save(tmp.name)
            tmp_path = tmp.name

        wb.close()

        try:
            # 2. Sử dụng UniversalParser trích xuất Markdown
            parser = UniversalParser()
            markdown_content = parser.extract_markdown(tmp_path)

            print("\n[INFO] Output Markdown trích xuất được từ Excel:")
            print(markdown_content)

            # 3. Kiểm định định dạng bảng chuẩn Markdown (`|`) và tiêu đề
            self.assertIsNotNone(markdown_content)
            self.assertTrue("|" in markdown_content, "Không phát hiện ký tự phân tách bảng '|' trong Markdown trích xuất")
            self.assertTrue("Sản Phẩm" in markdown_content, "Không tìm thấy tiêu đề cột 'Sản Phẩm'")
            self.assertTrue("G-Agent OS" in markdown_content, "Không tìm thấy dữ liệu 'G-Agent OS'")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("app.cl.user_session")
    @patch("core.rag.ingest_document_task")  # Mock Celery delay để tránh chạy worker thật khi test
    @patch("app.upload_file")  # Mock upload file MinIO
    def test_rag_deduplication_logic(self, mock_upload, mock_celery, mock_session):
        """Kiểm thử cơ chế chặn tải lên trùng lặp SHA-256."""
        # Mock session Chainlit
        mock_session.get.side_effect = lambda key, default=None: {
            "workspace_id": self.workspace_id,
            "product_id": "00000000-0000-0000-0000-000000000005"
        }.get(key, default)

        # Định nghĩa nội dung file kiểm thử
        file_content = b"Day la tai lieu kiem thu cho co che chong trung lap SHA-256 cua Marketing Agent OS."
        file_name = f"test_md_excel_{uuid.uuid4().hex[:8]}.txt"

        # Khởi tạo đối tượng upload giả lập
        element = MagicMock()
        element.name = file_name
        element.content = file_content

        # Chạy Event Loop để thực thi async function `run_vectorization_pipeline`
        loop = asyncio.get_event_loop()

        # ---- LẦN TẢI LÊN 1: File mới tinh ----
        result_1 = loop.run_until_complete(run_vectorization_pipeline(element))
        print(f"\n[INFO] Kết quả tải lên lần 1: {result_1}")
        
        # Xác minh kết quả báo nhận tài liệu thành công
        self.assertTrue("Tài liệu đã được nhận và đang xử lý" in result_1)
        self.assertTrue(mock_upload.called, "Chưa upload file lên MinIO trong lần tải thứ 1")
        self.assertTrue(mock_celery.delay.called, "Chưa trigger Celery Task trong lần tải thứ 1")

        # Reset mock
        mock_upload.reset_mock()
        mock_celery.delay.reset_mock()

        # ---- LẦN TẢI LÊN 2: File trùng lặp hoàn toàn ----
        result_2 = loop.run_until_complete(run_vectorization_pipeline(element))
        print(f"[INFO] Kết quả tải lên lần 2 (Trùng lặp): {result_2}")

        # Xác minh cơ chế chặn trùng lặp kích hoạt chính xác
        self.assertEqual(
            result_2,
            "Tài liệu này đã tồn tại trong Knowledge Base. Bỏ qua quá trình xử lý để tiết kiệm tài nguyên."
        )
        self.assertFalse(mock_upload.called, "Lỗi: Vẫn upload MinIO khi file bị trùng lặp")
        self.assertFalse(mock_celery.delay.called, "Lỗi: Vẫn trigger Celery Task khi file bị trùng lặp")

if __name__ == "__main__":
    unittest.main()
