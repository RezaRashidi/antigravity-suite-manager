"""
Live prompt turnaround test measuring actual model response latency.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from typing import Optional

from .account_discovery import call_cloudcode_rpc, call_ls_rpc, find_ls_ports_and_csrf
from .models_system import PromptTestMetric


def _ensure_bench_git_repo() -> str:
    suite_dir = os.environ.get("ANTIGRAVITY_SUITE_DIR")
    if suite_dir and os.path.isdir(os.path.join(suite_dir, ".git")):
        return suite_dir
    from antigravity_suite.detect.constants import get_suite_root_dir
    for cand in [
        get_suite_root_dir(),
        os.path.expanduser("~/.antigravity-suite-manager")
    ]:
        if os.path.isdir(os.path.join(cand, ".git")):
            return cand
    tmp_repo = "/tmp/antigravity-bench-repo"
    os.makedirs(tmp_repo, exist_ok=True)
    if not os.path.isdir(os.path.join(tmp_repo, ".git")):
        subprocess.run(["git", "init"], cwd=tmp_repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        fpath = os.path.join(tmp_repo, "bench.txt")
        if not os.path.isfile(fpath):
            with open(fpath, "w", encoding="utf-8") as f:
                f.write("probe\n")
            subprocess.run(["git", "add", "."], cwd=tmp_repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp_repo


def _get_stored_token() -> Optional[str]:
    paths = [
        "~/.gemini/jetski-standalone-oauth-token",
        "~/.gemide/jetski-standalone-oauth-token",
        "~/.antigravity-profile2/.gemini/jetski-standalone-oauth-token",
    ]
    for p in paths:
        exp = os.path.expanduser(p)
        if os.path.isfile(exp):
            try:
                with open(exp, "r", encoding="utf-8") as f:
                    tok = json.load(f).get("token", {}).get("access_token")
                if tok:
                    return str(tok)
            except Exception:
                pass
    return None


def run_prompt_test() -> PromptTestMetric:
    repo = _ensure_bench_git_repo()
    for pid, port, csrf in find_ls_ports_and_csrf():
        payload = json.dumps({"repoRoot": repo}).encode("utf-8")
        t0 = time.perf_counter()
        res = call_ls_rpc(port, csrf, "GenerateCommitMessage", payload=payload)
        elapsed = (time.perf_counter() - t0) * 1000.0
        if res and "commitMessage" in res:
            msg = res["commitMessage"].get("commitMessageSummary", "")
            return PromptTestMetric(
                prompt_text="GenerateCommitMessage (via LanguageServer)",
                latency_ms=round(elapsed, 2),
                success=True,
                output_preview=msg[:120],
            )

    tok = _get_stored_token()
    if tok:
        t0 = time.perf_counter()
        res = call_cloudcode_rpc(tok, "fetchUserInfo")
        elapsed = (time.perf_counter() - t0) * 1000.0
        if res:
            reg = res.get("regionCode", "US")
            return PromptTestMetric(
                prompt_text="fetchUserInfo (via CloudCode PA)",
                latency_ms=round(elapsed, 2),
                success=True,
                output_preview=f"Region: {reg}, active session verified",
            )

    return PromptTestMetric(
        prompt_text="LanguageServer / CloudCode",
        success=False,
        error="No active Language Server or OAuth token available",
    )
