from core.dependencies import get_session
from core.models import ProductService, MarketingCampaign, SocialAccount, CampaignSocialAccount
import uuid
from datetime import date

with get_session() as db:
    workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    
    # 1. Find product
    prod = db.query(ProductService).filter_by(workspace_id=workspace_id).first()
    if not prod:
        print("Product not found! Make sure seed_topvnsport.py was run.")
        sys.exit(1)
        
    print(f"Using Product ID: {prod.id} | Name: {prod.name}")
    
    # 2. Create or update campaign
    camp = db.query(MarketingCampaign).filter_by(id=uuid.UUID("55ae3ba4-d00a-4136-9686-5b64603e62fd")).first()
    if camp:
        camp.kpi_targets = {}
        camp.workspace_id = workspace_id
        camp.product_id = prod.id
        camp.name = "Chiến dịch Bùng nổ AI Agent Q2"
        camp.campaign_type = "LEAD_GEN"
        camp.status = "active"
        camp.budget = 2000000.0
        camp.start_date = date(2026, 6, 1)
        camp.end_date = date(2026, 6, 30)
        print("Updated existing campaign kpi_targets.")
    else:
        camp = MarketingCampaign(
            id=uuid.UUID("55ae3ba4-d00a-4136-9686-5b64603e62fd"),
            workspace_id=workspace_id,
            product_id=prod.id,
            name="Chiến dịch Bùng nổ AI Agent Q2",
            campaign_type="LEAD_GEN",
            status="active",
            budget=2000000.0,
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            kpi_targets={}
        )
        db.add(camp)
        print("Created new campaign.")
    db.commit()
    
    # 3. Ensure social account e8ff0c24-99ba-461a-9366-eb130b3de113 exists and has credentials
    acc = db.query(SocialAccount).filter_by(id=uuid.UUID("e8ff0c24-99ba-461a-9366-eb130b3de113")).first()
    if not acc:
        acc = SocialAccount(
            id=uuid.UUID("e8ff0c24-99ba-461a-9366-eb130b3de113"),
            workspace_id=workspace_id,
            platform="facebook",
            account_name="topvnsport",
            account_id="1336332588429387",
            app_id="1726784475006075",
            app_secret="df47841a6e5f71043fa71863f8454775",
            access_token="EAAYigFc8hHsBRoyUGv8J6wwBwFNEDwJcmGmJGaZAbA9ZB9NykvzZBBLWZBIMN8GkW0dxxAMY5xYZBm7AMydeKhEG7TVOve5t4cfRMdn0bmhmgki1EGBd5bSTWkw7lTdKWRMPx1JhNhsoT0vhXNehPpzEvmd1Prwu2D0FNwAJ8mAI4WkIZBb0uwncDc0L6DRLTQqAtl",
            status="active"
        )
        db.add(acc)
        db.commit()
        print("Created social account.")
    else:
        # Make sure app credentials are set
        acc.app_id = "1726784475006075"
        acc.app_secret = "df47841a6e5f71043fa71863f8454775"
        acc.access_token = "EAAYigFc8hHsBRoyUGv8J6wwBwFNEDwJcmGmJGaZAbA9ZB9NykvzZBBLWZBIMN8GkW0dxxAMY5xYZBm7AMydeKhEG7TVOve5t4cfRMdn0bmhmgki1EGBd5bSTWkw7lTdKWRMPx1JhNhsoT0vhXNehPpzEvmd1Prwu2D0FNwAJ8mAI4WkIZBb0uwncDc0L6DRLTQqAtl"
        db.commit()
        print("Updated social account app credentials.")
        
    # 4. Link campaign to social account in CampaignSocialAccount
    csa = db.query(CampaignSocialAccount).filter_by(campaign_id=camp.id, social_account_id=acc.id).first()
    if not csa:
        csa = CampaignSocialAccount(
            campaign_id=camp.id,
            social_account_id=acc.id
        )
        db.add(csa)
        db.commit()
        print("Linked campaign to social account.")
