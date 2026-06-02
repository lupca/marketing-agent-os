# scratch/apply_omnichannel_migration.py
import os
import sys
import uuid
import logging
from sqlalchemy import text

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("omnichannel_migration")

DDL_SQL = """
CREATE TABLE IF NOT EXISTS campaign_social_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    campaign_id UUID NOT NULL REFERENCES marketing_campaigns(id) ON DELETE CASCADE,
    social_account_id UUID NOT NULL REFERENCES social_accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_campaign_social_account UNIQUE (campaign_id, social_account_id)
);

CREATE INDEX IF NOT EXISTS idx_campaign_social_accounts_campaign ON campaign_social_accounts(campaign_id);
"""

def run_migration():
    logger.info("Starting DDL migration for campaign_social_accounts table...")
    try:
        with engine.connect() as conn:
            conn.execute(text(DDL_SQL))
            conn.commit()
        logger.info("DDL migration completed successfully! campaign_social_accounts table and index are initialized.")
    except Exception as e:
        logger.error(f"DDL migration failed: {e}")
        sys.exit(1)

    logger.info("Starting data migration from legacy kpi_targets.social_account_id...")
    try:
        migrated_count = 0
        skipped_count = 0
        
        with engine.connect() as conn:
            # Query all campaigns to find legacy accounts
            campaigns = conn.execute(text("SELECT id, kpi_targets, name FROM marketing_campaigns")).fetchall()
            
            for campaign in campaigns:
                camp_id = campaign[0]
                kpi_targets = campaign[1] or {}
                camp_name = campaign[2]
                
                # Check if kpi_targets contains social_account_id
                social_account_id_str = kpi_targets.get("social_account_id")
                if not social_account_id_str:
                    continue
                
                try:
                    social_acc_id = uuid.UUID(str(social_account_id_str))
                except ValueError:
                    logger.warning(f"Campaign '{camp_name}' ({camp_id}) has invalid social_account_id format: '{social_account_id_str}'")
                    continue
                
                # Verify that the social account actually exists in social_accounts to avoid FK violation
                acc_exists = conn.execute(
                    text("SELECT 1 FROM social_accounts WHERE id = :acc_id"),
                    {"acc_id": social_acc_id}
                ).fetchone()
                
                if not acc_exists:
                    logger.warning(f"Social account {social_acc_id} referenced by campaign '{camp_name}' does not exist in social_accounts. Skipping migration for this link.")
                    continue
                
                # Check if junction link already exists
                link_exists = conn.execute(
                    text("SELECT 1 FROM campaign_social_accounts WHERE campaign_id = :camp_id AND social_account_id = :acc_id"),
                    {"camp_id": camp_id, "acc_id": social_acc_id}
                ).fetchone()
                
                if link_exists:
                    skipped_count += 1
                    continue
                
                # Insert the new junction row
                new_id = uuid.uuid4()
                conn.execute(
                    text("INSERT INTO campaign_social_accounts (id, campaign_id, social_account_id) VALUES (:id, :camp_id, :acc_id)"),
                    {"id": new_id, "camp_id": camp_id, "acc_id": social_acc_id}
                )
                logger.info(f"Successfully migrated campaign '{camp_name}' -> social account {social_acc_id}")
                migrated_count += 1
            
            conn.commit()
            
        logger.info("Data migration completed successfully!")
        logger.info(f"Summary: Migrated: {migrated_count} | Already Linked (Skipped): {skipped_count}")
        
    except Exception as e:
        logger.error(f"Data migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
