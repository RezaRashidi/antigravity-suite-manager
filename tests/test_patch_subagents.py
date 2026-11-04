"""
Unit tests for Subagent Dynamic Multi-Account & Swarm Patch.
"""

import subprocess
import unittest
from pathlib import Path


class TestPatchSubagents(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.patch_sh = self.root / "bin/lib/sh/patch_subagents.sh"
        self.unpatch_sh = self.root / "bin/lib/sh/unpatch_subagents.sh"
        self.alloc_js = self.root / "bin/lib/patch/router/subagent_allocator.js"
        self.render_py = self.root / "src/antigravity_suite/detect/control_center_render.py"
        self.dispatch_py = self.root / "src/antigravity_suite/detect/control_center_dispatch.py"
        self.ctrl_sub_py = self.root / "src/antigravity_suite/detect/control_center_subagents.py"
        self.plugin_rule = self.root / "plugins/subagent-swarm/rules/AGENTS.md"

    def test_scripts_bounded_size(self):
        for f_path in [self.patch_sh, self.unpatch_sh, self.ctrl_sub_py]:
            self.assertTrue(f_path.is_file(), f"{f_path.name} must exist")
            with open(f_path, "r", encoding="utf-8") as fp:
                lines = len(fp.readlines())
            self.assertLessEqual(lines, 100, f"{f_path.name} is {lines} lines (must be <= 100)")

    def test_control_center_renders_and_dispatches_sa(self):
        with open(self.render_py, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[SA] Subagents", content)

        with open(self.dispatch_py, "r", encoding="utf-8") as f:
            d_content = f.read()
        self.assertIn('"SA"', d_content)
        self.assertIn("handle_control_center_subagents_patch", d_content)

    def test_plugin_and_rules_exist(self):
        self.assertTrue(self.plugin_rule.is_file(), "Swarm AGENTS.md rule must exist")
        with open(self.plugin_rule, "r", encoding="utf-8") as f:
            rule_text = f.read()
        self.assertIn("DeepInvestigator", rule_text)
        self.assertIn("DeepCoder", rule_text)
        self.assertIn("invoke_subagent", rule_text)

    def test_node_allocator_suite(self):
        res = subprocess.run(
            ["node", str(self.root / "tests/test_subagent_router.js")],
            capture_output=True,
            text=True
        )
        self.assertEqual(res.returncode, 0, f"Node subagent test failed: {res.stderr}")
        self.assertIn("All Subagent Allocator tests passed successfully!", res.stdout)
