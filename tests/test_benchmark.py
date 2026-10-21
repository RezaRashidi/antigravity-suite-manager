"""
Unit tests for the Antigravity AI performance and latency benchmark subsystem.
"""

import unittest
from antigravity_suite.benchmark.models import (
    BenchmarkReport,
    ContextMetric,
    NetworkMetric,
    ProcessMetric,
)
from antigravity_suite.benchmark.evaluator import evaluate_bottlenecks
from antigravity_suite.benchmark.reporter import format_report
from antigravity_suite.benchmark.runner import run_benchmark


class TestBenchmarkSubsystem(unittest.TestCase):
    def test_models_serialization(self):
        net = NetworkMetric(
            host="example.com",
            dns_ipv4_ms=1.5,
            tcp_ipv4_ms=10.0,
            tls_handshake_ms=25.0,
            alpn_protocol="h2",
            ipv6_blackhole=False,
        )
        ctx = ContextMetric(
            mcp_servers=2,
            mcp_eager_tools=5,
            mcp_lazy_tools=10,
            total_mcp_tools=15,
            active_skills=4,
            active_rules=2,
            estimated_prompt_tokens=3500,
        )
        proc = ProcessMetric(
            pid=1234,
            client_type="hub",
            gomaxprocs=4,
            rss_mb=256.0,
            port=33547,
            loopback_ping_ms=0.5,
        )
        report = BenchmarkReport(
            networks=[net],
            context=ctx,
            processes=[proc],
            speed_tier="OPTIMAL",
            estimated_ttft_sec="1.5s - 3.0s",
        )
        d = report.to_dict()
        self.assertEqual(d["speed_tier"], "OPTIMAL")
        self.assertEqual(len(d["networks"]), 1)
        self.assertEqual(d["context"]["total_mcp_tools"], 15)
        self.assertEqual(d["processes"][0]["pid"], 1234)

    def test_evaluator_ipv6_blackhole_detection(self):
        net = NetworkMetric(
            host="daily-cloudcode-pa.googleapis.com",
            ipv6_blackhole=True,
            tcp_ipv4_ms=20.0,
        )
        ctx = ContextMetric(estimated_prompt_tokens=2000)
        tier, ttft, b_list, r_list = evaluate_bottlenecks([net], ctx, [])
        self.assertIn("BOTTLENECKED", tier)
        self.assertTrue(any("IPv6 Blackhole" in b for b in b_list))
        self.assertTrue(any("sysctl" in r for r in r_list))

    def test_evaluator_prompt_bloat_detection(self):
        net = NetworkMetric(host="cloudcode-pa.googleapis.com", tcp_ipv4_ms=15.0)
        ctx = ContextMetric(
            total_mcp_tools=200,
            active_skills=50,
            estimated_prompt_tokens=25000,
        )
        tier, ttft, b_list, r_list = evaluate_bottlenecks([net], ctx, [])
        self.assertTrue(any("prefill bloat" in b for b in b_list))
        self.assertTrue(any("lazy-loaded" in r for r in r_list))

    def test_format_report(self):
        report = BenchmarkReport(
            networks=[NetworkMetric(host="test.com", tcp_ipv4_ms=12.3)],
            context=ContextMetric(mcp_servers=1, total_mcp_tools=5),
            processes=[ProcessMetric(pid=999, client_type="ide", port=3000)],
            speed_tier="OPTIMAL",
            estimated_ttft_sec="2.0s",
        )
        text = format_report(report)
        self.assertIn("=== Antigravity AI Response Speed & Latency Benchmark ===", text)
        self.assertIn("OPTIMAL", text)
        self.assertIn("test.com", text)
        self.assertIn("999", text)

    def test_run_benchmark_smoke(self):
        report = run_benchmark(skip_network=True, skip_prompt=True)
        self.assertIsInstance(report, BenchmarkReport)
        self.assertIsNotNone(report.context)
        self.assertIsNotNone(report.env)

    def test_environment_and_account_smoke(self):
        from antigravity_suite.benchmark import collect_environment, collect_accounts_and_quotas
        env = collect_environment()
        self.assertIsNotNone(env.os_name)
        accs = collect_accounts_and_quotas()
        self.assertIsInstance(accs, list)

    def test_recent_messages_step_latency(self):
        import tempfile
        from pathlib import Path
        from antigravity_suite.benchmark.step_latency import collect_recent_message_latencies
        from antigravity_suite.benchmark.reporter_history import format_recent_messages_section
        with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as tf:
            tf.write('{"step_index":1,"type":"USER_INPUT","source":"USER_EXPLICIT","created_at":"2026-10-21T10:00:00Z","content":"Hello"}\n')
            tf.write('{"step_index":2,"type":"PLANNER_RESPONSE","source":"MODEL","created_at":"2026-10-21T10:00:02Z"}\n')
            tf.write('{"step_index":3,"type":"GENERIC","source":"MODEL","created_at":"2026-10-21T10:00:05Z"}\n')
            tf.write('{"step_index":4,"type":"USER_INPUT","source":"USER_EXPLICIT","created_at":"2026-10-21T10:01:00Z","content":"Next"}\n')
            tf.write('{"step_index":5,"type":"PLANNER_RESPONSE","source":"MODEL","created_at":"2026-10-21T10:01:01Z"}\n')
            t_path = tf.name
        try:
            res = collect_recent_message_latencies(count=2, transcript_path=t_path)
            self.assertEqual(len(res), 2)
            self.assertEqual(res[0].ttft_sec, 2.0)
            self.assertEqual(res[0].total_duration_sec, 5.0)
            self.assertEqual(len(res[0].steps), 2)
            self.assertEqual(res[1].ttft_sec, 1.0)
            formatted = format_recent_messages_section(res, all_steps=True)
            text = "\n".join(formatted)
            self.assertIn("Recent Message Telemetry", text)
            self.assertIn("Message 01/02", text)
            self.assertIn("Message 02/02", text)
            self.assertIn("Initial Model Response", text)
        finally:
            Path(t_path).unlink(missing_ok=True)

    def test_cli_main_smoke(self):
        from antigravity_suite.benchmark.cli import main
        code = main(["--skip-network", "--skip-prompt", "--messages", "2", "--all-steps"])
        self.assertIn(code, (0, 1))


if __name__ == "__main__":
    unittest.main()
