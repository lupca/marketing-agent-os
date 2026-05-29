# core/parser.py
import os
import logging
from pypdf import PdfReader

logger = logging.getLogger("core_parser")
logging.basicConfig(level=logging.INFO)

def extract_text_from_file(file_path: str) -> str:
    """Extract plain text from TXT or PDF files."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".txt":
        logger.info(f"Parsing raw text file: {file_path}")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
            
    elif ext == ".pdf":
        logger.info(f"Parsing PDF file: {file_path}")
        text_content = []
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    # Inject page indicator for metadata tracking
                    text_content.append(f"[Trang {i+1}]\n{page_text}")
            return "\n".join(text_content)
        except Exception as e:
            logger.error(f"Error parsing PDF with pypdf: {e}")
            raise e
            
    else:
        raise ValueError(f"Unsupported file extension for parsing: '{ext}'")

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    Split text into chunks of chunk_size with overlap characters.
    Each chunk is returned as a dictionary: {"content": str, "char_range": (start, end)}
    """
    chunks = []
    if not text:
        return chunks
        
    text = text.strip()
    text_len = len(text)
    
    start = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunk_content = text[start:end].strip()
        
        # Only keep meaningful chunks
        if len(chunk_content) > 10:
            chunks.append({
                "content": chunk_content,
                "start_idx": start,
                "end_idx": end
            })
            
        # Prevent infinite loop if parameters are misconfigured
        if chunk_size <= overlap:
            break
            
        start += (chunk_size - overlap)
        
    logger.info(f"Splitted text of length {text_len} into {len(chunks)} chunks.")
    return chunks
