"""
Unit tests for deterministic constructible workspace fallback titles.
"""

import unittest
from antigravity_suite.history.title_fallback import (
    get_constructible_fallback_titles,
    is_workspace_fallback_title,
)
from antigravity_suite.history.title_resolver import (
    pick_first_valid_title,
    resolve_best_title,
)


class TestTitleFallbackConstructible(unittest.TestCase):
    def test_constructible_fallback_generation(self):
        fallbacks = get_constructible_fallback_titles(workspace="Odirect")
        self.assertIn("odirect chat", fallbacks)
        self.assertIn("conversation", fallbacks)
        self.assertNotIn("how to fork a chat", fallbacks)

    def test_is_workspace_fallback_title(self):
        # Generic placeholders
        self.assertTrue(is_workspace_fallback_title("Conversation"))
        self.assertTrue(is_workspace_fallback_title("Untitled Conversation"))
        self.assertTrue(is_workspace_fallback_title("Desktop: My Project"))

        # Workspace fallback matching
        self.assertTrue(is_workspace_fallback_title("Odirect Chat", "Odirect"))
        self.assertTrue(is_workspace_fallback_title(".Antigravity Suite Manager Chat", ".antigravity-suite-manager"))

        # Authentic titles ending in 'Chat' must NOT be classified as fallback
        self.assertFalse(is_workspace_fallback_title("How To Fork A Chat", "Odirect"))
        self.assertFalse(is_workspace_fallback_title("Chat with PDF", "Odirect"))
        self.assertFalse(is_workspace_fallback_title("Fast Live Chat Implementation", "Odirect"))

    def test_pick_first_valid_title_preserves_authentic_chat_titles(self):
        cands = [
            "Odirect Chat",             # Fallback
            "How To Fork A Chat",       # Authentic candidate
            "Conversation",             # Generic
        ]
        winner = pick_first_valid_title(cands, prompt_cands=set(), fallback_workspace="Odirect")
        self.assertEqual(winner, "How To Fork A Chat")

    def test_resolve_best_title_selection(self):
        title, src = resolve_best_title(
            existing_candidates=["Odirect Chat"],
            llm_candidates=["How To Fork A Chat"],
            clean_artifact_title=None,
            prompt_cands=set(),
            fallback_workspace="Odirect",
        )
        self.assertEqual(title, "How To Fork A Chat")
        self.assertEqual(src, "llm_summary")
