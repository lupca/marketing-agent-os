from core.dependencies import get_session
from core.models import SocialAccount
import uuid

with get_session() as db:
    acc = db.query(SocialAccount).filter_by(id=uuid.UUID("e8ff0c24-99ba-461a-9366-eb130b3de113")).first()
    if acc:
        print("Before update:")
        print(f"app_id: {acc.app_id}")
        print(f"app_secret: {acc.app_secret}")
        
        acc.app_id = "1726784475006075"
        acc.app_secret = "df47841a6e5f71043fa71863f8454775"
        db.commit()
        db.refresh(acc)
        
        print("After update:")
        print(f"app_id: {acc.app_id}")
        print(f"app_secret: {acc.app_secret}")
    else:
        print("Account not found")
