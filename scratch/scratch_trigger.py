import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
import asyncio
import uuid
from db.connection import get_db, SessionLocal
from core import pipeline_tracker
from core.models import MarketingCampaign
from core.bandit_orchestrator import trigger_autonomous_generation

async def main():
    print("Initializing Database Session...")
    db = SessionLocal()
    try:
        campaign_id_str = "55ae3ba4-d00a-4136-9686-5b64603e62fd"
        campaign_uuid = uuid.UUID(campaign_id_str)
        
        # Query Campaign to resolve Workspace and Product IDs
        campaign = db.query(MarketingCampaign).filter_by(id=campaign_uuid).first()
        if not campaign:
            print(f"Error: Campaign {campaign_id_str} not found.")
            return
            
        workspace_id = str(campaign.workspace_id)
        product_id = str(campaign.product_id) if campaign.product_id else None
        
        print(f"Campaign Name: {campaign.name}")
        print(f"Workspace ID:  {workspace_id}")
        print(f"Product ID:    {product_id}")
        
        # Force set execution mode to LIVE
        print("Setting execution mode to LIVE...")
        pipeline_tracker.set_execution_mode("live")
        
        print("Triggering autonomous generation in LIVE mode (outbound Facebook Ads enabled)...")
        result = await trigger_autonomous_generation(
            workspace_id=workspace_id,
            campaign_id=str(campaign.id),
            product_id=product_id,
            db=db
        )
        
        print("\n--- Execution Result State ---")
        print(result)
        
    except Exception as e:
        print(f"Error executing autonomous generation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
