-- ============================================================
-- Migration 003: Thêm cột file_hash để chống trùng lặp tài liệu
-- Date: 2026-05-30
-- Description:
--   Thêm cột file_hash VARCHAR(64) vào bảng rag_documents
-- ============================================================

BEGIN;

ALTER TABLE rag_documents ADD COLUMN IF NOT EXISTS file_hash VARCHAR(64);

-- Thêm index cho workspace_id + file_hash (không unique để tránh xung đột soft delete)
CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_hash
    ON rag_documents (workspace_id, file_hash)
    WHERE is_deleted = FALSE;

COMMIT;
