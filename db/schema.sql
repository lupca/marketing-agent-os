-- PostgreSQL + pgvector Schema Design v2.0
-- Marketing Agent OS v2.0 CSDL DDL

-- Enable UUID extension and pgvector extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Table: users (Authentication & Multi-tenant members)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'member', -- 'admin', 'member'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Table: workspaces
CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) UNIQUE NOT NULL,
    owner_id UUID REFERENCES users(id) ON DELETE RESTRICT,
    members UUID[] DEFAULT '{}',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Table: brand_identities
CREATE TABLE brand_identities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    brand_name VARCHAR(255) NOT NULL,
    core_messaging JSONB DEFAULT '{}',
    visual_assets JSONB DEFAULT '{}',
    voice_and_tone TEXT,
    dos_and_donts JSONB DEFAULT '{}',
    content_pillars JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Table: customer_personas
CREATE TABLE customer_personas (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    persona_name VARCHAR(255) NOT NULL,
    summary TEXT,
    demographics JSONB DEFAULT '{}',
    psychographics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Table: products_services
CREATE TABLE products_services (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    brand_id UUID NOT NULL REFERENCES brand_identities(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    usp TEXT,
    key_features JSONB DEFAULT '[]',
    key_benefits JSONB DEFAULT '[]',
    default_offer VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Table: media_assets
CREATE TABLE media_assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    file_key TEXT NOT NULL,           -- MinIO object key e.g., 'workspaces/ws1/images/banner.png'
    file_url TEXT NOT NULL,           -- Public or internal accessible URL
    file_type VARCHAR(50) NOT NULL,    -- 'image', 'video', 'doc'
    aspect_ratio VARCHAR(50),         -- '1:1', '16:9', '9:16', etc.
    tags JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Table: inspiration_events
CREATE TABLE inspiration_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE, -- NULL means global event
    event_name VARCHAR(255) NOT NULL,
    event_date DATE,
    type VARCHAR(100),                -- 'holiday', 'industry_event', 'trend', etc.
    description TEXT,
    suggested_angles JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 8. Table: social_accounts
CREATE TABLE social_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,     -- 'facebook', 'tiktok', etc.
    account_name VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    app_id VARCHAR(255),
    app_secret VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Table: prompt_templates
CREATE TABLE prompt_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_role VARCHAR(255) NOT NULL,  -- 'Strategist', 'Copywriter', etc.
    template_text TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 10. Table: worksheets
CREATE TABLE worksheets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    event_id UUID REFERENCES inspiration_events(id) ON DELETE SET NULL,
    brand_refs UUID[] DEFAULT '{}',
    customer_refs UUID[] DEFAULT '{}',
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'processing', 'completed', 'archived'
    agent_context JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 11. Table: marketing_campaigns (CPA Anchor Table)
CREATE TABLE marketing_campaigns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    worksheet_id UUID REFERENCES worksheets(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products_services(id) ON DELETE RESTRICT,
    name VARCHAR(255) NOT NULL,
    campaign_type VARCHAR(100),       -- 'awareness', 'conversion', etc.
    status VARCHAR(50) DEFAULT 'planned', -- 'planned', 'active', 'paused', 'completed'
    budget NUMERIC(15, 2) DEFAULT 0.00,
    kpi_targets JSONB DEFAULT '{}',     -- Target CPA, ROAS, etc.
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Hard limit check constraint to prevent AI budget overflow (Max 500 million VND)
    CONSTRAINT check_campaign_budget CHECK (budget >= 0 AND budget <= 500000000)
);

-- 12. Table: content_briefs
CREATE TABLE content_briefs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    angle_name VARCHAR(255) NOT NULL,
    funnel_stage VARCHAR(100) NOT NULL,       -- 'Awareness', 'Consideration', etc.
    psychological_angle VARCHAR(100) NOT NULL, -- 'Fear', 'Emotion', 'Logic', 'Social Proof', 'Urgency', 'Curiosity'
    pain_point_focus TEXT,
    key_message_variation TEXT,
    call_to_action_direction TEXT,
    brief TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 13. Table: master_contents
CREATE TABLE master_contents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    content_brief_id UUID REFERENCES content_briefs(id) ON DELETE SET NULL,
    core_message TEXT,
    primary_media_ids UUID[] DEFAULT '{}',
    approval_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected', 'revision_needed'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 14. Table: agent_logs
CREATE TABLE agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    agent_name VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'success', 'failed', 'pending'
    tokens_used INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 15. Table: platform_variants
CREATE TABLE platform_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    master_content_id UUID NOT NULL REFERENCES master_contents(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,        -- 'facebook', 'tiktok', 'instagram', 'linkedin', 'email', 'blog'
    adapted_copy TEXT,
    platform_media_ids UUID[] DEFAULT '{}',
    publish_status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'scheduled', 'published', 'failed', 'killed', 'scaled'
    content_type VARCHAR(50),            -- 'text', 'video_script', 'carousel', etc.
    scheduled_at TIMESTAMP WITH TIME ZONE,
    published_at TIMESTAMP WITH TIME ZONE,
    platform_post_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    metric_views INTEGER DEFAULT 0,
    metric_likes INTEGER DEFAULT 0,
    metric_shares INTEGER DEFAULT 0,
    metric_comments INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 16. Table: tracking_links
CREATE TABLE tracking_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    variant_id UUID NOT NULL REFERENCES platform_variants(id) ON DELETE CASCADE,
    original_url TEXT NOT NULL,
    short_url TEXT,
    utm_source VARCHAR(100),
    utm_campaign VARCHAR(100),
    click_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 17. Table: social_interactions
CREATE TABLE social_interactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    variant_id UUID NOT NULL REFERENCES platform_variants(id) ON DELETE CASCADE,
    platform_user_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    sentiment VARCHAR(50) NOT NULL, -- 'positive', 'neutral', 'negative'
    is_handled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 18. Table: leads
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE SET NULL,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    source VARCHAR(50), -- 'web', 'social', 'email', etc.
    status VARCHAR(50) DEFAULT 'new', -- 'new', 'contacted', 'qualified', 'converted', 'lost'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 19. Table: video_jobs
CREATE TABLE video_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    requested_by VARCHAR(255),
    status VARCHAR(50) DEFAULT 'queued', -- 'queued', 'claimed', 'rendering', 'uploading', 'done', 'failed'
    priority NUMERIC DEFAULT 0,
    input_json JSONB NOT NULL,
    input_images TEXT[] DEFAULT '{}',
    input_music TEXT,
    input_logo TEXT,
    variant_name VARCHAR(255),
    output_video TEXT,
    thumbnail TEXT,
    progress INTEGER DEFAULT 0,
    progress_stage VARCHAR(255),
    attempt_count INTEGER DEFAULT 0,
    max_attempts INTEGER DEFAULT 3,
    worker_id VARCHAR(255),
    lease_until TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    render_duration_ms INTEGER DEFAULT 0,
    idempotency_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 20. Table: rag_access_tags (Master Tags — RAG Permission System)
-- Quản lý danh sách tag hợp lệ per-workspace, ngăn insert sai chính tả
CREATE TABLE IF NOT EXISTS rag_access_tags (
    tag_id       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    tag_name     VARCHAR(100) NOT NULL,
    description  VARCHAR(500),
    color        VARCHAR(7) NOT NULL DEFAULT '#6366f1', -- Mã màu hex cho UI badge
    created_at   TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uq_tag_per_workspace UNIQUE (workspace_id, tag_name)
);
CREATE INDEX IF NOT EXISTS idx_rag_access_tags_workspace ON rag_access_tags (workspace_id);

-- 21a. Table: rag_documents (Parent — Quản lý file gốc)
CREATE TABLE IF NOT EXISTS rag_documents (
    document_id      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id     UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    file_name        VARCHAR(255) NOT NULL,
    file_key         TEXT,                              -- MinIO object key
    access_tags      JSONB NOT NULL DEFAULT '["global"]',
    upload_status    VARCHAR(50) NOT NULL DEFAULT 'processing', -- 'processing'|'ready'|'failed'
    sync_status      VARCHAR(50) NOT NULL DEFAULT 'synced',     -- 'synced'|'syncing'|'failed'
    chunk_count      INT NOT NULL DEFAULT 0,
    file_size_bytes  BIGINT NOT NULL DEFAULT 0,
    file_hash        VARCHAR(64),
    is_deleted       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_active
    ON rag_documents (workspace_id, created_at DESC) WHERE is_deleted = FALSE;

CREATE INDEX IF NOT EXISTS idx_rag_documents_workspace_hash
    ON rag_documents (workspace_id, file_hash) WHERE is_deleted = FALSE;


-- 21b. Table: rag_chunks (Child — Vector Store, Phi chuẩn hóa Zero-JOIN)
CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id  UUID NOT NULL REFERENCES rag_documents(document_id) ON DELETE CASCADE,
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    content      TEXT NOT NULL,
    embedding    VECTOR(1024),              -- bge-m3 1024-dim
    chunk_index  INT NOT NULL DEFAULT 0,    -- Thứ tự chunk trong document

    -- Phi chuẩn hóa: copy từ cha để bỏ JOIN khi query HNSW
    access_tags  JSONB NOT NULL DEFAULT '["global"]',
    is_deleted   BOOLEAN NOT NULL DEFAULT FALSE
);

-- HNSW Index: m=16, ef_construction=128 (nâng từ 64 để đảm bảo recall khi scale > 100K vectors)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_embedding
    ON rag_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 128);

-- GIN Index cho JSONB tag filter (Pre-Retrieval Filtering)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_tags ON rag_chunks USING GIN (access_tags);

-- Partial Index: workspace + soft-delete (query phổ biến nhất)
CREATE INDEX IF NOT EXISTS idx_rag_chunks_active
    ON rag_chunks (workspace_id, document_id) WHERE is_deleted = FALSE;

-- 21. Table: intent_routing_knowledge (Dynamic Semantic Router)
CREATE TABLE intent_routing_knowledge (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE, -- NULL = Mặc định hệ thống
    intent_category VARCHAR(50) NOT NULL, -- 'create_campaign', 'show_metrics', 'research', 'chat'
    utterance TEXT NOT NULL,              -- Câu người dùng hay gõ, ví dụ: "Lên camp cho tôi"
    embedding VECTOR(1024),               -- Embedding của utterance (dùng model bge-m3)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index tối ưu tốc độ tìm kiếm Semantic Router (dưới 10ms)
CREATE INDEX IF NOT EXISTS idx_intent_routing_embedding
ON intent_routing_knowledge USING hnsw (embedding vector_cosine_ops);

-- 22. Table: agent_decisions (Decision Audit Log)
CREATE TABLE IF NOT EXISTS agent_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE SET NULL,
    agent_name VARCHAR(255) NOT NULL,
    action VARCHAR(255) NOT NULL,
    decision_status VARCHAR(50) NOT NULL,
    reason TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);


-- 23. Table: workspace_integrations (Dynamic Third-Party Integrations Support - CTO Design)
CREATE TABLE IF NOT EXISTS workspace_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    platform_name VARCHAR(100) NOT NULL, -- e.g. 'upload-post', 'serpapi'
    config_key VARCHAR(100) NOT NULL,    -- e.g. 'api_key', 'user', 'default_page_id'
    config_value TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_workspace_platform_config UNIQUE (workspace_id, platform_name, config_key)
);

CREATE INDEX IF NOT EXISTS idx_workspace_integrations_lookup 
ON workspace_integrations (workspace_id, platform_name);


-- 24. Table: chat_threads (Conversation Thread Manager for UI Multi-threading)
CREATE TABLE IF NOT EXISTS chat_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    thread_id VARCHAR(255) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_chat_threads_thread_id ON chat_threads(thread_id);


-- 25. Table: campaign_analytics (OLAP Database Table for Campaign Metrics History)
CREATE TABLE IF NOT EXISTS campaign_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    spend NUMERIC(15, 2) DEFAULT 0.00,
    cpc NUMERIC(15, 2) DEFAULT 0.00,
    cpa NUMERIC(15, 2) DEFAULT 0.00,
    cpm NUMERIC(15, 2) DEFAULT 0.00,
    ctr NUMERIC(5, 4) DEFAULT 0.0000,
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_campaign_analytics_lookup ON campaign_analytics (campaign_id, platform);

-- 26. Table: ai_insights_pending (HITL Pending AI Insights Table)
CREATE TABLE IF NOT EXISTS ai_insights_pending (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    insight_text TEXT NOT NULL,
    priors_shift JSONB DEFAULT '{}',
    approval_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_ai_insights_pending_lookup ON ai_insights_pending (workspace_id, campaign_id);

-- 27. Table: ad_mapper (Variant ID to Platform Ad ID Mapper)
CREATE TABLE IF NOT EXISTS ad_mapper (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    variant_id UUID UNIQUE NOT NULL REFERENCES platform_variants(id) ON DELETE CASCADE,
    platform_ad_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ad_mapper_variant ON ad_mapper (variant_id);




