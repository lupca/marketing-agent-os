from core.dependencies import get_session
from core.models import SocialAccount
import uuid

with get_session() as db:
    acc = db.query(SocialAccount).filter_by(id=uuid.UUID("e8ff0c24-99ba-461a-9366-eb130b3de113")).first()
    if acc:
        print(f"Platform: {acc.platform}")
        print(f"Account Name: {acc.account_name}")
        print(f"Account ID: {acc.account_id}")
        print(f"App ID (masked): {acc.app_id[:4]}***" if acc.app_id else "None")
        print(f"App Secret (masked): {acc.app_secret[:4]}***" if acc.app_secret else "None")
        print(f"Access Token (masked): {acc.access_token[:10]}***" if acc.access_token else "None")
        print(f"Token is dummy: {'dummy' in (acc.access_token or '').lower()}")
    else:
        print("Account not found")
