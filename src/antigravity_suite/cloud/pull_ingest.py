"""
Staging ingestion, conflict resolution, workspace provisioning, and merge trigger.
"""

from __future__ import annotations

import glob
import os
import shutil

from antigravity_suite.cloud.conflict import evaluate_sync_action, fork_local_divergence
from antigravity_suite.cloud.constants import ANNOTATIONS_DIR, BRAIN_DIR, CONVERSATIONS_DIR, REAL_HOME
from antigravity_suite.cloud.workspace_guard import ensure_workspace_exists, resolve_local_workspace_path
from antigravity_suite.history.vscdb_meta import get_db_trajectory_meta
from antigravity_suite.migration.import_history import trigger_history_merge


def ingest_staged_conversations(staged_dir: str, real_home: str = REAL_HOME) -> dict[str, int]:
    """Ingests staged conversations into master storage with conflict guards."""
    stats = {"applied": 0, "skipped": 0, "forked": 0, "workspaces_created": 0}
    s_conv = os.path.join(staged_dir, "conversations")
    s_brain = os.path.join(staged_dir, "brain")
    s_anno = os.path.join(staged_dir, "annotations")
    for d in [CONVERSATIONS_DIR, BRAIN_DIR, ANNOTATIONS_DIR]:
        os.makedirs(d, exist_ok=True)

    if os.path.isdir(s_conv):
        for s_db in glob.glob(os.path.join(s_conv, "*.db")):
            cid = os.path.splitext(os.path.basename(s_db))[0]
            l_db = os.path.join(CONVERSATIONS_DIR, f"{cid}.db")
            apply, reason = evaluate_sync_action(l_db, s_db)
            if apply:
                if reason == "fast_forward" and os.path.isfile(l_db):
                    fork_local_divergence(l_db, BRAIN_DIR)
                    stats["forked"] += 1
                shutil.copy2(s_db, l_db)
                stats["applied"] += 1

                uri, _ = get_db_trajectory_meta(s_db)
                if uri:
                    ws_p = resolve_local_workspace_path(uri, real_home=real_home)
                    if ws_p and ensure_workspace_exists(ws_p):
                        stats["workspaces_created"] += 1

                b_src = os.path.join(s_brain, cid)
                if os.path.isdir(b_src):
                    shutil.copytree(b_src, os.path.join(BRAIN_DIR, cid), dirs_exist_ok=True)
            else:
                stats["skipped"] += 1

    if os.path.isdir(s_anno):
        for a_file in glob.glob(os.path.join(s_anno, "*")):
            dst_a = os.path.join(ANNOTATIONS_DIR, os.path.basename(a_file))
            if not os.path.exists(dst_a):
                shutil.copy2(a_file, dst_a)

    trigger_history_merge()
    return stats
