from core.dependencies import get_session
from core.models import SocialAccount
import json

with get_session() as db:
    accounts = db.query(SocialAccount).all()
    for acc in accounts:
        print(f"Platform: {acc.platform}, Account Name: {acc.account_name}, ID: {acc.account_id}, AppID: {acc.app_id}")
