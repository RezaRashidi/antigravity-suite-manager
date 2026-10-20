"""Unit tests for the Antigravity Multi-Account subsystem."""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from antigravity_suite.multi_account.bindings import (
    bind_cascade_to_account, get_account_for_cascade, load_bindings,
    unbind_cascade
)
from antigravity_suite.multi_account.models import (
    AccountRecord, AccountToken, ConversationBinding, QuotaBucket
)
from antigravity_suite.multi_account.proxy_core import (
    extract_cascade_id, prepare_upstream_headers, resolve_account_token
)
from antigravity_suite.multi_account.proxy_server import run_proxy_server
from antigravity_suite.multi_account.quota import parse_quota_buckets
from antigravity_suite.multi_account.service import is_proxy_running
from antigravity_suite.multi_account.tokens import (
    is_token_expired, parse_jwt_claims
)
from antigravity_suite.multi_account.vault import (
    list_vault_accounts, load_account_from_file, remove_account_from_vault,
    save_account_to_vault
)


def test_models_serialization():
    tok = AccountToken(access_token="tok123", refresh_token="ref123", expiry="2026-10-25T00:00:00Z")
    q1 = QuotaBucket(family="gemini", window="weekly", fraction=0.75, reset_time="2026-10-25T00:00:00Z")
    rec = AccountRecord(
        email="test@example.com",
        name="Test User",
        token=tok,
        quotas=[q1],
        is_primary=True,
    )
    d = rec.to_dict()
    assert d["email"] == "test@example.com"
    assert d["is_primary"] is True
    assert d["quotas"][0]["family"] == "gemini"
    assert q1.percent() == 75.0


def test_parse_jwt_claims():
    # Header: {"alg":"none"}, Payload: {"email":"user@domain.com","name":"Domain User","sub":"12345"}
    dummy_jwt = "eyJhbGciOiJub25lIn0.eyJlbWFpbCI6InVzZXJAZG9tYWluLmNvbSIsIm5hbWUiOiJEb21haW4gVXNlciIsInN1YiI6IjEyMzQ1In0."
    claims = parse_jwt_claims(dummy_jwt)
    assert claims.get("email") == "user@domain.com"
    assert claims.get("sub") == "12345"


def test_is_token_expired():
    assert is_token_expired("") is True
    assert is_token_expired("2020-01-01T00:00:00Z") is True
    assert is_token_expired("2099-01-01T00:00:00Z") is False


def test_vault_and_bindings_roundtrip(tmp_path, monkeypatch):
    test_dir = tmp_path / "accounts"
    test_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "antigravity_suite.multi_account.vault.get_accounts_dir",
        lambda: test_dir,
    )
    monkeypatch.setattr(
        "antigravity_suite.multi_account.bindings.get_bindings_file",
        lambda: test_dir / "bindings.json",
    )

    tok = AccountToken(access_token="ya29.test", refresh_token="1//test", expiry="2099-01-01T00:00:00Z")
    rec = AccountRecord(email="roundtrip@test.com", name="Round Trip", token=tok)
    saved_path = save_account_to_vault(rec)
    assert saved_path.is_file()

    loaded = load_account_from_file(saved_path)
    assert loaded is not None
    assert loaded.email == "roundtrip@test.com"

    # Test bindings
    bind_cascade_to_account("cascade-abc", "roundtrip@test.com", "gemini-3.8-flash")
    assert get_account_for_cascade("cascade-abc") == "roundtrip@test.com"

    all_bindings = load_bindings()
    assert "cascade-abc" in all_bindings
    assert all_bindings["cascade-abc"].model == "gemini-3.8-flash"

    unbind_cascade("cascade-abc")
    assert get_account_for_cascade("cascade-abc") is None

    assert remove_account_from_vault("roundtrip@test.com") is True
    assert not saved_path.is_file()


def test_extract_cascade_id():
    b1 = b'{"cascadeId":"cascade-999","model":"gemini"}'
    assert extract_cascade_id(b1) == "cascade-999"

    b2 = b'{"conversationId":"conv-123"}'
    assert extract_cascade_id(b2) == "conv-123"

    b3 = b"some raw binary with embedded \"cascadeId\": \"found-it-55\""
    assert extract_cascade_id(b3) == "found-it-55"

    assert extract_cascade_id(b"") is None


def test_prepare_upstream_headers():
    in_h = {
        "Host": "127.0.0.1:41999",
        "Authorization": "Bearer old_token",
        "Content-Length": "123",
        "User-Agent": "Antigravity/2.0",
    }
    out_h = prepare_upstream_headers(in_h, "new_secret_token", "daily-cloudcode-pa.googleapis.com")
    assert out_h["Host"] == "daily-cloudcode-pa.googleapis.com"
    assert out_h["Authorization"] == "Bearer new_secret_token"
    assert "Content-Length" not in out_h


def test_parse_quota_buckets():
    groups = [
        {
            "displayName": "Gemini Limits",
            "buckets": [
                {"window": "Weekly", "remainingFraction": 0.85, "resetTime": "2026-10-25T00:00:00Z"},
                {"window": "5h", "remainingFraction": 1.0, "resetTime": "2026-10-21T00:00:00Z"},
            ],
        },
        {
            "displayName": "Claude & GPT Limits",
            "buckets": [
                {"window": "Weekly", "remainingFraction": 0.40, "resetTime": "2026-10-25T00:00:00Z"},
            ],
        },
    ]
    buckets = parse_quota_buckets(groups)
    assert len(buckets) == 3
    assert buckets[0].family == "gemini"
    assert buckets[0].window == "weekly"
    assert buckets[0].percent() == 85.0
    assert buckets[1].family == "gemini"
    assert buckets[1].window == "5h"
    assert buckets[2].family == "claude"
    assert buckets[2].percent() == 40.0


def test_proxy_server_healthz():
    server = run_proxy_server(port=41998)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    try:
        assert is_proxy_running(port=41998) is True
    finally:
        server.shutdown()
        server.server_close()
