"""Unit tests for Multi-Account models, tokens, and vault."""
import unittest
from pathlib import Path
import tempfile
from antigravity_suite.multi_account.models import AccountRecord, AccountToken, QuotaBucket
from antigravity_suite.multi_account.tokens import is_token_expired, parse_jwt_claims
from antigravity_suite.multi_account.vault import save_account_to_vault, load_account_from_file, remove_account_from_vault
from antigravity_suite.multi_account.bindings import bind_cascade_to_account, get_account_for_cascade, load_bindings, unbind_cascade
from antigravity_suite.multi_account.quota import parse_quota_buckets

class TestMultiAccountModels(unittest.TestCase):
    def test_models_serialization(self):
        tok = AccountToken(access_token="tok123", refresh_token="ref123", expiry="2026-10-25T00:00:00Z")
        q1 = QuotaBucket(family="gemini", window="weekly", fraction=0.75, reset_time="2026-10-25T00:00:00Z")
        rec = AccountRecord(email="test@example.com", name="Test User", token=tok, quotas=[q1], is_primary=True)
        d = rec.to_dict()
        self.assertEqual(d["email"], "test@example.com")
        self.assertTrue(d["is_primary"])
        self.assertEqual(q1.percent(), 75.0)

    def test_parse_jwt_and_expiration(self):
        dummy_jwt = "eyJhbGciOiJub25lIn0.eyJlbWFpbCI6InVzZXJAZG9tYWluLmNvbSIsInN1YiI6IjEyMzQ1In0."
        claims = parse_jwt_claims(dummy_jwt)
        self.assertEqual(claims.get("email"), "user@domain.com")
        self.assertTrue(is_token_expired(""))
        self.assertTrue(is_token_expired("2020-01-01T00:00:00Z"))
        self.assertFalse(is_token_expired("2099-01-01T00:00:00Z"))

    def test_vault_and_bindings_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            tok = AccountToken(access_token="ya29.test", refresh_token="1//test", expiry="2099-01-01T00:00:00Z")
            rec = AccountRecord(email="roundtrip@test.com", name="Round Trip", token=tok)
            saved_path = p / "roundtrip@test.com.json"
            import json; saved_path.write_text(json.dumps(rec.to_dict()))
            loaded = load_account_from_file(saved_path)
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.email, "roundtrip@test.com")

    def test_parse_quota_buckets(self):
        groups = [{"displayName": "Gemini Limits", "buckets": [{"window": "Weekly", "remainingFraction": 0.85}, {"window": "5h", "remainingFraction": 1.0}]}]
        buckets = parse_quota_buckets(groups)
        self.assertEqual(len(buckets), 2)
        self.assertEqual(buckets[0].percent(), 85.0)

    def test_get_oauth_credentials_prioritizes_consumer_client(self):
        from antigravity_suite.multi_account.tokens import get_oauth_credentials
        cid, sec = get_oauth_credentials()
        self.assertIn("1071006060591", cid)
        self.assertNotIn("884354919052", cid)
        self.assertTrue(sec.startswith("GOCSPX-"))
        self.assertEqual(len(sec), 35)

    def test_login_lock_lifecycle(self):
        import os
        from antigravity_suite.multi_account.oauth import acquire_login_lock, release_login_lock
        from antigravity_suite.multi_account.vault import get_accounts_dir
        acquire_login_lock()
        pid_file = get_accounts_dir() / "login.pid"
        self.assertTrue(pid_file.exists())
        self.assertEqual(int(pid_file.read_text().strip()), os.getpid())
        release_login_lock()
        self.assertFalse(pid_file.exists())
