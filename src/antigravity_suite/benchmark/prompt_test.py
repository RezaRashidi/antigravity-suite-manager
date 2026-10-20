"""
Live prompt turnaround test measuring actual model response latency.
"""

from __future__ import annotations

import json
import os
import time
from typing import Optional

from .account_discovery import call_cloudcode_rpc, call_ls_rpc, find_ls_ports_and_csrf
from .models_system import PromptTestMetric


def run_prompt_test() -> PromptTestMetric:
    repo_candidate = os.path.expanduser("~/PhpstormProjects/antigravity-suite-manager")
    if not os.path.isdir(repo_candidate):
        repo_candidate = os.path.expanduser("~")

    ls_targets = find_ls_ports_and_csrf()
    for pid, port, csrf in ls_targets:
        payload = json.dumps({"repoRoot": repo_candidate}).encode("utf-8")
        t0 = time.perf_counter()
        res = call_ls_rpc(port, csrf, "GenerateCommitMessage", payload=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if res and "commitMessage" in res:
            msg = res["commitMessage"].get("commitMessageSummary", "")
            return PromptTestMetric(
                prompt_text="GenerateCommitMessage (via LanguageServer)",
                latency_ms=round(elapsed_ms, 2),
                success=True,
                output_preview=msg[:120],
            )

    tok_path = os.path.expanduser("~/.gemini/jetski-standalone-oauth-token")
    if os.path.isfile(tok_path):
        try:
            with open(tok_path, "r", encoding="utf-8") as f:
                acc_tok = json.load(f).get("token", {}).get("access_token", "")
            if acc_tok:
                t0 = time.perf_counter()
                res = call_cloudcode_rpc(acc_tok, "fetchUserInfo")
                elapsed_ms = (time.perf_counter() - t0) * 1000
                if res:
                    reg = res.get("regionCode", "US")
                    return PromptTestMetric(
                        prompt_text="fetchUserInfo (via CloudCode PA)",
                        latency_ms=round(elapsed_ms, 2),
                        success=True,
                        output_preview=f"Region: {reg}, active session verified",
                    )
        except Exception as e:
            return PromptTestMetric(
                prompt_text="CloudCode Fallback",
                success=False,
                error=str(e),
            )

    return PromptTestMetric(
        prompt_text="LanguageServer / CloudCode",
        success=False,
        error="No active Language Server or OAuth token available",
    )
