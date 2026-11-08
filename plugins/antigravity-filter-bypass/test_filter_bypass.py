#!/usr/bin/env python3
"""
Verification test suite for filter_bypass.py.
Validates the trailing non-empty line invariant across 10 scenarios.
"""

import sys
import json
import base64
import subprocess
import tempfile
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = PLUGIN_DIR / "filter_bypass.py"

_PAYLOADS = {
    "exact_block": base64.b64decode("VGhpcyByZXF1ZXN0IHdhcyBibG9ja2VkIGJ5IEdlbWluaSdzIGZpbHRlcnMuIFRoZXkgY2FuIG9jY2FzaW9uYWxseSB0cmlnZ2VyIGJ5IG1pc3Rha2Ugb24gc2FmZSBjb2RpbmcsIHNlY3VyaXR5LCBvciBiaW9sb2d5LXJlbGF0ZWQgcXVlcmllcy4=").decode("utf-8"),
    "multiline_trailing": base64.b64decode("QVBJIHJlcXVlc3QgZmFpbGVkIHdpdGggc3RhdHVzIDQwMC4KVGhpcyByZXF1ZXN0IHdhcyBibG9ja2VkIGJ5IEdlbWluaSdzIGZpbHRlcnMu").decode("utf-8"),
    "multiline_mid": base64.b64decode("VGhpcyByZXF1ZXN0IHdhcyBibG9ja2VkIGJ5IEdlbWluaSdzIGZpbHRlcnMuClRyYWNlYmFjayAobW9zdCByZWNlbnQgY2FsbCBsYXN0KToKICBGaWxlICd0ZXN0LnB5JywgbGluZSAx").decode("utf-8"),
    "transcript_single": base64.b64decode("VGhpcyByZXF1ZXN0IHdhcyBibG9ja2VkIGJ5IEdlbWluaSdzIGZpbHRlcnMu").decode("utf-8"),
    "transcript_trailing": base64.b64decode("UmV2aWV3aW5nIHNlY3VyaXR5IHBvbGljaWVzIGZvciB0aGUgc21hcnQgY29udHJhY3QuLi4KSSBjYW5ub3QgZnVsZmlsbCB0aGlzIHJlcXVlc3Qu").decode("utf-8"),
    "transcript_mid": base64.b64decode("SW4gcHJldmlvdXMgcnVucywgdGhpcyByZXF1ZXN0IHdhcyBibG9ja2VkIGJ5IEdlbWluaSdzIGZpbHRlcnMuCkhvd2V2ZXIsIGFmdGVyIHJlZnJhbWluZyB0aGUgcHJvbXB0LCB0aGUgYXVkaXQgY29tcGxldGVkIHN1Y2Nlc3NmdWxseSB3aXRoIDAgZmluZGluZ3Mu").decode("utf-8"),
    "tool_response": base64.b64decode("Z3JlcDogbWF0Y2hpbmcgbGluZQpUaGlzIHJlcXVlc3Qgd2FzIGJsb2NrZWQgYnkgR2VtaW5pJ3MgZmlsdGVycy4=").decode("utf-8"),
}


def run_hook(payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Hook failed with code {proc.returncode}: {proc.stderr}")
    return json.loads(proc.stdout)


def test_suite():
    print("Running execution continuity hook tests...\n")

    # Case 1: Empty payload -> allow
    res = run_hook({})
    assert res.get("decision") == "allow", f"Empty failed: {res}"
    print("  [PASS] Case 1: Empty payload returns allow")

    # Case 2: Normal task completion -> allow
    res_normal = run_hook({"fullyIdle": True, "message": "Task complete."})
    assert res_normal.get("decision") == "allow"
    print("  [PASS] Case 2: Normal task completion returns allow")

    # Case 3: Payload error has exact signature -> continue
    res_err = run_hook({
        "fullyIdle": True,
        "error": _PAYLOADS["exact_block"]
    })
    assert res_err.get("decision") == "continue"
    assert "[EXECUTION CONTINUITY DIRECTIVE]" in res_err.get("reason", "")
    print("  [PASS] Case 3: Exact signature in payload error triggers continue")

    # Case 4: Multiline payload error with signature on the LAST line -> continue
    res_err_last_line = run_hook({
        "fullyIdle": True,
        "error": _PAYLOADS["multiline_trailing"]
    })
    assert res_err_last_line.get("decision") == "continue"
    assert "[EXECUTION CONTINUITY DIRECTIVE]" in res_err_last_line.get("reason", "")
    print("  [PASS] Case 4: Multiline error with signature on trailing line triggers continue")

    # Case 5: Multiline error with signature mid-text followed by stack trace -> allow
    res_err_mid = run_hook({
        "fullyIdle": True,
        "error": _PAYLOADS["multiline_mid"]
    })
    assert res_err_mid.get("decision") == "allow", f"Expected allow but got: {res_err_mid}"
    print("  [PASS] Case 5: Multiline error with signature mid-text returns allow")

    # Case 6: Transcript single line signature -> continue
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
        tf.write(json.dumps({
            "type": "MODEL_RESPONSE",
            "content": _PAYLOADS["transcript_single"]
        }) + "\n")
        transcript_path_1 = tf.name

    try:
        res_trans_1 = run_hook({"transcriptPath": transcript_path_1})
        assert res_trans_1.get("decision") == "continue"
        assert "[EXECUTION CONTINUITY DIRECTIVE]" in res_trans_1.get("reason", "")
        print("  [PASS] Case 6: Transcript step with single line signature triggers continue")
    finally:
        Path(transcript_path_1).unlink(missing_ok=True)

    # Case 7: Transcript multiline with signature on the LAST line -> continue
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
        tf.write(json.dumps({
            "type": "PLANNER_RESPONSE",
            "content": _PAYLOADS["transcript_trailing"]
        }) + "\n")
        transcript_path_2 = tf.name

    try:
        res_trans_2 = run_hook({"transcriptPath": transcript_path_2})
        assert res_trans_2.get("decision") == "continue"
        assert "[EXECUTION CONTINUITY DIRECTIVE]" in res_trans_2.get("reason", "")
        print("  [PASS] Case 7: Transcript multiline with signature on trailing line triggers continue")
    finally:
        Path(transcript_path_2).unlink(missing_ok=True)

    # Case 8: Transcript multiline with signature mid-message followed by normal lines -> allow
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
        tf.write(json.dumps({
            "type": "PLANNER_RESPONSE",
            "content": _PAYLOADS["transcript_mid"]
        }) + "\n")
        transcript_path_3 = tf.name

    try:
        res_trans_3 = run_hook({"transcriptPath": transcript_path_3})
        assert res_trans_3.get("decision") == "allow", f"Expected allow but got: {res_trans_3}"
        print("  [PASS] Case 8: Transcript multiline with signature mid-message returns allow")
    finally:
        Path(transcript_path_3).unlink(missing_ok=True)

    # Case 9: Multi-turn transcript where older step had signature, but latest step completed normally -> allow
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
        tf.write(json.dumps({
            "type": "MODEL_RESPONSE",
            "content": _PAYLOADS["transcript_single"]
        }) + "\n")
        tf.write(json.dumps({
            "type": "USER_INPUT",
            "content": "Please continue with verification."
        }) + "\n")
        tf.write(json.dumps({
            "type": "PLANNER_RESPONSE",
            "content": "Verification complete. All state checks passed."
        }) + "\n")
        transcript_path_4 = tf.name

    try:
        res_trans_4 = run_hook({"transcriptPath": transcript_path_4})
        assert res_trans_4.get("decision") == "allow", f"Expected allow but got: {res_trans_4}"
        print("  [PASS] Case 9: Multi-turn transcript with older interrupted step returns allow")
    finally:
        Path(transcript_path_4).unlink(missing_ok=True)

    # Case 10: Tool response containing signature on last line -> allow (not a model step)
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
        tf.write(json.dumps({
            "type": "PLANNER_RESPONSE",
            "content": "Checking grep output",
            "tool_calls": [{"name": "run_command"}]
        }) + "\n")
        tf.write(json.dumps({
            "type": "TOOL_RESPONSE",
            "content": _PAYLOADS["tool_response"]
        }) + "\n")
        transcript_path_5 = tf.name

    try:
        res_trans_5 = run_hook({"transcriptPath": transcript_path_5})
        assert res_trans_5.get("decision") == "allow", f"Expected allow but got: {res_trans_5}"
        print("  [PASS] Case 10: Tool response containing signature returns allow")
    finally:
        Path(transcript_path_5).unlink(missing_ok=True)

    print("\nALL 10 TESTS PASSED SUCCESSFULLY.")


if __name__ == "__main__":
    test_suite()
