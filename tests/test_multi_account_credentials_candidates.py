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
        target = "884354919052-36trc1jjb3tguiac32ov6cod268c5blh.apps.googleusercontent.com"
        creds = get_all_oauth_credentials(preferred_client_id=target)
        self.assertEqual(creds[0][0], target)


if __name__ == "__main__":
    unittest.main()

