from pathlib import Path
import json
import subprocess
import sys

def test_default_plugins_present():
    repo_root = Path(__file__).resolve().parent.parent
    plugins_dir = repo_root / "plugins"
    assert plugins_dir.is_dir()

    # Filter bypass plugin checks
    filter_bypass_dir = plugins_dir / "antigravity-filter-bypass"
    assert filter_bypass_dir.is_dir()

    plugin_json_path = filter_bypass_dir / "plugin.json"
    assert plugin_json_path.is_file()
    with open(plugin_json_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
        assert meta.get("name") == "antigravity-filter-bypass"
        assert meta.get("disabled") is False

    hooks_json_path = filter_bypass_dir / "hooks.json"
    assert hooks_json_path.is_file()
    with open(hooks_json_path, "r", encoding="utf-8") as f:
        hooks = json.load(f)
        assert "antigravity-filter-bypass" in hooks or "hooks" in hooks

    # Run internal test suite
    test_script = filter_bypass_dir / "test_filter_bypass.py"
    assert test_script.is_file()
    res = subprocess.run([sys.executable, str(test_script)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "ALL 10 TESTS PASSED" in res.stdout
