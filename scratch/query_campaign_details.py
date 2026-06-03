import sys
sys.path.append('.')
from core.dependencies import get_session
from core.models import MarketingCampaign

with get_session() as db:
    c = db.query(MarketingCampaign).filter_by(id='55ae3ba4-d00a-4136-9686-5b64603e62fd').first()
    if c:
        print('ID:', c.id)
        print('Name:', c.name)
        print('Campaign Type:', c.campaign_type)
        print('KPI Targets:', c.kpi_targets)
    else:
        print('Campaign not found')
