import sys
from core.dependencies import get_session
from core.models import SocialAccount

with get_session() as db:
    print("--- SOCIAL ACCOUNTS DETAIL ---")
    for sa in db.query(SocialAccount).all():
        print(f"ID: {sa.id} | Platform: {sa.platform} | Name: {sa.account_name} | AccID: {sa.account_id} | AppID: {sa.app_id} | Status: {sa.status}")


