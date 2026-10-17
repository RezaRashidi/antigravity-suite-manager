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
        test_cases = [
            (
                "file:///home/reza/PhpstormProjects/Odirect/.github/workflows",
                "file:///home/reza/PhpstormProjects/Odirect",
            ),
            (
                "file:///home/reza/PhpstormProjects/Odirect/instasi-backend/src",
                "file:///home/reza/PhpstormProjects/Odirect",
            ),
            (
                "file:///home/reza/Music/lede/package/kernel/mac80211",
                "file:///home/reza/Music/lede",
            ),
            (
                '["file:///home/reza/PhpstormProjects/k6/load-tests"]',
                "file:///home/reza/PhpstormProjects/k6",
            ),
            (
                "file:///home/reza/Downloads/cloudflare/workers",
                "file:///home/reza/Downloads/cloudflare",
            ),
        ]
        for sub_path, expected_root in test_cases:
            self.assertEqual(normalize_workspace_uri(sub_path), expected_root)

    def test_known_projects_resolve_to_registered_ids(self):
        """Verifies all registered workspace roots resolve to authentic project IDs."""
        self.assertEqual(
            get_project_id_for_workspace("file:///home/reza/PhpstormProjects/Odirect"),
            "7bc454c1-6ec0-4ab3-b5eb-09fb9887e76f",
        )
        self.assertEqual(
            get_project_id_for_workspace("file:///home/reza/Music/lede"),
            "247e98f3-52b3-41c9-aebb-1732fb2b7070",
        )
        self.assertEqual(
            get_project_id_for_workspace("file:///home/reza/Library/nokia_modem"),
            "1c547948-02a7-481b-b9f6-1218b789cbde",
        )
        self.assertEqual(
            get_project_id_for_workspace("file:///home/reza/Music/irankhodro"),
            "23773526-c9f9-4e44-b037-c47941ed0160",
        )
        self.assertEqual(
            get_project_id_for_workspace("file:///home/reza/PhpstormProjects/api"),
            "3ee949ba-1b1a-4941-a05a-282d79f5636b",
        )

    def test_ensure_project_configs_creation(self):
        """Verifies missing project JSON definitions are properly created."""
        ensure_project_configs(user_home=self.temp_dir)
        projects_dir = self.temp_dir / ".gemini" / "config" / "projects"
        self.assertTrue(projects_dir.is_dir())

        created_files = list(projects_dir.glob("*.json"))
        self.assertGreaterEqual(len(created_files), 6)

        k6_file = projects_dir / "9e1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8.json"
        self.assertTrue(k6_file.is_file())
        with open(k6_file, "r", encoding="utf-8") as f:
            k6_data = json.load(f)
        self.assertEqual(k6_data["name"], "k6")
        self.assertEqual(k6_data["id"], "9e1a2b3c-4d5e-6f70-8192-a3b4c5d6e7f8")

    def test_dynamic_project_discovery(self):
        """Verifies new project JSONs in ~/.gemini/config/projects are dynamically resolved."""
        projects_dir = self.temp_dir / ".gemini" / "config" / "projects"
        projects_dir.mkdir(parents=True)

        custom_pid = "d8e7f6a5-b4c3-2109-8765-fedcba987654"
        custom_uri = "file:///home/reza/custom/project"
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


if __name__ == "__main__":
    unittest.main()
