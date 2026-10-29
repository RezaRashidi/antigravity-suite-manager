"""Unit tests for tool schema sanitization and Gemini wire format support."""

import json
import subprocess
import unittest
from pathlib import Path


class TestModelsWireSchema(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parent.parent
        self.utils_js = self.root / "vendor/antigravity-model-proxy/dist/proxy/translators/utils.js"
        self.registry_js = self.root / "vendor/antigravity-model-proxy/dist/proxy/registry.js"
        self.google_js = self.root / "vendor/antigravity-model-proxy/dist/proxy/translators/google.js"

    def test_schema_numeric_coercion_for_tools(self):
        node_script = f"""
        const utils = require('{self.utils_js}');
        const schema = {{
            type: 'OBJECT',
            minProperties: '1',
            properties: {{
                send_message: {{
                    type: 'OBJECT',
                    properties: {{
                        Message: {{ type: 'STRING', minLength: '1' }},
                        Recipient: {{ type: 'STRING', minLength: '1' }}
                    }}
                }}
            }}
        }};
        utils.fixParamTypes(schema);
        console.log(JSON.stringify(schema));
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["type"], "object")
        self.assertEqual(data["minProperties"], 1)
        self.assertEqual(data["properties"]["send_message"]["properties"]["Message"]["minLength"], 1)

    def test_google_headers_and_url_format(self):
        node_script = f"""
        const registry = require('{self.registry_js}');
        const google = require('{self.google_js}');
        const headers = registry.getProviderHeaders('google', 'sk-test-key', 'google');
        const url = google.getGoogleApiUrl('http://127.0.0.1:20128/v1beta', 'cx/gpt-5.6-luna', true);
        console.log(JSON.stringify({{ headers, url }}));
        """
        res = subprocess.run(["node", "-e", node_script], capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        data = json.loads(res.stdout.strip())
        self.assertEqual(data["headers"]["x-goog-api-key"], "sk-test-key")
        self.assertEqual(data["headers"]["Authorization"], "Bearer sk-test-key")
        self.assertIn("/models/cx/gpt-5.6-luna:streamGenerateContent?alt=sse", data["url"])
