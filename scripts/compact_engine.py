"""
SQLite and transcript compaction engine for conversation compactor.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path


def compact_sqlite_db(db_path: Path, base_step: int, last_step: int, dry_run: bool = True) -> int:
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    total_before = cur.execute("SELECT count(*) FROM steps;").fetchone()[0]
    cols = "idx, step_type, status, has_subtrajectory, metadata, error_details, permissions, task_details, render_info, step_payload, step_format"
    kept_steps = cur.execute(f"SELECT {cols} FROM steps WHERE idx >= ? AND idx <= ? ORDER BY idx ASC;", (base_step, last_step)).fetchall()
    new_count = len(kept_steps)
    print(f"[SQLite] Total steps before: {total_before} | Kept steps: {new_count} (range {base_step}..{last_step})")
    if dry_run:
        con.close()
        return new_count

    archive_db = db_path.with_name(f"{db_path.stem}.full_archive.db")
    if not archive_db.exists():
        shutil.copy2(db_path, archive_db)
        print(f"[SQLite] Full original database archived to {archive_db}")

    cur.execute("DELETE FROM steps;")
    for row in kept_steps:
        new_idx = row[0] - base_step
        cur.execute(
            f"INSERT INTO steps ({cols}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
            (new_idx, row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10]),
        )
    for tbl in ["gen_metadata", "executor_metadata", "parent_references"]:
        cur.execute(f"DELETE FROM {tbl} WHERE idx > ?;", (new_count,))
    con.commit()
    con.execute("VACUUM;")
    con.close()
    print(f"[SQLite] Compacted database down to {new_count} steps and VACUUM completed.")
    return new_count


def compact_transcript_file(file_path: Path, start_line: int, end_line: int, base_step: int, dry_run: bool = True) -> int:
    if not file_path.exists():
        return 0
    with open(file_path, "r", encoding="utf-8", errors="ignore") as fp:
        all_lines = fp.readlines()
    selected_lines = all_lines[start_line : end_line + 1]
    print(f"[Transcript] {file_path.name}: {len(all_lines)} total lines -> keeping {len(selected_lines)} lines ({start_line}..{end_line})")
    if dry_run:
        return len(selected_lines)

    archive_file = file_path.with_name(f"{file_path.stem}_full_archive{file_path.suffix}")
    if not archive_file.exists():
        shutil.copy2(file_path, archive_file)
        print(f"[Transcript] Archived {file_path.name} to {archive_file.name}")

    compacted_lines = []
    current_idx = 0
    for line in selected_lines:
        line_str = line.strip()
        if not line_str: continue
        try:
            data = json.loads(line_str)
            old_idx = data.get("step_index")
            data["step_index"] = (old_idx - base_step) if (old_idx is not None and old_idx >= base_step) else current_idx
            compacted_lines.append(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception:
            compacted_lines.append(line)
        current_idx += 1

    with open(file_path, "w", encoding="utf-8") as fp:
        fp.writelines(compacted_lines)
    print(f"[Transcript] Wrote {len(compacted_lines)} compacted lines to {file_path.name}")
    return len(compacted_lines)
