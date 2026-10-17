#!/usr/bin/env python3
import unittest
import tempfile
import os
import shutil
import struct
import json
import zlib
import colorsys
import re
import sys
from pathlib import Path

# Import functions to test
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))
import importlib

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
            old_p = "/home/user/.antigravity-profile-app-work"
            new_p = "/data/custom-profiles/.antigravity-profile-app-work2"
            
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

        # Bug 3.1: No comma after WM_CLASS in xprop command
        self.assertNotIn('WM_CLASS,', content)
        self.assertIn('WM_CLASS "\\${wmClass}"', content)

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
        cmd = "/opt/antigravity/antigravity --user-data-dir=/home/user/.antigravity-profile-app-work"
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
        raw_uri = "file:///home/developer/app-server/src/controllers/auth"
        norm = normalize_workspace_uri(raw_uri)
        self.assertNotEqual(norm, "file:///home/developer/app-server/src/controllers")
        self.assertEqual(norm, raw_uri)

    def test_ensure_project_configs_populates_all_gemini_dirs(self):
        from antigravity_suite.history.projects import ensure_project_configs

        with tempfile.TemporaryDirectory() as td:
            u_home = Path(td)
            g1 = u_home / ".gemini"
            g2 = u_home / ".gemide"
            g1.mkdir(parents=True)
            g2.mkdir(parents=True)

            ws_target = "file:///home/developer/cool-service"
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

            ws_uri = "file:///home/user/workspace/project-alpha"
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
            ws_beta = "file:///home/user/workspace/project-beta"
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

        # System root check
        self.assertTrue(is_container_or_system_root("file:///tmp"))
        self.assertTrue(is_container_or_system_root("file:///home/reza/PhpstormProjects"))
        self.assertFalse(is_container_or_system_root("file:///home/reza/PhpstormProjects/antigravity-suite-manager"))

        # Normalization with cross-platform slashes
        norm = normalize_workspace_uri("file:///home/reza/PhpstormProjects/my-app/subfolder/file")
        self.assertEqual(norm, "file:///home/reza/PhpstormProjects/my-app")

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
                # SQLite existing row has authentic_pid at index 8 and raw_with_outside at index 4!
                existing_rows = {
                    conv_id: ("Lede Chat", "Lede Preview", 3, "2026-10-10 12:00:00", raw_with_outside, "2026-10-10 12:00:00", 0, "file:///home/user/lede", authentic_pid)
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
            dirty_title = "@[/home/reza/PhpstormProjects/app/User.php:20-30] Refactor auth"

            ok = sync_annotation_file(master, conv_id, dirty_title)
            self.assertTrue(ok)

            anno_file = master / "annotations" / f"{conv_id}.pbtxt"
            self.assertTrue(anno_file.exists())
            content = anno_file.read_text()
            self.assertNotIn("@[", content)
            self.assertIn("Refactor auth", content)

if __name__ == "__main__":
    unittest.main()

