"""Tests for read-only token usage, Cache Hit Rate, and USD cost reporting."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from antigravity_suite.usage.pricing import calculate_turn_cost, extract_models_dev_rates, load_price_table, normalize_model_key
from antigravity_suite.usage.scanner import scan_usage


class TestUsageReport(unittest.TestCase):
    def test_normalize_model_key_and_extract_models_dev(self):
        self.assertEqual(normalize_model_key("gemini-4-hydrogen-high"), "gemini-4-hydrogen")
        self.assertEqual(normalize_model_key("MODEL_VERTEX_CLAUDE_SONNET_4_5"), "claude-sonnet-4-5")

        sample_api = {
            "google-vertex": {
                "models": {
                    "gemini-3-pro": {
                        "name": "Gemini 3 Pro",
                        "cost": {"input": 2.0, "cache_read": 0.2, "output": 12.0},
                        "limit": {"context": 1_048_576},
                    }
                }
            }
        }
        rates = extract_models_dev_rates(sample_api)
        self.assertIn("gemini-3-pro", rates)
        self.assertEqual(rates["gemini-3-pro"]["cache_read"], 0.2)

    def test_scan_usage_desktop_transcripts_and_bindings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            brain = root / "brain"
            c1_logs = brain / "11111111-1111-1111-1111-111111111111" / ".system_generated" / "logs"
            c2_logs = brain / "22222222-2222-2222-2222-222222222222" / ".system_generated" / "logs"
            c1_logs.mkdir(parents=True)
            c2_logs.mkdir(parents=True)

            # Includes: historical row without tokens, Desktop step 1 with model, step 3 with model=None
            # inheriting model + additive cache_read_tokens > input_tokens, and duplicate step_index.
            (c1_logs / "transcript.jsonl").write_text(
                "\n".join([
                    json.dumps({"step_index": 0, "type": "USER_INPUT", "created_at": "2026-10-01T10:00:00Z"}),
                    json.dumps({"step_index": 1, "model": "gemini-4-hydrogen-high", "input_tokens": 20000, "cache_read_tokens": 0, "output_tokens": 500, "created_at": "2026-11-28T08:00:00Z"}),
                    json.dumps({"step_index": 3, "model": None, "input_tokens": 3000, "cache_read_tokens": 17000, "output_tokens": 200, "created_at": "2026-11-28T09:00:00Z"}),
                    json.dumps({"step_index": 3, "model": None, "input_tokens": 3000, "cache_read_tokens": 17000, "output_tokens": 200, "created_at": "2026-11-28T09:00:00Z"}),
                ]) + "\n",
                encoding="utf-8",
            )
            # Older turn outside 7d window (20 days ago)
            (c2_logs / "transcript.jsonl").write_text(
                json.dumps({"step_index": 1, "model": "claude-sonnet-4-5", "input_tokens": 10000, "cache_read_tokens": 40000, "output_tokens": 1000, "created_at": "2026-11-08T10:00:00Z"}) + "\n",
                encoding="utf-8",
            )

            bindings_path = root / "bindings.json"
            bindings_path.write_text(json.dumps({
                "11111111-1111-1111-1111-111111111111": {"email": "user1@example.com"},
                "22222222-2222-2222-2222-222222222222": {"email": "user2@example.com"},
                "__active_account": "user1@example.com",
            }), encoding="utf-8")

            now_local = datetime(2026, 11, 28, 12, 0, tzinfo=timezone.utc).astimezone()
            res = scan_usage(
                days=7,
                brain_dir=brain,
                bindings_file=bindings_path,
                allow_network=False,
                price_cache_file=root / "nonexistent_prices.json",
                now_local=now_local,
            )

            self.assertEqual(res["totals"]["turns"], 2)
            self.assertEqual(res["totals"]["input_tokens"], 23000)
            self.assertEqual(res["totals"]["cache_read_tokens"], 17000)
            self.assertEqual(res["totals"]["output_tokens"], 700)
            self.assertAlmostEqual(res["totals"]["cache_hit_rate"], 42.5, places=1)
            self.assertGreater(res["totals"]["cost_usd"], 0.0)
            self.assertGreater(res["totals"]["cache_savings_usd"], 0.0)

            self.assertEqual(len(res["by_account"]), 1)
            self.assertEqual(res["by_account"][0]["account"], "user1@example.com")
            self.assertEqual(res["by_model"][0]["model"], "gemini-4-hydrogen-high")

            # All time window still counts user2's turn
            self.assertEqual(res["windows"]["all"]["turns"], 3)
            self.assertEqual(res["windows"]["7d"]["turns"], 2)

            table = load_price_table(allow_network=False, cache_file=root / "nonexistent_prices.json")
            c = calculate_turn_cost("claude-opus-4-6", 1_000_000, 0, 1_000_000, table)
            self.assertAlmostEqual(c["total_cost"], 30.0, places=3)


if __name__ == "__main__":
    unittest.main()
