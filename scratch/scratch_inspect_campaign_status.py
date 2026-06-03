import requests
import uuid
from core.dependencies import get_session
from core.models import SocialAccount

def main():
    with get_session() as db:
        acc = db.query(SocialAccount).filter_by(id=uuid.UUID("e8ff0c24-99ba-461a-9366-eb130b3de113")).first()
        if not acc:
            print("Account not found")
            return
            
        token = acc.access_token
        
        # Verify Campaign: 120245467004570448
        campaign_id = "120245467004570448"
        print(f"\n--- Querying Campaign {campaign_id} ---")
        r_camp = requests.get(
            f"https://graph.facebook.com/v19.0/{campaign_id}",
            params={"fields": "name,objective,status,effective_status", "access_token": token},
            timeout=10
        )
        print("Campaign status code:", r_camp.status_code)
        print("Campaign response:", r_camp.json())
        
        # Verify AdSet: 120245467005770448
        adset_id = "120245467005770448"
        print(f"\n--- Querying AdSet {adset_id} ---")
        r_adset = requests.get(
            f"https://graph.facebook.com/v19.0/{adset_id}",
            params={"fields": "name,campaign_id,status,effective_status,daily_budget,billing_event,optimization_goal", "access_token": token},
            timeout=10
        )
        print("AdSet status code:", r_adset.status_code)
        print("AdSet response:", r_adset.json())

if __name__ == "__main__":
    main()
