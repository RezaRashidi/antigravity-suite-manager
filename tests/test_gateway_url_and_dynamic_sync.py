import subprocess
import json

def test_registry_url_normalization_with_trailing_slash():
    node_code = """
    const registry = require('./vendor/antigravity-model-proxy/dist/proxy/registry');
    const u1 = registry.getProviderUrl('https://ai.odirect.app/v1/', 'test', false, null);
    const u2 = registry.getProviderUrl('https://ai.odirect.app/v1', 'test', false, null);
    const u3 = registry.getProviderUrl('https://ai.odirect.app/', 'test', false, null);
    const u4 = registry.getProviderUrl('https://ai.odirect.app/v1/chat/completions', 'test', false, null);
    console.log(JSON.stringify([u1, u2, u3, u4]));
    """
    res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True, check=True)
    urls = json.loads(res.stdout.strip())
    assert urls[0] == "https://ai.odirect.app/v1/chat/completions"
    assert urls[1] == "https://ai.odirect.app/v1/chat/completions"
    assert urls[2] == "https://ai.odirect.app/v1/chat/completions"
    assert urls[3] == "https://ai.odirect.app/v1/chat/completions"

def test_google_url_normalization_with_trailing_slash():
    node_code = """
    const google = require('./vendor/antigravity-model-proxy/dist/proxy/translators/google');
    const u1 = google.getGoogleApiUrl('https://ai.odirect.app/v1/', 'reza', true);
    const u2 = google.getGoogleApiUrl('https://generativelanguage.googleapis.com/', 'gemini-pro', true);
    console.log(JSON.stringify([u1, u2]));
    """
    res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True, check=True)
    urls = json.loads(res.stdout.strip())
    assert urls[0] == "https://ai.odirect.app/v1/models/reza:streamGenerateContent?alt=sse"
    assert urls[1] == "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:streamGenerateContent?alt=sse"

def test_model_store_delete_normalization():
    node_code = """
    const { ModelStore } = require('./vendor/antigravity-model-proxy/dist/modelStore');
    const fs = require('fs');
    const tmp = '/tmp/test_models_' + Date.now() + '.json';
    fs.writeFileSync(tmp, JSON.stringify({
        models: [
            { name: 'models/test-m1', displayName: 'M1', provider: 'p1' },
            { name: 'models/test-m2', displayName: 'M2', provider: 'p2' }
        ]
    }));
    const store = new ModelStore(tmp, null);
    store.delete('test-m1');
    const remaining = store.read();
    fs.unlinkSync(tmp);
    console.log(JSON.stringify(remaining.map(m => m.name)));
    """
    res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True, check=True)
    names = json.loads(res.stdout.strip())
    assert names == ["models/test-m2"]
