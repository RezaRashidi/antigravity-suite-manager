"""HTTP discovery client for fetching remote model catalogs."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


def get_discovery_urls(base_url: str) -> List[str]:
    """Generates candidate URLs for model discovery."""
    clean = base_url.strip().rstrip("/")
    if clean.endswith("/models"):
        return [clean]
    if clean.endswith("/v1"):
        return [f"{clean}/models"]
    return [f"{clean}/models", f"{clean}/v1/models"]


def fetch_models(
    base_url: str,
    api_key: Optional[str] = None,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None,
    verify_ssl: bool = True,
) -> Any:
    """Fetches model catalog from candidate endpoints using Bearer auth."""
    urls = get_discovery_urls(base_url)
    req_headers = {"Accept": "application/json", "User-Agent": "Antigravity-Suite/1.0"}
    if api_key:
        req_headers["Authorization"] = f"Bearer {api_key}"
    if headers:
        req_headers.update(headers)

    ctx = ssl.create_default_context() if verify_ssl else ssl._create_unverified_context()
    last_error: Optional[Exception] = None

    for url in urls:
        req = urllib.request.Request(url, headers=req_headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                status = resp.status if hasattr(resp, "status") else resp.getcode()
                if 200 <= status < 300:
                    raw_body = resp.read().decode("utf-8")
                    return json.loads(raw_body)
        except urllib.error.HTTPError as err:
            last_error = err
            if err.code == 404:
                continue
            raise
        except Exception as err:
            last_error = err
            continue

    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to discover models from {base_url}")
