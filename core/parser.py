# core/parser.py
"""
Universal Document Parser & Semantic Chunker using Microsoft MarkItDown.
Provides high-fidelity Markdown extraction and 2-step context-preserving chunking.
"""
import os
import logging
from typing import List, Union
from markitdown import MarkItDown
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

logger = logging.getLogger("core_parser")

class UniversalParser:
    def __init__(self):
        # Tắt plugins để đảm bảo an toàn bảo mật, tránh thực thi mã độc hại
        self.md = MarkItDown(enable_plugins=False)

    def extract_markdown(self, safe_local_file_path: str) -> str:
        """Trích xuất Markdown an toàn từ file local. BẮT BUỘC CHẠY TRONG CELERY WORKER."""
        if not os.path.exists(safe_local_file_path):
            raise FileNotFoundError(f"File không tồn tại: {safe_local_file_path}")
        
        logger.info(f"[parser] Trích xuất Markdown từ: {safe_local_file_path}")
        try:
            # Sử dụng API thu hẹp convert_local theo nguyên tắc Least Privilege
            result = self.md.convert_local(safe_local_file_path)
            return result.text_content
        except Exception as e:
            logger.error(f"[parser] Lỗi khi parse file bằng MarkItDown: {e}")
            raise e

    def chunk_markdown(self, markdown_text: str) -> List[any]:
        """
        Chiến lược Chunking 2 Bước (2-Step Pipeline):
        Bước 1: Chặt theo Header để giữ ngữ cảnh cấu trúc tài liệu.
        Bước 2: Cắt nhỏ các chunk quá dài bằng Recursive Character Splitter.
        """
        if not markdown_text or not markdown_text.strip():
            return []

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
        
        # Import cấu hình mặc định (CTO v3)
        try:
            from config.settings import RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP
            chunk_size = RAG_CHUNK_SIZE
            chunk_overlap = RAG_CHUNK_OVERLAP
        except ImportError:
            chunk_size = 1000
            chunk_overlap = 200

        # Bước 2: Recursive Character Splitting (Safety Net)
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        final_splits = text_splitter.split_documents(md_header_splits)
        
        logger.info(f"[parser] Chunking hoàn tất: {len(markdown_text)} ký tự -> {len(final_splits)} chunks")
        return final_splits


# ============================================================
# BACKWARD COMPATIBILITY WRAPPERS
# Giúp các thành phần cũ (app.py, core/tasks.py) hoạt động ổn định
# ============================================================
def extract_text_from_file(file_path: str) -> str:
    """Wrapper tương thích ngược: Trích xuất nội dung sử dụng UniversalParser."""
    parser = UniversalParser()
    return parser.extract_markdown(file_path)

def semantic_chunk_text(
    text: str,
    chunk_size: int = None,
    chunk_overlap: int = None,
    separators: list = None,
) -> List[str]:
    """Wrapper tương thích ngược: Chia nhỏ văn bản theo cấu trúc Markdown."""
    if not text or not text.strip():
        return []
    
    parser = UniversalParser()
    # Nếu chunk_size hoặc chunk_overlap được truyền động, chúng ta tự cấu hình Recursive splitter
    # Ngược lại dùng hàm mặc định của UniversalParser
    if chunk_size is not None or chunk_overlap is not None:
        # Chạy thủ công pipeline 2 bước với kích thước tùy biến
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )
        md_header_splits = markdown_splitter.split_text(text)
        
        c_size = chunk_size if chunk_size is not None else 1000
        c_overlap = chunk_overlap if chunk_overlap is not None else 200
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=c_size, 
            chunk_overlap=c_overlap
        )
        final_splits = text_splitter.split_documents(md_header_splits)
    else:
        final_splits = parser.chunk_markdown(text)
    
    # Trích xuất chuỗi thô từ page_content của Langchain Document
    chunks = [doc.page_content.strip() for doc in final_splits if doc and doc.page_content.strip()]
    # Lọc bỏ chunks quá ngắn (< 10 ký tự) như thiết kế cũ
    chunks = [c for c in chunks if len(c) >= 10]
    return chunks
