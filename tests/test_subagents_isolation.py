"""
Tests for Subagent Detection, Isolation, and History Leak Prevention.
"""

import json
import sqlite3
from pathlib import Path

from antigravity_suite.history.models import ConversationSummary
from antigravity_suite.history.reconstruction import gather_candidate_transcripts, reconstruct_missing_databases
from antigravity_suite.history.sqlite_schema import ensure_summaries_schema
from antigravity_suite.history.sqlite_store import upsert_summary
from antigravity_suite.history.subagents import discover_subagent_uuids, purge_subagents_from_store


def test_discover_subagent_uuids(tmp_path: Path):
    brain_pool = tmp_path / "brain"
    parent_uuid = "11111111-2222-3333-4444-555555555555"
    sub_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    sub_dir = brain_pool / parent_uuid / ".system_generated" / "subagents"
    sub_dir.mkdir(parents=True)
    (sub_dir / f"{sub_uuid}.json").write_text(
        json.dumps({"conversationId": sub_uuid, "state": "SUBAGENT_STATE_ALIVE"}),
        encoding="utf-8",
    )

    discovered = discover_subagent_uuids([brain_pool])
    assert sub_uuid in discovered
    assert parent_uuid not in discovered


def test_subagent_skipped_during_reconstruction(tmp_path: Path):
    brain_pool = tmp_path / "brain"
    sub_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    log_dir = brain_pool / sub_uuid / ".system_generated" / "logs"
    log_dir.mkdir(parents=True)
    (log_dir / "transcript.jsonl").write_text('{"step_index": 0}\n', encoding="utf-8")

    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir(parents=True)

    # With subagents set, reconstruction skips it
    reconstructed = reconstruct_missing_databases(
        brain_pools=[str(brain_pool)],
        master_brain_dir=brain_pool,
        master_conv_dir=conv_dir,
        subagents={sub_uuid},
    )
    assert reconstructed == 0
    assert not (conv_dir / f"{sub_uuid}.db").exists()


def test_purge_subagents_from_store(tmp_path: Path):
    conv_dir = tmp_path / "conversations"
    conv_dir.mkdir(parents=True)
    sub_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    fake_db = conv_dir / f"{sub_uuid}.db"
    fake_db.write_text("fake db", encoding="utf-8")

    db_sum = tmp_path / "conversation_summaries.db"
    con = sqlite3.connect(str(db_sum))
    ensure_summaries_schema(con)

    # Insert a subagent row
    summary = ConversationSummary(
        conversation_id=sub_uuid,
        title="Subagent Task",
        parent_conversation_id="11111111-2222-3333-4444-555555555555",
        nesting_depth=1,
    )
    upsert_summary(con, summary)

    purged = purge_subagents_from_store(conv_dir, con, {sub_uuid})
    assert purged == 1
    assert not fake_db.exists()

    rows = con.cursor().execute("SELECT count(*) FROM conversation_summaries WHERE conversation_id = ?;", (sub_uuid,)).fetchone()
    assert rows[0] == 0
    con.close()
