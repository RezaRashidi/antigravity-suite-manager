"""
Unit Tests for Project Mapping and Folder Grouping Management.
"""

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_SRC_DIR = str(Path(__file__).resolve().parent.parent / "src")
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from antigravity_suite.history.projects import (
    KNOWN_PROJECT_MAPPINGS,
    KNOWN_ROOTS,
    ensure_project_configs,
    get_project_id_for_workspace,
    normalize_workspace_uri,
)


class TestProjectMappingAndGrouping(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(str(self.temp_dir), ignore_errors=True)

    def test_normalize_subfolder_workspace_uris(self):
        """Verifies subfolders correctly normalize to their canonical project root."""
        fake_home = self.temp_dir
        alpha_base = (fake_home / "PhpstormProjects" / "project-alpha").as_uri()
        alpha_sub1 = (fake_home / "PhpstormProjects" / "project-alpha" / ".github" / "workflows").as_uri()
        alpha_sub2 = (fake_home / "PhpstormProjects" / "project-alpha" / "backend" / "src").as_uri()
        beta_base = (fake_home / "Music" / "project-beta").as_uri()
        beta_sub = (fake_home / "Music" / "project-beta" / "package" / "kernel" / "mac80211").as_uri()
        sample_base = (fake_home / "PhpstormProjects" / "sample-app").as_uri()
        sample_sub = json.dumps([(fake_home / "PhpstormProjects" / "sample-app" / "load-tests").as_uri()])
        cdn_base = (fake_home / "Downloads" / "cdn-worker").as_uri()
        cdn_sub = (fake_home / "Downloads" / "cdn-worker" / "workers").as_uri()

        test_cases = [
            (alpha_sub1, alpha_base),
            (alpha_sub2, alpha_base),
            (beta_sub, beta_base),
            (sample_sub, sample_base),
            (cdn_sub, cdn_base),
        ]
        for sub_path, expected_root in test_cases:
            self.assertEqual(normalize_workspace_uri(sub_path, user_home=fake_home), expected_root)

    def test_known_projects_resolve_to_registered_ids(self):
        """Verifies projects resolve to stable, deterministic IDs and subfolders match roots."""
        alpha_root = (self.temp_dir / "PhpstormProjects" / "project-alpha").as_uri()
        alpha_sub = (self.temp_dir / "PhpstormProjects" / "project-alpha" / ".github" / "workflows").as_uri()
        root_pid = get_project_id_for_workspace(alpha_root, user_home=self.temp_dir, create_missing=True)
        sub_pid = get_project_id_for_workspace(alpha_sub, user_home=self.temp_dir, create_missing=True)
        self.assertIsNotNone(root_pid)
        self.assertEqual(root_pid, sub_pid)

        beta_pid = get_project_id_for_workspace((self.temp_dir / "Music" / "project-beta").as_uri(), user_home=self.temp_dir, create_missing=True)
        self.assertIsNotNone(beta_pid)
        self.assertNotEqual(root_pid, beta_pid)

    def test_ensure_project_configs_creation(self):
        """Verifies missing project JSON definitions are properly created dynamically."""
        sample_uri = (self.temp_dir / "PhpstormProjects" / "sample-app").as_uri()
        cdn_uri = (self.temp_dir / "Downloads" / "cdn-worker").as_uri()
        test_workspaces = [sample_uri, cdn_uri]
        ensure_project_configs(user_home=self.temp_dir, workspace_uris=test_workspaces)
        projects_dir = self.temp_dir / ".gemini" / "config" / "projects"
        self.assertTrue(projects_dir.is_dir())

        created_files = list(projects_dir.glob("*.json"))
        self.assertEqual(len(created_files), 2)

        sample_pid = get_project_id_for_workspace(sample_uri, user_home=self.temp_dir)
        sample_file = projects_dir / f"{sample_pid}.json"
        self.assertTrue(sample_file.is_file())
        with open(sample_file, "r", encoding="utf-8") as f:
            sample_data = json.load(f)
        self.assertEqual(sample_data["name"], "sample-app")
        self.assertEqual(sample_data["id"], sample_pid)
        self.assertEqual(
            sample_data["projectResources"]["resources"][0]["gitFolder"]["folderUri"],
            sample_uri,
        )

    def test_dynamic_project_discovery(self):
        """Verifies new project JSONs in ~/.gemini/config/projects are dynamically resolved."""
        projects_dir = self.temp_dir / ".gemini" / "config" / "projects"
        projects_dir.mkdir(parents=True)

        custom_pid = "d8e7f6a5-b4c3-2109-8765-fedcba987654"
        custom_uri = (self.temp_dir / "custom" / "project").as_uri()
        custom_def = {
            "id": custom_pid,
            "name": "custom-project",
            "projectResources": {
                "resources": [{"folderUri": custom_uri}]
            },
        }
        with open(projects_dir / f"{custom_pid}.json", "w", encoding="utf-8") as f:
            json.dump(custom_def, f)

        resolved_pid = get_project_id_for_workspace(custom_uri, user_home=self.temp_dir)
        self.assertEqual(resolved_pid, custom_pid)

    def test_generic_container_heuristic_any_user_machine(self):
        """Verifies root normalization works for arbitrary users and container directories without hardcoding."""
        cases = [
            (
                "file:///Users/developer/repos/distributed-service/internal/handler/auth",
                "file:///Users/developer/repos/distributed-service",
            ),
            (
                "file:///home/ubuntu/workspace/cloud-api/src/controllers",
                "file:///home/ubuntu/workspace/cloud-api",
            ),
            (
                "file:///home/dev/projects/ai-bot/tests/integration",
                "file:///home/dev/projects/ai-bot",
            ),
            (
                "file:///home/dev/Desktop/quick-script/data",
                "file:///home/dev/Desktop/quick-script",
            ),
            (
                "file:///home/dev/code/web-portal",
                "file:///home/dev/code/web-portal",
            ),
            (
                (self.temp_dir / "code" / "web-portal" / "src" / "pkg").as_uri(),
                (self.temp_dir / "code" / "web-portal").as_uri(),
            ),
            (
                "file:///var/log/syslog",
                "file:///var/log/syslog",
            ),
        ]
        for sub_path, expected_root in cases:
            self.assertEqual(normalize_workspace_uri(sub_path, user_home=self.temp_dir), expected_root)

    def test_git_repository_root_dynamic_detection(self):
        """Verifies local filesystem git repository roots are automatically detected."""
        repo_dir = self.temp_dir / "my-git-repo"
        git_dir = repo_dir / ".git"
        sub_dir = repo_dir / "src" / "pkg" / "module"
        sub_dir.mkdir(parents=True)
        git_dir.mkdir()

        sub_uri = f"file://{sub_dir}"
        expected_root = f"file://{repo_dir}"
        self.assertEqual(normalize_workspace_uri(sub_uri, user_home=self.temp_dir), expected_root)


if __name__ == "__main__":
    unittest.main()
