import os
import subprocess
import unittest

REPO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MANAGE_SH = os.path.join(REPO_DIR, "bin", "manage-antigravity.sh")
INSTALL_SH = os.path.join(REPO_DIR, "install.sh")


class TestRepoUpdateAndServices(unittest.TestCase):
    def test_cli_help_includes_new_commands(self):
        res = subprocess.run([MANAGE_SH, "help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("update-repo", res.stdout)
        self.assertIn("restart-services", res.stdout)

    def test_install_cli_help_includes_flags(self):
        res = subprocess.run([INSTALL_SH, "--help"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertIn("--update-repo", res.stdout)
        self.assertIn("--restart-services", res.stdout)

    def test_find_suite_repo_root(self):
        cmd = f"source {REPO_DIR}/bin/lib/sh/env.sh && source {REPO_DIR}/bin/lib/sh/repo_update.sh && find_suite_repo_root"
        res = subprocess.run(["bash", "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0)
        self.assertTrue(os.path.isdir(res.stdout.strip()))
        self.assertTrue(os.path.isdir(os.path.join(res.stdout.strip(), ".git")))

    def test_restart_services_execution(self):
        res = subprocess.run([MANAGE_SH, "restart-services"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0)
        output = res.stdout + res.stderr
        self.assertIn("Restarting Antigravity Suite background services", output)
        self.assertIn("All Antigravity Suite background services restarted", output)


if __name__ == "__main__":
    unittest.main()
