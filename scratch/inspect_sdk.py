from facebook_business.api import FacebookResponse

resp = FacebookResponse(body='{"id": "123"}', http_status=200, headers={})
print("json attribute type:", type(resp.json))
print("json() result:", resp.json())
print("body attribute:", resp.body)
