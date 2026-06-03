from facebook_business.api import FacebookAdsApi

# Try initializing without app_id and app_secret
try:
    api = FacebookAdsApi.init(access_token="foo")
    print("Init success!")
except Exception as e:
    print("Init failed:", e)
