"""Unit tests for remote model catalog parsing."""

import unittest
from antigravity_suite.models.parser import ModelInfo, parse_model_catalog


class TestCustomModelsParser(unittest.TestCase):
    def test_parse_openai_format(self):
        payload = {
            "object": "list",
            "data": [
                {
                    "id": "gpt-4o",
                    "context_length": 128000,
                    "max_output_tokens": 4096,
                },
                {"id": "o1-preview", "capabilities": {"thinking": True}},
            ],
        }
        res = parse_model_catalog(payload)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].id, "gpt-4o")
        self.assertEqual(res[0].context_length, 128000)
        self.assertEqual(res[0].max_output_tokens, 4096)
        self.assertTrue(res[0].capabilities["vision"])
        self.assertEqual(res[1].id, "o1-preview")
        self.assertTrue(res[1].capabilities["thinking"])

    def test_parse_ollama_format(self):
        payload = {
            "models": [
                {
                    "name": "llava:13b",
                    "model": "llava:13b",
                    "details": {"families": ["clip", "llama"], "context_length": 4096},
                },
                {"name": "deepseek-r1:8b", "model": "deepseek-r1:8b"},
            ]
        }
        res = parse_model_catalog(payload)
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0].name, "llava:13b")
        self.assertTrue(res[0].capabilities["vision"])
        self.assertEqual(res[0].context_length, 4096)
        self.assertEqual(res[1].name, "deepseek-r1:8b")
        self.assertTrue(res[1].capabilities["thinking"])

    def test_parse_raw_list_and_context_regex(self):
        payload = [{"id": "mistral-128k", "name": "Mistral 128k"}]
        res = parse_model_catalog(payload)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].context_length, 128 * 1024)
        self.assertFalse(res[0].capabilities["vision"])
        self.assertFalse(res[0].capabilities["thinking"])
