-- ============================================================
-- Migration 001: RAG Knowledge Base v2 Schema
-- Date: 2026-05-30
-- Description: Thay thế bảng rag_knowledgebase (flat) bằng
--   kiến trúc Pool-Tags-Keys với 3 bảng:
--   rag_access_tags → rag_documents → rag_chunks
-- ============================================================

BEGIN;

-- ============================================================
-- BẢNG 1: rag_access_tags (Master Tags)
-- Quản lý danh sách tag hợp lệ, ngăn insert sai chính tả
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_access_tags (
    tag_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tag_name    VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    color       VARCHAR(7) NOT NULL DEFAULT '#6366f1', -- Mã màu hex cho UI badge
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_tag_per_workspace UNIQUE (workspace_id, tag_name)
);

COMMENT ON TABLE rag_access_tags IS 'Master data cho hệ thống phân quyền RAG. Mỗi workspace có bộ tags riêng.';
COMMENT ON COLUMN rag_access_tags.color IS 'Mã màu hex (#rrggbb) hiển thị trên UI badge.';

CREATE INDEX IF NOT EXISTS idx_rag_access_tags_workspace
    ON rag_access_tags (workspace_id);

-- ============================================================
-- BẢNG 2: rag_documents (Parent — Quản lý file gốc)
-- Dùng cho giao diện quản trị UI
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_documents (
    document_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id     UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    file_name        VARCHAR(255) NOT NULL,
    file_key         TEXT,                          -- MinIO object key (file gốc)
    access_tags      JSONB NOT NULL DEFAULT '["global"]',
    upload_status    VARCHAR(50) NOT NULL DEFAULT 'processing',
        -- 'processing' | 'ready' | 'failed'
    sync_status      VARCHAR(50) NOT NULL DEFAULT 'synced',
        -- 'synced' | 'syncing' | 'failed' (dùng khi cascade update tags / soft-delete)
    chunk_count      INT NOT NULL DEFAULT 0,
    file_size_bytes  BIGINT NOT NULL DEFAULT 0,
    is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE rag_documents IS 'Bảng cha quản lý file gốc của hệ thống RAG. Phi chuẩn hóa: access_tags và is_deleted được copy xuống rag_chunks để bỏ JOIN.';
COMMENT ON COLUMN rag_documents.sync_status IS 'Trạng thái đồng bộ Cascade. synced=OK, syncing=Celery đang chạy, failed=Worker crash.';

-- Index cho query chính: lấy danh sách docs của workspace (partial: bỏ qua đã xóa)
CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_active
    ON rag_documents (workspace_id, created_at DESC)
    WHERE is_deleted = FALSE;

-- ============================================================
-- BẢNG 3: rag_chunks (Child — Vector Store)
-- Chứa embeddings + dữ liệu lọc phi chuẩn hóa
-- ============================================================
CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id  UUID NOT NULL REFERENCES rag_documents(document_id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    content      TEXT NOT NULL,
    embedding    VECTOR(1024),              -- bge-m3 1024-dim
    chunk_index  INT NOT NULL DEFAULT 0,   -- Thứ tự chunk trong document gốc

    -- Phi chuẩn hóa: copy từ bảng cha để bỏ JOIN khi query vector
    access_tags  JSONB NOT NULL DEFAULT '["global"]',
    is_deleted   BOOLEAN NOT NULL DEFAULT FALSE
);

COMMENT ON TABLE rag_chunks IS 'Bảng con lưu trữ vector embeddings. Phi chuẩn hóa: access_tags + is_deleted copy từ rag_documents để đạt Zero-JOIN query tốc độ HNSW.';
COMMENT ON COLUMN rag_chunks.embedding IS 'Vector 1024 chiều từ model bge-m3. NULL khi chưa nhúng xong.';

-- ---------------------------------------------------------
-- Index HNSW (vector similarity search)
-- m=16: số neighbor mỗi node (balance recall vs memory)
-- ef_construction=128: chất lượng build, nâng từ 64→128
--   để giữ recall tốt khi dataset > 100K vectors
-- ---------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- Index GIN cho JSONB tag filter (Pre-Retrieval Filtering Zero-JOIN)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_tags
    ON rag_chunks USING GIN (access_tags);

-- Partial index cho workspace + soft-delete filter (hay dùng nhất)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_active
    ON rag_chunks (workspace_id, document_id)
    WHERE is_deleted = FALSE;

-- ============================================================
-- Seed: Tag 'global' mặc định cho mỗi workspace hiện có
-- ============================================================
INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT
    id AS workspace_id,
    'global'    AS tag_name,
    'Tài liệu công khai cho tất cả Agent trong workspace' AS description,
    '#22c55e'   AS color
FROM workspaces
ON CONFLICT (workspace_id, tag_name) DO NOTHING;

-- Seed: Các tag nghiệp vụ mặc định
INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT id, 'marketing',     'Tài liệu chiến lược marketing, brief, insights', '#3b82f6' FROM workspaces
ON CONFLICT DO NOTHING;

INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT id, 'economics',     'Kinh tế học hành vi, tài liệu nghiên cứu thị trường', '#f59e0b' FROM workspaces
ON CONFLICT DO NOTHING;

INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT id, 'psychology',    'Tâm lý học quảng cáo, trigger hành vi người dùng', '#8b5cf6' FROM workspaces
ON CONFLICT DO NOTHING;

INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT id, 'anti_patterns', 'Mẫu quảng cáo thất bại, bài học kinh nghiệm', '#ef4444' FROM workspaces
ON CONFLICT DO NOTHING;

INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT id, 'policies',      'Chính sách quảng cáo Facebook, TikTok, quy định nền tảng', '#06b6d4' FROM workspaces
ON CONFLICT DO NOTHING;

INSERT INTO rag_access_tags (workspace_id, tag_name, description, color)
SELECT id, 'manager_feedback', 'Feedback từ CMO/Manager về nội dung đã duyệt/từ chối', '#f97316' FROM workspaces
ON CONFLICT DO NOTHING;

COMMIT;
