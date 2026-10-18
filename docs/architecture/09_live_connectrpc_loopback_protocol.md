# Live ConnectRPC Loopback Protocol

The Desktop App and IDE communicate with the Language Server via ConnectRPC (gRPC-Web over loopback TLS).

### 9.1 Zero-Restart Live Annotation Script

```python
#!/usr/bin/env python3
"""
Pushes real-time conversation title, pinned status, and archival state
directly into the running Go Language Server's in-memory index without restarting.
"""
import json
import ssl
import urllib.request

# 1. Discover loopback port dynamically: ss -tulpn | grep language_server
LS_PORT = 44711

# 2. Parse active CSRF token from command line arguments: ps aux | grep -- --csrf_token
CSRF_TOKEN = "b131a5c6-e151-430d-a7a2-05847ee8f030"

url = f"https://127.0.0.1:{LS_PORT}/exa.language_server_pb.LanguageServerService/UpdateConversationAnnotations"

payload = {
    "cascadeIds": ["7b382c83-e685-4637-84bc-4520cdfcb94c"],
    "annotations": {
        "title": "Performance Engineering Strategy: Load Test Scenario Design Catalog",
        "pinned": False,
        "archived": False
    }
}

ctx = ssl._create_unverified_context()
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Content-Type": "application/json",
        "x-codeium-csrf-token": CSRF_TOKEN
    }
)

with urllib.request.urlopen(req, context=ctx) as response:
    result = json.loads(response.read().decode("utf-8"))
    print("Response from Go Language Server:", result)
```

---
