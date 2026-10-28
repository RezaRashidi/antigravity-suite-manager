"""Unit tests for model selector and standard naming generator."""

import unittest
from antigravity_suite.models.parser import ModelInfo
from antigravity_suite.models.selector import (
    enable_all_models,
    enable_selected_models,
    make_standard_name,
    toggle_model,
)


class TestCustomModelsSelector(unittest.TestCase):
    def test_make_standard_name(self):
        self.assertEqual(make_standard_name("ollama", "llama3"), "models/ollama-llama3")
        self.assertEqual(make_standard_name("ollama", "models/ollama-llama3"), "models/ollama-llama3")
        self.assertEqual(make_standard_name("openai", "models/gpt-4o"), "models/openai-gpt-4o")

    def test_enable_all_models(self):
        catalog = [
            ModelInfo(id="m1", name="Model 1", context_length=8192),
            ModelInfo(id="m2", name="Model 2", context_length=16384),
        ]
        cfg = {"version": 1, "providers": {}, "models": []}
        updated = enable_all_models(cfg, "ollama", catalog)
        self.assertEqual(len(updated["models"]), 2)
        self.assertTrue(all(m["enabled"] for m in updated["models"]))
        self.assertEqual(updated["models"][0]["id"], "models/ollama-m1")

    def test_enable_selected_models(self):
        catalog = [
            ModelInfo(id="m1", name="Model 1"),
            ModelInfo(id="m2", name="Model 2"),
        ]
        cfg = {"version": 1, "providers": {}, "models": []}
        updated = enable_selected_models(cfg, "ollama", catalog, ["models/ollama-m2"])
        self.assertFalse(updated["models"][0]["enabled"])
        self.assertTrue(updated["models"][1]["enabled"])

    def test_toggle_model(self):
        cfg = {
            "version": 1,
            "models": [
                {"id": "models/ollama-m1", "model_id": "m1", "provider": "ollama", "enabled": True}
            ],
        }
        toggle_model(cfg, "models/ollama-m1")
        self.assertFalse(cfg["models"][0]["enabled"])
        toggle_model(cfg, "m1", provider="ollama", enabled=True)
        self.assertTrue(cfg["models"][0]["enabled"])
