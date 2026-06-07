import logging
import requests
from core.models import SocialAccount
from core.ai_clients import UploadPostAuthError, UploadPostServerError

logger = logging.getLogger("social_worker_native_publisher")

def publish_via_native_api(db, variant, fb_page_id, title, is_video_post, photos) -> dict:
    logger.info(f"[publish_via_native_api] Native Facebook Publishing for variant_id={variant.id}")
    account = db.query(SocialAccount).filter_by(workspace_id=variant.workspace_id, platform='facebook').first()
    if not account or not account.access_token:
        raise UploadPostAuthError("Missing Facebook access_token for Native API publishing.")
    token = account.access_token
    
    link_url = "https://shopee.vn/topvnsport"
    if isinstance(variant.meta_data, dict) and variant.meta_data.get("destination_link"):
        link_url = variant.meta_data.get("destination_link")

    if is_video_post and photos:
        url = f"https://graph.facebook.com/v19.0/{fb_page_id}/videos"
        with open(photos[0], "rb") as f:
            res = requests.post(url, data={"access_token": token, "description": title, "published": "false"}, files={"source": f}, timeout=120)
    elif photos:
        url = f"https://graph.facebook.com/v19.0/{fb_page_id}/photos"
        with open(photos[0], "rb") as f:
            res = requests.post(url, data={"access_token": token, "message": title, "published": "false"}, files={"source": f}, timeout=90)
    else:
        url = f"https://graph.facebook.com/v19.0/{fb_page_id}/feed"
        res = requests.post(url, data={"access_token": token, "message": title, "link": link_url, "published": "false"}, timeout=60)
    
    if res.status_code >= 400:
        raise UploadPostServerError(f"Native Meta API error: {res.text}")
    
    res_data = res.json()
    return {"post_id": res_data.get("id"), "results": {"facebook": {"post_id": res_data.get("id")}}, "raw": res_data}
