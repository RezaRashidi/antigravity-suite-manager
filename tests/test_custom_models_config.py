"""Unit tests for custom models configuration management."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from antigravity_suite.models.config import (
    get_custom_models_path,
    get_default_config,
    load_config,
    save_config,
)


class TestCustomModelsConfig(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cfg_file = Path(self.tmp_dir.name) / "custom_models.json"

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_default_config_structure(self):
        cfg = get_default_config()
        self.assertEqual(cfg["version"], 1)
        self.assertEqual(cfg["providers"], {})
        self.assertEqual(cfg["models"], [])

    def test_get_custom_models_path_env(self):
        os.environ["ANTIGRAVITY_CUSTOM_MODELS_PATH"] = str(self.cfg_file)
        try:
            self.assertEqual(get_custom_models_path(), self.cfg_file)
        finally:
            os.environ.pop("ANTIGRAVITY_CUSTOM_MODELS_PATH", None)

    def test_load_non_existent_and_corrupt(self):
        self.assertEqual(load_config(self.cfg_file)["version"], 1)
        self.cfg_file.write_text("{corrupt json")
        self.assertEqual(load_config(self.cfg_file)["models"], [])

    def test_save_and_load_roundtrip_with_permissions(self):
        data = {
            "version": 1,
            "providers": {"ollama": {"base_url": "http://localhost:11434"}},
            "models": [{"id": "models/ollama-llama3", "enabled": True}],
        }
        saved_path = save_config(data, self.cfg_file)
        self.assertTrue(saved_path.is_file())
        mode = stat.S_IMODE(os.stat(saved_path).st_mode)
        self.assertEqual(mode, 0o600)
        loaded = load_config(saved_path)
        self.assertEqual(loaded["providers"]["ollama"]["base_url"], "http://localhost:11434")
        self.assertEqual(len(loaded["models"]), 1)
