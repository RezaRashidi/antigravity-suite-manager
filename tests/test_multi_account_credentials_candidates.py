import unittest
from antigravity_suite.multi_account.credentials import get_all_oauth_credentials, get_oauth_credentials
from antigravity_suite.multi_account.tokens import refresh_access_token


class TestOAuthCandidates(unittest.TestCase):
    def test_get_all_oauth_credentials(self):
        creds = get_all_oauth_credentials()
        self.assertGreater(len(creds), 0)
        cids = [c[0] for c in creds]
        self.assertTrue(any("1071006060591" in cid for cid in cids))
        self.assertTrue(any("884354919052" in cid for cid in cids))

    def test_preferred_client_id(self):
        creds_orig = get_all_oauth_credentials()
        target = next(c[0] for c in creds_orig if "884354919052" in c[0])
        creds = get_all_oauth_credentials(preferred_client_id=target)
        self.assertEqual(creds[0][0], target)

    def test_default_is_consumer_client_id(self):
        cid, sec = get_oauth_credentials()
        self.assertIn("1071006060591", cid)
        self.assertNotIn("884354919052", cid)
        self.assertTrue(sec.startswith("GOCSPX-"))
        self.assertEqual(len(sec), 35)

    def test_first_candidate_is_consumer_when_no_preference(self):
        creds = get_all_oauth_credentials()
        self.assertIn("1071006060591", creds[0][0])


if __name__ == "__main__":
    unittest.main()

