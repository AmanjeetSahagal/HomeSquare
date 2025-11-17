import requests
from typing import List

BASE = "http://localhost:5050"
TEST_URL = "https://www.redfin.com/VA/Glen-Allen/5835-Shady-Hills-Way-23059/home/59613712"

endpoints: List[str] = [
    f"{BASE}/api/analyze_ai",
    f"{BASE}/api/analyze",
    f"{BASE}/analyze_ai",
    f"{BASE}/analyze",
]

payload = {"url": TEST_URL}
headers = {"Content-Type": "application/json", "Accept": "application/json"}

for ep in endpoints:
    print("\n=== Trying:", ep)
    try:
        resp = requests.post(ep, json=payload, headers=headers, timeout=60)
    except Exception as e:
        print("Request error:", e)
        continue

    print("Status:", resp.status_code)
    # Always show raw text to see Flask error pages if any
    print("Body:", (resp.text or "<empty>"))

    # Try to parse JSON only if server says it returned JSON
    ctype = resp.headers.get("Content-Type", "")
    if resp.ok and "application/json" in ctype:
        try:
            print("JSON:", resp.json())
            print("\nSUCCESS on:", ep)
            break
        except Exception as je:
            print("JSON parse error:", je)
    elif resp.status_code == 404:
        print("Hint: 404 means this route doesn't exist on the server. Check your Flask @app.route path and any blueprint url_prefix like '/api'.")
    elif resp.status_code == 405:
        print("Hint: 405 = method not allowed. Ensure your route has methods=['POST'].")
else:
    print("\nNo endpoint succeeded. Verify server is running and the route names match.")