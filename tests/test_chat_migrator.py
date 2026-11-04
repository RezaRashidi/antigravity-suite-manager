"""
Unit tests for One-Shot Legacy Chat Migrator (v2.5.5 -> v2.6.0).
"""

from __future__ import annotations

import base64
import sqlite3
from pathlib import Path
from unittest.mock import patch

from antigravity_suite.migration.chat_migrator import (
    check_ide_version,
    parse_version_tuple,
    plan_migration,
    run_migration,
)


def test_parse_version_tuple():
    assert parse_version_tuple("2.6.0") == (2, 6, 0)
    assert parse_version_tuple("v2.5.5") == (2, 5, 5)
    assert parse_version_tuple("1.107.0") == (1, 107, 0)
    assert parse_version_tuple("Unknown") == (0, 0, 0)


def test_check_ide_version():
    with patch("antigravity_suite.migration.chat_migrator.inspect_ide_dir") as mock_insp:
        mock_insp.return_value = {"version": "2.6.0", "path": "/opt/antigravity-ide"}
        res = check_ide_version("/opt/antigravity-ide")
        assert res["version"] == "2.6.0"
        assert res["is_v260_plus"] is True
        assert res["supported"] is True

        mock_insp.return_value = {"version": "2.5.5", "path": "/opt/antigravity-ide"}
        res = check_ide_version("/opt/antigravity-ide")
        assert res["version"] == "2.5.5"
        assert res["is_v260_plus"] is False
        assert res["supported"] is False


def test_plan_migration_detects_unmigrated_chats(tmp_path: Path):
    vscdb_path = tmp_path / "state.vscdb"
    con = sqlite3.connect(vscdb_path)
    cur = con.cursor()
    cur.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);")
    # Empty item table
    con.commit()
    con.close()

    m_dir = tmp_path / ".gemini" / "antigravity"
    m_dir.mkdir(parents=True, exist_ok=True)
    m_db = m_dir / "conversation_summaries.db"
    con_m = sqlite3.connect(m_db)
    cur_m = con_m.cursor()
    cur_m.execute("CREATE TABLE conversation_summaries (conversation_id TEXT PRIMARY KEY, title TEXT);")
    cur_m.execute("INSERT INTO conversation_summaries VALUES ('conv-1', 'Test 1');")
    con_m.commit()
    con_m.close()

    with patch("antigravity_suite.migration.chat_migrator.discover_candidate_vscdbs", return_value=[vscdb_path]):
        plan = plan_migration(tmp_path)
        assert plan["legacy_total"] == 0
        assert plan["to_migrate_count"] == 0
        assert plan["total_existing_v260"] == 1


def test_run_migration_one_shot(tmp_path: Path):
    with patch("antigravity_suite.migration.chat_migrator.check_ide_version") as mock_v, \
         patch("antigravity_suite.migration.chat_migrator.plan_migration") as mock_p, \
         patch("antigravity_suite.migration.chat_migrator.merge_histories") as mock_m:
        mock_v.return_value = {"version": "2.6.0", "is_v260_plus": True}
        mock_p.side_effect = [
            {"legacy_total": 5, "already_in_v260": 2, "to_migrate_count": 3, "total_existing_v260": 2},
            {"legacy_total": 5, "already_in_v260": 5, "to_migrate_count": 0, "total_existing_v260": 5},
        ]
        class DummyStats:
            def to_dict(self): return {"migrated": 3}
        mock_m.return_value = DummyStats()

        res = run_migration(home=tmp_path)
        assert res["status"] == "success"
        assert res["newly_migrated"] == 3
        assert res["total_v260_chats"] == 5
        mock_m.assert_called_once_with(quiet=True, force_rebuild=False, user_home=tmp_path, skip_backup=False)
