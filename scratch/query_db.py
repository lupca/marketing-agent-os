import sys
sys.path.append('/root/marketing/marketing-agent-os')
from core.dependencies import get_session
from core.models import Workspace, MarketingCampaign, SocialAccount, CampaignSocialAccount

with get_session() as db:
    print("--- WORKSPACES ---")
    for w in db.query(Workspace).all():
        print(f"{w.id} | {w.name}")
    
    print("\n--- CAMPAIGNS ---")
    for c in db.query(MarketingCampaign).all():
        print(f"{c.id} | {c.name} | WS: {c.workspace_id}")
        
    print("\n--- SOCIAL ACCOUNTS ---")
    for s in db.query(SocialAccount).all():
        print(f"{s.id} | {s.platform} | {s.account_name} | WS: {s.workspace_id}")
        
    print("\n--- CAMPAIGN SOCIAL ACCOUNTS ---")
    for csa in db.query(CampaignSocialAccount).all():
        print(f"Camp: {csa.campaign_id} | Social: {csa.social_account_id}")
