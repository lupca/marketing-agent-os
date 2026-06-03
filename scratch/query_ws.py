import sys
from core.dependencies import get_session
from core.models import Workspace

with get_session() as db:
    ws = db.query(Workspace).filter_by(id='00000000-0000-0000-0000-000000000002').first()
    if ws:
        print(ws.settings)
    else:
        print('Not found')
