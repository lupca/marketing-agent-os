import urllib.request
import json
import urllib.error

data = json.dumps({"mode": "live"}).encode('utf-8')
req = urllib.request.Request('http://localhost:8000/api/cockpit/execution-mode', data=data, headers={'Content-Type': 'application/json'})
try:
    res = urllib.request.urlopen(req)
    print(res.read().decode())
except urllib.error.HTTPError as e:
    print(f"Error: {e.code}")
    print(e.read().decode())
