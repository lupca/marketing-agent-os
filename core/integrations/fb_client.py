# core/integrations/fb_client.py
import collections
import collections.abc
# Monkeypatch collections for Python 3.10+ compatibility with older facebook_business SDK
for name in ['MutableMapping', 'Iterable', 'Mapping', 'MutableSequence', 'Sequence']:
    if not hasattr(collections, name):
        setattr(collections, name, getattr(collections.abc, name))

import logging
import requests
import uuid
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.exceptions import FacebookRequestError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.models import SocialAccount, AdMapper, CampaignSocialAccount

logger = logging.getLogger("fb_client")
logger.setLevel(logging.INFO)

class FacebookAccountDisabledError(Exception):
    """Custom exception raised when the Facebook Ad Account is disabled or restricted."""
    pass

def parse_fb_error(e: FacebookRequestError) -> Tuple[str, int]:
    """Helper to extract error message and error code from FacebookRequestError."""
    err_msg = e.api_error_message() or str(e)
    err_code = e.api_error_code()
    return err_msg, err_code

def check_and_raise_if_disabled(e: FacebookRequestError, fb_account_id: str = "") -> None:
    """Helper to check if a FacebookRequestError indicates a restricted or disabled account and raise an exception."""
    err_msg, err_code = parse_fb_error(e)
    if err_code in [100, 10, 200] or any(kw in err_msg.lower() for kw in ["disabled", "restricted", "suspended", "inactive"]):
        logger.error(f"Facebook Ad Account is disabled or restricted: {err_msg}")
        raise FacebookAccountDisabledError(f"Facebook Ad Account {fb_account_id} is disabled/restricted: {err_msg}") from e

def get_fb_client(workspace_id: str, db: Session, campaign_id: str = None) -> Tuple[FacebookAdsApi, str]:
    """
    Factory function that retrieves credentials from the database and initializes FacebookAdsApi.
    Returns a tuple of (api_instance, fb_account_id).
    """
    try:
        ws_uuid = uuid.UUID(str(workspace_id))
    except ValueError as val_err:
        raise ValueError(f"Invalid workspace_id UUID format: {workspace_id}") from val_err

    from core.models import MarketingCampaign
    account = None
    if campaign_id:
        try:
            camp_uuid = uuid.UUID(str(campaign_id))
            
            # Tier 1: Query the new many-to-many CampaignSocialAccount junction table
            account = db.query(SocialAccount).join(
                CampaignSocialAccount,
                CampaignSocialAccount.social_account_id == SocialAccount.id
            ).filter(
                CampaignSocialAccount.campaign_id == camp_uuid,
                SocialAccount.platform == 'facebook'
            ).first()

            # Tier 2: Legacy Fallback to campaign.kpi_targets.social_account_id
            if not account:
                campaign = db.query(MarketingCampaign).filter_by(id=camp_uuid).first()
                if campaign and campaign.kpi_targets:
                    social_account_id_str = campaign.kpi_targets.get("social_account_id")
                    if social_account_id_str:
                        try:
                            social_acc_uuid = uuid.UUID(str(social_account_id_str))
                            account = db.query(SocialAccount).filter_by(id=social_acc_uuid, platform='facebook').first()
                        except ValueError:
                            pass
        except ValueError:
            pass

    # Tier 3: Workspace Default Fallback (querying the first active Facebook account in the workspace)
    if not account:
        account = db.query(SocialAccount).filter_by(
            workspace_id=ws_uuid,
            platform='facebook'
        ).first()

    if not account:
        raise ValueError(f"No Facebook social account found in workspace {workspace_id}")

    # Check status column
    status = (account.status or "active").lower()
    if status in ['disabled', 'restricted', 'inactive']:
        raise FacebookAccountDisabledError(
            f"Facebook account is marked as '{status}' in the local database. "
            f"Account ID: {account.account_id}, Name: {account.account_name}"
        )

    if not account.access_token:
        raise ValueError(
            f"Facebook access_token is not configured "
            f"for social account ID {account.id}."
        )

    # Allow using raw Page Tokens without an FB App
    app_id = account.app_id or None
    app_secret = account.app_secret or None

    # Initialize Facebook SDK default API
    try:
        if app_id and app_secret:
            api = FacebookAdsApi.init(
                app_id=app_id,
                app_secret=app_secret,
                access_token=account.access_token
            )
        else:
            api = FacebookAdsApi.init(
                access_token=account.access_token
            )
        logger.info(f"Successfully initialized Facebook Ads API for account {account.account_id}")
        return api, account.account_id
    except Exception as e:
        logger.error(f"Failed to initialize FacebookAdsApi: {e}")
        raise

# Exponential Backoff configuration specifically for FacebookRequestError
# Particularly handles error code 17 (User Level Rate Limit) and 613 (Custom Rate Limit)
def is_rate_limit_or_transient_error(exception):
    if isinstance(exception, FacebookRequestError):
        _, error_code = parse_fb_error(exception)
        # Code 17: User-level rate limit, 613: Custom rate limit, 1: API Unknown error (transient)
        # 2: API Service transient error
        if error_code in [17, 613, 1, 2]:
            logger.warning(f"Facebook Rate Limit or Transient error encountered (code {error_code}). Retrying with backoff...")
            return True
    return False

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=is_rate_limit_or_transient_error,
    reraise=True
)
def _execute_sdk_insights_call(account: AdAccount, fields: List[str], params: Dict[str, Any]):
    """Wrapper that executes get_insights with tenacity retry logic."""
    return account.get_insights(fields=fields, params=params)

def fetch_campaign_metrics(campaign_id: str, fb_account_id: str, db: Session = None) -> List[Dict[str, Any]]:
    """
    Queries campaign insights from the Facebook Ads API at the 'ad' level.
    Maps Facebook's ad_id back to our internal variant_id using the ad_mapper table.
    """
    if db is None:
        from core.dependencies import get_session
        with get_session() as session:
            return _fetch_campaign_metrics_impl(campaign_id, fb_account_id, session)
    else:
        return _fetch_campaign_metrics_impl(campaign_id, fb_account_id, db)

def _fetch_campaign_metrics_impl(campaign_id: str, fb_account_id: str, db: Session) -> List[Dict[str, Any]]:
    # Prepend act_ if not present
    if not fb_account_id.startswith('act_'):
        fb_account_id = f"act_{fb_account_id}"

    account = AdAccount(fb_account_id)

    # Standard metrics fields to fetch
    fields = [
        'ad_id',
        'ad_name',
        'impressions',
        'clicks',
        'spend',
        'cpc',
        'ctr',
        'actions'
    ]

    params = {
        'level': 'ad',
        'filtering': [{
            'field': 'campaign.id',
            'operator': 'EQUAL',
            'value': campaign_id
        }]
    }

    logger.info(f"Querying Facebook Ads insights for Campaign: {campaign_id} under Account: {fb_account_id}")

    try:
        insights = _execute_sdk_insights_call(account, fields, params)
    except FacebookRequestError as e:
        check_and_raise_if_disabled(e, fb_account_id)
        err_msg, _ = parse_fb_error(e)
        logger.error(f"Facebook SDK error querying insights: {err_msg}")
        raise

    results = []
    for insight in insights:
        ad_id = insight.get('ad_id')
        impressions = int(insight.get('impressions') or 0)
        clicks = int(insight.get('clicks') or 0)
        spend = float(insight.get('spend') or 0.0)
        cpc = float(insight.get('cpc') or 0.0)
        ctr = float(insight.get('ctr') or 0.0)

        # Extract conversions/actions for CPA calculation
        conversions = 0
        actions = insight.get('actions') or []
        for action in actions:
            action_type = action.get('action_type', '')
            # Capture lead generation, purchases or general conversions
            if any(t in action_type for t in ['lead', 'purchase', 'conversion', 'offsite_conversion']):
                conversions += int(action.get('value') or 0)

        cpa = spend / conversions if conversions > 0 else 0.0

        # Query local mapping
        mapper = db.query(AdMapper).filter_by(platform_ad_id=ad_id).first()
        variant_id = mapper.variant_id if mapper else None

        results.append({
            "variant_id": variant_id,
            "platform_ad_id": ad_id,
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,
            "cpc": cpc,
            "ctr": ctr,
            "conversions": conversions,
            "cpa": cpa
        })

        logger.info(f"Mapped Ad {ad_id} to Variant {variant_id}: imp={impressions}, clk={clicks}, spend={spend}")

    return results

def init_facebook_client(workspace_id: str, db: Session, campaign_id: str = None) -> Tuple[Any, str, bool]:
    """Helper to initialize the Facebook Ads client with workspace credentials."""
    use_real_fb = True
    try:
        api, fb_account_id = get_fb_client(workspace_id, db, campaign_id=campaign_id)
        if not fb_account_id.startswith('act_'):
            fb_account_id = f"act_{fb_account_id}"
        
        # Check for mock/dummy credentials
        token = api._session.access_token if hasattr(api, "_session") else None
        if not api or not token or "dummy" in token:
            raise ValueError("Dummy or missing Facebook API credentials detected.")
            
        return api, fb_account_id, use_real_fb
    except FacebookAccountDisabledError:
        raise
    except ValueError as val_err:
        err_msg = str(val_err)
        if "credentials" in err_msg or "configured" in err_msg or "Dummy" in err_msg:
            logger.warning(f"Facebook Ads credentials not configured or dummy: {err_msg}. Skipping Ads API initialization but proceeding with page publishing fallback.")
            
            fb_account_id = "mock_publisher_account"
            try:
                ws_uuid = uuid.UUID(str(workspace_id))
                from core.models import SocialAccount
                account = db.query(SocialAccount).filter_by(workspace_id=ws_uuid, platform='facebook').first()
                if account and account.account_id:
                    fb_account_id = account.account_id
                    if not fb_account_id.startswith('act_'):
                        fb_account_id = f"act_{fb_account_id}"
            except Exception:
                pass
                
            return None, fb_account_id, use_real_fb
        else:
            logger.error(f"Validation error initializing Facebook API ({val_err}).")
            raise RuntimeError(f"Failed to initialize Facebook API: {val_err}") from val_err
    except Exception as cred_err:
        logger.error(f"Could not initialize Facebook API ({cred_err}).")
        raise RuntimeError(f"Failed to initialize Facebook API: {cred_err}") from cred_err

def batch_create_creatives(api: Any, fb_account_id: str, workspace_id: str, variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Uses the Upload-Post API to publish posts, then creates AdCreatives sequentially."""
    from facebook_business.adobjects.adcreative import AdCreative
    from core.utils import get_integration_config
    from core.ai_clients import upload_text
    import time
    
    creative_responses = []
    
    configs_post = get_integration_config(workspace_id, "upload-post")
    configs_pos = get_integration_config(workspace_id, "upload-pos")
    integration_configs = {**configs_pos, **configs_post}
        
    page_id = integration_configs.get("facebook_page_id")
    api_key = integration_configs.get("api_key")
    
    # Try environment variable fallback for API key if missing in DB
    if not api_key:
        import os
        api_key = os.environ.get("UPLOAD_POST_API_KEY", "dummy_key")
        
    # Dynamic Facebook Page Resolution from Meta API using Ad Account Access Token (Priority)
    token = api._session.access_token if hasattr(api, "_session") else None
    if not page_id and token and "dummy" not in token:
        logger.info("facebook_page_id không cấu hình. Bắt đầu phân giải động từ Meta API bằng tài khoản quảng cáo...")
        # 1. Try Meta API /me/accounts
        try:
            resp = requests.get("https://graph.facebook.com/v19.0/me/accounts", params={"access_token": token}, timeout=20)
            if resp.status_code == 200:
                pages_data = resp.json()
                pages = pages_data.get("data", [])
                for p in pages:
                    name = p.get("name", "").lower()
                    if "top vn sport" in name or "topvnsport" in name:
                        page_id = p.get("id")
                        logger.info(f"Đã phân giải được page_id: {page_id} từ Meta /me/accounts.")
                        break
                if not page_id and pages:
                    page_id = pages[0].get("id")
                    logger.info(f"Fallback lấy page đầu tiên từ /me/accounts: {page_id}")
        except Exception as e:
            logger.warning(f"Lỗi khi gọi Meta /me/accounts: {e}")
            
        # 2. Try Meta API /{ad_account_id}/promote_pages if still unresolved
        if not page_id and fb_account_id:
            try:
                act_id = fb_account_id if fb_account_id.startswith("act_") else f"act_{fb_account_id}"
                resp = requests.get(f"https://graph.facebook.com/v19.0/{act_id}/promote_pages", params={"access_token": token}, timeout=20)
                if resp.status_code == 200:
                    pages_data = resp.json()
                    pages = pages_data.get("data", [])
                    for p in pages:
                        name = p.get("name", "").lower()
                        if "top vn sport" in name or "topvnsport" in name:
                            page_id = p.get("id")
                            logger.info(f"Đã phân giải được page_id: {page_id} từ Meta /{act_id}/promote_pages.")
                            break
                    if not page_id and pages:
                        page_id = pages[0].get("id")
                        logger.info(f"Fallback lấy page đầu tiên từ promote_pages: {page_id}")
            except Exception as e:
                logger.warning(f"Lỗi khi gọi Meta promote_pages: {e}")
                
    # Fallback: Dynamic Facebook Page Resolution from Upload-Post API (3rd party)
    if not page_id and api_key and api_key != "dummy_key":
        logger.info("facebook_page_id không cấu hình. Bắt đầu phân giải động từ Upload-Post API bên thứ ba...")
        try:
            headers = {"Authorization": f"Apikey {api_key}"}
            resp = requests.get("https://api.upload-post.com/api/uploadposts/facebook/pages", headers=headers, timeout=20)
            if resp.status_code == 200:
                pages_data = resp.json()
                pages = pages_data.get("pages", [])
                for p in pages:
                    name = p.get("name", "").lower()
                    if "top vn sport" in name or "topvnsport" in name:
                        page_id = p.get("id")
                        logger.info(f"Đã phân giải động được page_id: {page_id} từ Upload-Post API.")
                        break
                # Fallback to the first page in the list if no name matches
                if not page_id and pages:
                    page_id = pages[0].get("id")
                    logger.info(f"Không tìm thấy page khớp tên. Fallback lấy page đầu tiên từ Upload-Post: {page_id} ({pages[0].get('name')})")
        except Exception as e:
            logger.warning(f"Lỗi khi tự động phân giải facebook_page_id từ Upload-Post: {e}")
        
    for v in variants:
        v_id = v.get("variant_id") or v.get("id")
        copy = v.get("adapted_copy", "")
        angle_name = v.get("angle_name", "Creative")
        
        # Replace or append the destination Shopee link
        link_url = "https://shopee.vn/topvnsport"
        import re
        modified_copy = re.sub(r'\[Link sản phẩm\]|\[link sản phẩm\]', link_url, copy, flags=re.IGNORECASE)
        if modified_copy != copy:
            copy = modified_copy
        else:
            if link_url not in copy:
                copy = f"{copy}\n\n👉 Chi tiết sản phẩm: {link_url}"
        
        v["adapted_copy"] = copy
        v["destination_link"] = link_url
        
        var_page_id = v.get("facebook_page_id") or v.get("page_id") or page_id
        if not var_page_id:
            raise ValueError(f"Thiếu cấu hình 'facebook_page_id' cho variant {v_id}. Không thể tạo Creative.")
            
        try:
            is_upload_post_active = bool(api_key and api_key != "dummy_key")
            if is_upload_post_active:
                logger.info(f"Sử dụng Upload-Post API để đăng bài Public cho variant {v_id}...")
                api_res = upload_text(
                    api_key=api_key,
                    user="topvnsport",
                    platforms=["facebook"],
                    title=copy,
                    facebook_page_id=var_page_id
                )
                
                post_id = api_res.get("results", {}).get("facebook", {}).get("post_id") or api_res.get("post_id") or api_res.get("request_id")
                if not post_id:
                    raise RuntimeError(f"Upload-Post API không trả về post_id. Phản hồi: {api_res}")
            else:
                logger.info(f"Sử dụng Native Meta Graph API để đăng bài Public cho variant {v_id}...")
                token = api._session.access_token if hasattr(api, "_session") else None
                if not token or "dummy" in token:
                    raise ValueError("Thiếu Native Access Token hợp lệ để đăng bài lên Meta API.")
                url = f"https://graph.facebook.com/v19.0/{var_page_id}/feed"
                res = requests.post(url, data={"access_token": token, "message": copy, "link": link_url}, timeout=60)
                if res.status_code >= 400:
                    raise RuntimeError(f"Native Meta API đăng bài thất bại: {res.text}")
                post_id = res.json().get("id")
                if not post_id:
                    raise RuntimeError(f"Native Meta API không trả về post_id. Phản hồi: {res.text}")
                
            # Đảm bảo định dạng object_story_id hợp lệ (page_id_post_id)
            object_story_id = f"{var_page_id}_{post_id}" if "_" not in str(post_id) else str(post_id)
            
            # Kiểm tra trạng thái bài viết sẵn sàng trên Meta Graph API (Active Polling)
            token = api._session.access_token if hasattr(api, "_session") else None
            is_ready = False
            max_attempts = 6
            poll_interval = 2
            
            if token and "dummy" not in token:
                logger.info(f"Kiểm tra trạng thái bài viết {object_story_id} trên Meta Graph API...")
                for attempt in range(max_attempts):
                    try:
                        graph_url = f"https://graph.facebook.com/v19.0/{object_story_id}"
                        resp = requests.get(graph_url, params={"access_token": token}, timeout=10)
                        if resp.status_code == 200:
                            logger.info(f"Bài viết {object_story_id} đã sẵn sàng trên Meta Graph API ở attempt {attempt + 1}.")
                            is_ready = True
                            break
                        else:
                            logger.warning(
                                f"Bài viết {object_story_id} chưa sẵn sàng (Lần thử {attempt + 1}/{max_attempts}). "
                                f"Status: {resp.status_code}, Response: {resp.text}"
                            )
                    except Exception as poll_err:
                        logger.warning(f"Lỗi khi kiểm tra trạng thái bài viết: {poll_err}")
                    time.sleep(poll_interval)
            else:
                logger.info("Bỏ qua kiểm tra Graph API do dùng credentials giả lập.")
                is_ready = True
                
            if not is_ready:
                logger.warning(f"Bài viết {object_story_id} chưa phản hồi 200 OK sau {max_attempts * poll_interval} giây. Tiếp tục tạo Creative...")
            
            # Tạo AdCreative trỏ tới bài viết đã Public
            if api:
                creative = AdCreative(parent_id=fb_account_id, api=api)
                creative.update({
                    'name': f"Creative_{str(v_id)[:8]}_{angle_name}",
                    'object_story_id': object_story_id,
                })
                
                try:
                    response = creative.remote_create()
                    if response and hasattr(response, 'get') and response.get('id'):
                        c_id = response.get('id')
                    else:
                        c_id = creative.get('id') if hasattr(creative, 'get') else getattr(creative, 'id', None)
                        
                    logger.info(f"AdCreative created successfully for variant {v_id}: Creative ID {c_id}")
                    creative_responses.append({
                        "variant_id": v_id,
                        "creative_id": c_id,
                        "error": None
                    })
                except Exception as create_err:
                    create_err_detail = create_err.json() if hasattr(create_err, 'json') else str(create_err)
                    logger.warning(
                        f"Tạo AdCreative bằng object_story_id {object_story_id} thất bại ({create_err_detail}). "
                        f"Thử fallback tạo bằng object_story_spec (inline)..."
                    )
                    try:
                        creative_fallback = AdCreative(parent_id=fb_account_id, api=api)
                        creative_fallback.update({
                            'name': f"Creative_{str(v_id)[:8]}_{angle_name}_Fallback",
                            'object_story_spec': {
                                'page_id': var_page_id,
                                'link_data': {
                                    'message': copy,
                                    'link': link_url,
                                    'name': f"TOPVNSPORT - {angle_name}"
                                }
                            }
                        })
                        response = creative_fallback.remote_create()
                        if response and hasattr(response, 'get') and response.get('id'):
                            c_id = response.get('id')
                        else:
                            c_id = creative_fallback.get('id') if hasattr(creative_fallback, 'get') else getattr(creative_fallback, 'id', None)
                            
                        logger.info(f"Fallback AdCreative created successfully using object_story_spec for variant {v_id}: Creative ID {c_id}")
                        creative_responses.append({
                            "variant_id": v_id,
                            "creative_id": c_id,
                            "error": None
                        })
                    except Exception as fallback_err:
                        fallback_err_detail = fallback_err.json() if hasattr(fallback_err, 'json') else str(fallback_err)
                        logger.error(f"Fallback AdCreative creation also failed cho variant {v_id}: {fallback_err_detail}")
                        creative_responses.append({
                            "variant_id": v_id,
                            "creative_id": None,
                            "error": fallback_err_detail
                        })
            else:
                logger.info(f"Facebook Ads API not initialized. Skipping AdCreative creation for variant {v_id}.")
                creative_responses.append({
                    "variant_id": v_id,
                    "creative_id": None,
                    "error": None
                })
            
        except Exception as e:
            err_detail = e.json() if hasattr(e, 'json') else str(e)
            logger.error(f"AdCreative process failed cho variant {v_id}: {err_detail}")
            creative_responses.append({
                "variant_id": v_id,
                "creative_id": None,
                "error": err_detail
            })
            
    return creative_responses

def ensure_facebook_campaign_and_adset(api: Any, fb_account_id: str, campaign_id: uuid.UUID, db: Session) -> str:
    """
    Ensures that a Facebook Campaign and AdSet exist for the given campaign.
    If not, it creates them via the Facebook Ads API and updates the local campaign's kpi_targets.
    Returns the target_adset_id.
    """
    from core.models import MarketingCampaign
    from facebook_business.adobjects.campaign import Campaign
    from facebook_business.adobjects.adset import AdSet
    from facebook_business.adobjects.adaccount import AdAccount

    campaign = db.query(MarketingCampaign).filter_by(id=campaign_id).first()
    if not campaign:
        raise ValueError(f"Campaign with ID {campaign_id} not found in database.")

    # Initialize kpi_targets if None
    kpi_targets = dict(campaign.kpi_targets) if campaign.kpi_targets else {}
    target_adset_id = kpi_targets.get("facebook_adset_id")

    if target_adset_id:
        logger.info(f"Using pre-configured facebook_adset_id: {target_adset_id} for campaign {campaign_id}")
        return str(target_adset_id)

    # If facebook_adset_id is missing, we need to ensure the campaign exists first
    fb_campaign_id = kpi_targets.get("facebook_campaign_id")
    ad_account = AdAccount(fb_account_id, api=api)

    if not fb_campaign_id:
        logger.info(f"facebook_campaign_id is missing. Auto-creating Facebook Campaign for campaign {campaign_id}...")
        campaign_name = campaign.name or f"Autogenerated Campaign {uuid.uuid4().hex[:6]}"
        
    # Determine objective and optimization goal dynamically based on campaign type
    local_objective = campaign.campaign_type or "LEAD_GEN"
    if local_objective == "BRAND_AWARENESS":
        objective = "OUTCOME_AWARENESS"
        optimization_goal = "IMPRESSIONS"
    else:
        objective = "OUTCOME_TRAFFIC"
        optimization_goal = "LINK_CLICKS"

    if not fb_campaign_id:
        logger.info(f"facebook_campaign_id is missing. Auto-creating Facebook Campaign for campaign {campaign_id}...")
        campaign_name = campaign.name or f"Autogenerated Campaign {uuid.uuid4().hex[:6]}"
        
        campaign_params = {
            'name': campaign_name,
            'objective': objective,
            'status': 'PAUSED',
            'special_ad_categories': [],
            'is_adset_budget_sharing_enabled': False,
        }
        
        try:
            fb_campaign = ad_account.create_campaign(params=campaign_params)
            fb_campaign_id = fb_campaign.get('id') if hasattr(fb_campaign, 'get') else getattr(fb_campaign, 'id', None)
            if not fb_campaign_id:
                raise RuntimeError(f"Facebook Campaign creation did not return a valid ID. Response: {fb_campaign}")
                
            kpi_targets["facebook_campaign_id"] = fb_campaign_id
            campaign.kpi_targets = kpi_targets
            db.commit()
            logger.info(f"Successfully auto-created Facebook Campaign: {fb_campaign_id}")
        except Exception as e:
            logger.error(f"Failed to create Facebook Campaign: {e}")
            raise

    # Now ensure the Facebook AdSet exists under the Facebook Campaign
    logger.info(f"Auto-creating Facebook AdSet under campaign {fb_campaign_id}...")
    
    # Get account currency to resolve daily_budget correctly (Meta daily_budget uses cents for USD, etc.)
    try:
        account_info = ad_account.api_get(fields=['currency'])
        currency = account_info.get('currency', 'VND') if hasattr(account_info, 'get') else 'VND'
    except Exception as cur_err:
        logger.warning(f"Failed to query ad account currency: {cur_err}. Defaulting to VND.")
        currency = 'VND'

    # Budget setup (Default to 100,000 VND or equivalent 1,000 cents / $10)
    local_budget = float(campaign.budget or 2000000.0)
    if currency == 'USD':
        daily_budget_raw = max(int(local_budget * 0.1), 10)
        daily_budget = daily_budget_raw * 100 # In cents
    else:
        daily_budget = max(int(local_budget * 0.1), 100000)

    adset_name = f"{campaign.name or 'Autogenerated'} - AdSet"
    adset_params = {
        'name': adset_name,
        'campaign_id': fb_campaign_id,
        'billing_event': 'IMPRESSIONS',
        'optimization_goal': optimization_goal,
        'daily_budget': str(daily_budget),
        'bid_strategy': 'LOWEST_COST_WITHOUT_CAP',
        'status': 'PAUSED',
        'targeting': {
            'geo_locations': {'countries': ['VN']} # Default target country to Vietnam
        },
    }

    try:
        fb_adset = ad_account.create_ad_set(params=adset_params)
        fb_adset_id = fb_adset.get('id') if hasattr(fb_adset, 'get') else getattr(fb_adset, 'id', None)
        if not fb_adset_id:
            raise RuntimeError(f"Facebook AdSet creation did not return a valid ID. Response: {fb_adset}")
            
        kpi_targets["facebook_adset_id"] = fb_adset_id
        campaign.kpi_targets = kpi_targets
        db.commit()
        logger.info(f"Successfully auto-created Facebook AdSet: {fb_adset_id}")
        return fb_adset_id
    except Exception as e:
        logger.error(f"Failed to create Facebook AdSet: {e}")
        raise

def batch_create_ads(api: Any, fb_account_id: str, campaign_id: uuid.UUID, creative_responses: List[Dict[str, Any]], db: Session) -> Dict[str, str]:
    """Uses the Facebook Batch API to associate successfully created creatives with the target AdSet."""
    from facebook_business.adobjects.ad import Ad
    
    # Get or Auto-Create Target AdSet ID from campaign kpi_targets
    try:
        target_adset_id = ensure_facebook_campaign_and_adset(api, fb_account_id, campaign_id, db)
    except Exception as e:
        logger.error(f"Failed to auto-create Facebook Campaign/AdSet: {e}", exc_info=True)
        return {}
    
    if not target_adset_id:
        logger.warning("Thiếu cấu hình 'facebook_adset_id' (Target AdSet) và không thể tự động tạo. Bỏ qua bước tạo Ads.")
        return {}
    ad_batch = api.new_batch()
    ad_responses = []
    
    def make_ad_success_callback(v_id):
        def callback(response):
            ad_id = None
            if hasattr(response, 'json'):
                try:
                    res_json = response.json()
                    ad_id = res_json.get('id') if isinstance(res_json, dict) else None
                except Exception:
                    pass
            if not ad_id:
                ad_id = response.get('id') if hasattr(response, 'get') else getattr(response, 'id', None)
            logger.info(f"Ad created successfully for variant {v_id}: Ad ID {ad_id}")
            ad_responses.append({
                "variant_id": v_id,
                "ad_id": ad_id,
                "error": None
            })
        return callback
    
    def make_ad_failure_callback(v_id):
        def callback(response):
            err_detail = response.json() if hasattr(response, 'json') else str(response)
            logger.error(f"Ad batch creation failed for variant {v_id}: {err_detail}")
            ad_responses.append({
                "variant_id": v_id,
                "ad_id": None,
                "error": response
            })
        return callback
        
    has_ads_to_create = False
    for cres in creative_responses:
        v_id = cres["variant_id"]
        c_id = cres["creative_id"]
        if not c_id:
            logger.warning(f"Skipping Ad creation for variant {v_id} due to creative creation failure.")
            continue
        
        has_ads_to_create = True
        ad = Ad(parent_id=fb_account_id)
        ad.update({
            'name': f"Ad_{v_id[:8]}",
            'adset_id': target_adset_id,
            'creative': {'creative_id': c_id},
            'status': 'PAUSED'
        })
        ad.remote_create(
            batch=ad_batch,
            success=make_ad_success_callback(v_id),
            failure=make_ad_failure_callback(v_id)
        )
        
    if has_ads_to_create:
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=2, min=4, max=60),
            retry=is_rate_limit_or_transient_error,
            reraise=True
        )
        def run_ad_batch():
            ad_batch.execute()
            
        try:
            run_ad_batch()
        except FacebookRequestError as fb_err:
            check_and_raise_if_disabled(fb_err, fb_account_id)
            raise
            
    return {ares["variant_id"]: ares["ad_id"] for ares in ad_responses if ares["ad_id"]}
