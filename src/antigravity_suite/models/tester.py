"""Model endpoint connectivity and latency tester."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request
from typing import Dict, Optional, Tuple


def test_model_endpoint(
    base_url: str,
    model_id: str,
    api_key: Optional[str] = None,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None,
    verify_ssl: bool = True,
    prompt: str = "ping",
) -> Tuple[bool, float, str]:
    """Tests a model endpoint with a minimal completion, returning (success, latency_ms, reply/error)."""
    clean_url = base_url.strip().rstrip("/")
    endpoint = clean_url if clean_url.endswith("/chat/completions") else f"{clean_url}/chat/completions"

    payload = json.dumps({
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 16,
        "stream": False,
    }).encode("utf-8")

    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Antigravity-Suite/1.0",
    }
    if api_key:
        req_headers["Authorization"] = f"Bearer {api_key}"
    if headers:
        req_headers.update(headers)

    ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    req = urllib.request.Request(endpoint, data=payload, headers=req_headers, method="POST")

    start_t = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                data = json.loads(raw)
                choices = data.get("choices", [])
                if choices and isinstance(choices, list):
                    first = choices[0]
                    content = (
                        first.get("message", {}).get("content")
                        or first.get("text")
                        or raw
                    )
                    return True, latency_ms, str(content).strip()
                return True, latency_ms, raw.strip()
            except json.JSONDecodeError:
                return True, latency_ms, raw.strip()
    except urllib.error.HTTPError as err:
        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        try:
            err_body = err.read().decode("utf-8", errors="replace")
            return False, latency_ms, f"HTTP {err.code}: {err_body}"
        except Exception:
            return False, latency_ms, f"HTTP {err.code}: {err.reason}"
    except Exception as err:
        latency_ms = round((time.perf_counter() - start_t) * 1000.0, 2)
        return False, latency_ms, str(err)


test_model_endpoint.__test__ = False

