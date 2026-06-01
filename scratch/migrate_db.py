# scratch/migrate_db.py
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from sqlalchemy import text
from db.connection import engine

MIGRATION_SQL = """
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

CREATE TABLE IF NOT EXISTS ai_insights_pending (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    campaign_id UUID REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    insight_text TEXT NOT NULL,
    priors_shift JSONB DEFAULT '{}',
    approval_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_ai_insights_pending_lookup ON ai_insights_pending (workspace_id, campaign_id);

CREATE TABLE IF NOT EXISTS ad_mapper (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    variant_id UUID UNIQUE NOT NULL REFERENCES platform_variants(id) ON DELETE CASCADE,
    platform_ad_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ad_mapper_variant ON ad_mapper (variant_id);
"""

def run_migration():
    print("Running DDL migration on PostgreSQL database for new v3.0 tables...")
    try:
        with engine.connect() as conn:
            conn.execute(text(MIGRATION_SQL))
            conn.commit()
        print("DDL Migration completed successfully! campaign_analytics, ai_insights_pending, and ad_mapper initialized.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
