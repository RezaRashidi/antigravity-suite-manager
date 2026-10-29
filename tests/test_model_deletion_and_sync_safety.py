import json
import subprocess

def test_case_insensitive_model_deletion():
    node_code = """
    const { ModelStore } = require('./vendor/antigravity-model-proxy/dist/modelStore');
    const fs = require('fs');
    const tmp = '/tmp/test_del_' + Date.now() + '.json';
    fs.writeFileSync(tmp, JSON.stringify({
        models: [
            { name: 'models/gateway/OC-Jev', externalModelName: 'oc/jev', displayName: 'OC/JEV', provider: 'gateway' },
            { name: 'models/gateway/Keep-Me', externalModelName: 'keep/me', displayName: 'Keep Me', provider: 'gateway' }
        ]
    }));
    const store = new ModelStore(tmp, null);
    store.delete('oc/jev');
    const remaining = store.read();
    fs.unlinkSync(tmp);
    console.log(JSON.stringify(remaining.map(m => m.name)));
    """
    res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True, check=True)
    rem = json.loads(res.stdout.strip())
    assert rem == ["models/gateway/Keep-Me"]

def test_delete_by_display_name_case_insensitive():
    node_code = """
    const { ModelStore } = require('./vendor/antigravity-model-proxy/dist/modelStore');
    const fs = require('fs');
    const tmp = '/tmp/test_del2_' + Date.now() + '.json';
    fs.writeFileSync(tmp, JSON.stringify({
        models: [
            { name: 'models/p/m1', externalModelName: 'x1', displayName: 'Alpha Beta', provider: 'p' },
            { name: 'models/p/m2', externalModelName: 'x2', displayName: 'Gamma Delta', provider: 'p' }
        ]
    }));
    const store = new ModelStore(tmp, null);
    store.delete('alpha beta');
    const remaining = store.read();
    fs.unlinkSync(tmp);
    console.log(JSON.stringify(remaining.map(m => m.name)));
    """
    res = subprocess.run(["node", "-e", node_code], capture_output=True, text=True, check=True)
    rem = json.loads(res.stdout.strip())
    assert rem == ["models/p/m2"]

def test_custom_ipc_no_raw_redux_injection():
    with open("vendor/antigravity-model-proxy/dist/customIpc.js", "r") as f:
        content = f.read()
    assert "executeJavaScript(injectionScript)" not in content
    assert "type: 'userStatus/setUserStatus', payload: payload" not in content
