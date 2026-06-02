import sys
import os
sys.path.append('/root/marketing/marketing-agent-os')
from core.dependencies import get_session
from core.models import Workspace

with get_session() as db:
    for w in db.query(Workspace).all():
        print(f"WS ID: {w.id} | Name: {w.name}")
        print("Settings:", w.settings)
        print("-" * 50)
