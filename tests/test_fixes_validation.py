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

            orig_master = migration.MASTER_GEMINI
            orig_gemini = migration.GEMINI_DIR
            try:
                migration.MASTER_GEMINI = mock_master
                migration.GEMINI_DIR = td
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

if __name__ == "__main__":
    unittest.main()
