-- ============================================================
-- Migration 004: Add metadata column to RAG tables
-- Date: 2026-05-31
-- Description: Thêm cột metadata (JSONB) vào bảng rag_documents 
--   và rag_chunks để lưu trữ thông tin phân tích sâu từ SerpApi & LLM.
-- ============================================================

BEGIN;

-- Thêm cột metadata vào bảng rag_documents
ALTER TABLE rag_documents 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Thêm cột metadata vào bảng rag_chunks
ALTER TABLE rag_chunks 
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

COMMENT ON COLUMN rag_documents.metadata IS 'Metadata lưu thông tin phân tích chung (video_id, title, sentiment, hook_type, pain_points).';
COMMENT ON COLUMN rag_chunks.metadata IS 'Metadata phi chuẩn hóa từ bảng cha rag_documents phục vụ Zero-JOIN query.';

COMMIT;
