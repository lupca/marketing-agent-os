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
from core.document_service import process_and_store_document, DuplicateDocumentError

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

    @patch("core.document_service.store_document")
    @patch("core.document_service.upload_file")
    def test_rag_deduplication_logic(self, mock_upload, mock_store):
        """Kiểm thử cơ chế chặn tải lên trùng lặp SHA-256."""
        # Mock store_document to return a mock document object
        mock_doc = MagicMock()
        mock_doc.document_id = "11111111-1111-1111-1111-111111111111"
        mock_store.return_value = mock_doc

        # Định nghĩa nội dung file kiểm thử
        file_content = b"Day la tai lieu kiem thu cho co che chong trung lap SHA-256 cua Marketing Agent OS."
        file_name = f"test_md_excel_{uuid.uuid4().hex[:8]}.txt"

        # Mock the database query so that it returns None (no duplicate) on first call,
        # and returns mock_doc (duplicate found) on the second call.
        mock_query = MagicMock()
        mock_query.filter.return_value.first.side_effect = [None, mock_doc]
        
        with patch.object(self.db, "query", return_value=mock_query):
            # ---- LẦN TẢI LÊN 1 ----
            res1 = process_and_store_document(self.db, self.workspace_id, file_content, file_name)
            self.assertEqual(res1["status"], "processing")
            self.assertTrue(mock_upload.called)

            # Reset mock
            mock_upload.reset_mock()

            # ---- LẦN TẢI LÊN 2 (Trùng lặp) ----
            with self.assertRaises(DuplicateDocumentError) as context:
                process_and_store_document(self.db, self.workspace_id, file_content, file_name)
                
            self.assertTrue("Tài liệu này đã tồn tại" in str(context.exception))
            self.assertFalse(mock_upload.called)

if __name__ == "__main__":
    unittest.main()
