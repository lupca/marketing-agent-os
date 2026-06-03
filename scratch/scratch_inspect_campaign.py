from core.dependencies import get_session
from core.models import MarketingCampaign
import uuid

with get_session() as db:
    camp = db.query(MarketingCampaign).filter_by(id=uuid.UUID("55ae3ba4-d00a-4136-9686-5b64603e62fd")).first()
    if camp:
        print(f"Campaign ID: {camp.id}")
        print(f"Campaign Name: {camp.name}")
        print(f"kpi_targets: {camp.kpi_targets}")
    else:
        print("Campaign not found")
