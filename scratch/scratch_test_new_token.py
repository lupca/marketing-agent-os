import requests
import json
import traceback

TOKEN = "EAAYigFc8hHsBRtfoxdJD1XWXEG4dHlaZADnmUpw13ZBYUiJZCpVYBzsjPEifLZC8W9EsDu03jiuEZBZCphJfZAmkMYu9qEeyvVjZBQvoQdWkQSGs2BKwuZCThmcDeEOYLJn7b4Df59bsOZBrQyNTWKy1DEtV2cbDaZCkyxNH7VUlErrlZCnsoWLfic1wIiKdY7zkAchrNcaY"
POST_ID = "122111091441026769"
AD_ACCOUNT_ID = "313131084168462"
API_VERSION = "v21.0" # Trying v21.0 based on user's hint of newer versions

def print_res(name, res):
    print(f"--- {name} ---")
    print(f"Status Code: {res.status_code}")
    try:
        print(json.dumps(res.json(), indent=2))
    except:
        print(res.text)
    print("\n")

def run_test():
    # 1. Lấy thông tin tài khoản (Page) từ Token
    res = requests.get(f"https://graph.facebook.com/{API_VERSION}/me", params={"access_token": TOKEN})
    print_res("GET /me", res)
    page_data = res.json()
    page_id = page_data.get("id")
    
    if not page_id:
        print("Không lấy được Page ID từ Token.")
        return

    # 2. Thử tạo 1 bài post mới trên Page
    post_payload = {
        "access_token": TOKEN,
        "message": "Bài test tạo mới tự động bằng Page Token - API version test"
    }
    res_post = requests.post(f"https://graph.facebook.com/{API_VERSION}/{page_id}/feed", data=post_payload)
    print_res("POST /page_id/feed (Tạo post mới)", res_post)
    new_post_id = res_post.json().get("id")

    # 3. Thử tạo Campaign, AdSet, Ad với Token này
    # Campaign
    camp_payload = {
        "access_token": TOKEN,
        "name": "Test Campaign (Awareness) from Page Token",
        "objective": "OUTCOME_AWARENESS",
        "status": "PAUSED",
        "special_ad_categories": "[\"NONE\"]",
        "is_adset_budget_sharing_enabled": "False"
    }
    res_camp = requests.post(f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/campaigns", data=camp_payload)
    print_res("POST /act_id/campaigns", res_camp)
    camp_id = res_camp.json().get("id")

    if not camp_id:
        print("Tạo Campaign thất bại, dừng test Ads.")
        return

    # AdSet
    adset_payload = {
        "access_token": TOKEN,
        "name": "Test AdSet from Page Token",
        "campaign_id": camp_id,
        "daily_budget": 50000,
        "billing_event": "IMPRESSIONS",
        "optimization_goal": "REACH",
        "bid_amount": 20000,
        "targeting": json.dumps({"geo_locations": {"countries": ["VN"]}}),
        "status": "PAUSED"
    }
    res_adset = requests.post(f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/adsets", data=adset_payload)
    print_res("POST /act_id/adsets", res_adset)
    adset_id = res_adset.json().get("id")

    if not adset_id:
        return

    # AdCreative bằng Existing Post ID (122111091441026769)
    creative_payload = {
        "access_token": TOKEN,
        "name": "Test Creative with Existing Post",
        "object_story_id": POST_ID
    }
    res_creative = requests.post(f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/adcreatives", data=creative_payload)
    print_res(f"POST /act_id/adcreatives (Using provided post {POST_ID})", res_creative)
    creative_id = res_creative.json().get("id")

    # Nếu tạo bằng post_id của user ko thành công, thử tạo bằng post_id mới tạo
    if not creative_id and new_post_id:
        print("Thử tạo lại AdCreative với bài post vừa tạo mới...")
        creative_payload_new = {
            "access_token": TOKEN,
            "name": "Test Creative with New Post",
            "object_story_id": new_post_id
        }
        res_creative_new = requests.post(f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/adcreatives", data=creative_payload_new)
        print_res(f"POST /act_id/adcreatives (Using new post {new_post_id})", res_creative_new)
        creative_id = res_creative_new.json().get("id")

    if not creative_id:
        return

    # Tạo Ad
    ad_payload = {
        "access_token": TOKEN,
        "name": "Test Ad from Page Token",
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": "PAUSED"
    }
    res_ad = requests.post(f"https://graph.facebook.com/{API_VERSION}/act_{AD_ACCOUNT_ID}/ads", data=ad_payload)
    print_res("POST /act_id/ads", res_ad)

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        traceback.print_exc()
