# core/integrations/fb_client.py
import logging
import uuid
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adsinsights import AdsInsights
from facebook_business.exceptions import FacebookRequestError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from core.models import SocialAccount, AdMapper

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

def get_fb_client(workspace_id: str, db: Session) -> Tuple[FacebookAdsApi, str]:
    """
    Factory function that retrieves credentials from the database and initializes FacebookAdsApi.
    Returns a tuple of (api_instance, fb_account_id).
    """
    try:
        ws_uuid = uuid.UUID(str(workspace_id))
    except ValueError as val_err:
        raise ValueError(f"Invalid workspace_id UUID format: {workspace_id}") from val_err

    # Query active social account for Facebook
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

    if not account.app_id or not account.app_secret or not account.access_token:
        raise ValueError(
            f"Facebook credentials (app_id, app_secret, access_token) are not fully configured "
            f"for social account ID {account.id}."
        )

    # Initialize Facebook SDK default API
    try:
        api = FacebookAdsApi.init(
            app_id=account.app_id,
            app_secret=account.app_secret,
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

def init_facebook_client(workspace_id: str, db: Session) -> Tuple[Any, str, bool]:
    """Helper to initialize the Facebook Ads client with workspace credentials."""
    use_real_fb = True
    try:
        api, fb_account_id = get_fb_client(workspace_id, db)
        if not fb_account_id.startswith('act_'):
            fb_account_id = f"act_{fb_account_id}"
        
        # Check for mock/dummy credentials
        if not api or not api.access_token or "dummy" in api.access_token:
            logger.warning("Mocking Facebook Ads API due to dummy credentials.")
            use_real_fb = False
        return api, fb_account_id, use_real_fb
    except FacebookAccountDisabledError:
        raise
    except Exception as cred_err:
        logger.warning(f"Could not initialize Facebook API ({cred_err}). Falling back to mock publishing.")
        return None, "act_10509876_mock", False

def batch_create_creatives(api: Any, fb_account_id: str, workspace_id: str, variants: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Uses the Facebook Batch API to upload the dynamic creatives in a single call."""
    from facebook_business.adobjects.adcreative import AdCreative
    from core.utils import get_integration_config
    
    creative_batch = api.new_batch()
    creative_responses = []
    
    def make_creative_success_callback(v_id):
        def callback(response):
            c_id = response.get('id') if hasattr(response, 'get') else getattr(response, 'id', None)
            logger.info(f"AdCreative created successfully for variant {v_id}: Creative ID {c_id}")
            creative_responses.append({
                "variant_id": v_id,
                "creative_id": c_id,
                "error": None
            })
        return callback
    
    def make_creative_failure_callback(v_id):
        def callback(response):
            logger.error(f"AdCreative batch creation failed for variant {v_id}: {response}")
            creative_responses.append({
                "variant_id": v_id,
                "creative_id": None,
                "error": response
            })
        return callback
    
    integration_configs = get_integration_config(workspace_id, "upload-post")
    page_id = integration_configs.get("facebook_page_id") or "10509876"
    
    for v in variants:
        v_id = v["variant_id"]
        copy = v.get("adapted_copy", "")
        angle_name = v.get("angle_name", "Creative")
        
        creative = AdCreative(parent_id=fb_account_id)
        creative.update({
            'name': f"Creative_{v_id[:8]}_{angle_name}",
            'title': f"Top VN Sports - {angle_name}",
            'body': copy,
            'object_story_spec': {
                'page_id': page_id,
                'link_data': {
                    'message': copy,
                    'link': 'https://facebook.com/topvnsports',
                    'name': f"Top VN Sports - {angle_name}"
                }
            }
        })
        creative.remote_create(
            batch=creative_batch,
            success=make_creative_success_callback(v_id),
            failure=make_creative_failure_callback(v_id)
        )
    
    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        retry=is_rate_limit_or_transient_error,
        reraise=True
    )
    def run_creative_batch():
        creative_batch.execute()
        
    try:
        run_creative_batch()
    except FacebookRequestError as fb_err:
        check_and_raise_if_disabled(fb_err, fb_account_id)
        raise
        
    return creative_responses

def batch_create_ads(api: Any, fb_account_id: str, campaign_id: uuid.UUID, creative_responses: List[Dict[str, Any]], db: Session) -> Dict[str, str]:
    """Uses the Facebook Batch API to associate successfully created creatives with the target AdSet."""
    from facebook_business.adobjects.ad import Ad
    from core.models import MarketingCampaign
    
    # Get Target AdSet ID from campaign kpi_targets
    campaign = db.query(MarketingCampaign).filter_by(id=campaign_id).first()
    target_adset_id = None
    if campaign and campaign.kpi_targets:
        target_adset_id = campaign.kpi_targets.get("facebook_adset_id")
    
    if not target_adset_id:
        target_adset_id = "12021111002233" # Fallback sandbox adset ID
        
    ad_batch = api.new_batch()
    ad_responses = []
    
    def make_ad_success_callback(v_id):
        def callback(response):
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
            logger.error(f"Ad batch creation failed for variant {v_id}: {response}")
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
