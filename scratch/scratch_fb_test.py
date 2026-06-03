# scratch_fb_test.py
import logging
logging.basicConfig(level=logging.INFO)

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign
from facebook_business.api import FacebookAdsApi

access_token = "EAAYigFc8hHsBRoyUGv8J6wwBwFNEDwJcmGmJGaZAbA9ZB9NykvzZBBLWZBIMN8GkW0dxxAMY5xYZBm7AMydeKhEG7TVOve5t4cfRMdn0bmhmgki1EGBd5bSTWkw7lTdKWRMPx1JhNhsoT0vhXNehPpzEvmd1Prwu2D0FNwAJ8mAI4WkIZBb0uwncDc0L6DRLTQqAtl"
app_id = "1726784475006075"
ad_account_id = "act_1336332588429387"
campaign_name = "My Quickstart Campaign"

print("Initializing Facebook API...")
FacebookAdsApi.init(access_token=access_token)

print(f"Attempting to create a campaign under account {ad_account_id}...")
fields = []
params = {
    "name": campaign_name,
    "objective": "OUTCOME_TRAFFIC",
    "status": "PAUSED",
    "special_ad_categories": [],
    "is_adset_budget_sharing_enabled": False,
}

try:
    campaign = AdAccount(ad_account_id).create_campaign(
        fields=fields,
        params=params,
    )
    campaign_id = campaign.get_id()
    print("SUCCESS!")
    print("Your created campaign id is: " + str(campaign_id))
except Exception as e:
    print("FAILED!")
    print(f"Error during campaign creation: {e}")
    import traceback
    traceback.print_exc()
