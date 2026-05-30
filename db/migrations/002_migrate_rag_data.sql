-- ============================================================
-- Migration 002: Backup & Migrate Data từ rag_knowledgebase
-- Date: 2026-05-30
-- Description: 
--   Bước 1: Backup bảng cũ
--   Bước 2: Import data vào rag_documents + rag_chunks
--   Bước 3: DROP bảng cũ
--
-- CHẠY SAU KHI migration 001 đã thành công.
-- ============================================================

BEGIN;

-- ============================================================
-- BƯỚC 1: BACKUP bảng cũ (giữ nguyên để rollback nếu cần)
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_knowledgebase_backup AS
SELECT * FROM rag_knowledgebase;

COMMENT ON TABLE rag_knowledgebase_backup IS 'Backup bảng rag_knowledgebase cũ trước khi migrate sang kiến trúc v2. Có thể DROP sau khi verify thành công.';

-- ============================================================
-- BƯỚC 2: Tạo rag_documents records (1 document / source_name)
-- Map: mỗi source_name unique trong 1 workspace → 1 rag_documents
-- ============================================================
INSERT INTO rag_documents (
    document_id,
    workspace_id,
    file_name,
    file_key,
    access_tags,
    upload_status,
    sync_status,
    chunk_count,
    is_deleted,
    created_at,
    updated_at
)
SELECT
    uuid_generate_v4()          AS document_id,
    COALESCE(workspace_id,
        (SELECT id FROM workspaces ORDER BY created_at LIMIT 1)
    )                           AS workspace_id,

    -- Lấy source_name làm file_name, fallback về category nếu null
    COALESCE(source_name, category || '_legacy_data')  AS file_name,

    -- Không có MinIO key cho data cũ (đã nhúng sẵn)
    NULL                        AS file_key,

    -- Map category cũ → access_tags JSON array
    CASE category
        WHEN 'economics'         THEN '["economics", "global"]'::jsonb
        WHEN 'psychology'        THEN '["psychology", "global"]'::jsonb
        WHEN 'anti_patterns'     THEN '["anti_patterns"]'::jsonb
        WHEN 'user_upload'       THEN '["marketing", "global"]'::jsonb
        WHEN 'policies'          THEN '["policies", "global"]'::jsonb
        WHEN 'manager_feedback'  THEN '["manager_feedback", "anti_patterns"]'::jsonb
        ELSE                          '["global"]'::jsonb
    END                         AS access_tags,

    'ready'                     AS upload_status,
    'synced'                    AS sync_status,
    COUNT(*)                    AS chunk_count,
    FALSE                       AS is_deleted,
    MIN(created_at)             AS created_at,
    NOW()                       AS updated_at

FROM rag_knowledgebase
GROUP BY workspace_id, source_name, category
ORDER BY MIN(created_at);

-- ============================================================
-- BƯỚC 3: Tạo rag_chunks records (giữ nguyên embedding gốc)
-- ============================================================
INSERT INTO rag_chunks (
    chunk_id,
    document_id,
    workspace_id,
    content,
    embedding,
    chunk_index,
    access_tags,
    is_deleted
)
SELECT
    uuid_generate_v4()      AS chunk_id,

    -- Tìm document_id tương ứng đã tạo ở bước 2
    (
        SELECT d.document_id
        FROM rag_documents d
        WHERE d.workspace_id = COALESCE(kb.workspace_id,
            (SELECT id FROM workspaces ORDER BY created_at LIMIT 1))
          AND d.file_name = COALESCE(kb.source_name, kb.category || '_legacy_data')
        LIMIT 1
    )                       AS document_id,

    COALESCE(kb.workspace_id,
        (SELECT id FROM workspaces ORDER BY created_at LIMIT 1)
    )                       AS workspace_id,

    kb.content              AS content,
    kb.embedding            AS embedding,   -- Giữ nguyên vector cũ (1024-dim)
    ROW_NUMBER() OVER (
        PARTITION BY kb.workspace_id, kb.source_name, kb.category
        ORDER BY kb.created_at
    ) - 1                   AS chunk_index,

    -- Map access_tags giống bước 2
    CASE kb.category
        WHEN 'economics'         THEN '["economics", "global"]'::jsonb
        WHEN 'psychology'        THEN '["psychology", "global"]'::jsonb
        WHEN 'anti_patterns'     THEN '["anti_patterns"]'::jsonb
        WHEN 'user_upload'       THEN '["marketing", "global"]'::jsonb
        WHEN 'policies'          THEN '["policies", "global"]'::jsonb
        WHEN 'manager_feedback'  THEN '["manager_feedback", "anti_patterns"]'::jsonb
        ELSE                          '["global"]'::jsonb
    END                     AS access_tags,

    FALSE                   AS is_deleted

FROM rag_knowledgebase kb;

-- ============================================================
-- BƯỚC 4: Verify số lượng trước khi DROP
-- ============================================================
DO $$
DECLARE
    old_count   BIGINT;
    new_chunks  BIGINT;
    new_docs    BIGINT;
BEGIN
    SELECT COUNT(*) INTO old_count  FROM rag_knowledgebase;
    SELECT COUNT(*) INTO new_chunks FROM rag_chunks;
    SELECT COUNT(*) INTO new_docs   FROM rag_documents;

    RAISE NOTICE '=== Migration Verification ===';
    RAISE NOTICE 'Old rag_knowledgebase rows : %', old_count;
    RAISE NOTICE 'New rag_chunks rows        : %', new_chunks;
    RAISE NOTICE 'New rag_documents rows     : %', new_docs;

    IF new_chunks < old_count THEN
        RAISE EXCEPTION 'MIGRATION FAILED: rag_chunks (%) < rag_knowledgebase (%). Rollback!', new_chunks, old_count;
    END IF;

    RAISE NOTICE '=== Migration OK — Ready to DROP old table ===';
END $$;

-- ============================================================
-- BƯỚC 5: DROP bảng cũ
-- (Backup vẫn còn trong rag_knowledgebase_backup)
-- ============================================================
DROP TABLE rag_knowledgebase;

COMMIT;

-- ============================================================
-- HƯỚNG DẪN ROLLBACK (nếu cần):
-- DROP TABLE rag_chunks;
-- DROP TABLE rag_documents;
-- DROP TABLE rag_access_tags;
-- CREATE TABLE rag_knowledgebase AS SELECT * FROM rag_knowledgebase_backup;
-- (Sau đó recreate indexes cũ)
-- ============================================================
