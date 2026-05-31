# scratch/check_integration.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from db.connection import SessionLocal
from core.models import WorkspaceIntegration

db = SessionLocal()
try:
    print("Attempting to query workspace_integrations table...")
    res = db.query(WorkspaceIntegration).all()
    print("Success! Found records:", len(res))
except Exception as e:
    print("Error querying workspace_integrations:")
    import traceback
    traceback.print_exc()
finally:
    db.close()
