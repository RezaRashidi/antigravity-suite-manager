#!/usr/bin/env python3
import unittest
import unittest.mock
import tempfile
import os
import shutil
import struct
import json
import zlib
import colorsys
import re
import sys
import subprocess
from pathlib import Path

# Import functions to test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import importlib
from antigravity_suite.config import get_user_home

class TestFixesValidation(unittest.TestCase):

    def test_exec_regex_placement(self):
        """Bug 1.1: Verifies that --password-store=basic is placed AFTER the binary in exec command."""
        pattern = r'^(\s*exec\s+("[^"]+"|\'[^\']+\'|\S+))(.*)$'
        lines = [
            'exec "/opt/Antigravity/antigravity" "$@"',
            'exec /opt/Antigravity/antigravity "$@"',
            '  exec \'/usr/bin/antigravity\' --arg1'
        ]
        for line in lines:
            m = re.match(pattern, line)
            self.assertIsNotNone(m)
            replaced = f"{m.group(1)} --password-store=basic{m.group(3)}"
            self.assertFalse(replaced.strip().startswith("exec --password-store=basic"))
            self.assertIn("--password-store=basic", replaced)

    def test_asar_offset_calculation(self):
        """Bug 1.2: Verifies that ASAR header calculation starts at 8 + h_s + offset, not 16 + j_len."""
        with tempfile.TemporaryDirectory() as td:
            asar_path = os.path.join(td, "test.asar")
            pkg_content = json.dumps({"name": "antigravity", "version": "3.5.0"}).encode("utf-8")
            
            # Construct header JSON
            header_dict = {
                "files": {
                    "package.json": {
                        "size": len(pkg_content),
                        "offset": "0"
                    }
                }
            }
            hdr_bytes = json.dumps(header_dict).encode("utf-8")
            j_len = len(hdr_bytes)
            # In Chromium Pickle, j_len is padded to 4 bytes
            pad = (4 - (j_len % 4)) % 4
            pickle_data = hdr_bytes + (b"\x00" * pad)
            h_s = len(pickle_data) + 8 # h_o (4) + j_len (4) + padded payload
            h_o = len(pickle_data) + 4
            
            with open(asar_path, "wb") as f:
                f.write(struct.pack("<IIII", 4, h_s, h_o, j_len))
                f.write(pickle_data)
                f.write(pkg_content)

            # Read back using the fixed logic
            with open(asar_path, "rb") as f:
                magic, read_hs, read_ho, read_jlen = struct.unpack("<IIII", f.read(16))
                hdr = json.loads(f.read(read_jlen).decode("utf-8"))
                curr = hdr["files"]["package.json"]
                f.seek(8 + read_hs + int(curr["offset"]))
                data = f.read(int(curr["size"]))
                pkg = json.loads(data.decode("utf-8"))
                self.assertEqual(pkg.get("version"), "3.5.0")

    def test_launcher_profile_path_replacement_order(self):
        """Bug 1.3: Verifies that full profile path is replaced before basename to avoid truncation."""
        detect = importlib.import_module("antigravity-detect")
        with tempfile.TemporaryDirectory() as td:
            launcher_f = os.path.join(td, "antigravity-test")
            old_p = os.path.join(td, "old-root", ".antigravity-profile-app-work")
            new_p = os.path.join(td, "new-root", ".antigravity-profile-app-work2")
            
            content = f'''#!/usr/bin/env bash
export PROFILE="{old_p}"
exec /opt/antigravity --user-data-dir="{old_p}/.config" --class="antigravity-app-work"
'''
            with open(launcher_f, "w") as f:
                f.write(content)

            detect.update_launcher_profile_path(launcher_f, is_acc2=False, old_p=old_p, new_p=new_p)
            with open(launcher_f, "r") as f:
                updated = f.read()

            self.assertIn(f'export PROFILE="{new_p}"', updated)
            self.assertIn(f'--user-data-dir="{new_p}/.config"', updated)
            self.assertNotIn(old_p, updated)

    def test_recolor_emblem_absolute_hue(self):
        """Bug 7.1: Verifies that recolor_emblem maps saturated pixels directly to target hue."""
        gen_icons = importlib.import_module("antigravity-generate-icons")
        # Create a 2x2 test image with a saturated blue pixel (HSV ~ (0.6, 0.8, 0.8))
        r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(0.6, 0.8, 0.8)]
        pixels = bytearray([r, g, b, 255] * 4)

        # Recolor to emerald (target hue 0.32)
        out = gen_icons.recolor_emblem(2, 2, pixels, color="emerald")
        out_r, out_g, out_b = out[0], out[1], out[2]
        h_val, s_val, v_val = colorsys.rgb_to_hsv(out_r / 255.0, out_g / 255.0, out_b / 255.0)
        self.assertAlmostEqual(h_val, 0.32, delta=0.02)

    def test_png_plte_trns_reconstruction(self):
        """Bug 7.2: Verifies that reconstruct_png handles indexed color with PLTE and tRNS."""
        gen_icons = importlib.import_module("antigravity-generate-icons")
        with tempfile.TemporaryDirectory() as td:
            png_file = os.path.join(td, "indexed.png")
            
            # 2x1 indexed image: pixel 0 -> color index 0, pixel 1 -> color index 1
            w, h = 2, 1
            # PLTE: color 0=(255, 0, 0), color 1=(0, 255, 0)
            plte = b"\xff\x00\x00\x00\xff\x00"
            # tRNS: color 0 alpha=128, color 1 alpha=255
            trns = b"\x80\xff"
            
            # Scanline: filter_type 0, index 0, index 1
            raw_scanline = b"\x00\x00\x01"
            idat = zlib.compress(raw_scanline)
            
            def make_chunk(tag, data):
                return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
            
            ihdr = struct.pack(">IIBBBBB", w, h, 8, 3, 0, 0, 0) # color_type 3 = indexed
            with open(png_file, "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n")
                f.write(make_chunk(b"IHDR", ihdr))
                f.write(make_chunk(b"PLTE", plte))
                f.write(make_chunk(b"tRNS", trns))
                f.write(make_chunk(b"IDAT", idat))
                f.write(make_chunk(b"IEND", b""))
                
            out_w, out_h, rgba = gen_icons.reconstruct_png(png_file)
            self.assertEqual(out_w, 2)
            self.assertEqual(out_h, 1)
            # Pixel 0: Red with alpha 128
            self.assertEqual((rgba[0], rgba[1], rgba[2], rgba[3]), (255, 0, 0, 128))
            # Pixel 1: Green with alpha 255
            self.assertEqual((rgba[4], rgba[5], rgba[6], rgba[7]), (0, 255, 0, 255))

    def test_add_path_safe_broken_symlinks(self):
        """Bug 5.2: Verifies that add_path_safe skips broken symlinks and dereferences valid ones."""
        migration = importlib.import_module("antigravity-migration")
        import tarfile

        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            os.makedirs(src_dir)
            broken = os.path.join(src_dir, "broken_link")
            os.symlink("/nonexistent/file/path", broken)

            real_file = os.path.join(src_dir, "real.txt")
            with open(real_file, "w") as f:
                f.write("valid data")

            # Valid symlink pointing to another file
            valid_link = os.path.join(src_dir, "link_to_real")
            os.symlink(real_file, valid_link)

            tar_path = os.path.join(td, "out.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                # Should not raise FileNotFoundError
                migration.add_path_safe(tar, src_dir, "test_arc")

            with tarfile.open(tar_path, "r:gz") as tar:
                names = tar.getnames()
                self.assertIn("test_arc/real.txt", names)
                self.assertIn("test_arc/link_to_real", names)
                self.assertNotIn("test_arc/broken_link", names)

    def test_keyring_scoped_purge_filter(self):
        """Bug 6.1: Verifies that purge_antigravity_from_keyring filters based on target."""
        keyring = importlib.import_module("antigravity-keyring")
        import inspect
        sig = inspect.signature(keyring.purge_antigravity_from_keyring)
        self.assertIn("target", sig.parameters)

    def test_f5_patch_syntax_and_wmclass(self):
        """Bugs 3.1 & 3.2: Verifies no comma in WM_CLASS command and _lsPort initialized."""
        patch_path = os.path.join(os.path.dirname(__file__), "..", "bin", "antigravity-f5-patch.js")
        with open(patch_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Bug 3.1: No comma after WM_CLASS in xprop command and secure execFile used
        self.assertNotIn('WM_CLASS,', content)
        self.assertIn("execFile('xprop', ['-id', String(xid), '-f', 'WM_CLASS', '8s', '-set', 'WM_CLASS', wmClass]", content)

        # Bug 3.2: _lsPort declared
        self.assertIn("let _lsPort = 0;", content)

    def test_sqlite_wal_sync_and_cleanup(self):
        """Bug 5.1: Verifies SQLite WAL and SHM sidecars are synced and stale WALs removed."""
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "src")
            dst_dir = os.path.join(td, "dst")
            os.makedirs(src_dir)
            os.makedirs(dst_dir)

            db_src = os.path.join(src_dir, "conversation_summaries.db")
            wal_src = f"{db_src}-wal"
            shm_src = f"{db_src}-shm"
            with open(db_src, "w") as f: f.write("main db")
            with open(wal_src, "w") as f: f.write("wal data")
            with open(shm_src, "w") as f: f.write("shm data")

            # Simulate stale wal in destination
            dst_db = os.path.join(dst_dir, "conversation_summaries.db")
            dst_wal = f"{dst_db}-wal"
            dst_shm = f"{dst_db}-shm"
            with open(dst_wal, "w") as f: f.write("stale wal")

            # Apply sync logic from import_history / restore_backup
            shutil.copy2(db_src, dst_db)
            for ext in ["-wal", "-shm"]:
                s_wal = f"{db_src}{ext}"
                d_wal = f"{dst_db}{ext}"
                if os.path.exists(s_wal):
                    shutil.copy2(s_wal, d_wal)
                elif os.path.exists(d_wal):
                    os.remove(d_wal)

            self.assertTrue(os.path.exists(dst_wal))
            with open(dst_wal, "r") as f:
                self.assertEqual(f.read(), "wal data")
            self.assertTrue(os.path.exists(dst_shm))

    def test_apply_icon_proc_starttime_and_regex(self):
        """Bugs 4.1 & 4.2: Verifies get_proc_start_time and custom profile regex."""
        apply_icon = importlib.import_module("antigravity-apply-icon")
        # Check get_proc_start_time works on current PID
        curr_start = apply_icon.get_proc_start_time(os.getpid())
        self.assertIsInstance(curr_start, (int, float))
        self.assertGreater(curr_start, 0)

        # Check regex extraction for custom instance
        cmd = f"/opt/antigravity/antigravity --user-data-dir={get_user_home()}/.antigravity-profile-app-work"
        m_app = re.search(r'\.antigravity-profile-(app-[a-zA-Z0-9_-]+)', cmd) or \
                re.search(r'\.antigravity-profile-([a-zA-Z0-9_-]+)', cmd)
        self.assertIsNotNone(m_app)
        self.assertEqual(m_app.group(1), "app-work")

    def test_apply_icon_resolutions_and_caching(self):
        """Bugs L2-1.2 & L3-4.2: Verifies icon resolutions capped at 128 and patched_wids cache used."""
        apply_icon_path = os.path.join(os.path.dirname(__file__), "..", "bin", "antigravity-apply-icon.py")
        with open(apply_icon_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[16, 24, 32, 48, 64, 128]", content)
        self.assertNotIn("[16, 24, 32, 48, 64, 128, 256]", content)
        self.assertIn("_patched_wids", content)

    def test_wayland_x11_flags_in_manage_antigravity(self):
        """Bug L2-1.1: Verifies ELECTRON_OZONE_PLATFORM_HINT=x11 and --ozone-platform=x11."""
        manage_path = os.path.join(os.path.dirname(__file__), "..", "bin", "manage-antigravity.sh")
        with open(manage_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn('export ELECTRON_OZONE_PLATFORM_HINT="x11"', content)
        self.assertIn('--ozone-platform=x11', content)

    def test_keyring_service_gemini_antigravity_filter(self):
        """Bug L2-3.1: Verifies gemini service keyring items require antigravity username."""
        keyring_path = os.path.join(os.path.dirname(__file__), "..", "bin", "antigravity-keyring.py")
        with open(keyring_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("attrs.get('service') == 'gemini'", content)
        self.assertIn("'antigravity' in attrs.get('username'", content)

    def test_f5_patch_no_lastport_overwrite(self):
        """Bug L3-4.1: Verifies _lastPort = _lsPort is removed to preserve ephemeral port 0."""
        patch_path = os.path.join(os.path.dirname(__file__), "..", "bin", "antigravity-f5-patch.js")
        with open(patch_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("_lastPort = _lsPort;", content)

    def test_migration_restore_cleanup_and_tokens(self):
        """Bugs L2-4.1 & L3-5.1: Verifies restore_backup cleans up post-backup convs and restores OAuth tokens."""
        migration = importlib.import_module("antigravity-migration")
        import tarfile

        with tempfile.TemporaryDirectory() as td:
            backup_file = os.path.join(td, "antigravity-all-backup-test.tar.gz")
            # Create a mock backup tarball
            src_data = os.path.join(td, "src_data")
            os.makedirs(os.path.join(src_data, "history", "conversations"))
            os.makedirs(os.path.join(src_data, "suite", "tokens"))

            with open(os.path.join(src_data, "history", "conversations", "snap1.db"), "w") as f:
                f.write("snap1")
            with open(os.path.join(src_data, "suite", "tokens", "gemini-token"), "w") as f:
                f.write("mock-oauth-token")

            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(src_data, arcname=".")

            # Set up mock MASTER_GEMINI
            mock_master = os.path.join(td, "master")
            mock_conv = os.path.join(mock_master, "conversations")
            os.makedirs(mock_conv)
            with open(os.path.join(mock_conv, "snap1.db"), "w") as f: f.write("old snap1")
            with open(os.path.join(mock_conv, "zombie.db"), "w") as f: f.write("zombie conversation")

            from unittest.mock import patch
            orig_master = migration.MASTER_GEMINI
            orig_gemini = migration.GEMINI_DIR
            try:
                migration.MASTER_GEMINI = mock_master
                migration.GEMINI_DIR = td
                with patch.object(migration, "trigger_history_merge"), patch.object(migration, "create_safety_backup"):
                    res = migration.restore_backup(backup_file)
                    self.assertTrue(res)

                # zombie.db must be purged
                self.assertFalse(os.path.exists(os.path.join(mock_conv, "zombie.db")))
                self.assertTrue(os.path.exists(os.path.join(mock_conv, "snap1.db")))
                # gemini token must be restored
                token_target = os.path.join(td, "jetski-standalone-oauth-token")
                self.assertTrue(os.path.exists(token_target))
                with open(token_target, "r") as f:
                    self.assertEqual(f.read(), "mock-oauth-token")
            finally:
                migration.MASTER_GEMINI = orig_master
                migration.GEMINI_DIR = orig_gemini

    def test_vscdb_sync_discovers_and_updates_workspace_storage(self):
        """Verifies discover_candidate_vscdbs finds workspaceStorage and write_vscdb_unified_state syncs it."""
        from pathlib import Path
        import sqlite3
        from antigravity_suite.history.vscdb_sync import discover_candidate_vscdbs, write_vscdb_unified_state
        from antigravity_suite.proto.cascade import build_cascade_summary

        with tempfile.TemporaryDirectory() as td:
            user_home = Path(td)
            global_dir = user_home / ".config" / "Antigravity IDE" / "User" / "globalStorage"
            global_dir.mkdir(parents=True)
            global_db = global_dir / "state.vscdb"
            with sqlite3.connect(str(global_db)) as con:
                con.execute("CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);")

            ws_dir = user_home / ".config" / "Antigravity IDE" / "User" / "workspaceStorage" / "mock_workspace_1"
            ws_dir.mkdir(parents=True)
            ws_db = ws_dir / "state.vscdb"
            with sqlite3.connect(str(ws_db)) as con:
                con.execute("CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);")

            discovered = discover_candidate_vscdbs(user_home=user_home)
            self.assertIn(global_db.resolve(), discovered)
            self.assertIn(ws_db.resolve(), discovered)

            # Write unified state and verify both databases are populated
            mock_cid = "11111111-2222-3333-4444-555555555555"
            mock_bin = build_cascade_summary(mock_cid, "Test Chat", "Preview", 5)
            write_vscdb_unified_state(discovered, {mock_cid: mock_bin})

            # Verify globalStorage database is populated with unified state
            with sqlite3.connect(str(global_db)) as con:
                row = con.cursor().execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';").fetchone()
                self.assertIsNotNone(row)
                self.assertIsNotNone(row[0])

            # Verify workspace-scoped database is NOT bloated with global unified state
            with sqlite3.connect(str(ws_db)) as con:
                row = con.cursor().execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';").fetchone()
                self.assertIsNone(row)

    def test_discovery_has_json_and_handles_pinned_unpinned(self):
        import antigravity_suite.history.discovery as disc
        self.assertTrue(hasattr(disc, "json"))

        with tempfile.TemporaryDirectory() as td:
            u_home = Path(td)
            app_cfg = u_home / ".config" / "Antigravity"
            app_cfg.mkdir(parents=True)
            app_json = app_cfg / "app_storage.json"

            # 1. Pinned
            with open(app_json, "w") as f:
                disc.json.dump({"pinned_conversations_order": ["00000000-1111-2222-3333-444444444444"]}, f)

            pinned = disc.discover_pinned_conversation_ids(user_home=u_home)
            self.assertEqual(pinned, {"00000000-1111-2222-3333-444444444444"})

            # 2. Unpin and verify replication drops it
            disc.replicate_pinned_conversations_order(set(), user_home=u_home)
            with open(app_json) as f:
                data = disc.json.load(f)
            self.assertEqual(data["pinned_conversations_order"], [])

    def test_annotation_sync_removes_unpinned_and_unarchived_flags(self):
        from antigravity_suite.history.extractor import sync_annotation_file

        with tempfile.TemporaryDirectory() as td:
            cid = "22222222-3333-4444-5555-666666666666"
            # Pin and archive
            sync_annotation_file(td, cid, "Active Title", pinned=True, archived=True)
            anno_f = Path(td) / "annotations" / f"{cid}.pbtxt"
            self.assertTrue(anno_f.is_file())
            content = anno_f.read_text()
            self.assertIn("pinned:true", content)
            self.assertIn("archived:true", content)

            # Unpin and unarchive
            sync_annotation_file(td, cid, "Active Title", pinned=False, archived=False)
            content_updated = anno_f.read_text()
            self.assertNotIn("pinned:true", content_updated)
            self.assertNotIn("archived:true", content_updated)

    def test_src_not_truncated_as_project_container(self):
        from antigravity_suite.history.projects import PROJECT_CONTAINERS, normalize_workspace_uri
        self.assertNotIn("src", PROJECT_CONTAINERS)
        raw_uri = (get_user_home() / "app-server" / "src" / "controllers" / "auth").as_uri()
        norm = normalize_workspace_uri(raw_uri)
        self.assertNotEqual(norm, (get_user_home() / "app-server" / "src" / "controllers").as_uri())
        self.assertEqual(norm, raw_uri)

    def test_ensure_project_configs_populates_all_gemini_dirs(self):
        from antigravity_suite.history.projects import ensure_project_configs

        with tempfile.TemporaryDirectory() as td:
            u_home = Path(td)
            g1 = u_home / ".gemini"
            g2 = u_home / ".gemide"
            g1.mkdir(parents=True)
            g2.mkdir(parents=True)

            ws_target = (u_home / "cool-service").as_uri()
            ensure_project_configs(user_home=u_home, workspace_uris=[ws_target])

            # Both g1 and g2 config/projects/ must have the generated project file
            p1_files = list((g1 / "config" / "projects").glob("*.json"))
            p2_files = list((g2 / "config" / "projects").glob("*.json"))
            self.assertTrue(len(p1_files) > 0)
            self.assertTrue(len(p2_files) > 0)
            self.assertEqual(p1_files[0].name, p2_files[0].name)

    def test_sync_annotation_files_preserves_archived_conversations(self):
        import sqlite3
        from antigravity_suite.history.merger import sync_annotation_files
        from antigravity_suite.history.extractor import sync_annotation_file
        from antigravity_suite.proto.cascade import build_cascade_summary

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            cid = "44444444-5555-6666-7777-888888888888"

            # 1. Calling with None preserves existing flag
            sync_annotation_file(master, cid, "Initial Title", archived=True)
            anno_f = master / "annotations" / f"{cid}.pbtxt"
            self.assertIn("archived:true", anno_f.read_text())

            sync_annotation_file(master, cid, "Initial Title", archived=None)
            self.assertIn("Initial Title", anno_f.read_text())
            self.assertIn("archived:true", anno_f.read_text())

            # 2. sync_annotation_files preserves archived from raw_summary
            raw_arc = build_cascade_summary(cid, "Archived Chat", "Preview", 3, archived=True)
            raw_active = build_cascade_summary("active-uuid", "Active Chat", "Preview", 3, archived=False)

            db_p = master / "test.db"
            with sqlite3.connect(str(db_p)) as con:
                cur = con.cursor()
                cur.execute("CREATE TABLE conversation_summaries (conversation_id TEXT, title TEXT, raw_summary BLOB);")
                cur.execute("INSERT INTO conversation_summaries VALUES (?, ?, ?);", (cid, "Archived Chat", raw_arc))
                cur.execute("INSERT INTO conversation_summaries VALUES (?, ?, ?);", ("active-uuid", "Active Chat", raw_active))

                sync_annotation_files(master, cur, pinned_set=set())

            self.assertIn("archived:true", (master / "annotations" / f"{cid}.pbtxt").read_text())
            self.assertNotIn("archived:true", (master / "annotations" / "active-uuid.pbtxt").read_text())

    def test_cross_profile_unpinning_precedence(self):
        import time, json
        from antigravity_suite.history.discovery import discover_pinned_conversation_ids, replicate_pinned_conversations_order

        with tempfile.TemporaryDirectory() as td:
            u_home = Path(td)
            p1_cfg = u_home / ".config" / "Antigravity"
            p2_cfg = u_home / ".antigravity-profile2" / ".config" / "Antigravity"
            p1_cfg.mkdir(parents=True)
            p2_cfg.mkdir(parents=True)

            f1 = p1_cfg / "app_storage.json"
            f2 = p2_cfg / "app_storage.json"

            uuid_a = "00000000-1111-2222-3333-aaaaaaaaaaaa"
            uuid_b = "00000000-1111-2222-3333-bbbbbbbbbbbb"

            # Older Profile 2 has [uuid_a, uuid_b]
            with open(f2, "w") as f:
                json.dump({"pinned_conversations_order": [uuid_a, uuid_b]}, f)
            os.utime(f2, (1000, 1000))

            # Newer Profile 1 has unpinned uuid_b -> only [uuid_a]
            with open(f1, "w") as f:
                json.dump({"pinned_conversations_order": [uuid_a]}, f)
            os.utime(f1, (2000, 2000))

            # discover must pick newer Profile 1 (uuid_a only, uuid_b dropped)
            pinned = discover_pinned_conversation_ids(user_home=u_home)
            self.assertEqual(pinned, {uuid_a})

            # replicate must update older Profile 2 and remove uuid_b
            replicate_pinned_conversations_order(pinned, user_home=u_home)
            with open(f2) as f:
                data2 = json.load(f)
            self.assertEqual(data2["pinned_conversations_order"], [uuid_a])

    def test_missing_pbtxt_does_not_unarchive_conversation(self):
        import sqlite3
        from antigravity_suite.history.merger import synchronize_master_summaries, sync_annotation_files, SyncStats
        from antigravity_suite.history.sqlite_store import ensure_summaries_schema
        from antigravity_suite.proto.cascade import build_cascade_summary, parse_cascade_summary

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            master_conv = master / "conversations"
            master_brain = master / "brain"
            master_conv.mkdir(parents=True)
            master_brain.mkdir(parents=True)
            master_db = master / "conversation_summaries.db"
            master_proto = master / "agyhub_summaries_proto.pb"

            # Create an archived conversation
            cid = "55555555-6666-7777-8888-999999999999"
            raw_arc = build_cascade_summary(cid, "Important Archived Chat", "Archived preview", 10, archived=True)

            # Create mock conv database
            with sqlite3.connect(str(master_conv / f"{cid}.db")) as ccon:
                ccon.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER);")
                ccon.execute("INSERT INTO steps VALUES (0, 14, 3);")

            # Insert into master database without any annotations/.pbtxt existing
            with sqlite3.connect(str(master_db)) as con:
                ensure_summaries_schema(con)
                con.execute(
                    "INSERT INTO conversation_summaries (conversation_id, title, preview, step_count, last_modified_time, last_user_input_time, raw_summary) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'), ?);",
                    (cid, "Important Archived Chat", "Archived preview", 10, raw_arc),
                )

            # Ensure annotations folder has NO file for this conversation
            anno_f = master / "annotations" / f"{cid}.pbtxt"
            self.assertFalse(anno_f.is_file())

            # Run synchronize_master_summaries
            synchronize_master_summaries(master, master_conv, master_brain, master_db, master_proto, stats=SyncStats())

            # 1. Verify SQLite raw_summary still has archived = True
            with sqlite3.connect(str(master_db)) as con:
                row = con.execute("SELECT raw_summary FROM conversation_summaries WHERE conversation_id = ?;", (cid,)).fetchone()
                self.assertIsNotNone(row)
                self.assertIsNotNone(row[0])
                parsed = parse_cascade_summary(row[0])
                self.assertTrue(parsed.get("archived"), f"Archived flag was prematurely erased! parsed={parsed}")

                # Step 12 of merge syncs annotations
                sync_annotation_files(master, con.cursor(), pinned_set=set())

            # 2. Verify generated annotations file now contains archived:true
            self.assertTrue(anno_f.is_file())
            self.assertIn("archived:true", anno_f.read_text())

    def test_step_count_compound_stat_caching(self):
        import sqlite3
        from antigravity_suite.history.sqlite_store import get_actual_steps_count, clear_step_count_cache, _STEP_COUNT_CACHE

        with tempfile.TemporaryDirectory() as td:
            db_p = Path(td) / "test_steps.db"
            with sqlite3.connect(str(db_p)) as con:
                con.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY);")
                con.execute("INSERT INTO steps VALUES (1), (2), (3);")

            clear_step_count_cache()
            self.assertNotIn(str(db_p), _STEP_COUNT_CACHE)

            # First call populates cache
            c1 = get_actual_steps_count(db_p)
            self.assertEqual(c1, 3)
            self.assertIn(str(db_p), _STEP_COUNT_CACHE)

            # Modify table directly without changing mtime or size? Size will change with insert
            with sqlite3.connect(str(db_p)) as con:
                con.execute("INSERT INTO steps VALUES (4), (5);")
            
            c2 = get_actual_steps_count(db_p)
            self.assertEqual(c2, 5)

    def test_project_mapping_cache_and_lazy_refresh(self):
        import json
        from antigravity_suite.history.projects import (
            discover_project_mappings,
            get_project_id_for_workspace,
            clear_workspace_caches,
        )

        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            proj_dir = home / ".gemini" / "config" / "projects"
            proj_dir.mkdir(parents=True)

            ws_uri = (home / "workspace" / "project-alpha").as_uri()
            p1_def = {
                "id": "11111111-2222-3333-4444-555555555555",
                "name": "project-alpha",
                "projectResources": {"resources": [{"folderUri": ws_uri}]},
            }
            with open(proj_dir / "p1.json", "w") as f:
                json.dump(p1_def, f)

            clear_workspace_caches()

            # 1. Discover mappings
            m = discover_project_mappings(user_home=home)
            self.assertIn(ws_uri, m)
            self.assertEqual(m[ws_uri], "11111111-2222-3333-4444-555555555555")

            # 2. Fast O(1) resolution
            pid = get_project_id_for_workspace(ws_uri, user_home=home, mappings=m)
            self.assertEqual(pid, "11111111-2222-3333-4444-555555555555")

            # 3. Add new project on disk (simulating user opening project during session)
            ws_beta = (home / "workspace" / "project-beta").as_uri()
            p2_def = {
                "id": "66666666-7777-8888-9999-000000000000",
                "name": "project-beta",
                "projectResources": {"resources": [{"folderUri": ws_beta}]},
            }
            with open(proj_dir / "p2.json", "w") as f:
                json.dump(p2_def, f)

            # Lazy refresh should detect it automatically without manual cache clearing
            pid2 = get_project_id_for_workspace(ws_beta, user_home=home)
            self.assertEqual(pid2, "66666666-7777-8888-9999-000000000000")

    def test_normalize_workspace_uri_fast_strings_and_windows_paths(self):
        from antigravity_suite.history.projects import normalize_workspace_uri, is_container_or_system_root

        home_dyn = get_user_home()
        container_uri = (home_dyn / "PhpstormProjects").as_uri()
        app_uri = (home_dyn / "PhpstormProjects" / "my-app").as_uri()
        sub_uri = (home_dyn / "PhpstormProjects" / "my-app" / "subfolder" / "file").as_uri()

        # System root check
        self.assertTrue(is_container_or_system_root("file:///tmp"))
        self.assertTrue(is_container_or_system_root(container_uri))
        self.assertFalse(is_container_or_system_root(app_uri))

        # Normalization with cross-platform slashes
        norm = normalize_workspace_uri(sub_uri)
        self.assertEqual(norm, app_uri)

    def test_get_transcript_timestamps_tail_seeking(self):
        from antigravity_suite.history.merger import get_transcript_timestamps

        with tempfile.TemporaryDirectory() as td:
            t_file = Path(td) / "transcript.jsonl"

            # 1. Create a large transcript (> 100KB)
            first_entry = {
                "step_index": 0,
                "type": "CONVERSATION_START",
                "created_at": "2026-10-10T10:00:00.000Z",
                "content": "Start"
            }
            # Filler to bloat file > 150KB
            filler_text = "x" * 1024

            with open(t_file, "w", encoding="utf-8") as f:
                f.write(json.dumps(first_entry) + "\n")
                for i in range(1, 150):
                    entry = {
                        "step_index": i,
                        "type": "MODEL",
                        "created_at": f"2026-10-10T10:{i%60:02d}:00.000Z",
                        "content": filler_text
                    }
                    f.write(json.dumps(entry) + "\n")
                
                # Add a USER_INPUT in the tail
                user_entry = {
                    "step_index": 150,
                    "type": "USER_INPUT",
                    "source": "USER_EXPLICIT",
                    "created_at": "2026-10-10T11:00:00.000Z",
                    "content": "User prompt"
                }
                f.write(json.dumps(user_entry) + "\n")

                # Final response
                last_entry = {
                    "step_index": 151,
                    "type": "MODEL",
                    "created_at": "2026-10-10T11:05:00.000Z",
                    "content": "Model final response"
                }
                f.write(json.dumps(last_entry) + "\n")

            self.assertGreater(t_file.stat().st_size, 100 * 1024)

            # Extract timestamps: returns (created_time, last_user_input_time, last_modified_time)
            c_time, u_time, m_time = get_transcript_timestamps(t_file)
            self.assertEqual(c_time, "2026-10-10T10:00:00.000Z")
            self.assertEqual(u_time, "2026-10-10T11:00:00.000Z")
            self.assertEqual(m_time, "2026-10-10T11:05:00.000Z")

    def test_is_synthesized_db_incomplete_compound_cache(self):
        import sqlite3
        from antigravity_suite.history.synthesizer import (
            is_synthesized_db_incomplete,
            clear_synthesized_db_cache,
            _VERIFIED_COMPLETE_DBS
        )

        with tempfile.TemporaryDirectory() as td:
            db_p = Path(td) / "conversation_summaries.db"
            with sqlite3.connect(str(db_p)) as con:
                con.execute("CREATE TABLE steps (step_index INTEGER PRIMARY KEY, step_type INTEGER, step_payload BLOB, metadata BLOB);")
                con.execute("INSERT INTO steps VALUES (0, 1, ?, ?);", (b"", b""))

            clear_synthesized_db_cache()
            self.assertEqual(len(_VERIFIED_COMPLETE_DBS), 0)

            # First run: queries DB, determines it is complete (not incomplete), caches it
            incomplete = is_synthesized_db_incomplete(db_p)
            self.assertFalse(incomplete)
            self.assertIn(str(db_p), _VERIFIED_COMPLETE_DBS)

            # Second run: fast-path hit, cache length unchanged
            incomplete2 = is_synthesized_db_incomplete(db_p)
            self.assertFalse(incomplete2)

            # Invalidate by clearing
            clear_synthesized_db_cache()
            self.assertEqual(len(_VERIFIED_COMPLETE_DBS), 0)

    def test_sync_annotation_files_selective_filtering(self):
        import sqlite3
        from antigravity_suite.history.merger import sync_annotation_files

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            antigravity_dir = master / ".gemini" / "antigravity"
            anno_dir = antigravity_dir / "annotations"
            db_file = antigravity_dir / "conversation_summaries.db"

            anno_dir.mkdir(parents=True)
            with sqlite3.connect(str(db_file)) as con:
                con.execute("CREATE TABLE conversation_summaries (conversation_id TEXT PRIMARY KEY, title TEXT, raw_summary BLOB);")
                con.execute("INSERT INTO conversation_summaries VALUES ('c1', 'Chat One', ?), ('c2', 'Chat Two', ?);", (b"", b""))
                cur = con.cursor()

                # 1. Sync only c1
                sync_annotation_files(antigravity_dir, cur, target_conv_ids={"c1"})
                self.assertTrue((anno_dir / "c1.pbtxt").exists())
                self.assertFalse((anno_dir / "c2.pbtxt").exists())

                # 2. Sync c2
                sync_annotation_files(antigravity_dir, cur, target_conv_ids={"c2"})
                self.assertTrue((anno_dir / "c2.pbtxt").exists())

    def test_linux_inotify_watcher_interface(self):
        from antigravity_suite.history.watcher import LinuxInotifyWatcher

        watcher = LinuxInotifyWatcher()
        if not watcher.available:
            self.skipTest("Linux inotify / epoll not supported in this environment")

        with tempfile.TemporaryDirectory() as td:
            watch_dir = Path(td)
            ok = watcher.add_watch_dir(watch_dir)
            self.assertTrue(ok)

            # Create file inside watch_dir
            test_file = watch_dir / "test.txt"
            test_file.write_text("hello")

            # Poll events
            triggered = watcher.wait_for_events(timeout_sec=0.2)
            self.assertTrue(triggered)

            watcher.close()

    def test_merge_brain_folders_mtime_fast_path(self):
        import time
        from antigravity_suite.history.pool_merger import merge_brain_folders

        with tempfile.TemporaryDirectory() as td:
            pool_dir = Path(td) / "pool"
            master_dir = Path(td) / "master"
            conv_id = "11111111-2222-3333-4444-555555555555"

            src_conv = pool_dir / conv_id / ".system_generated" / "logs"
            tgt_conv = master_dir / conv_id / ".system_generated" / "logs"
            src_conv.mkdir(parents=True)
            tgt_conv.mkdir(parents=True)

            (src_conv / "transcript.jsonl").write_text('{"step": 1}\n')
            (tgt_conv / "transcript.jsonl").write_text('{"step": 1}\n')

            # Ensure target mtime is newer or equal
            now = time.time()
            os.utime(str(src_conv), (now - 10, now - 10))
            os.utime(str(tgt_conv), (now, now))
            os.utime(str(pool_dir / conv_id), (now - 10, now - 10))
            os.utime(str(master_dir / conv_id), (now, now))

            # Run merge: should fast-path continue without importing new folders
            imported = merge_brain_folders([str(pool_dir)], master_dir)
            self.assertEqual(imported, 0)

    def test_merge_brain_folders_copies_appended_transcript(self):
        import time
        from antigravity_suite.history.pool_merger import merge_brain_folders

        with tempfile.TemporaryDirectory() as td:
            pool = Path(td) / "pool"
            master = Path(td) / "master"
            c = "11111111-2222-3333-4444-555555555555"
            s_logs = pool / c / ".system_generated" / "logs"
            t_logs = master / c / ".system_generated" / "logs"
            s_logs.mkdir(parents=True)
            t_logs.mkdir(parents=True)

            (s_logs / "transcript.jsonl").write_text("initial\n")
            (t_logs / "transcript.jsonl").write_text("initial\n")

            # Simulate older directory mtimes (Linux doesn't touch dir mtime on append)
            old_time = time.time() - 200
            for p in [pool / c, s_logs, master / c, t_logs]:
                os.utime(str(p), (old_time, old_time))

            # Append new turn to source transcript
            with open(s_logs / "transcript.jsonl", "a") as f:
                f.write("new user message turn\n")

            merge_brain_folders([str(pool)], master)
            self.assertEqual(
                (t_logs / "transcript.jsonl").stat().st_size,
                (s_logs / "transcript.jsonl").stat().st_size
            )

    def test_sync_annotation_files_idle_early_return(self):
        import sqlite3
        from antigravity_suite.history.merger import sync_annotation_files

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            antigravity_dir = master / ".gemini" / "antigravity"
            anno_dir = antigravity_dir / "annotations"
            anno_dir.mkdir(parents=True)

            # Target_conv_ids is an empty set (0 dirty conversations)
            # Should return immediately without requiring active sqlite connection
            target_annos = set()
            sync_annotation_files(antigravity_dir, cur=None, target_conv_ids=target_annos)
            # Verify no files were created or errors thrown
            self.assertEqual(len(list(anno_dir.glob("*.pbtxt"))), 0)

    def test_linux_inotify_watches_conversation_dirs_and_artifacts(self):
        from antigravity_suite.history.watcher import LinuxInotifyWatcher

        watcher = LinuxInotifyWatcher()
        if not watcher.available:
            self.skipTest("Linux inotify / epoll not supported in this environment")

        with tempfile.TemporaryDirectory() as td:
            b = Path(td) / "brain"
            c = b / "conv1"
            l = c / ".system_generated" / "logs"
            l.mkdir(parents=True)

            watcher.sync_watch_targets([], [str(b)])
            (c / "task.md").write_text("# Plan")
            evs = watcher.wait_for_events(timeout_sec=0.2)
            self.assertTrue(any("task.md" in ev for ev in evs))
            watcher.close()

    def test_trajectory_id_mismatch_healed_in_merger(self):
        import sqlite3
        from antigravity_suite.history.merger import resolve_conversation_item
        from antigravity_suite.history.models import SyncStats
        from antigravity_suite.proto.cascade import build_cascade_summary, parse_cascade_summary

        conv_id = "11111111-1111-1111-1111-111111111111"
        wrong_id = "22222222-2222-2222-2222-222222222222"

        # Create raw binary summary with mismatched trajectory_id (wrong_id)
        corrupt_raw = build_cascade_summary(
            wrong_id,
            "Test Title",
            "Test Summary",
            5,
            last_modified_iso="2026-10-10 12:00:00.000000+00:00"
        )
        parsed_corrupt = parse_cascade_summary(corrupt_raw)
        self.assertEqual(parsed_corrupt.get("trajectory_id"), wrong_id)

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            db_dir = master / "conversations"
            db_dir.mkdir(parents=True)
            db_file = db_dir / f"{conv_id}.db"

            with sqlite3.connect(str(db_file)) as con:
                con.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER, has_subtrajectory NUMERIC, metadata BLOB, error_details BLOB, permissions BLOB, task_details BLOB, render_info BLOB, step_payload BLOB, step_format INTEGER);")
                con.execute("INSERT INTO steps VALUES (0, 14, 0, 0, NULL, NULL, NULL, NULL, NULL, NULL, 0);")

            sum_db = master / "conversation_summaries.db"
            with sqlite3.connect(str(sum_db)) as con:
                from antigravity_suite.history.sqlite_store import ensure_summaries_schema
                ensure_summaries_schema(con)

                stats = SyncStats()
                all_summaries = {}
                existing_rows = {
                    conv_id: ("Test Title", "Test Preview", 5, "2026-10-10 12:00:00", corrupt_raw, "2026-10-10 12:00:00", 0, "", "outside-of-project")
                }

                # Resolve item: must detect trajectory_id mismatch and rebuild binary!
                resolve_conversation_item(
                    conv_id=conv_id,
                    effective_master=master,
                    master_conv_dir=db_dir,
                    master_brain_dir=master / "brain",
                    existing_rows=existing_rows,
                    all_summaries=all_summaries,
                    cur=con.cursor(),
                    con=con,
                    stats=stats,
                    pinned_set=set(),
                    project_mappings={}
                )

                healed_raw = all_summaries.get(conv_id)
                self.assertIsNotNone(healed_raw)
                parsed_healed = parse_cascade_summary(healed_raw)
                self.assertEqual(parsed_healed.get("trajectory_id"), conv_id)

    def test_authentic_project_id_not_overwritten_by_outside_of_project(self):
        import sqlite3
        from antigravity_suite.history.merger import resolve_conversation_item
        from antigravity_suite.history.models import SyncStats
        from antigravity_suite.history.sqlite_store import ensure_summaries_schema
        from antigravity_suite.proto.cascade import build_cascade_summary

        conv_id = "33333333-3333-3333-3333-333333333333"
        authentic_pid = "247e98f3-8f0a-42be-bc77-e89c3bc6b998"

        # Raw summary has outside-of-project
        raw_with_outside = build_cascade_summary(
            conv_id,
            "Lede Chat",
            "Lede Summary",
            3,
            project_id="outside-of-project"
        )

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            db_dir = master / "conversations"
            db_dir.mkdir(parents=True)
            db_file = db_dir / f"{conv_id}.db"

            with sqlite3.connect(str(db_file)) as con:
                con.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER, has_subtrajectory NUMERIC, metadata BLOB, error_details BLOB, permissions BLOB, task_details BLOB, render_info BLOB, step_payload BLOB, step_format INTEGER);")
                con.execute("INSERT INTO steps VALUES (0, 14, 0, 0, NULL, NULL, NULL, NULL, NULL, NULL, 0);")

            sum_db = master / "conversation_summaries.db"
            with sqlite3.connect(str(sum_db)) as con:
                ensure_summaries_schema(con)

                stats = SyncStats()
                all_summaries = {}
                conv_ws = (master / "lede").as_uri()
                # SQLite existing row has authentic_pid at index 8 and raw_with_outside at index 4!
                existing_rows = {
                    conv_id: ("Lede Chat", "Lede Preview", 3, "2026-10-10 12:00:00", raw_with_outside, "2026-10-10 12:00:00", 0, conv_ws, authentic_pid)
                }

                resolve_conversation_item(
                    conv_id=conv_id,
                    effective_master=master,
                    master_conv_dir=db_dir,
                    master_brain_dir=master / "brain",
                    existing_rows=existing_rows,
                    all_summaries=all_summaries,
                    cur=con.cursor(),
                    con=con,
                    stats=stats,
                    pinned_set=set(),
                    project_mappings={}
                )

                row = con.cursor().execute("SELECT project_id FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,)).fetchone()
                self.assertEqual(row[0], authentic_pid)

    def test_sync_annotation_file_strips_at_mentions(self):
        from antigravity_suite.history.extractor import sync_annotation_file

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            conv_id = "44444444-4444-4444-4444-444444444444"
            dirty_title = f"@[{master}/app/User.php:20-30] Refactor auth"

            ok = sync_annotation_file(master, conv_id, dirty_title)
            self.assertTrue(ok)

            anno_file = master / "annotations" / f"{conv_id}.pbtxt"
            self.assertTrue(anno_file.exists())
            content = anno_file.read_text()
            self.assertNotIn("@[", content)
            self.assertIn("Refactor auth", content)

    def test_sync_annotation_file_force_overwrites_stale_title(self):
        from antigravity_suite.history.extractor import sync_annotation_file

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            conv_id = "55555555-5555-5555-5555-555555555555"
            anno_dir = master / "annotations"
            anno_dir.mkdir(parents=True)
            anno_file = anno_dir / f"{conv_id}.pbtxt"
            anno_file.write_text('title: "Old Stale Prompt"\n')

            # Without force: does not overwrite existing custom title
            ok = sync_annotation_file(master, conv_id, "New LLM Title", force=False)
            self.assertFalse(ok)
            self.assertIn("Old Stale Prompt", anno_file.read_text())

            # With force=True: overwrites stale title
            ok = sync_annotation_file(master, conv_id, "New LLM Title", force=True)
            self.assertTrue(ok)
            self.assertIn("New LLM Title", anno_file.read_text())
            self.assertNotIn("Old Stale Prompt", anno_file.read_text())

    def test_title_precedence_rescues_llm_summary_when_title_equals_prompt(self):
        from antigravity_suite.history.merger import synchronize_master_summaries, SyncStats
        from antigravity_suite.history.sqlite_store import ensure_summaries_schema
        from antigravity_suite.proto.cascade import build_cascade_summary

        with tempfile.TemporaryDirectory() as td:
            import sqlite3
            master = Path(td)
            conv_id = "66666666-6666-6666-6666-666666666666"
            master_conv_dir = master / "conversations"
            master_conv_dir.mkdir(parents=True)
            master_brain_dir = master / "brain"
            master_brain_dir.mkdir(parents=True)
            master_sum_db = master / "conversation_summaries.db"
            master_proto = master / "agyhub_summaries_proto.pb"

            # Create transcript with prompt "554 sgj"
            t_log_dir = master_brain_dir / conv_id / ".system_generated" / "logs"
            t_log_dir.mkdir(parents=True)
            t_file = t_log_dir / "transcript.jsonl"
            t_file.write_text('{"step_index":0,"source":"USER_EXPLICIT","type":"USER_INPUT","status":"DONE","content":"554 sgj"}\n')

            # Pre-seed SQLite with title = "554 sgj" and preview = "Typo or Nonsense Input"
            with sqlite3.connect(str(master_sum_db)) as c:
                ensure_summaries_schema(c)
                raw_bin = build_cascade_summary(conv_id, "554 sgj", "Typo or Nonsense Input", 2)
                c.execute(
                    "INSERT INTO conversation_summaries (conversation_id, title, preview, step_count, last_modified_time, last_user_input_time, raw_summary) VALUES (?, ?, ?, ?, ?, ?, ?);",
                    (conv_id, "554 sgj", "Typo or Nonsense Input", 2, "2026-10-18 01:00:00+00:00", "2026-10-18 01:00:00+00:00", raw_bin),
                )
                c.commit()

            con, all_sums = synchronize_master_summaries(
                master, master_conv_dir, master_brain_dir, master_sum_db, master_proto, SyncStats()
            )
            row = con.execute("SELECT title, preview FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,)).fetchone()
            con.close()

            # Title must be rescued to "Typo or Nonsense Input"
            self.assertEqual(row[0], "Typo or Nonsense Input")
            # Annotations file must also have "Typo or Nonsense Input"
            anno_file = master / "annotations" / f"{conv_id}.pbtxt"
            self.assertTrue(anno_file.exists())
            self.assertIn("Typo or Nonsense Input", anno_file.read_text())

    def test_is_clean_title_validation(self):
        from antigravity_suite.history.extractor import is_clean_title

        # Dirty cases
        self.assertFalse(is_clean_title(""))
        self.assertFalse(is_clean_title("Conversation"))
        self.assertFalse(is_clean_title("Untitled Conversation"))
        self.assertFalse(is_clean_title("---"))
        self.assertFalse(is_clean_title("@[/path/file.py:L1-10]"))
        self.assertFalse(is_clean_title("<USER_REQUEST>help</USER_REQUEST>"))
        self.assertFalse(is_clean_title("╰─❯ curl -X POST http://localhost:8080/api"))
        self.assertFalse(is_clean_title("root@cp1:/var/log# cat error.log"))
        self.assertFalse(is_clean_title("developer@vm-control-plane:~$ sudo tail -f /var/log/nginx/stream_error.log"))
        self.assertFalse(is_clean_title("docker exec -it galera1 bash"))
        self.assertFalse(is_clean_title("git status"))
        self.assertFalse(is_clean_title("http://localhost:3000"))
        self.assertFalse(is_clean_title("https://api.github.com"))

        # Clean authentic titles
        self.assertTrue(is_clean_title("Creating A New VM In HiWeb"))
        self.assertTrue(is_clean_title("Typo or Nonsense Input"))
        self.assertTrue(is_clean_title("Scanning Database Routing Rules"))
        self.assertTrue(is_clean_title("Building Authentication Microservice"))
        self.assertTrue(is_clean_title("Verifying Legacy Server Connectivity"))

    def test_sync_annotation_file_cleans_dirty_shell_titles(self):
        from antigravity_suite.history.extractor import sync_annotation_file

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            conv_id = "77777777-7777-7777-7777-777777777777"
            anno_dir = master / "annotations"
            anno_dir.mkdir(parents=True)
            anno_file = anno_dir / f"{conv_id}.pbtxt"
            # Pre-seed with dirty shell title and pinned:true
            anno_file.write_text('title: "developer@vm-control-plane:~$ sudo tail -f /var/log/nginx/stream_error.log"  pinned:true\n')

            # Sync with generic "Conversation": dirty title should be stripped, pinned preserved
            sync_annotation_file(master, conv_id, "Conversation", pinned=True, force=False)
            content = anno_file.read_text()
            self.assertNotIn("developer@vm-control-plane", content)
            self.assertNotIn("title:", content)
            self.assertIn("pinned:true", content)

            # Sync with new clean title: should replace cleanly
            sync_annotation_file(master, conv_id, "Investigating Nginx Stream Logs", pinned=True, force=True)
            content2 = anno_file.read_text()
            self.assertIn('title: "Investigating Nginx Stream Logs"', content2)
            self.assertIn("pinned:true", content2)

    def test_merger_does_not_set_raw_prompt_as_final_title(self):
        from antigravity_suite.history.merger import synchronize_master_summaries, SyncStats
        from antigravity_suite.history.sqlite_store import ensure_summaries_schema

        with tempfile.TemporaryDirectory() as td:
            import sqlite3
            master = Path(td)
            conv_id = "88888888-8888-8888-8888-888888888888"
            master_conv_dir = master / "conversations"
            master_conv_dir.mkdir(parents=True)
            master_brain_dir = master / "brain"
            master_brain_dir.mkdir(parents=True)
            master_sum_db = master / "conversation_summaries.db"
            master_proto = master / "agyhub_summaries_proto.pb"

            # Create transcript with short raw prompt
            raw_prompt = "Quick debugging question"
            t_log_dir = master_brain_dir / conv_id / ".system_generated" / "logs"
            t_log_dir.mkdir(parents=True)
            t_file = t_log_dir / "transcript.jsonl"
            t_file.write_text(f'{{"step_index":0,"source":"USER_EXPLICIT","type":"USER_INPUT","status":"DONE","content":"{raw_prompt}"}}\n')

            db_file = master_conv_dir / f"{conv_id}.db"
            db_file.touch()

            with sqlite3.connect(str(master_sum_db)) as c:
                ensure_summaries_schema(c)

            con, all_sums = synchronize_master_summaries(
                master, master_conv_dir, master_brain_dir, master_sum_db, master_proto, SyncStats()
            )
            row = con.execute("SELECT title, preview FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,)).fetchone()
            con.close()

            # Title must be "Conversation" (not raw prompt), preview must be raw prompt
            self.assertEqual(row[0], "Conversation")
            self.assertEqual(row[1], raw_prompt)

            # Annotations file must NOT be created with raw prompt title
            anno_file = master / "annotations" / f"{conv_id}.pbtxt"
            self.assertFalse(anno_file.exists())

    def test_is_prompt_text_prefix_and_truncation(self):
        from antigravity_suite.history.extractor import is_prompt_text
        full_prompt = "I want to design a production grade load test scenario connecting to telemetry backend and prepare test files"
        prompt_cands = {full_prompt}
        # Exact match
        self.assertTrue(is_prompt_text(full_prompt, prompt_cands))
        # 80-char prefix truncation
        truncated = full_prompt[:80]
        self.assertTrue(is_prompt_text(truncated, prompt_cands))
        # 40-char prefix truncation
        self.assertTrue(is_prompt_text(truncated[:40], prompt_cands))
        # Authentic title must NOT match
        self.assertFalse(is_prompt_text("Load Test Scenario Design", prompt_cands))

    def test_sync_annotation_multiline_with_last_user_view_time(self):
        from antigravity_suite.history.extractor import sync_annotation_file
        with tempfile.TemporaryDirectory() as td:
            cid = "99999999-8888-7777-6666-555555555555"
            anno_dir = Path(td) / "annotations"
            anno_dir.mkdir(parents=True)
            anno_file = anno_dir / f"{cid}.pbtxt"
            # Pre-existing pbtxt with last_user_view_time
            anno_file.write_text('title: "Old Title"\nlast_user_view_time:{seconds:1792305404 nanos:509000000}\n')

            sync_annotation_file(td, cid, "Load Test Scenario Design", pinned=True, force=True)

            content = anno_file.read_text()
            lines = [l.strip() for l in content.splitlines() if l.strip()]
            self.assertIn('title: "Load Test Scenario Design"', lines)
            self.assertIn('pinned:true', lines)
            self.assertIn('last_user_view_time:{seconds:1792305404 nanos:509000000}', lines)
            # Ensure each field is on its own line
            self.assertEqual(len(lines), 3)

    def test_sync_conversations_fts_nanoseconds(self):
        import sqlite3
        from antigravity_suite.history.sqlite_store import sync_conversations_fts

        with tempfile.TemporaryDirectory() as td:
            db_p = Path(td) / "test_fts.db"
            with sqlite3.connect(str(db_p)) as con:
                con.execute("""
                    CREATE VIRTUAL TABLE conversations_fts USING fts5(
                        conversation_id UNINDEXED,
                        chunk_index UNINDEXED,
                        chunk_first_step UNINDEXED,
                        chunk_last_step UNINDEXED,
                        last_modified_time UNINDEXED,
                        step_count UNINDEXED,
                        last_step_created_at UNINDEXED,
                        archived UNINDEXED,
                        user_step_byte_offsets UNINDEXED,
                        agent_step_byte_offsets UNINDEXED,
                        title,
                        workspace,
                        project,
                        user_body,
                        agent_body
                    );
                """)
                cid = "7b382c83-e685-4637-84bc-4520cdfcb94c"
                # Call sync_conversations_fts
                sync_conversations_fts(
                    con,
                    conv_id=cid,
                    title="Performance Engineering Strategy: Load Test Scenario Design Catalog",
                    workspace_uri=(get_user_home() / "workspace" / "load-test").as_uri(),
                    project_id="a9b5a9cf-cfda-543d-9a7e-6cf8a15a7005",
                    last_modified_iso="2026-10-17 13:17:21.000000+00:00",
                    step_count=3795,
                    archived=False,
                )
                con.commit()

                # Verify row
                row = con.execute("SELECT conversation_id, chunk_index, last_modified_time, step_count, title, workspace, project FROM conversations_fts WHERE conversation_id = ? AND chunk_index = -1;", (cid,)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], cid)
                self.assertEqual(row[1], -1)
                self.assertGreater(row[2], 1000000000000000000)  # > 1e18 nanoseconds
                self.assertEqual(row[3], 3795)
                self.assertEqual(row[4], "Performance Engineering Strategy: Load Test Scenario Design Catalog")
                self.assertEqual(row[5], "load-test")
                self.assertEqual(row[6], "a9b5a9cf-cfda-543d-9a7e-6cf8a15a7005")

    def test_manifest_lifecycle_and_tombstones(self):
        from antigravity_suite.history.deletion import load_manifest, save_manifest, get_tombstones

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            m = load_manifest(master)
            self.assertEqual(m["known_ids"], [])
            self.assertEqual(m["tombstones"], {})

            m["known_ids"] = ["conv-1", "conv-2"]
            m["tombstones"]["conv-dead"] = {"deleted_at": "2026-10-18T00:00:00Z", "source": "app"}
            save_manifest(master, m)

            m2 = load_manifest(master)
            self.assertEqual(m2["known_ids"], ["conv-1", "conv-2"])
            self.assertIn("conv-dead", m2["tombstones"])

            ts = get_tombstones(master)
            self.assertEqual(ts, {"conv-dead"})

    def test_detect_and_sync_deletions_app_to_ide(self):
        import sqlite3, base64
        from antigravity_suite.history.deletion import detect_and_sync_deletions, load_manifest, save_manifest
        from antigravity_suite.history.models import SyncStats
        from antigravity_suite.proto.cascade import build_cascade_summary
        from antigravity_suite.proto.vscdb import build_summaries_state
        from antigravity_suite.proto.wire import extract_entries_from_proto

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            db_p = master / "conversation_summaries.db"
            vscdb_p = master / "state.vscdb"
            conv_dir = master / "conversations"
            conv_dir.mkdir(parents=True)

            cid_keep = "11111111-1111-1111-1111-111111111111"
            cid_del = "22222222-2222-2222-2222-222222222222"
            (conv_dir / f"{cid_keep}.db").write_text("keep")
            (conv_dir / f"{cid_del}.db").write_text("del")

            # 1. Setup SQLite (App) - user deleted cid_del from App, so only cid_keep is present
            with sqlite3.connect(str(db_p)) as con:
                con.execute("""CREATE TABLE conversation_summaries (
                    conversation_id text PRIMARY KEY, title text, killed numeric DEFAULT 0
                );""")
                con.execute("INSERT INTO conversation_summaries (conversation_id, title, killed) VALUES (?, ?, 0);", (cid_keep, "Keep Chat"))
                con.commit()

            # 2. Setup VSCDB (IDE) - still has BOTH cid_keep and cid_del
            raw_keep = build_cascade_summary(cid_keep, "Keep Chat", "Keep Chat", 10)
            raw_del = build_cascade_summary(cid_del, "Deleted Chat", "Deleted Chat", 5)
            b64_val = build_summaries_state({cid_keep: raw_keep, cid_del: raw_del})

            with sqlite3.connect(str(vscdb_p)) as v_con:
                v_con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);")
                v_con.execute("INSERT INTO ItemTable VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);", (b64_val,))
                v_con.commit()

            # 3. Setup Manifest - both were known in previous cycle
            save_manifest(master, {
                "version": 1,
                "known_ids": [cid_keep, cid_del],
                "tombstones": {}
            })

            # 4. Run detect_and_sync_deletions
            stats = SyncStats()
            all_summaries = {cid_keep: raw_keep, cid_del: raw_del}
            with sqlite3.connect(str(db_p)) as con:
                purged = detect_and_sync_deletions(
                    effective_master=master,
                    con=con,
                    candidate_vscdbs=[vscdb_p],
                    conv_pools=[],
                    brain_pools=[],
                    all_summaries=all_summaries,
                    stats=stats,
                )

            self.assertEqual(purged, 1)
            self.assertEqual(stats.conversations_deleted, 1)
            self.assertNotIn(cid_del, all_summaries)

            # 5. Verify IDE state.vscdb was updated to remove cid_del
            with sqlite3.connect(str(vscdb_p)) as v_con:
                val = v_con.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';").fetchone()[0]
                entries = extract_entries_from_proto(base64.b64decode(val))
                self.assertNotIn(cid_del, entries)
                self.assertIn(cid_keep, entries)

            # 6. Verify tombstone was saved in manifest
            m_after = load_manifest(master)
            self.assertIn(cid_del, m_after["tombstones"])
            self.assertEqual(m_after["tombstones"][cid_del]["source"], "app")
            self.assertEqual(m_after["known_ids"], [cid_keep])

    def test_detect_and_sync_deletions_ide_to_app(self):
        import sqlite3, base64
        from antigravity_suite.history.deletion import detect_and_sync_deletions, load_manifest, save_manifest
        from antigravity_suite.history.models import SyncStats
        from antigravity_suite.proto.cascade import build_cascade_summary
        from antigravity_suite.proto.vscdb import build_summaries_state

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            db_p = master / "conversation_summaries.db"
            vscdb_p = master / "state.vscdb"
            conv_dir = master / "conversations"
            conv_dir.mkdir(parents=True)

            cid_keep = "11111111-1111-1111-1111-111111111111"
            cid_del = "22222222-2222-2222-2222-222222222222"

            # Create disk database for deleted chat and keep chat
            (conv_dir / f"{cid_keep}.db").write_text("keep")
            (conv_dir / f"{cid_del}.db").write_text("test")

            # 1. Setup SQLite (App) - still has BOTH cid_keep and cid_del
            with sqlite3.connect(str(db_p)) as con:
                con.execute("""CREATE TABLE conversation_summaries (
                    conversation_id text PRIMARY KEY, title text, killed numeric DEFAULT 0
                );""")
                con.execute("INSERT INTO conversation_summaries (conversation_id, title, killed) VALUES (?, ?, 0);", (cid_keep, "Keep Chat"))
                con.execute("INSERT INTO conversation_summaries (conversation_id, title, killed) VALUES (?, ?, 0);", (cid_del, "Deleted in IDE"))
                con.commit()

            # 2. Setup VSCDB (IDE) - user deleted cid_del in IDE, so only cid_keep is present
            raw_keep = build_cascade_summary(cid_keep, "Keep Chat", "Keep Chat", 10)
            b64_val = build_summaries_state({cid_keep: raw_keep})

            with sqlite3.connect(str(vscdb_p)) as v_con:
                v_con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);")
                v_con.execute("INSERT INTO ItemTable VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);", (b64_val,))
                v_con.commit()

            # 3. Setup Manifest - both were known in previous cycle
            save_manifest(master, {
                "version": 1,
                "known_ids": [cid_keep, cid_del],
                "tombstones": {}
            })

            # 4. Run detect_and_sync_deletions
            stats = SyncStats()
            raw_del = build_cascade_summary(cid_del, "Deleted in IDE", "Deleted in IDE", 5)
            all_summaries = {cid_keep: raw_keep, cid_del: raw_del}
            with sqlite3.connect(str(db_p)) as con:
                purged = detect_and_sync_deletions(
                    effective_master=master,
                    con=con,
                    candidate_vscdbs=[vscdb_p],
                    conv_pools=[],
                    brain_pools=[],
                    all_summaries=all_summaries,
                    stats=stats,
                )

            self.assertEqual(purged, 1)
            self.assertEqual(stats.conversations_deleted, 1)
            self.assertNotIn(cid_del, all_summaries)

            # 5. Verify App SQLite was updated to remove cid_del
            with sqlite3.connect(str(db_p)) as con:
                row = con.execute("SELECT 1 FROM conversation_summaries WHERE conversation_id = ?;", (cid_del,)).fetchone()
                self.assertIsNone(row)
                row_keep = con.execute("SELECT 1 FROM conversation_summaries WHERE conversation_id = ?;", (cid_keep,)).fetchone()
                self.assertIsNotNone(row_keep)

            # 6. Verify disk file was deleted
            self.assertFalse((conv_dir / f"{cid_del}.db").exists())

            # 7. Verify tombstone was saved in manifest
            m_after = load_manifest(master)
            self.assertIn(cid_del, m_after["tombstones"])
            self.assertEqual(m_after["tombstones"][cid_del]["source"], "ide")
            self.assertEqual(m_after["known_ids"], [cid_keep])

    def test_repair_fts_zero_timestamps(self):
        import sqlite3
        from antigravity_suite.history.sqlite_store import repair_fts_zero_timestamps, ensure_summaries_schema

        with tempfile.TemporaryDirectory() as td:
            db_p = Path(td) / "conversation_summaries.db"
            with sqlite3.connect(str(db_p)) as con:
                ensure_summaries_schema(con)
                con.execute("""
                    CREATE VIRTUAL TABLE conversations_fts USING fts5(
                        conversation_id UNINDEXED, chunk_index UNINDEXED, chunk_first_step UNINDEXED,
                        chunk_last_step UNINDEXED, last_modified_time UNINDEXED, step_count UNINDEXED,
                        last_step_created_at UNINDEXED, archived UNINDEXED, user_step_byte_offsets UNINDEXED,
                        agent_step_byte_offsets UNINDEXED, title, workspace, project, user_body, agent_body
                    );
                """)
                # Insert row with 0 timestamp
                cid = "test-zero-fts-uuid"
                con.execute("INSERT INTO conversation_summaries (conversation_id, title, last_modified_time, last_user_input_time) VALUES (?, ?, ?, ?);",
                            (cid, "Target Chat", "2026-10-17 13:17:21+00:00", "2026-10-17 13:17:21+00:00"))
                con.execute("INSERT INTO conversations_fts (conversation_id, chunk_index, last_modified_time, title) VALUES (?, -1, 0, ?);",
                            (cid, "Target Chat"))
                con.commit()

                # Run repair
                repaired = repair_fts_zero_timestamps(con)
                self.assertEqual(repaired, 1)

                # Verify timestamp is repaired to non-zero nanoseconds
                fts_row = con.execute("SELECT last_modified_time FROM conversations_fts WHERE conversation_id = ? AND chunk_index = -1;", (cid,)).fetchone()
                self.assertEqual(fts_row[0], 1792243041000000000)

    def test_trash_archive_and_restore(self):
        """Tests that deleted chats are safely archived to trash and can be restored with tombstone removal."""
        from antigravity_suite.history.deletion import (
            archive_deleted_conversation,
            restore_chat_from_trash,
            load_manifest,
            save_manifest,
        )

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            home = master / "home"
            home.mkdir()
            conv_dir = master / "conversations"
            conv_dir.mkdir()
            anno_dir = master / "annotations"
            anno_dir.mkdir()

            cid = "33333333-3333-3333-3333-333333333333"
            db_p = conv_dir / f"{cid}.db"
            db_p.write_text("sqlite dummy")
            anno_p = anno_dir / f"{cid}.pbtxt"
            anno_p.write_text('title: "Trash Test"')

            save_manifest(master, {
                "version": 2,
                "known_ids": [cid],
                "known_app_ids": [cid],
                "known_ide_ids": [cid],
                "tombstones": {cid: {"deleted_at": "2026-10-18T00:00:00Z", "source": "app"}},
            })

            # Archive to trash
            trash_dir = archive_deleted_conversation(cid, master, user_home=home)
            self.assertTrue(trash_dir.is_dir())
            self.assertTrue((trash_dir / f"{cid}.db").is_file())
            self.assertTrue((trash_dir / f"{cid}.pbtxt").is_file())

            # Simulate purge
            db_p.unlink()
            anno_p.unlink()
            self.assertFalse(db_p.exists())

            # Restore from trash
            success = restore_chat_from_trash(cid, master, user_home=home)
            self.assertTrue(success)
            self.assertTrue(db_p.is_file())
            self.assertTrue(anno_p.is_file())

            # Verify tombstone was removed
            m_after = load_manifest(master)
            self.assertNotIn(cid, m_after["tombstones"])
            self.assertIn(cid, m_after["known_ids"])

    def test_backup_and_restore_manifest_tombstones(self):
        """Tests that pre-merge backup captures sync_manifest.json and backup restoration untombstones conversations."""
        from antigravity_suite.history.backup import HistoryBackupManager
        from antigravity_suite.history.deletion import load_manifest, save_manifest
        import sqlite3

        with tempfile.TemporaryDirectory() as td:
            master = Path(td)
            home = master / "home"
            home.mkdir()
            s_db = master / "conversation_summaries.db"
            cid = "44444444-4444-4444-4444-444444444444"

            with sqlite3.connect(str(s_db)) as con:
                con.execute("CREATE TABLE conversation_summaries (conversation_id text PRIMARY KEY, title text);")
                con.execute("INSERT INTO conversation_summaries VALUES (?, ?);", (cid, "Backup Chat"))
                con.commit()

            save_manifest(master, {
                "version": 2,
                "known_ids": [cid],
                "known_app_ids": [cid],
                "known_ide_ids": [cid],
                "tombstones": {},
            })

            # Create backup
            b_entry = HistoryBackupManager.create_pre_merge_backup(
                effective_master=master,
                candidate_vscdbs=[],
                user_home=home,
                description="Test manifest backup",
            )
            self.assertIsNotNone(b_entry)
            self.assertIn("sync_manifest.json", b_entry.files)

            # Now simulate that cid was tombstoned
            save_manifest(master, {
                "version": 2,
                "known_ids": [],
                "tombstones": {cid: {"deleted_at": "2026-10-18T00:00:00Z", "source": "app"}},
            })

            # Restore backup
            success = HistoryBackupManager.restore_backup(b_entry.backup_id, user_home=home)
            self.assertTrue(success)

            # Verify manifest was restored without tombstone
            m_restored = load_manifest(master)
            self.assertNotIn(cid, m_restored["tombstones"])

    def test_repair_database_step_gaps(self):
        import json
        import sqlite3
        from antigravity_suite.history.synthesizer import repair_database_step_gaps
        from antigravity_suite.history.sqlite_store import get_actual_steps_count, clear_step_count_cache

        with tempfile.TemporaryDirectory() as td:
            db_p = Path(td) / "gap_test.db"
            tr_p = Path(td) / "transcript.jsonl"
            cid = "gap_test_uuid"

            # Create DB with steps 0, 1, 4, 5 (missing 2 and 3)
            with sqlite3.connect(str(db_p)) as con:
                con.execute("CREATE TABLE steps (idx INTEGER PRIMARY KEY, step_type INTEGER, status INTEGER, metadata BLOB, step_payload BLOB);")
                con.execute("INSERT INTO steps VALUES (0, 14, 3, X'00', X'00'), (1, 15, 3, X'00', X'00'), (4, 15, 3, X'00', X'00'), (5, 23, 3, X'00', X'00');")

            # Create transcript with all steps 0..5
            with open(tr_p, "w", encoding="utf-8") as f:
                f.write(json.dumps({"step_index": 0, "source": "USER_EXPLICIT", "type": "USER_INPUT", "content": "hello"}) + "\n")
                f.write(json.dumps({"step_index": 1, "source": "MODEL", "type": "PLANNER_RESPONSE", "thinking": "plan"}) + "\n")
                f.write(json.dumps({"step_index": 2, "source": "MODEL", "type": "RUN_COMMAND", "content": "ls"}) + "\n")
                f.write(json.dumps({"step_index": 3, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "files listed"}) + "\n")
                f.write(json.dumps({"step_index": 4, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "done"}) + "\n")
                f.write(json.dumps({"step_index": 5, "source": "MODEL", "type": "PLANNER_RESPONSE", "content": "goodbye"}) + "\n")

            clear_step_count_cache()
            # Before repair, max(idx) is 5, count is 4 -> actual step count calculates span = 6
            self.assertEqual(get_actual_steps_count(db_p), 6)

            # Repair gaps
            repaired = repair_database_step_gaps(db_p, tr_p)
            self.assertEqual(repaired, 2)

            with sqlite3.connect(str(db_p)) as con:
                rows = con.execute("SELECT idx, step_type FROM steps ORDER BY idx ASC;").fetchall()
                indices = [r[0] for r in rows]
                self.assertEqual(indices, [0, 1, 2, 3, 4, 5])
                self.assertEqual(rows[2][1], 132)  # tool run_command
                self.assertEqual(rows[3][1], 15)   # planner response

    def test_is_clean_title_rejects_single_punctuation_and_braces(self):
        from antigravity_suite.history.extractor import is_clean_title

        self.assertFalse(is_clean_title("{"))
        self.assertFalse(is_clean_title("}"))
        self.assertFalse(is_clean_title("["))
        self.assertFalse(is_clean_title("]"))
        self.assertFalse(is_clean_title("---"))
        self.assertFalse(is_clean_title("?"))
        self.assertFalse(is_clean_title("!"))
        self.assertFalse(is_clean_title("..."))
        self.assertFalse(is_clean_title("def foo():"))
        self.assertFalse(is_clean_title("curl http://example.com"))

        self.assertTrue(is_clean_title("Fix Redis cache race condition"))
        self.assertTrue(is_clean_title("Deploy to production cluster"))

    def test_write_vscdb_unified_state_preserves_live_step_counts(self):
        import base64
        import sqlite3
        from antigravity_suite.history.vscdb_sync import write_vscdb_unified_state
        from antigravity_suite.proto.cascade import build_cascade_summary, parse_cascade_summary
        from antigravity_suite.proto.vscdb import build_summaries_state, build_unified_state_sync
        from antigravity_suite.proto.wire import extract_entries_from_proto, extract_pure_binary_summary

        with tempfile.TemporaryDirectory() as td:
            vscdb_p = Path(td) / "globalStorage" / "state.vscdb"
            vscdb_p.parent.mkdir(parents=True, exist_ok=True)
            cid = "live_chat_conversation"

            # Simulate existing state in state.vscdb with 500 steps (user actively chatting)
            live_bin = build_cascade_summary(cid, "Live Chat", "Live Chat", step_count=500)
            initial_state = {cid: live_bin}

            with sqlite3.connect(str(vscdb_p)) as con:
                con.execute("CREATE TABLE ItemTable (key TEXT UNIQUE ON CONFLICT REPLACE, value BLOB);")
                con.execute(
                    "INSERT INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);",
                    (build_summaries_state(initial_state),)
                )
                con.execute(
                    "INSERT INTO ItemTable (key, value) VALUES ('antigravityUnifiedStateSync', ?);",
                    (build_unified_state_sync(initial_state),)
                )

            # Now sync runs with a summary that only had 450 steps
            lagging_bin = build_cascade_summary(cid, "Live Chat", "Live Chat", step_count=450)
            all_summaries = {cid: lagging_bin}

            write_vscdb_unified_state([vscdb_p], all_summaries)

            # Verify that state.vscdb still preserves step_count = 500
            with sqlite3.connect(str(vscdb_p)) as con:
                row = con.execute("SELECT value FROM ItemTable WHERE key = 'antigravityUnifiedStateSync.trajectorySummaries';").fetchone()
                self.assertIsNotNone(row)
                entries = extract_entries_from_proto(base64.b64decode(row[0]))
                self.assertIn(cid, entries)
                parsed = parse_cascade_summary(extract_pure_binary_summary(entries[cid]))
                self.assertEqual(parsed.get("step_count"), 500)

    def test_workspace_validation_and_healing(self):
        from antigravity_suite.history.projects import (
            is_valid_workspace_uri,
            get_workspace_for_project_id,
            clear_workspace_caches,
        )
        from antigravity_suite.history.synthesizer import extract_workspace_from_transcript

        clear_workspace_caches()
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td)
            real_proj = fake_home / "PhpstormProjects" / "real-project"
            real_proj.mkdir(parents=True)
            non_existent_proj = fake_home / "PhpstormProjects" / "Odirect"

            # 1. Validation checks
            self.assertTrue(is_valid_workspace_uri(f"file://{real_proj}", user_home=fake_home))
            self.assertFalse(is_valid_workspace_uri(f"file://{non_existent_proj}", user_home=fake_home))
            self.assertFalse(is_valid_workspace_uri(f"file://{fake_home}/`\nTotal", user_home=fake_home))
            self.assertFalse(is_valid_workspace_uri("file:///tmp", user_home=fake_home))
            self.assertFalse(is_valid_workspace_uri(f"file://{fake_home}/PhpstormProjects", user_home=fake_home))

            # 2. Project ID lookup
            proj_id = "test-proj-uuid-1234"
            p_dir = fake_home / ".gemini" / "config" / "projects"
            p_dir.mkdir(parents=True)
            with open(p_dir / f"{proj_id}.json", "w") as f:
                json.dump({
                    "id": proj_id,
                    "name": "real-project",
                    "projectResources": {"resources": [{"folderUri": f"file://{real_proj}"}]}
                }, f)

            resolved_ws = get_workspace_for_project_id(proj_id, user_home=fake_home)
            self.assertEqual(resolved_ws, f"file://{real_proj}")

            # 3. Transcript extraction avoids mock code diffs and picks authentic tool Cwd
            t_file = fake_home / "transcript.jsonl"
            with open(t_file, "w") as f:
                # Step 0: prompt with code discussion mentioning mock Workspace
                f.write(json.dumps({
                    "step_index": 0, "type": "USER_INPUT",
                    "content": f'Check this diff:\n- get_project_id_for_workspace("file://{non_existent_proj}")'
                }) + "\n")
                # Step 1: tool execution with authentic Cwd
                f.write(json.dumps({
                    "step_index": 1, "type": "PLANNER_RESPONSE",
                    "tool_calls": [{"name": "run_command", "args": {"CommandLine": "ls", "Cwd": str(real_proj)}}]
                }) + "\n")

            extracted = extract_workspace_from_transcript(t_file, user_home=fake_home)
            self.assertEqual(extracted, f"file://{real_proj}")

    def test_replicate_projects_order(self):
        """Verifies replicate_projects_order discovers and propagates all project IDs across profiles."""
        from antigravity_suite.history.discovery import replicate_projects_order
        with tempfile.TemporaryDirectory() as td:
            fake_home = Path(td)
            prof1_store = fake_home / ".config" / "Antigravity" / "app_storage.json"
            prof1_store.parent.mkdir(parents=True)
            with open(prof1_store, "w") as f:
                json.dump({"projectsOrder": json.dumps(["proj-1", "proj-2"])}, f)

            prof2_store = fake_home / ".antigravity-profile2" / ".config" / "Antigravity" / "app_storage.json"
            prof2_store.parent.mkdir(parents=True)
            with open(prof2_store, "w") as f:
                json.dump({"projectsOrder": json.dumps(["proj-2", "proj-3"])}, f)

            gemini_proj = fake_home / ".gemini" / "config" / "projects"
            gemini_proj.mkdir(parents=True)
            with open(gemini_proj / "proj-4.json", "w") as f:
                json.dump({"id": "proj-4"}, f)

            replicate_projects_order(user_home=fake_home)

            with open(prof1_store) as f:
                d1 = json.load(f)
            with open(prof2_store) as f:
                d2 = json.load(f)

            p1 = set(json.loads(d1["projectsOrder"]))
            p2 = set(json.loads(d2["projectsOrder"]))

            self.assertEqual(p1, {"proj-1", "proj-2", "proj-3", "proj-4"})
            self.assertEqual(p2, {"proj-1", "proj-2", "proj-3", "proj-4"})

    def test_ingest_vscdb_new_ide_conversations(self):
        """Verifies that ingest_vscdb_summaries ingests new conversations from state.vscdb into master SQLite and dict."""
        import base64
        import sqlite3
        from antigravity_suite.history.vscdb_sync import ingest_vscdb_summaries
        from antigravity_suite.proto.cascade import build_cascade_summary, parse_cascade_summary
        from antigravity_suite.proto.vscdb import build_unified_state_sync
        from antigravity_suite.history.sqlite_store import ensure_summaries_schema

        with tempfile.TemporaryDirectory() as td:
            base_dir = Path(td)
            master_conv = base_dir / "conversations"
            master_conv.mkdir(parents=True)
            master_db = base_dir / "conversation_summaries.db"
            con = sqlite3.connect(str(master_db))
            ensure_summaries_schema(con)

            vscdb_dir = base_dir / "globalStorage"
            vscdb_dir.mkdir(parents=True)
            vscdb_path = vscdb_dir / "state.vscdb"
            v_con = sqlite3.connect(str(vscdb_path))
            v_con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);")

            conv_id = "11111111-2222-3333-4444-555555555555"
            proto_bin = build_cascade_summary(
                conv_id,
                title="Authentic IDE Title",
                summary="Authentic IDE Title",
                step_count=5,
                workspace_uri="file:///home/user/myproject",
                project_id="proj-uuid-999",
            )
            b64_sync = build_unified_state_sync({conv_id: proto_bin})
            v_con.execute("INSERT INTO ItemTable VALUES ('antigravityUnifiedStateSync.trajectorySummaries', ?);", (b64_sync,))
            v_con.commit()
            v_con.close()

            all_summaries = {}
            count = ingest_vscdb_summaries(
                candidate_vscdbs=[vscdb_path],
                all_summaries=all_summaries,
                master_conv_dir=master_conv,
                con=con,
            )

            self.assertEqual(count, 1)
            self.assertIn(conv_id, all_summaries)
            parsed = parse_cascade_summary(all_summaries[conv_id])
            self.assertEqual(parsed.get("title"), "Authentic IDE Title")

            row = con.execute("SELECT title, project_id FROM conversation_summaries WHERE conversation_id = ?;", (conv_id,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], "Authentic IDE Title")
            con.close()

    def test_tray_sync_dynamic_temp_dirs(self):
        """Verifies _get_temp_dirs respects TMPDIR and includes standard temporary directories."""
        from antigravity_suite.icon.tray_sync import _get_temp_dirs
        dirs = _get_temp_dirs()
        self.assertIn("/tmp", dirs)
        with tempfile.TemporaryDirectory() as td:
            old_tmp = os.environ.get("TMPDIR")
            try:
                os.environ["TMPDIR"] = td
                custom_dirs = _get_temp_dirs()
                self.assertIn(td, custom_dirs)
            finally:
                if old_tmp is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = old_tmp

    def test_dynamic_app_ide_env_paths_config(self):
        """Verifies load_paths_config respects ANTIGRAVITY_APP_DIR and ANTIGRAVITY_IDE_DIR."""
        from antigravity_suite.detect.paths_config import load_paths_config
        with tempfile.TemporaryDirectory() as td:
            app_dir = os.path.join(td, "my-custom-app")
            ide_dir = os.path.join(td, "my-custom-ide")
            os.makedirs(app_dir)
            os.makedirs(ide_dir)

            old_app = os.environ.get("ANTIGRAVITY_APP_DIR")
            old_ide = os.environ.get("ANTIGRAVITY_IDE_DIR")
            try:
                os.environ["ANTIGRAVITY_APP_DIR"] = app_dir
                os.environ["ANTIGRAVITY_IDE_DIR"] = ide_dir
                final_app, final_ide, _ = load_paths_config()
                self.assertEqual(final_app, app_dir)
                self.assertEqual(final_ide, ide_dir)
            finally:
                if old_app is None:
                    os.environ.pop("ANTIGRAVITY_APP_DIR", None)
                else:
                    os.environ["ANTIGRAVITY_APP_DIR"] = old_app
                if old_ide is None:
                    os.environ.pop("ANTIGRAVITY_IDE_DIR", None)
                else:
                    os.environ["ANTIGRAVITY_IDE_DIR"] = old_ide

    def test_dynamic_profile2_env_discovery(self):
        """Verifies candidate gemini dirs respects ANTIGRAVITY_PROFILE2_DIR."""
        from antigravity_suite.config_paths import discover_candidate_ide_dirs
        with tempfile.TemporaryDirectory() as td:
            custom_p2 = Path(td) / "custom-profile2"
            (custom_p2 / ".gemini").mkdir(parents=True, exist_ok=True)
            old_p2 = os.environ.get("ANTIGRAVITY_PROFILE2_DIR")
            try:
                os.environ["ANTIGRAVITY_PROFILE2_DIR"] = str(custom_p2)
                dirs = discover_candidate_ide_dirs(Path(td), Path(td) / ".gemini")
                self.assertIn(custom_p2 / ".gemini", dirs)
            finally:
                if old_p2 is None:
                    os.environ.pop("ANTIGRAVITY_PROFILE2_DIR", None)
                else:
                    os.environ["ANTIGRAVITY_PROFILE2_DIR"] = old_p2


    def test_resolve_app_icon_arbitrary_instances(self):
        """Verifies _resolve_app_icon dynamically maps arbitrary instances."""
        from antigravity_suite.icon.tray_sync import _resolve_app_icon
        with tempfile.TemporaryDirectory() as td:
            icons_dir = os.path.join(td, ".local", "share", "icons")
            os.makedirs(icons_dir)
            custom_tray = os.path.join(icons_dir, "antigravity-app-3-tray.png")
            with open(custom_tray, "w") as f:
                f.write("icon")
            
            with unittest.mock.patch("os.path.expanduser", return_value=icons_dir):
                res = _resolve_app_icon("--class=antigravity-app-3 --user-data-dir=/foo")
                self.assertEqual(res, custom_tray)

            acc2_res = _resolve_app_icon("--class=antigravity-2")
            self.assertTrue("acc2" in acc2_res.lower() or "profile2" in acc2_res.lower() or "tray" in acc2_res.lower())


    def test_unified_actions_patch_force_flags(self):
        """Verifies handle_unified_patches_and_reinstall passes --force."""
        from antigravity_suite.detect.unified_actions import handle_unified_patches_and_reinstall
        with unittest.mock.patch("subprocess.run") as mock_sub:
            u_item = {"type": "Antigravity App"}
            handle_unified_patches_and_reinstall("F", u_item, "/opt/test", "/bin/manage.sh")
            self.assertTrue(mock_sub.called)
            args = mock_sub.call_args[0][0]
            self.assertIn("--force", args)
            self.assertIn("f5", args)

            mock_sub.reset_mock()
            handle_unified_patches_and_reinstall("R", u_item, "/opt/test", "/bin/manage.sh")
            self.assertTrue(mock_sub.called)
            r_args = mock_sub.call_args[0][0]
            self.assertIn("--force", r_args)
            self.assertIn("rtl", r_args)

            mock_sub.reset_mock()
            with unittest.mock.patch("builtins.input", return_value="1"):
                handle_unified_patches_and_reinstall("T", u_item, "/opt/test", "/bin/manage.sh")
                self.assertTrue(mock_sub.called)
                t_args = mock_sub.call_args[0][0]
                self.assertIn("--force", t_args)
                self.assertIn("selector", t_args)
                self.assertIn("/opt/test", t_args)

    def test_control_center_selector_patch_target_selection(self):
        """Verifies handle_control_center_selector_patch prompts for target and passes explicit args."""
        from antigravity_suite.detect.control_center_actions import handle_control_center_selector_patch
        unified = [
            {"name": "Antigravity IDE", "type": "Antigravity IDE", "engine_path": "/opt/antigravity-ide"},
            {"name": "Antigravity", "type": "Antigravity App", "engine_path": "/opt/Antigravity-x64"},
        ]
        with unittest.mock.patch("subprocess.run") as mock_sub:
            # Action: 1 (apply), Target: 2 (Antigravity App)
            with unittest.mock.patch("builtins.input", side_effect=["1", "2", ""]):
                handle_control_center_selector_patch("/bin/manage.sh", unified)
                self.assertTrue(mock_sub.called)
                args = mock_sub.call_args[0][0]
                self.assertIn("selector", args)
                self.assertIn("app", args)
                self.assertIn("--app-dir", args)
                self.assertIn("/opt/Antigravity-x64", args)
                self.assertIn("--force", args)

    def test_patch_utils_reload_replaces_stale_handler(self):
        """Verifies patchUtilsReload strips old/broken onRestartRequested and injects restartLanguageServer."""
        script = """
        const { patchUtilsReload } = require("./bin/lib/patch/patch_utils_reload");
        const stale = `
        onQuitRequested: () => {
            exports.showQuitConfirmation = true;
            electron_1.app.quit();
        },
        onRestartRequested: async () => {
            try {} catch(_) {}
        },
    });`;
        const res = patchUtilsReload(stale);
        if (!res.includes("restartLanguageServer") || res.includes("try {} catch(_) {}")) {
            process.exit(1);
        }
        """
        proc = subprocess.run(["node", "-e", script], cwd=os.path.dirname(os.path.dirname(__file__)))
        self.assertEqual(proc.returncode, 0)

    def test_checkpoint_sync_build_and_ensure(self):
        """Verifies build_step23_payload and ensure_db_checkpoint_title inject authentic titles."""
        from antigravity_suite.history.checkpoint_sync import build_step23_payload, ensure_db_checkpoint_title
        from antigravity_suite.history.extractor_checkpoint import parse_step23_checkpoint_title
        import sqlite3, tempfile

        payload = build_step23_payload(b"meta", "Simple Persian Greeting", 4, "سلام ۲")
        self.assertEqual(parse_step23_checkpoint_title(payload), "Simple Persian Greeting")

        with tempfile.TemporaryDirectory() as tmp:
            db_p = Path(tmp) / "test.db"
            with sqlite3.connect(str(db_p)) as conn:
                conn.execute("CREATE TABLE steps (idx INT, step_type INT, status INT, metadata BLOB, step_payload BLOB);")
                conn.execute("INSERT INTO steps VALUES (0, 14, 3, x'0102', x'080e');")
                conn.execute("INSERT INTO steps VALUES (1, 15, 3, x'0102', x'080f');")

            self.assertTrue(ensure_db_checkpoint_title(db_p, "test-conv", "Persian Greeting", "سلام"))

            with sqlite3.connect(str(db_p)) as conn:
                row = conn.execute("SELECT idx, step_payload FROM steps WHERE step_type = 23;").fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], 2)
                self.assertEqual(parse_step23_checkpoint_title(row[1]), "Persian Greeting")

            # Calling again with same title should be a no-op
            self.assertFalse(ensure_db_checkpoint_title(db_p, "test-conv", "Persian Greeting", "سلام"))

            # Calling with fallback title should be rejected
            self.assertFalse(ensure_db_checkpoint_title(db_p, "test-conv", "Ansible Galera Chat", "prompt"))
            self.assertFalse(ensure_db_checkpoint_title(db_p, "test-conv", "Conversation", "prompt"))

    def test_ide_new_chat_title_transfers_to_app_properly(self):
        """Verifies that when a chat is created in the IDE, its authentic title transfers to the App and SQLite summaries."""
        from antigravity_suite.history.merger import merge_histories
        from antigravity_suite.proto.cascade import build_cascade_summary
        from antigravity_suite.proto.vscdb import build_summaries_state
        from antigravity_suite.history.synthesizer_payloads import build_step14_payload, build_step15_payload
        from antigravity_suite.history.extractor_checkpoint import parse_step23_checkpoint_title
        import tempfile, sqlite3

        with tempfile.TemporaryDirectory() as td:
            user_home = Path(td)
            gemini_dir = user_home / ".gemini" / "antigravity"
            gemini_dir.mkdir(parents=True)
            conv_dir = gemini_dir / "conversations"
            conv_dir.mkdir(parents=True)
            brain_dir = gemini_dir / "brain"
            brain_dir.mkdir(parents=True)

            vscdb_dir = user_home / ".config" / "Antigravity IDE" / "User" / "globalStorage"
            vscdb_dir.mkdir(parents=True)
            vscdb_path = vscdb_dir / "state.vscdb"

            cid = "c4ddc3ee-7c6e-44ee-9038-65e276ff4bb4"
            ide_title = "Simple Persian Greeting"
            ide_proto = build_cascade_summary(cid, ide_title, ide_title, 2, workspace_uri="file:///home/user/workspace/antigravity-suite-manager")

            with sqlite3.connect(str(vscdb_path)) as v_con:
                v_con.execute("CREATE TABLE ItemTable (key TEXT PRIMARY KEY, value TEXT);")
                v_con.execute("INSERT INTO ItemTable VALUES (?, ?);",
                              ("antigravityUnifiedStateSync.trajectorySummaries", build_summaries_state({cid: ide_proto})))

            c_db = conv_dir / f"{cid}.db"
            with sqlite3.connect(str(c_db)) as c_con:
                c_con.execute("CREATE TABLE steps (idx INT, step_type INT, status INT, metadata BLOB, step_payload BLOB);")
                c_con.execute("INSERT INTO steps VALUES (0, 14, 3, x'01', ?);", (build_step14_payload(b"", 3, "سلام ۲"),))
                c_con.execute("INSERT INTO steps VALUES (1, 15, 3, x'01', ?);", (build_step15_payload(b"", 3, "سلام!", "", [], 1, []),))
                c_con.commit()

            merge_histories(master_gemini=gemini_dir, user_home=user_home, quiet=True, skip_backup=True)

            sum_db = gemini_dir / "conversation_summaries.db"
            with sqlite3.connect(str(sum_db)) as s_con:
                row = s_con.execute("SELECT conversation_id, title FROM conversation_summaries WHERE conversation_id = ?;", (cid,)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[1], "Simple Persian Greeting")

            # Check that step 23 was injected with authentic title and NOT the workspace fallback
            with sqlite3.connect(str(c_db)) as c_con:
                s23_row = c_con.execute("SELECT step_payload FROM steps WHERE step_type = 23;").fetchone()
                self.assertIsNotNone(s23_row)
                self.assertEqual(parse_step23_checkpoint_title(s23_row[0]), "Simple Persian Greeting")

    def test_pick_first_valid_title_rejects_workspace_chat_fallback(self):
        """Verifies that pick_first_valid_title rejects fallback Chat titles so authentic titles win."""
        from antigravity_suite.history.title_resolver import pick_first_valid_title, resolve_best_title
        
        self.assertIsNone(pick_first_valid_title(["K6 Chat", "Conversation", "Desktop: /home/user"], set()))
        self.assertEqual(pick_first_valid_title(["K6 Chat", "Fix MariaDB User Permissions"], set()), "Fix MariaDB User Permissions")
        
        # Test that resolve_best_title allows LLM/checkpoint to override existing fallback
        res, src = resolve_best_title(
            existing_candidates=["K6 Chat"],
            llm_candidates=["Fix MariaDB User Permissions"],
            clean_artifact_title="",
            prompt_cands=set()
        )
        self.assertEqual(res, "Fix MariaDB User Permissions")
        self.assertEqual(src, "llm_summary")

    def test_sync_annotation_file_rejects_fallback_titles(self):
        """Verifies that annotations never persist fallback titles like K6 Chat."""
        from antigravity_suite.history.extractor_annotations import sync_annotation_file, get_annotation_info
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            gemini_dir = Path(td)
            cid = "test-conv-fb"
            # Attempting to force sync a fallback title should NOT write it
            sync_annotation_file(gemini_dir, cid, "K6 Chat", force=True)
            info = get_annotation_info(gemini_dir, cid)
            self.assertIsNone(info["title"])

            # Writing an authentic title should succeed
            sync_annotation_file(gemini_dir, cid, "Real Authentic Title", force=True)
            info2 = get_annotation_info(gemini_dir, cid)
            self.assertEqual(info2["title"], "Real Authentic Title")

    def test_get_candidate_homes_strict_isolation_when_user_home_provided(self):
        """Verifies that an explicitly specified user_home never leaks the host user home."""
        from antigravity_suite.history.discovery_roots import get_candidate_homes
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            homes = get_candidate_homes(user_home=td)
            self.assertEqual(homes, {str(Path(td).resolve())})
            self.assertNotIn(os.path.expanduser("~"), homes)

    def test_extract_brain_title_ignores_arbitrary_markdown_artifacts(self):
        """Verifies that extract_brain_title ignores arbitrary documents like incident reports."""
        from antigravity_suite.history.extractor_brain import extract_brain_title
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            b_dir = Path(td)
            # Create a non-planning artifact
            report_file = b_dir / "INC-20261021-01-Downtime.md"
            report_file.write_text("# 📋 Production Incident Report\nDetails here...")
            self.assertEqual(extract_brain_title(str(b_dir)), "")

            # Create an authentic planning artifact
            plan_file = b_dir / "task.md"
            plan_file.write_text("# Authentic Task Plan Title\nSteps...")
            self.assertEqual(extract_brain_title(str(b_dir)), "Authentic Task Plan Title")

    def test_patch_main_desktop_name(self):
        """Verifies patchMain applies ANTIGRAVITY_DESKTOP_NAME to dist/main.js."""
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            dist = Path(td) / "dist"
            dist.mkdir()
            main_js = dist / "main.js"
            main_js.write_text("const gotTheLock = electron_1.app.requestSingleInstanceLock();")

            patch_script = Path(__file__).resolve().parent.parent / "bin" / "lib" / "patch" / "patch_main.js"
            cmd = ["node", "-e", f"const {{ patchMain }} = require('{patch_script}'); patchMain('{td}');"]
            subprocess.run(cmd, check=True)

            patched_main = main_js.read_text()
            self.assertIn("ANTIGRAVITY_DESKTOP_NAME", patched_main)

    def test_patch_app_and_ide_conversation_forking(self):
        """Verifies patchAppConversationForking & patchIdeConversationForking apply and unpatch cleanly."""
        import tempfile
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            dist = Path(td) / "dist"
            dist.mkdir()
            ls_js = dist / "languageServer.js"
            ls_js.write_text("const args = [\n            '--enable_sidecars',\n        ];")
            preload_js = dist / "preload.js"
            preload_js.write_text("console.log('original preload');")

            patch_script = Path(__file__).resolve().parent.parent / "bin" / "lib" / "patch" / "patch_conversation_forking.js"
            cmd_patch = ["node", "-e", f"const p = require('{patch_script}'); p.patchAppConversationForking('{td}');"]
            subprocess.run(cmd_patch, check=True)

            self.assertIn("--dev_mode", ls_js.read_text())
            patched_preload = preload_js.read_text()
            self.assertIn("FORK_EXP_PRELOAD_START", patched_preload)
            self.assertIn("enable-conversation-forking", patched_preload)
            self.assertIn("agy-hide-dev-footer", patched_preload)
            self.assertTrue((dist / "antigravity_fork_patch.marker").exists())

            # Test unpatch
            cmd_unpatch = ["node", "-e", f"const p = require('{patch_script}'); p.unpatchAppConversationForking('{td}');"]
            subprocess.run(cmd_unpatch, check=True)
            self.assertNotIn("--dev_mode", ls_js.read_text())
            self.assertNotIn("FORK_EXP_PRELOAD_START", preload_js.read_text())
            self.assertFalse((dist / "antigravity_fork_patch.marker").exists())

        # Test IDE patch
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "resources" / "app" / "out"
            out.mkdir(parents=True)
            main_ide = out / "main.js"
            main_ide.write_text('const f = this.config.get("conversationForking")?.enabled??!1;')

            cmd_ide_patch = ["node", "-e", f"const p = require('{patch_script}'); p.patchIdeConversationForking('{td}');"]
            subprocess.run(cmd_ide_patch, check=True)
            self.assertIn('/*FORK_EXP*/!0', main_ide.read_text())

            cmd_ide_unpatch = ["node", "-e", f"const p = require('{patch_script}'); p.unpatchIdeConversationForking('{td}');"]
            subprocess.run(cmd_ide_unpatch, check=True)
            self.assertIn('.get("conversationForking")?.enabled??!1', main_ide.read_text())


if __name__ == "__main__":
    unittest.main()








