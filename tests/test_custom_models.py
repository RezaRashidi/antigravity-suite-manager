"""Integration tests for Antigravity custom models core modules."""

import tempfile
import unittest
from pathlib import Path
from antigravity_suite.models import (
    apply_ide_proxy_url,
    enable_all_models,
    get_ide_proxy_url,
    load_config,
    parse_model_catalog,
    restore_ide_proxy_url,
    save_config,
    toggle_model,
)


class TestCustomModelsIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg_file = Path(self.tmp.name) / "custom_models.json"
        self.settings_file = Path(self.tmp.name) / "settings.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_full_models_workflow(self):
        # 1. Parse catalog
        raw_catalog = {
            "models": [
                {"name": "llama3.2:latest", "details": {"context_length": 8192}},
                {"name": "deepseek-r1:14b", "details": {"context_length": 65536}},
            ]
        }
        models = parse_model_catalog(raw_catalog)
        self.assertEqual(len(models), 2)
        self.assertTrue(models[1].capabilities["thinking"])

        # 2. Configure and select models
        cfg = {"version": 1, "providers": {"ollama": {"base_url": "http://127.0.0.1:11434"}}, "models": []}
        enable_all_models(cfg, "ollama", models)
        self.assertEqual(len(cfg["models"]), 2)
        self.assertTrue(cfg["models"][0]["enabled"])

        # 3. Toggle a model off
        toggle_model(cfg, "models/ollama-llama3.2:latest", enabled=False)
        self.assertFalse(cfg["models"][0]["enabled"])

        # 4. Save and reload config
        save_config(cfg, self.cfg_file)
        reloaded = load_config(self.cfg_file)
        self.assertEqual(len(reloaded["models"]), 2)
        self.assertFalse(reloaded["models"][0]["enabled"])

        # 5. IDE settings apply and restore
        apply_ide_proxy_url("http://127.0.0.1:50999", self.settings_file)
        self.assertEqual(get_ide_proxy_url(self.settings_file), "http://127.0.0.1:50999")
        restore_ide_proxy_url(self.settings_file)
        self.assertIsNone(get_ide_proxy_url(self.settings_file))
