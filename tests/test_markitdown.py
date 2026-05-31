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
        
        # Query seeded Workspace ID dynamically
        from core.models import Workspace
        ws = self.db.query(Workspace).filter_by(name="Team Alpha Workspace").first()
        if not ws:
            ws = self.db.query(Workspace).first()
        self.workspace_id = str(ws.id) if ws else "00000000-0000-0000-0000-000000000002"

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
        # We need to be careful here because UniversalParser might load weights.
        # But this test checks actual parsing logic. Let's keep it but it might be slow.
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Báo Cáo Doanh Thu"
        ws.append(["Sản Phẩm", "Số Lượng", "Doanh Thu"])
        ws.append(["G-Agent OS", 10, 50000000])
        ws.append(["AI Consultant", 5, 25000000])

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            wb.save(tmp.name)
            tmp_path = tmp.name
        wb.close()

        try:
            parser = UniversalParser()
            markdown_content = parser.extract_markdown(tmp_path)
            self.assertIsNotNone(markdown_content)
            self.assertTrue("|" in markdown_content)
            self.assertTrue("Sản Phẩm" in markdown_content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    @patch("app.cl.user_session")
    @patch("core.rag.ingest_document_task")
    @patch("core.document_service.upload_file")
    @patch("core.parser.MarkItDown") # Mock the heavy part
    def test_rag_deduplication_logic(self, mock_mid_cls, mock_upload, mock_celery, mock_session):
        """Kiểm thử cơ chế chặn tải lên trùng lặp SHA-256."""
        # Mock MarkItDown
        mock_mid = mock_mid_cls.return_value
        mock_res = MagicMock()
        mock_res.text_content = "Fake markdown content"
        mock_mid.convert_local.return_value = mock_res

        # Query seeded Product ID dynamically
        from core.models import ProductService
        prod = self.db.query(ProductService).filter_by(workspace_id=uuid.UUID(self.workspace_id)).first()
        if not prod:
            prod = self.db.query(ProductService).first()
        product_id = str(prod.id) if prod else "00000000-0000-0000-0000-000000000005"

        # Mock session Chainlit
        mock_session.get.side_effect = lambda key, default=None: {
            "workspace_id": self.workspace_id,
            "product_id": product_id
        }.get(key, default)

        # Định nghĩa nội dung file kiểm thử
        file_content = b"Day la tai lieu kiem thu cho co che chong trung lap SHA-256 cua Marketing Agent OS."
        file_name = f"test_md_excel_{uuid.uuid4().hex[:8]}.txt"

        # Khởi tạo đối tượng upload giả lập
        element = MagicMock()
        element.name = file_name
        element.content = file_content
        # Ensure it doesn't have a 'path' or it's a valid one. 
        # run_vectorization_pipeline checks hasattr(element, 'path')
        element.path = None 

        # Chạy Event Loop
        loop = asyncio.get_event_loop()

        # ---- LẦN TẢI LÊN 1 ----
        result_1 = loop.run_until_complete(run_vectorization_pipeline(element))
        self.assertTrue("Tài liệu đã được nhận và đang xử lý" in result_1)
        self.assertTrue(mock_upload.called)

        # Reset mock
        mock_upload.reset_mock()
        mock_celery.delay.reset_mock()

        # ---- LẦN TẢI LÊN 2 (Trùng lặp) ----
        result_2 = loop.run_until_complete(run_vectorization_pipeline(element))
        
        # Xác minh cơ chế chặn trùng lặp
        self.assertEqual(
            result_2,
            "Tài liệu này đã tồn tại trong Knowledge Base. Bỏ qua quá trình xử lý để tiết kiệm tài nguyên."
        )
        self.assertFalse(mock_upload.called)

if __name__ == "__main__":
    unittest.main()
