# scratch/inspect_campaign_settings.py
import sys
import os
import uuid
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core.models import Workspace, MarketingCampaign

db = SessionLocal()
try:
    camp_id = uuid.UUID("4206bbc5-89fb-4057-b07c-acc4f1483fc1")
    camp = db.query(MarketingCampaign).filter_by(id=camp_id).first()
    if not camp:
        print("Campaign not found in database!")
    else:
        print("Campaign found:")
        print(f"  Name: {camp.name}")
        print(f"  Workspace ID: {camp.workspace_id}")
        
        ws = db.query(Workspace).filter_by(id=camp.workspace_id).first()
        if not ws:
            print("Workspace not found!")
        else:
            print("Workspace found:")
            print(f"  Name: {ws.name}")
            print(f"  Settings: {ws.settings}")
finally:
    db.close()
