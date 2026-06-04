# 04_DATABASE_SCHEMA.md

Dự án dùng **PostgreSQL** kết hợp extension **pgvector**.
Dưới đây là các bảng quan trọng liên quan đến luồng vận hành của AI.

> [!TIP]
> Tất cả các bảng chính đều có trường `workspace_id` phục vụ cho Multi-tenant.

## 1. RAG Vector Tables

Hệ thống RAG sử dụng HNSW index cho `pgvector` để tối ưu tốc độ.

```sql
-- rag_documents: Quản lý file gốc đã upload
CREATE TABLE rag_documents (
    document_id      UUID PRIMARY KEY,
    workspace_id     UUID NOT NULL,
    file_name        VARCHAR(255) NOT NULL,
    upload_status    VARCHAR(50) DEFAULT 'processing',
    file_hash        VARCHAR(64),
    -- ...
);

-- rag_chunks: Bảng chứa Vector Embeddings (Zero-JOIN optimized)
CREATE TABLE rag_chunks (
    chunk_id     UUID PRIMARY KEY,
    document_id  UUID NOT NULL REFERENCES rag_documents,
    workspace_id UUID NOT NULL,
    content      TEXT NOT NULL,
    embedding    VECTOR(1024), -- bge-m3 1024 dimensions
    access_tags  JSONB DEFAULT '["global"]',
    is_deleted   BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_rag_chunks_embedding 
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);
```

## 2. Campaign & Variants Tables

Dùng để lưu trữ nội dung do Agent tạo ra và theo dõi các chỉ số từ nền tảng thật.

```sql
-- marketing_campaigns: Chiến dịch tổng, giới hạn budget bằng CHECK CONSTRAINT
CREATE TABLE marketing_campaigns (
    id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    budget NUMERIC(15, 2) DEFAULT 0.00,
    CONSTRAINT check_campaign_budget CHECK (budget >= 0 AND budget <= 500000000)
    -- ...
);

-- platform_variants: Chứa các variant copy được sinh ra từ Agent (sẵn sàng đẩy lên FB, TikTok)
CREATE TABLE platform_variants (
    id UUID PRIMARY KEY,
    master_content_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    adapted_copy TEXT,
    publish_status VARCHAR(50) DEFAULT 'draft',
    -- Các chỉ số performance thực tế từ mạng xã hội
    metric_views INTEGER DEFAULT 0,
    metric_likes INTEGER DEFAULT 0,
    -- ...
);

-- campaign_analytics: Bảng OLAP lưu trữ lịch sử performance
CREATE TABLE campaign_analytics (
    id UUID PRIMARY KEY,
    campaign_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    impressions INTEGER DEFAULT 0,
    cpa NUMERIC(15, 2) DEFAULT 0.00,
    -- ...
);
```

## 3. Intent Routing (Semantic Router)

Dùng cho việc route ý định người dùng ở mức Supervisor (Chat UI) một cách cực nhanh (<10ms).

```sql
CREATE TABLE intent_routing_knowledge (
    id UUID PRIMARY KEY,
    workspace_id UUID,
    intent_category VARCHAR(50) NOT NULL, -- 'create_campaign', 'research', 'chat'
    utterance TEXT NOT NULL,
    embedding VECTOR(1024)
);
```
